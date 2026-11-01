"""Regression tests for bugs found by scripts/smoke_test.py against a real server."""

from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine

import app.database as database
from app.models import Store


@pytest.mark.asyncio
async def test_init_db_seeds_default_store(monkeypatch):
    """Fresh DB started via `python run.py` (no alembic) must still be usable:
    dev user is bound to store_id=1, so init_db must create that store."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    monkeypatch.setattr(database, "engine", engine)
    try:
        await database.init_db()
        await database.init_db()  # idempotent: second start must not duplicate/crash
        async with engine.connect() as conn:
            count = await conn.scalar(select(func.count()).select_from(Store))
            store = (await conn.execute(select(Store.id, Store.is_active, Store.is_default))).one()
        assert count == 1
        assert store.id == 1 and store.is_active and store.is_default
    finally:
        await engine.dispose()


async def _make_product(client: AsyncClient, code: str, stock: int = 10) -> dict:
    r = await client.post("/api/v1/products", json={
        "code": code, "name": f"P {code}", "price": 15, "cost": 9, "stock": stock,
    })
    assert r.status_code == 201, r.text
    return r.json()


@pytest.mark.asyncio
async def test_purchase_total_matches_items_when_line_total_omitted(client: AsyncClient):
    """PO header total must equal the sum of the item line totals the server computes
    (unit_cost * quantity) — not the optional client-sent line_total (default 0)."""
    p = await _make_product(client, "POTOTAL01")
    r = await client.post("/api/v1/purchases", json={"items": [{
        "product_id": p["id"], "product_code": p["code"], "product_name": p["name"],
        "quantity": 12, "unit_cost": 9,
    }]})
    assert r.status_code == 201, r.text
    po = r.json()
    assert Decimal(po["items"][0]["line_total"]) == Decimal("108")
    assert Decimal(po["total"]) == Decimal("108")


@pytest.mark.asyncio
async def test_restore_accepts_file_downloaded_from_backup(client: AsyncClient):
    """POST /sync/restore with exactly what GET /sync/backup returned
    ({timestamp, version, data:{...}}) must restore the data, not wipe the store."""
    await _make_product(client, "RTRIP01", stock=7)
    backup = (await client.get("/api/v1/sync/backup")).json()
    assert len(backup["data"]["products"]) == 1

    r = await client.post("/api/v1/sync/restore", json=backup)
    assert r.status_code == 200, r.text
    assert r.json()["counts"].get("products") == 1

    p = await client.get("/api/v1/products/code/RTRIP01")
    assert p.status_code == 200 and p.json()["stock"] == 7


@pytest.mark.asyncio
async def test_restore_rejects_payload_without_backup_sections(client: AsyncClient):
    """A payload with none of the backup sections (e.g. {} or a random JSON file)
    must be rejected with 400 and must not delete the store's data."""
    await _make_product(client, "KEEPME01")
    for bad in ({}, {"foo": 1}, {"timestamp": "x", "version": "1.0.0"}):
        r = await client.post("/api/v1/sync/restore", json=bad)
        assert r.status_code == 400, (bad, r.status_code, r.text)
    assert (await client.get("/api/v1/products/code/KEEPME01")).status_code == 200


async def _sell(client: AsyncClient, p: dict, qty: int = 1) -> dict:
    r = await client.post("/api/v1/sales", json={"payment_method": "cash", "paid_amount": 1000, "items": [{
        "product_id": p["id"], "product_code": p["code"], "product_name": p["name"],
        "quantity": qty, "unit_price": 15,
    }]})
    assert r.status_code == 201, r.text
    return r.json()


@pytest.mark.asyncio
async def test_restore_keeps_bill_numbers(client: AsyncClient):
    """Backup -> restore must keep each sale's bill_no (receipts/debts refer to it)."""
    p = await _make_product(client, "BILLKEEP01")
    bills = sorted([(await _sell(client, p))["bill_no"], (await _sell(client, p))["bill_no"]])
    backup = (await client.get("/api/v1/sync/backup")).json()

    r = await client.post("/api/v1/sync/restore", json=backup["data"])
    assert r.status_code == 200, r.text

    after = (await client.get("/api/v1/sync/backup")).json()["data"]
    assert sorted(s["bill_no"] for s in after["sales"]) == bills
    for b in bills:
        assert (await client.get(f"/api/v1/sales/bill/{b}")).status_code == 200


@pytest.mark.asyncio
async def test_sync_sale_with_taken_bill_no_gets_new_number(client: AsyncClient):
    """Syncing a sale whose bill_no already exists must not 500 on the unique index."""
    p = await _make_product(client, "BILLDUP01")
    taken = (await _sell(client, p))["bill_no"]
    r = await client.post("/api/v1/sync", json={"sales": [{
        "bill_no": taken, "payment_method": "cash", "paid_amount": 15,
        "items": [{"product_id": p["id"], "product_code": p["code"], "product_name": p["name"],
                   "quantity": 1, "unit_price": 15}],
    }]})
    assert r.status_code == 200, r.text
    sales = (await client.get("/api/v1/sales")).json()
    assert sales["total"] == 2
    assert len({s["bill_no"] for s in sales["items"]}) == 2


@pytest.mark.asyncio
async def test_restore_relinks_purchase_items_by_product_code(client: AsyncClient):
    """After restore products get new ids (recreated in code order); purchase items
    must be re-linked by product_code like sale items, not keep the stale id."""
    z = await _make_product(client, "ZZZ-PO")   # id 1, but sorts last in backup
    a = await _make_product(client, "AAA-PO")   # id 2, sorts first -> gets id 1 on restore
    r = await client.post("/api/v1/purchases", json={"items": [{
        "product_id": a["id"], "product_code": a["code"], "product_name": a["name"],
        "quantity": 3, "unit_cost": 9,
    }]})
    assert r.status_code == 201, r.text
    backup = (await client.get("/api/v1/sync/backup")).json()

    assert (await client.post("/api/v1/sync/restore", json=backup)).status_code == 200

    new_a = (await client.get("/api/v1/products/code/AAA-PO")).json()
    pos = (await client.get("/api/v1/purchases")).json()["items"]
    assert len(pos) == 1
    assert pos[0]["items"][0]["product_id"] == new_a["id"]
    assert new_a["id"] != a["id"] or z["id"] == a["id"]  # sanity: ids really were reshuffled
