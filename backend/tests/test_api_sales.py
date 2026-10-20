"""Tests for Sales API."""
import pytest
from decimal import Decimal
from httpx import AsyncClient


class TestSalesAPI:
    """Test Sales API endpoints."""

    @pytest.mark.asyncio
    async def test_create_sale(self, client: AsyncClient):
        """Test POST /api/v1/sales."""
        # Create product first
        prod_resp = await client.post("/api/v1/products", json={
            "code": "SALEAPI001",
            "name": "Sale Product",
            "price": "100.00",
            "stock": 10,
        })
        product = prod_resp.json()

        sale_data = {
            "customer_name": "API Customer",
            "customer_phone": "0812345678",
            "discount": "10.00",
            "vat": "0.00",
            "payment_method": "cash",
            "paid_amount": "100.00",
            "notes": "API test sale",
            "items": [
                {
                    "product_id": product["id"],
                    "product_code": product["code"],
                    "product_name": product["name"],
                    "unit": "ชิ้น",
                    "quantity": 1,
                    "unit_price": "100.00",
                    "discount": "10.00",
                    "line_total": "90.00",
                }
            ],
        }

        response = await client.post("/api/v1/sales", json=sale_data)

        assert response.status_code == 201
        data = response.json()
        assert data["bill_no"].startswith("POS-")
        assert data["customer_name"] == "API Customer"
        assert data["payment_method"] == "cash"
        assert data["status"] == "completed"
        assert data["subtotal"] == "90.00"
        assert data["discount"] == "10.00"

    @pytest.mark.asyncio
    async def test_create_credit_sale(self, client: AsyncClient):
        """Test creating a credit sale (status=held)."""
        prod_resp = await client.post("/api/v1/products", json={
            "code": "SALEAPI002",
            "name": "Credit Product",
            "price": "200.00",
            "stock": 5,
        })
        product = prod_resp.json()

        sale_data = {
            "customer_name": "Credit Customer",
            "payment_method": "credit",
            "paid_amount": "0.00",
            "items": [
                {
                    "product_id": product["id"],
                    "product_code": product["code"],
                    "product_name": product["name"],
                    "unit": "ชิ้น",
                    "quantity": 1,
                    "unit_price": "200.00",
                    "discount": "0.00",
                    "line_total": "200.00",
                }
            ],
        }

        response = await client.post("/api/v1/sales", json=sale_data)

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "held"
        assert data["payment_method"] == "credit"

    @pytest.mark.asyncio
    async def test_create_sale_insufficient_stock(self, client: AsyncClient):
        """Test creating sale with insufficient stock fails."""
        prod_resp = await client.post("/api/v1/products", json={
            "code": "SALEAPI003",
            "name": "Low Stock Product",
            "price": "100.00",
            "stock": 1,
        })
        product = prod_resp.json()

        sale_data = {
            "payment_method": "cash",
            "paid_amount": "100.00",
            "items": [
                {
                    "product_id": product["id"],
                    "product_code": product["code"],
                    "product_name": product["name"],
                    "unit": "ชิ้น",
                    "quantity": 5,  # More than stock
                    "unit_price": "100.00",
                    "discount": "0.00",
                    "line_total": "500.00",
                }
            ],
        }

        response = await client.post("/api/v1/sales", json=sale_data)

        assert response.status_code == 400
        assert "stock" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_sale(self, client: AsyncClient):
        """Test GET /api/v1/sales/{id}."""
        prod_resp = await client.post("/api/v1/products", json={
            "code": "SALEAPI004",
            "name": "Get Sale Product",
            "price": "150.00",
            "stock": 10,
        })
        product = prod_resp.json()

        sale_resp = await client.post("/api/v1/sales", json={
            "payment_method": "cash",
            "paid_amount": "150.00",
            "items": [{
                "product_id": product["id"],
                "product_code": product["code"],
                "product_name": product["name"],
                "unit": "ชิ้น",
                "quantity": 1,
                "unit_price": "150.00",
                "discount": "0.00",
                "line_total": "150.00",
            }],
        })
        sale = sale_resp.json()

        response = await client.get(f"/api/v1/sales/{sale['id']}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sale["id"]
        assert len(data["items"]) == 1

    @pytest.mark.asyncio
    async def test_get_sale_by_bill_no(self, client: AsyncClient):
        """Test GET /api/v1/sales/bill/{bill_no}."""
        prod_resp = await client.post("/api/v1/products", json={
            "code": "SALEAPI005",
            "name": "Bill No Product",
            "price": "100.00",
            "stock": 10,
        })
        product = prod_resp.json()

        sale_resp = await client.post("/api/v1/sales", json={
            "payment_method": "cash",
            "paid_amount": "100.00",
            "items": [{
                "product_id": product["id"],
                "product_code": product["code"],
                "product_name": product["name"],
                "unit": "ชิ้น",
                "quantity": 1,
                "unit_price": "100.00",
                "discount": "0.00",
                "line_total": "100.00",
            }],
        })
        sale = sale_resp.json()

        response = await client.get(f"/api/v1/sales/bill/{sale['bill_no']}")

        assert response.status_code == 200
        data = response.json()
        assert data["bill_no"] == sale["bill_no"]

    @pytest.mark.asyncio
    async def test_list_sales(self, client: AsyncClient):
        """Test GET /api/v1/sales with pagination."""
        prod_resp = await client.post("/api/v1/products", json={
            "code": "SALEAPI006",
            "name": "List Sale Product",
            "price": "100.00",
            "stock": 20,
        })
        product = prod_resp.json()

        for _ in range(3):
            await client.post("/api/v1/sales", json={
                "payment_method": "cash",
                "paid_amount": "100.00",
                "items": [{
                    "product_id": product["id"],
                    "product_code": product["code"],
                    "product_name": product["name"],
                    "unit": "ชิ้น",
                    "quantity": 1,
                    "unit_price": "100.00",
                    "discount": "0.00",
                    "line_total": "100.00",
                }],
            })

        response = await client.get("/api/v1/sales?page=1&page_size=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 3

    @pytest.mark.asyncio
    async def test_list_sales_filter_payment_method(self, client: AsyncClient):
        """Test filtering sales by payment method."""
        prod_resp = await client.post("/api/v1/products", json={
            "code": "SALEAPI007",
            "name": "Filter Product",
            "price": "100.00",
            "stock": 10,
        })
        product = prod_resp.json()

        await client.post("/api/v1/sales", json={
            "payment_method": "cash",
            "paid_amount": "100.00",
            "items": [{
                "product_id": product["id"],
                "product_code": product["code"],
                "product_name": product["name"],
                "unit": "ชิ้น",
                "quantity": 1,
                "unit_price": "100.00",
                "discount": "0.00",
                "line_total": "100.00",
            }],
        })
        await client.post("/api/v1/sales", json={
            "payment_method": "transfer",
            "paid_amount": "100.00",
            "items": [{
                "product_id": product["id"],
                "product_code": product["code"],
                "product_name": product["name"],
                "unit": "ชิ้น",
                "quantity": 1,
                "unit_price": "100.00",
                "discount": "0.00",
                "line_total": "100.00",
            }],
        })

        response = await client.get("/api/v1/sales?payment_method=cash")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["payment_method"] == "cash"

    @pytest.mark.asyncio
    async def test_daily_summary(self, client: AsyncClient):
        """Test GET /api/v1/sales/summary/daily."""
        prod_resp = await client.post("/api/v1/products", json={
            "code": "SALEAPI008",
            "name": "Summary Product",
            "price": "100.00",
            "stock": 10,
        })
        product = prod_resp.json()

        await client.post("/api/v1/sales", json={
            "payment_method": "cash",
            "paid_amount": "100.00",
            "items": [{
                "product_id": product["id"],
                "product_code": product["code"],
                "product_name": product["name"],
                "unit": "ชิ้น",
                "quantity": 1,
                "unit_price": "100.00",
                "discount": "0.00",
                "line_total": "100.00",
            }],
        })

        response = await client.get("/api/v1/sales/summary/daily")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert "total" in data
        assert "payment_methods" in data

    @pytest.mark.asyncio
    async def test_top_products(self, client: AsyncClient):
        """Test GET /api/v1/sales/summary/top-products."""
        prod_resp = await client.post("/api/v1/products", json={
            "code": "SALEAPI009",
            "name": "Top Product",
            "price": "100.00",
            "stock": 10,
        })
        product = prod_resp.json()

        await client.post("/api/v1/sales", json={
            "payment_method": "cash",
            "paid_amount": "100.00",
            "items": [{
                "product_id": product["id"],
                "product_code": product["code"],
                "product_name": product["name"],
                "unit": "ชิ้น",
                "quantity": 1,
                "unit_price": "100.00",
                "discount": "0.00",
                "line_total": "100.00",
            }],
        })

        response = await client.get("/api/v1/sales/summary/top-products?start_date=2026-01-01&end_date=2026-12-31")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["product_code"] == "SALEAPI009"

    @pytest.mark.asyncio
    async def test_update_sale(self, client: AsyncClient):
        """Test PUT /api/v1/sales/{id}."""
        prod_resp = await client.post("/api/v1/products", json={
            "code": "SALEAPI010",
            "name": "Update Sale Product",
            "price": "100.00",
            "stock": 10,
        })
        product = prod_resp.json()

        sale_resp = await client.post("/api/v1/sales", json={
            "customer_name": "Original",
            "payment_method": "cash",
            "paid_amount": "100.00",
            "items": [{
                "product_id": product["id"],
                "product_code": product["code"],
                "product_name": product["name"],
                "unit": "ชิ้น",
                "quantity": 1,
                "unit_price": "100.00",
                "discount": "0.00",
                "line_total": "100.00",
            }],
        })
        sale = sale_resp.json()

        response = await client.put(f"/api/v1/sales/{sale['id']}", json={
            "customer_name": "Updated",
            "notes": "Updated notes",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["customer_name"] == "Updated"
        assert data["notes"] == "Updated notes"