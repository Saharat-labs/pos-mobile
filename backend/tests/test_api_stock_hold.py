"""Tests for Stock Movements and Hold Bills APIs."""
import pytest
from decimal import Decimal
from httpx import AsyncClient


class TestStockMovementsAPI:
    """Test Stock Movements API endpoints."""

    @pytest.mark.asyncio
    async def test_create_stock_movement(self, client: AsyncClient):
        """Test POST /api/v1/stock-movements."""
        # Create product first
        prod_resp = await client.post("/api/v1/products", json={
            "code": "STKMVT001",
            "name": "Stock Movement Product",
            "price": "100.00",
            "stock": 10,
        })
        product = prod_resp.json()

        movement_data = {
            "product_id": product["id"],
            "movement_type": "in",
            "quantity": 5,
            "reference_type": "purchase",
            "reference_id": 1,
            "notes": "Stock in from purchase",
        }

        response = await client.post("/api/v1/stock-movements", json=movement_data)

        assert response.status_code == 201
        data = response.json()
        assert data["product_id"] == product["id"]
        assert data["movement_type"] == "in"
        assert data["quantity"] == 5

    @pytest.mark.asyncio
    async def test_list_stock_movements(self, client: AsyncClient):
        """Test GET /api/v1/stock-movements."""
        prod_resp = await client.post("/api/v1/products", json={
            "code": "STKMVT002",
            "name": "List Movement Product",
            "price": "100.00",
        })
        product = prod_resp.json()

        for i in range(3):
            await client.post("/api/v1/stock-movements", json={
                "product_id": product["id"],
                "movement_type": "in" if i % 2 == 0 else "out",
                "quantity": i + 1,
            })

        response = await client.get("/api/v1/stock-movements?page=1&page_size=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 3

    @pytest.mark.asyncio
    async def test_get_stock_movements_by_product(self, client: AsyncClient):
        """Test GET /api/v1/stock-movements/product/{id}."""
        prod1 = await client.post("/api/v1/products", json={
            "code": "STKMVT003",
            "name": "Product 1",
            "price": "100.00",
        })
        product1 = prod1.json()

        prod2 = await client.post("/api/v1/products", json={
            "code": "STKMVT004",
            "name": "Product 2",
            "price": "200.00",
        })
        product2 = prod2.json()

        await client.post("/api/v1/stock-movements", json={
            "product_id": product1["id"],
            "movement_type": "in",
            "quantity": 10,
        })
        await client.post("/api/v1/stock-movements", json={
            "product_id": product2["id"],
            "movement_type": "in",
            "quantity": 5,
        })

        response = await client.get(f"/api/v1/stock-movements/product/{product1['id']}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["product_id"] == product1["id"]


class TestHoldBillsAPI:
    """Test Hold Bills API endpoints."""

    @pytest.mark.asyncio
    async def test_create_hold_bill(self, client: AsyncClient):
        """Test POST /api/v1/hold-bills."""
        import json
        items = [{"product_id": 1, "product_code": "TEST001", "product_name": "Test", "quantity": 2, "unit_price": "100.00"}]

        hold_data = {
            "bill_no": "HOLD-API-001",
            "items": json.dumps(items),
            "customer_name": "Hold Customer",
            "customer_phone": "0812345678",
            "subtotal": "200.00",
            "discount": "10.00",
            "vat": "13.30",
            "total": "203.30",
        }

        response = await client.post("/api/v1/hold-bills", json=hold_data)

        assert response.status_code == 201
        data = response.json()
        assert data["bill_no"] == "HOLD-API-001"
        assert data["customer_name"] == "Hold Customer"
        assert data["total"] == "203.30"

    @pytest.mark.asyncio
    async def test_get_hold_bill(self, client: AsyncClient):
        """Test GET /api/v1/hold-bills/{id}."""
        import json
        items = [{"product_id": 1, "quantity": 1}]

        create_resp = await client.post("/api/v1/hold-bills", json={
            "bill_no": "HOLD-API-002",
            "items": json.dumps(items),
            "subtotal": "100.00",
            "total": "100.00",
        })
        hold = create_resp.json()

        response = await client.get(f"/api/v1/hold-bills/{hold['id']}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == hold["id"]
        assert data["bill_no"] == "HOLD-API-002"

    @pytest.mark.asyncio
    async def test_get_hold_bill_by_bill_no(self, client: AsyncClient):
        """Test GET /api/v1/hold-bills/bill/{bill_no}."""
        import json
        items = [{"product_id": 1, "quantity": 1}]

        await client.post("/api/v1/hold-bills", json={
            "bill_no": "HOLD-API-003",
            "items": json.dumps(items),
            "subtotal": "100.00",
            "total": "100.00",
        })

        response = await client.get("/api/v1/hold-bills/bill/HOLD-API-003")

        assert response.status_code == 200
        data = response.json()
        assert data["bill_no"] == "HOLD-API-003"

    @pytest.mark.asyncio
    async def test_list_hold_bills(self, client: AsyncClient):
        """Test GET /api/v1/hold-bills."""
        import json
        items = [{"product_id": 1, "quantity": 1}]

        for i in range(3):
            await client.post("/api/v1/hold-bills", json={
                "bill_no": f"HOLD-LIST-{i:03d}",
                "items": json.dumps(items),
                "subtotal": "100.00",
                "total": "100.00",
            })

        response = await client.get("/api/v1/hold-bills?page=1&page_size=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 3

    @pytest.mark.asyncio
    async def test_delete_hold_bill(self, client: AsyncClient):
        """Test DELETE /api/v1/hold-bills/{id}."""
        import json
        items = [{"product_id": 1, "quantity": 1}]

        create_resp = await client.post("/api/v1/hold-bills", json={
            "bill_no": "HOLD-DELETE-API",
            "items": json.dumps(items),
            "subtotal": "100.00",
            "total": "100.00",
        })
        hold = create_resp.json()

        response = await client.delete(f"/api/v1/hold-bills/{hold['id']}")

        assert response.status_code == 200

        # Verify deleted
        get_resp = await client.get(f"/api/v1/hold-bills/{hold['id']}")
        assert get_resp.status_code == 404