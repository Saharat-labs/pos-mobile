"""Tests for Products API."""
import pytest
from decimal import Decimal
from httpx import AsyncClient


class TestProductsAPI:
    """Test Products API endpoints."""

    @pytest.mark.asyncio
    async def test_create_product(self, client: AsyncClient):
        """Test POST /api/v1/products."""
        product_data = {
            "code": "API001",
            "name": "API Product",
            "category": "Test",
            "unit": "ชิ้น",
            "price": "100.00",
            "cost": "50.00",
            "stock": 10,
            "min_stock": 5,
        }

        response = await client.post("/api/v1/products", json=product_data)

        assert response.status_code == 201
        data = response.json()
        assert data["code"] == "API001"
        assert data["name"] == "API Product"
        assert data["price"] == "100.00"
        assert data["id"] is not None

    @pytest.mark.asyncio
    async def test_create_duplicate_product(self, client: AsyncClient):
        """Test creating product with duplicate code fails."""
        product_data = {
            "code": "DUP001",
            "name": "Duplicate Product",
            "price": "100.00",
        }

        # First creation succeeds
        response1 = await client.post("/api/v1/products", json=product_data)
        assert response1.status_code == 201

        # Second creation fails
        response2 = await client.post("/api/v1/products", json=product_data)
        assert response2.status_code == 400
        assert "already exists" in response2.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_product(self, client: AsyncClient):
        """Test GET /api/v1/products/{id}."""
        # Create product first
        create_resp = await client.post("/api/v1/products", json={
            "code": "API002",
            "name": "Get Product",
            "price": "200.00",
        })
        product_id = create_resp.json()["id"]

        # Get by ID
        response = await client.get(f"/api/v1/products/{product_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == product_id
        assert data["code"] == "API002"

    @pytest.mark.asyncio
    async def test_get_product_by_code(self, client: AsyncClient):
        """Test GET /api/v1/products/code/{code}."""
        await client.post("/api/v1/products", json={
            "code": "API003",
            "name": "Code Product",
            "price": "300.00",
        })

        response = await client.get("/api/v1/products/code/API003")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "API003"

    @pytest.mark.asyncio
    async def test_get_product_by_barcode(self, client: AsyncClient):
        """Test GET /api/v1/products/barcode/{barcode}."""
        await client.post("/api/v1/products", json={
            "code": "API004",
            "name": "Barcode Product",
            "price": "400.00",
            "barcode": "8851234567890",
        })

        response = await client.get("/api/v1/products/barcode/8851234567890")

        assert response.status_code == 200
        data = response.json()
        assert data["barcode"] == "8851234567890"

    @pytest.mark.asyncio
    async def test_update_product(self, client: AsyncClient):
        """Test PUT /api/v1/products/{id}."""
        create_resp = await client.post("/api/v1/products", json={
            "code": "API005",
            "name": "Original",
            "price": "100.00",
        })
        product_id = create_resp.json()["id"]

        response = await client.put(f"/api/v1/products/{product_id}", json={
            "name": "Updated",
            "price": "150.00",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated"
        assert data["price"] == "150.00"

    @pytest.mark.asyncio
    async def test_delete_product(self, client: AsyncClient):
        """Test DELETE /api/v1/products/{id} (soft delete)."""
        create_resp = await client.post("/api/v1/products", json={
            "code": "API006",
            "name": "To Delete",
            "price": "100.00",
        })
        product_id = create_resp.json()["id"]

        response = await client.delete(f"/api/v1/products/{product_id}")

        assert response.status_code == 200

        # Product should be inactive
        get_resp = await client.get(f"/api/v1/products/{product_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["is_active"] is False

    @pytest.mark.asyncio
    async def test_list_products(self, client: AsyncClient):
        """Test GET /api/v1/products with pagination."""
        for i in range(5):
            await client.post("/api/v1/products", json={
                "code": f"LIST{i:03d}",
                "name": f"List Product {i}",
                "price": "100.00",
            })

        response = await client.get("/api/v1/products?page=1&page_size=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["page_size"] == 2

    @pytest.mark.asyncio
    async def test_list_products_filter_category(self, client: AsyncClient):
        """Test filtering products by category."""
        await client.post("/api/v1/products", json={
            "code": "CAT001",
            "name": "Cat Product",
            "category": "Electronics",
            "price": "100.00",
        })
        await client.post("/api/v1/products", json={
            "code": "CAT002",
            "name": "Other Product",
            "category": "Food",
            "price": "100.00",
        })

        response = await client.get("/api/v1/products?category=Electronics")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["category"] == "Electronics"

    @pytest.mark.asyncio
    async def test_low_stock_products(self, client: AsyncClient):
        """Test GET /api/v1/products/low-stock."""
        await client.post("/api/v1/products", json={
            "code": "LOW001",
            "name": "Low Stock",
            "price": "100.00",
            "stock": 2,
            "min_stock": 5,
        })
        await client.post("/api/v1/products", json={
            "code": "LOW002",
            "name": "OK Stock",
            "price": "100.00",
            "stock": 10,
            "min_stock": 5,
        })

        response = await client.get("/api/v1/products/low-stock")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["code"] == "LOW001"

    @pytest.mark.asyncio
    async def test_update_stock(self, client: AsyncClient):
        """Test POST /api/v1/products/{id}/stock."""
        create_resp = await client.post("/api/v1/products", json={
            "code": "STK001",
            "name": "Stock Product",
            "price": "100.00",
            "stock": 10,
        })
        product_id = create_resp.json()["id"]

        response = await client.post(f"/api/v1/products/{product_id}/stock", json={
            "quantity": 5,
            "movement_type": "in",
            "reference_type": "manual",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["stock"] == 15

    @pytest.mark.asyncio
    async def test_get_categories(self, client: AsyncClient):
        """Test GET /api/v1/products/categories."""
        await client.post("/api/v1/products", json={
            "code": "CATG001",
            "name": "Product 1",
            "category": "Category A",
            "price": "100.00",
        })
        await client.post("/api/v1/products", json={
            "code": "CATG002",
            "name": "Product 2",
            "category": "Category B",
            "price": "100.00",
        })

        response = await client.get("/api/v1/products/categories")

        assert response.status_code == 200
        data = response.json()
        assert "Category A" in data
        assert "Category B" in data