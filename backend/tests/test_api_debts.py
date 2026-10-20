"""Tests for Debts API."""
import pytest
from decimal import Decimal
from httpx import AsyncClient


class TestDebtsAPI:
    """Test Debts API endpoints."""

    @pytest.mark.asyncio
    async def test_create_debt(self, client: AsyncClient):
        """Test POST /api/v1/debts."""
        debt_data = {
            "customer_name": "API Debt Customer",
            "customer_phone": "0811112222",
            "total_debt": "500.00",
            "notes": "API test debt",
        }

        response = await client.post("/api/v1/debts", json=debt_data)

        assert response.status_code == 201
        data = response.json()
        assert data["customer_name"] == "API Debt Customer"
        assert data["total_debt"] == "500.00"
        assert data["paid_amount"] == "0.00"
        assert data["remaining"] == "500.00"
        assert data["status"] == "open"

    @pytest.mark.asyncio
    async def test_get_debt(self, client: AsyncClient):
        """Test GET /api/v1/debts/{id}."""
        create_resp = await client.post("/api/v1/debts", json={
            "customer_name": "Get Debt Customer",
            "total_debt": "300.00",
        })
        debt = create_resp.json()

        response = await client.get(f"/api/v1/debts/{debt['id']}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == debt["id"]
        assert data["customer_name"] == "Get Debt Customer"

    @pytest.mark.asyncio
    async def test_get_debts_by_customer(self, client: AsyncClient):
        """Test GET /api/v1/debts/customer/{name}."""
        await client.post("/api/v1/debts", json={
            "customer_name": "Multi Debt Customer",
            "total_debt": "100.00",
        })
        await client.post("/api/v1/debts", json={
            "customer_name": "Multi Debt Customer",
            "total_debt": "200.00",
        })
        await client.post("/api/v1/debts", json={
            "customer_name": "Other Customer",
            "total_debt": "500.00",
        })

        response = await client.get("/api/v1/debts/customer/Multi%20Debt%20Customer")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(d["customer_name"] == "Multi Debt Customer" for d in data)

    @pytest.mark.asyncio
    async def test_add_payment(self, client: AsyncClient):
        """Test POST /api/v1/debts/{id}/payments."""
        create_resp = await client.post("/api/v1/debts", json={
            "customer_name": "Payment Customer",
            "total_debt": "1000.00",
        })
        debt = create_resp.json()

        response = await client.post(f"/api/v1/debts/{debt['id']}/payments", json={
            "amount": "300.00",
            "payment_method": "cash",
            "notes": "Partial payment",
        })

        assert response.status_code == 201
        data = response.json()
        assert data["amount"] == "300.00"
        assert data["payment_method"] == "cash"

        # Check debt updated
        get_resp = await client.get(f"/api/v1/debts/{debt['id']}")
        updated = get_resp.json()
        assert updated["paid_amount"] == "300.00"
        assert updated["remaining"] == "700.00"
        assert updated["status"] == "partial"

    @pytest.mark.asyncio
    async def test_full_payment(self, client: AsyncClient):
        """Test paying off a debt completely."""
        create_resp = await client.post("/api/v1/debts", json={
            "customer_name": "Full Pay Customer",
            "total_debt": "250.00",
        })
        debt = create_resp.json()

        await client.post(f"/api/v1/debts/{debt['id']}/payments", json={
            "amount": "250.00",
            "payment_method": "transfer",
        })

        get_resp = await client.get(f"/api/v1/debts/{debt['id']}")
        updated = get_resp.json()
        assert updated["paid_amount"] == "250.00"
        assert updated["remaining"] == "0.00"
        assert updated["status"] == "paid"

    @pytest.mark.asyncio
    async def test_list_debts(self, client: AsyncClient):
        """Test GET /api/v1/debts with pagination."""
        for i in range(5):
            await client.post("/api/v1/debts", json={
                "customer_name": f"List Customer {i}",
                "total_debt": f"{100 * (i + 1)}.00",
            })

        response = await client.get("/api/v1/debts?page=1&page_size=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5

    @pytest.mark.asyncio
    async def test_debt_summary(self, client: AsyncClient):
        """Test GET /api/v1/debts/summary."""
        await client.post("/api/v1/debts", json={
            "customer_name": "Summary Customer 1",
            "total_debt": "100.00",
        })
        await client.post("/api/v1/debts", json={
            "customer_name": "Summary Customer 2",
            "total_debt": "200.00",
        })

        # Add payment to first
        debt1_resp = await client.get("/api/v1/debts/customer/Summary%20Customer%201")
        debt1_id = debt1_resp.json()[0]["id"]

        await client.post(f"/api/v1/debts/{debt1_id}/payments", json={
            "amount": "50.00",
            "payment_method": "cash",
        })

        response = await client.get("/api/v1/debts/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["total_customers"] == 2
        assert data["total_debt"] == 300.0
        assert data["total_paid"] == 50.0
        assert data["total_remaining"] == 250.0

    @pytest.mark.asyncio
    async def test_update_debt(self, client: AsyncClient):
        """Test PUT /api/v1/debts/{id}."""
        create_resp = await client.post("/api/v1/debts", json={
            "customer_name": "Original Name",
            "total_debt": "400.00",
            "notes": "Original notes",
        })
        debt = create_resp.json()

        response = await client.put(f"/api/v1/debts/{debt['id']}", json={
            "customer_name": "Updated Name",
            "notes": "Updated notes",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["customer_name"] == "Updated Name"
        assert data["notes"] == "Updated notes"