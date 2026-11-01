#!/usr/bin/env python3
"""Smoke test for a *running* POS-MOBILE backend.

Usage:
    python3 scripts/smoke_test.py --base-url http://localhost:8000

Runs the checks in order and prints PASS / FAIL / WARN per check.
Exit code is non-zero if any check FAILs (WARN does not fail the run unless
--strict is given).

WARNING: the restore check replaces the current store's data with the backup
it just downloaded. Run it against a throwaway database, not a real shop.
"""

from __future__ import annotations

import argparse
import sys
import time
import uuid
from decimal import Decimal

import httpx

API = "/api/v1"

EXPECTED_TAGS = {
    "Auth", "Products", "Sales", "Purchases", "Debts", "Expenses",
    "Sync/Backup",
}


class Smoke:
    def __init__(self, base_url: str, username: str | None, password: str | None, strict: bool):
        self.c = httpx.Client(base_url=base_url.rstrip("/"), timeout=15.0)
        self.username = username
        self.password = password
        self.strict = strict
        self.results: list[tuple[str, str, str]] = []
        self.run_id = uuid.uuid4().hex[:6].upper()
        self.ctx: dict = {}

    # ── helpers ───────────────────────────────────────────
    def record(self, name: str, status: str, reason: str) -> None:
        self.results.append((name, status, reason))
        print(f"[{status}] {name} — {reason}", flush=True)

    def check(self, name: str, fn) -> None:
        try:
            out = fn()
        except AssertionError as exc:
            self.record(name, "FAIL", str(exc) or "assertion failed")
            return
        except httpx.HTTPError as exc:
            self.record(name, "FAIL", f"HTTP error: {exc!r}")
            return
        except Exception as exc:  # noqa: BLE001 - smoke test reports everything
            self.record(name, "FAIL", f"{type(exc).__name__}: {exc}")
            return
        if isinstance(out, tuple):
            status, reason = out
        else:
            status, reason = "PASS", out or "ok"
        self.record(name, status, reason)

    @staticmethod
    def expect(resp: httpx.Response, *codes: int) -> dict | list | None:
        assert resp.status_code in codes, (
            f"{resp.request.method} {resp.request.url.path} -> {resp.status_code} "
            f"(expected {codes}): {resp.text[:300]}"
        )
        if resp.content and resp.headers.get("content-type", "").startswith("application/json"):
            return resp.json()
        return None

    def get_product(self, pid: int) -> dict:
        return self.expect(self.c.get(f"{API}/products/{pid}"), 200)

    # ── checks ────────────────────────────────────────────
    def docs(self):
        r = self.c.get("/docs")
        self.expect(r, 200)
        assert "swagger" in r.text.lower(), "/docs does not look like Swagger UI"
        spec = self.expect(self.c.get("/openapi.json"), 200)
        paths = spec.get("paths", {})
        tags = {t for p in paths.values() for op in p.values() if isinstance(op, dict) for t in op.get("tags", [])}
        missing = EXPECTED_TAGS - tags
        assert not missing, f"openapi.json missing routers/tags: {sorted(missing)}"
        for p in (f"{API}/products", f"{API}/sales", f"{API}/purchases", f"{API}/sync", f"{API}/sync/backup", f"{API}/sync/restore"):
            assert p in paths, f"openapi.json missing path {p}"
        return f"/docs 200, openapi: {len(paths)} paths, tags={sorted(tags)}"

    def health(self):
        g = self.c.get(f"{API}/sync/health")
        self.expect(g, 200)
        assert g.json().get("status") == "healthy", f"unexpected body {g.text}"
        h = self.c.head(f"{API}/sync/health")
        assert h.status_code == 200, f"HEAD -> {h.status_code}"
        return "GET 200 status=healthy, HEAD 200"

    def auth(self):
        r = self.c.get(f"{API}/products", params={"page_size": 1})
        if r.status_code == 200:
            return "AUTH_ENABLED=false (dev mode): API usable without token"
        if r.status_code != 401:
            raise AssertionError(f"GET /products without auth -> {r.status_code}: {r.text[:300]}")
        user = self.username or f"smoke{self.run_id.lower()}"
        pw = self.password or "smoke-pass-1234"
        if not self.username:
            reg = self.c.post(f"{API}/auth/register", json={
                "email": f"{user}@example.com", "username": user, "password": pw, "role": "admin",
            })
            assert reg.status_code in (201, 400, 403), f"register -> {reg.status_code}: {reg.text[:200]}"
            if reg.status_code == 403:
                raise AssertionError("auth is on and registration is closed: pass --username/--password")
        tok = self.expect(self.c.post(f"{API}/auth/login", json={"username": user, "password": pw}), 200)
        self.c.headers["Authorization"] = f"Bearer {tok['access_token']}"
        self.expect(self.c.get(f"{API}/products", params={"page_size": 1}), 200)
        return f"AUTH_ENABLED=true: logged in as {user}, bearer token accepted"

    def products(self):
        code = f"SMK{self.run_id}"
        body = {
            "code": code, "barcode": f"885{self.run_id}01", "name": "Smoke น้ำดื่ม",
            "category": "SMOKE", "price": 15, "cost": 9, "stock": 10, "min_stock": 2,
        }
        p = self.expect(self.c.post(f"{API}/products", json=body), 201)
        got = self.get_product(p["id"])
        assert got["code"] == code and got["stock"] == 10, f"GET returned {got}"
        by_code = self.expect(self.c.get(f"{API}/products/code/{code}"), 200)
        assert by_code["id"] == p["id"], "lookup by code returned another product"
        dup = self.c.post(f"{API}/products", json=body)
        assert dup.status_code == 400, f"duplicate code should be 400, got {dup.status_code}"
        self.ctx["product"] = got
        return f"created id={p['id']} code={code} stock=10, GET by id/code ok, duplicate -> 400"

    def _sale_body(self, qty: int, discount: float = 0) -> dict:
        p = self.ctx["product"]
        return {
            "payment_method": "cash", "paid_amount": 1000, "discount": discount,
            "items": [{
                "product_id": p["id"], "product_code": p["code"], "product_name": p["name"],
                "quantity": qty, "unit_price": float(p["price"]),
            }],
        }

    def sales(self):
        p = self.ctx["product"]
        before = self.get_product(p["id"])["stock"]
        s1 = self.expect(self.c.post(f"{API}/sales", json=self._sale_body(3, discount=5)), 201)
        after = self.get_product(p["id"])["stock"]
        assert after == before - 3, f"stock {before} -> {after}, expected {before - 3}"

        sub, disc, vat, tot = (Decimal(str(s1[k])) for k in ("subtotal", "discount", "vat", "total"))
        exp_sub = Decimal(str(p["price"])) * 3
        assert sub == exp_sub, f"subtotal {sub} != price*qty {exp_sub}"
        assert disc == Decimal("5"), f"discount {disc} != 5"
        # vat mode no/exclude: total = sub - disc + vat ; include: total = sub - disc
        assert tot in (sub - disc + vat, sub - disc), f"total {tot} inconsistent with {sub}-{disc}+{vat}"
        assert Decimal(str(s1["change_amount"])) == Decimal("1000") - tot, f"change {s1['change_amount']} wrong"

        over = self.c.post(f"{API}/sales", json=self._sale_body(after + 1))
        assert 400 <= over.status_code < 500, f"oversell -> {over.status_code}, expected 4xx"
        still = self.get_product(p["id"])["stock"]
        assert still == after, f"rejected sale changed stock {after} -> {still}"

        s2 = self.expect(self.c.post(f"{API}/sales", json=self._sale_body(1)), 201)
        assert s1["bill_no"] != s2["bill_no"], f"duplicate bill_no {s1['bill_no']}"
        got = self.expect(self.c.get(f"{API}/sales/bill/{s1['bill_no']}"), 200)
        assert got["id"] == s1["id"], "GET by bill_no returned another sale"
        self.ctx["bills"] = [s1["bill_no"], s2["bill_no"]]
        return (f"stock {before}->{after} (-3); sub={sub} disc={disc} vat={vat} total={tot}; "
                f"oversell {after + 1} -> {over.status_code}; bills {s1['bill_no']} != {s2['bill_no']}")

    def purchases(self):
        p = self.ctx["product"]
        before = self.get_product(p["id"])["stock"]
        po = self.expect(self.c.post(f"{API}/purchases", json={
            "supplier_name": "Smoke Supplier",
            "items": [{
                "product_id": p["id"], "product_code": p["code"], "product_name": p["name"],
                "quantity": 12, "unit_cost": 9,
            }],
        }), 201)
        assert po["status"] == "pending", f"new PO status {po['status']}"
        assert Decimal(str(po["total"])) == Decimal("108"), f"PO total {po['total']} != 12*9=108"
        mid = self.get_product(p["id"])["stock"]
        assert mid == before, f"creating PO changed stock {before}->{mid}"
        item_id = po["items"][0]["id"]
        rec = self.expect(self.c.post(f"{API}/purchases/{po['id']}/receive",
                                      json=[{"item_id": item_id, "received_qty": 12}]), 200)
        after = self.get_product(p["id"])["stock"]
        assert after == before + 12, f"stock {before}->{after}, expected +12"
        assert rec["status"] == "received", f"PO status after full receive = {rec['status']}"
        return f"PO {po['po_no']} total=108, receive 12 -> stock {before}->{after}, status=received"

    # Frontend shape: exactly what exportBackupJSON() in script-pos.js produces
    def _frontend_payload(self) -> dict:
        rid = self.run_id
        prod_id = f"fe{rid.lower()}"
        return {
            "products": [{
                "id": prod_id, "product_id": f"01FE{rid}", "barcode": f"886{rid}", "name": "FE ข้าวกล่อง",
                "category": "แซนวิชเย็น", "type": "", "price": 45, "cost": 30, "stock": 7,
                "minStock": 5, "expiry": "2026-12-31", "createdAt": int(time.time() * 1000),
            }],
            "sales": [{
                "id": "s1", "billNo": "B00001", "date": "2026-10-30T10:00:00.000Z",
                "items": [{"productId": prod_id, "name": "FE ข้าวกล่อง", "qty": 2, "price": 45, "subtotal": 90, "cost": 30}],
                "subtotal": 90, "discount": 0, "vat": 0, "total": 90, "received": 100, "change": 10,
                "payType": "เงินสด", "note": "",
            }],
            "purchases": [{
                "id": "p1", "date": "2026-10-30", "supplier": "FE Supplier",
                "items": [{"productId": prod_id, "name": "FE ข้าวกล่อง", "product_id": f"01FE{rid}",
                           "barcode": f"886{rid}", "qty": 5, "price": 30, "total": 150}],
                "createdAt": int(time.time() * 1000),
            }],
            "debts": [{
                "id": "d1", "customer": "FE ลูกค้า", "phone": "0800000000", "billNo": "B00001", "billId": "s1",
                "amount": 90, "paid": 0, "date": "2026-10-30", "note": "", "status": "ค้าง", "payments": [],
            }],
            "expenses": [{"id": "e1", "name": "ค่าไฟ", "amount": 500, "date": "2026-10-30", "note": "",
                          "createdAt": int(time.time() * 1000)}],
            "settings": {"storeName": "Quick POS", "storeAddr": "", "storePhone": "", "taxId": "",
                         "lowStock": 5, "expiryDays": 30, "vat": "no"},
            "holdBills": [{"id": "h1", "name": "บิล 1", "cart": [], "time": "2026-10-30T10:00:00.000Z"}],
            "billCounter": 2,
            "categoryMapping": [{"prefix": "01", "name": "แซนวิชเย็น", "locked": True}],
            "exportedAt": "2026-10-30T10:00:00.000Z",
            "version": 1,
        }

    def sync_frontend_shape(self):
        payload = self._frontend_payload()
        r = self.c.post(f"{API}/sync", json=payload)
        if r.status_code == 200:
            counts = r.json().get("counts", {})
            expected = {"products", "sales", "purchases", "debts", "expenses", "settings", "hold_bills"}
            dropped = sorted(expected - set(counts))
            if dropped:
                return ("WARN", f"200 but silently ignored: {dropped} (counts={counts})")
            return f"frontend payload accepted: {counts}"
        assert r.status_code == 422, f"POST /sync frontend shape -> {r.status_code}: {r.text[:300]}"
        errs = r.json().get("detail", [])
        summary = sorted({".".join(str(x) for x in e.get("loc", [])[1:] if not isinstance(x, int)) + ":" + e.get("type", "")
                          for e in errs})
        ignored = ["holdBills", "billCounter", "categoryMapping", "exportedAt", "version"]
        return ("WARN", f"frontend export shape REJECTED 422 ({len(errs)} errors): {summary}; "
                        f"keys silently ignored by schema: {ignored}")

    def sync_backend_shape(self):
        # Same data as the frontend export, mapped by hand to the backend SyncRequest schema.
        rid = self.run_id
        code = f"01FE{rid}"
        payload = {
            "products": [{"code": code, "barcode": f"886{rid}", "name": "FE ข้าวกล่อง", "category": "แซนวิชเย็น",
                          "price": 45, "cost": 30, "stock": 7, "min_stock": 5, "expiry_date": "2026-12-31T00:00:00"}],
            "debts": [{"customer_name": "FE ลูกค้า", "customer_phone": "0800000000", "total_debt": 90}],
            "expenses": [{"category": "ทั่วไป", "description": "ค่าไฟ", "amount": 500, "date": "2026-10-30T00:00:00"}],
            "settings": [{"key": "storeName", "value": "Quick POS"}, {"key": "vat", "value": "no"}],
            "hold_bills": [{"items": "[]", "subtotal": 0, "total": 0}],
            "category_mappings": [{"code_prefix": "01", "category": "แซนวิชเย็น"}],
        }
        r = self.expect(self.c.post(f"{API}/sync", json=payload), 200)
        p = self.expect(self.c.get(f"{API}/products/code/{code}"), 200)
        # sale referencing the synced product (needs its backend id)
        r2 = self.expect(self.c.post(f"{API}/sync", json={"sales": [{
            "payment_method": "cash", "paid_amount": 100,
            "items": [{"product_id": p["id"], "product_code": code, "product_name": p["name"], "quantity": 2, "unit_price": 45}],
        }]}), 200)
        p2 = self.expect(self.c.get(f"{API}/products/code/{code}"), 200)
        assert p2["stock"] == 7, f"synced sale must not deduct stock again: {p['stock']} -> {p2['stock']}"
        return f"mapped payload ok counts={r['counts']}, sale counts={r2['counts']}, stock unchanged=7"

    def backup_restore(self):
        r = self.c.get(f"{API}/sync/backup")
        backup = self.expect(r, 200)
        assert "data" in backup and "timestamp" in backup, f"unexpected backup keys {list(backup)}"
        data = backup["data"]
        before = {k: len(v) for k, v in data.items()}
        stock_before = {p["code"]: p["stock"] for p in data["products"]}
        bills_before = sorted(s["bill_no"] for s in data["sales"])
        for b in self.ctx.get("bills", []):
            assert b in bills_before, f"bill {b} missing from backup"

        # restore exactly the file that /sync/backup returned
        rr = self.expect(self.c.post(f"{API}/sync/restore", json=backup), 200)
        assert rr.get("success") is True, f"restore not successful: {rr}"

        after_data = self.expect(self.c.get(f"{API}/sync/backup"), 200)["data"]
        after = {k: len(v) for k, v in after_data.items()}
        problems = []
        if after != before:
            problems.append(f"counts {before} -> {after}")
        stock_after = {p["code"]: p["stock"] for p in after_data["products"]}
        if stock_after != stock_before:
            diff = {k: (stock_before.get(k), stock_after.get(k)) for k in set(stock_before) | set(stock_after)
                    if stock_before.get(k) != stock_after.get(k)}
            problems.append(f"stock changed {diff}")
        bills_after = sorted(s["bill_no"] for s in after_data["sales"])
        if bills_after != bills_before:
            problems.append(f"bill numbers changed ({len(set(bills_before) - set(bills_after))} lost)")
        # purchase items must still point at existing products
        pids = {p["code"] for p in after_data["products"]}
        prod_ids_live = {self.expect(self.c.get(f"{API}/products/code/{c}"), 200)["id"] for c in pids}
        for po in after_data["purchases"]:
            for it in po["items"]:
                if it["product_id"] not in prod_ids_live:
                    problems.append(f"PO item {it['product_code']} points at stale product_id {it['product_id']}")
                    break
        assert not problems, "; ".join(problems)
        return f"backup {r.headers.get('content-length', '?')}B, restore ok, counts={after}, stock+bill_no preserved"

    # ── runner ────────────────────────────────────────────
    def run(self) -> int:
        print(f"POS-MOBILE smoke test against {self.c.base_url} (run {self.run_id})")
        self.check("docs + openapi", self.docs)
        self.check("sync health GET/HEAD", self.health)
        self.check("auth", self.auth)
        self.check("products create/get", self.products)
        if "product" in self.ctx:
            self.check("sales: stock, totals, oversell, bill_no", self.sales)
            self.check("purchases create + receive", self.purchases)
        else:
            self.record("sales/purchases", "FAIL", "skipped: product check failed")
        self.check("sync: frontend export shape", self.sync_frontend_shape)
        self.check("sync: backend schema shape", self.sync_backend_shape)
        self.check("backup -> restore round trip", self.backup_restore)

        fails = [r for r in self.results if r[1] == "FAIL"]
        warns = [r for r in self.results if r[1] == "WARN"]
        print(f"\n{len(self.results) - len(fails) - len(warns)} passed, {len(warns)} warnings, {len(fails)} failed")
        if fails or (self.strict and warns):
            return 1
        return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--username", help="existing user (only needed when AUTH_ENABLED=true)")
    ap.add_argument("--password")
    ap.add_argument("--strict", action="store_true", help="treat WARN (known frontend/backend gaps) as failures")
    args = ap.parse_args()
    try:
        return Smoke(args.base_url, args.username, args.password, args.strict).run()
    except httpx.ConnectError as exc:
        print(f"[FAIL] connect — cannot reach {args.base_url}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
