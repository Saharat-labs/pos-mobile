"""Tests for Expenses API."""
import pytest
from decimal import Decimal
from datetime import datetime
from httpx import AsyncClient


class TestExpensesAPI:
    """Test Expenses API endpoints."""

    @pytest.mark.asyncio
    async def test_create_expense(self, client: AsyncClient):
        """Test POST /api/v1/expenses."""
        expense_data = {
            "date": datetime.utcnow().isoformat(),
            "category": "ค่าสาธารณูปโภค",
            "description": "ค่าไฟฟ้าเดือนมกราคม",
            "amount": "1500.00",
            "payment_method": "cash",
            "notes": "Electric bill",
        }

        response = await client.post("/api/v1/expenses", json=expense_data)

        assert response.status_code == 201
        data = response.json()
        assert data["category"] == "ค่าสาธารณูปโภค"
        assert data["amount"] == "1500.00"
        assert data["payment_method"] == "cash"

    @pytest.mark.asyncio
    async def test_get_expense(self, client: AsyncClient):
        """Test GET /api/v1/expenses/{id}."""
        create_resp = await client.post("/api/v1/expenses", json={
            "date": datetime.utcnow().isoformat(),
            "category": "ค่าเช่า",
            "description": "ค่าเช่าร้าน",
            "amount": "10000.00",
        })
        expense = create_resp.json()

        response = await client.get(f"/api/v1/expenses/{expense['id']}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == expense["id"]
        assert data["category"] == "ค่าเช่า"

    @pytest.mark.asyncio
    async def test_update_expense(self, client: AsyncClient):
        """Test PUT /api/v1/expenses/{id}."""
        create_resp = await client.post("/api/v1/expenses", json={
            "date": datetime.utcnow().isoformat(),
            "category": "ค่าอุปกรณ์",
            "description": "ซื้อคอมพิวเตอร์",
            "amount": "25000.00",
        })
        expense = create_resp.json()

        response = await client.put(f"/api/v1/expenses/{expense['id']}", json={
            "category": "ค่าอุปกรณ์สำนักงาน",
            "amount": "26000.00",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "ค่าอุปกรณ์สำนักงาน"
        assert data["amount"] == "26000.00"

    @pytest.mark.asyncio
    async def test_delete_expense(self, client: AsyncClient):
        """Test DELETE /api/v1/expenses/{id}."""
        create_resp = await client.post("/api/v1/expenses", json={
            "date": datetime.utcnow().isoformat(),
            "category": "ค่าต่างๆ",
            "description": "รายจ่ายทั่วไป",
            "amount": "500.00",
        })
        expense = create_resp.json()

        response = await client.delete(f"/api/v1/expenses/{expense['id']}")

        assert response.status_code == 204

        # Verify deleted
        get_resp = await client.get(f"/api/v1/expenses/{expense['id']}")
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_list_expenses(self, client: AsyncClient):
        """Test GET /api/v1/expenses with pagination."""
        now = datetime.utcnow().isoformat()
        for i in range(5):
            await client.post("/api/v1/expenses", json={
                "date": now,
                "category": f"Category {i % 3}",
                "description": f"Expense {i}",
                "amount": f"{100 * (i + 1)}.00",
            })

        response = await client.get("/api/v1/expenses?page=1&page_size=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5

    @pytest.mark.asyncio
    async def test_list_expenses_filter_category(self, client: AsyncClient):
        """Test filtering expenses by category."""
        now = datetime.utcnow().isoformat()
        await client.post("/api/v1/expenses", json={
            "date": now,
            "category": "ค่าอาหาร",
            "description": "Lunch",
            "amount": "200.00",
        })
        await client.post("/api/v1/expenses", json={
            "date": now,
            "category": "ค่าขนส่ง",
            "description": "Taxi",
            "amount": "100.00",
        })

        response = await client.get("/api/v1/expenses?category=ค่าอาหาร")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["category"] == "ค่าอาหาร"

    @pytest.mark.asyncio
    async def test_get_expense_categories(self, client: AsyncClient):
        """Test GET /api/v1/expenses/categories."""
        now = datetime.utcnow().isoformat()
        await client.post("/api/v1/expenses", json={
            "date": now,
            "category": "ค่าอาหาร",
            "description": "Lunch",
            "amount": "200.00",
        })
        await client.post("/api/v1/expenses", json={
            "date": now,
            "category": "ค่าขนส่ง",
            "description": "Taxi",
            "amount": "100.00",
        })

        response = await client.get("/api/v1/expenses/categories")

        assert response.status_code == 200
        data = response.json()
        assert "ค่าอาหาร" in data
        assert "ค่าขนส่ง" in data

    @pytest.mark.asyncio
    async def test_monthly_summary(self, client: AsyncClient):
        """Test GET /api/v1/expenses/summary/monthly."""
        now = datetime.utcnow()
        await client.post("/api/v1/expenses", json={
            "date": now.isoformat(),
            "category": "ค่าอาหาร",
            "description": "Lunch",
            "amount": "200.00",
        })
        await client.post("/api/v1/expenses", json={
            "date": now.isoformat(),
            "category": "ค่าขนส่ง",
            "description": "Taxi",
            "amount": "100.00",
        })

        response = await client.get(f"/api/v1/expenses/summary/monthly?year={now.year}&month={now.month}")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 300.0
        by_cat = {c["category"]: c["total"] for c in data["categories"]}
        assert by_cat["ค่าอาหาร"] == 200.0

    @pytest.mark.asyncio
    async def test_yearly_summary(self, client: AsyncClient):
        """Test GET /api/v1/expenses/summary/yearly."""
        now = datetime.utcnow()
        await client.post("/api/v1/expenses", json={
            "date": now.isoformat(),
            "category": "ค่าอาหาร",
            "description": "Lunch",
            "amount": "200.00",
        })

        response = await client.get(f"/api/v1/expenses/summary/yearly?year={now.year}")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 200.0
        assert data["months"][str(now.month)] == 200.0