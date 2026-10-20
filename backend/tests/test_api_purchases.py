"""Tests for Purchases API."""
import pytest
from decimal import Decimal
from httpx import AsyncClient


class TestPurchasesAPI:
    """Test Purchases API endpoints."""

    @pytest.mark.asyncio
    async def test_create_purchase(self, client: AsyncClient):
        """Test POST /api/v1/purchases."""
        prod_resp = await client.post("/api/v1/products", json={
            "code": "PURAPI001",
            "name": "Purchase Product",
            "price": "150.00",
            "cost": "80.00",
            "stock": 10,
        })
        product = prod_resp.json()

        purchase_data = {
            "supplier_name": "API Supplier",
            "supplier_phone": "0898765432",
            "status": "pending",
            "notes": "API test purchase",
            "items": [
                {
                    "product_id": product["id"],
                    "product_code": product["code"],
                    "product_name": product["name"],
                    "unit": "ชิ้น",
                    "quantity": 5,
                    "unit_cost": "80.00",
                    "line_total": "400.00",
                }
            ],
        }

        response = await client.post("/api/v1/purchases", json=purchase_data)

        assert response.status_code == 201
        data = response.json()
        assert data["po_no"].startswith("PO-")
        assert data["supplier_name"] == "API Supplier"
        assert data["status"] == "pending"
        assert data["total"] == "400.00"

    @pytest.mark.asyncio
    async def test_receive_purchase(self, client: AsyncClient):
        """Test POST /api/v1/purchases/{id}/receive."""
        prod_resp = await client.post("/api/v1/products", json={
            "code": "PURAPI002",
            "name": "Receive Product",
            "price": "200.00",
            "cost": "100.00",
            "stock": 5,
        })
        product = prod_resp.json()

        # Create purchase
        pur_resp = await client.post("/api/v1/purchases", json={
            "supplier_name": "Receive Supplier",
            "items": [{
                "product_id": product["id"],
                "product_code": product["code"],
                "product_name": product["name"],
                "unit": "ชิ้น",
                "quantity": 10,
                "unit_cost": "100.00",
                "line_total": "1000.00",
            }],
        })
        purchase = pur_resp.json()

        # Receive it
        response = await client.post(f"/api/v1/purchases/{purchase['id']}/receive")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "received"
        assert data["received_date"] is not None

        # Check stock increased
        get_resp = await client.get(f"/api/v1/products/{product['id']}")
        assert get_resp.json()["stock"] == 15  # 5 + 10

    @pytest.mark.asyncio
    async def test_get_purchase(self, client: AsyncClient):
        """Test GET /api/v1/purchases/{id}."""
        prod_resp = await client.post("/api/v1/products", json={
            "code": "PURAPI003",
            "name": "Get Purchase Product",
            "price": "100.00",
        })
        product = prod_resp.json()

        pur_resp = await client.post("/api/v1/purchases", json={
            "items": [{
                "product_id": product["id"],
                "product_code": product["code"],
                "product_name": product["name"],
                "unit": "ชิ้น",
                "quantity": 3,
                "unit_cost": "50.00",
                "line_total": "150.00",
            }],
        })
        purchase = pur_resp.json()

        response = await client.get(f"/api/v1/purchases/{purchase['id']}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == purchase["id"]
        assert len(data["items"]) == 1

    @pytest.mark.asyncio
    async def test_get_purchase_by_po_no(self, client: AsyncClient):
        """Test GET /api/v1/purchases/po/{po_no}."""
        prod_resp = await client.post("/api/v1/products", json={
            "code": "PURAPI004",
            "name": "PO Number Product",
            "price": "100.00",
        })
        product = prod_resp.json()

        pur_resp = await client.post("/api/v1/purchases", json={
            "items": [{
                "product_id": product["id"],
                "product_code": product["code"],
                "product_name": product["name"],
                "unit": "ชิ้น",
                "quantity": 1,
                "unit_cost": "50.00",
                "line_total": "50.00",
            }],
        })
        purchase = pur_resp.json()

        response = await client.get(f"/api/v1/purchases/po/{purchase['po_no']}")

        assert response.status_code == 200
        data = response.json()
        assert data["po_no"] == purchase["po_no"]

    @pytest.mark.asyncio
    async def test_list_purchases(self, client: AsyncClient):
        """Test GET /api/v1/purchases with pagination."""
        prod_resp = await client.post("/api/v1/products", json={
            "code": "PURAPI005",
            "name": "List Purchase Product",
            "price": "100.00",
            "stock": 20,
        })
        product = prod_resp.json()

        for i in range(3):
            await client.post("/api/v1/purchases", json={
                "supplier_name": f"Supplier {i}",
                "items": [{
                    "product_id": product["id"],
                    "product_code": product["code"],
                    "product_name": product["name"],
                    "unit": "ชิ้น",
                    "quantity": 1,
                    "unit_cost": "50.00",
                    "line_total": "50.00",
                }],
            })

        response = await client.get("/api/v1/purchases?page=1&page_size=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 3

    @pytest.mark.asyncio
    async def test_update_purchase(self, client: AsyncClient):
        """Test PUT /api/v1/purchases/{id}."""
        prod_resp = await client.post("/api/v1/products", json={
            "code": "PURAPI006",
            "name": "Update Purchase Product",
            "price": "100.00",
        })
        product = prod_resp.json()

        pur_resp = await client.post("/api/v1/purchases", json={
            "supplier_name": "Original Supplier",
            "items": [{
                "product_id": product["id"],
                "product_code": product["code"],
                "product_name": product["name"],
                "unit": "ชิ้น",
                "quantity": 1,
                "unit_cost": "50.00",
                "line_total": "50.00",
            }],
        })
        purchase = pur_resp.json()

        response = await client.put(f"/api/v1/purchases/{purchase['id']}", json={
            "supplier_name": "Updated Supplier",
            "notes": "Updated notes",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["supplier_name"] == "Updated Supplier"
        assert data["notes"] == "Updated notes"