"""Tests for ProductService."""
import pytest
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.product_service import ProductService
from app.schemas import ProductCreate, ProductUpdate

STORE_ID = 1  # Default test store (created in conftest)


class TestProductService:
    """Test ProductService methods."""

    @pytest.mark.asyncio
    async def test_create_product(self, test_session: AsyncSession):
        """Test creating a product."""
        service = ProductService(test_session)

        product_data = ProductCreate(
            code="TEST001",
            name="Test Product",
            category="Test",
            unit="ชิ้น",
            price=Decimal("100.00"),
            cost=Decimal("50.00"),
            stock=10,
            min_stock=5,
        )

        product = await service.create(product_data, store_id=STORE_ID)

        assert product.id is not None
        assert product.code == "TEST001"
        assert product.name == "Test Product"
        assert product.stock == 10
        assert product.store_id == STORE_ID

    @pytest.mark.asyncio
    async def test_get_product(self, test_session: AsyncSession):
        """Test getting a product by ID."""
        service = ProductService(test_session)

        # Create product first
        product_data = ProductCreate(
            code="TEST002",
            name="Test Product 2",
            price=Decimal("200.00"),
        )
        created = await service.create(product_data, store_id=STORE_ID)

        # Get by ID
        product = await service.get(created.id, store_id=STORE_ID)

        assert product is not None
        assert product.id == created.id
        assert product.code == "TEST002"

    @pytest.mark.asyncio
    async def test_get_by_code(self, test_session: AsyncSession):
        """Test getting a product by code."""
        service = ProductService(test_session)

        product_data = ProductCreate(
            code="TEST003",
            name="Test Product 3",
            price=Decimal("300.00"),
        )
        await service.create(product_data, store_id=STORE_ID)

        product = await service.get_by_code("TEST003", store_id=STORE_ID)

        assert product is not None
        assert product.code == "TEST003"

    @pytest.mark.asyncio
    async def test_update_product(self, test_session: AsyncSession):
        """Test updating a product."""
        service = ProductService(test_session)

        product_data = ProductCreate(
            code="TEST004",
            name="Original Name",
            price=Decimal("100.00"),
        )
        created = await service.create(product_data, store_id=STORE_ID)

        update_data = ProductUpdate(name="Updated Name", price=Decimal("150.00"))
        updated = await service.update(created.id, update_data, store_id=STORE_ID)

        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.price == Decimal("150.00")

    @pytest.mark.asyncio
    async def test_update_stock(self, test_session: AsyncSession):
        """Test updating product stock."""
        service = ProductService(test_session)

        product_data = ProductCreate(
            code="TEST005",
            name="Stock Test",
            price=Decimal("100.00"),
            stock=10,
        )
        created = await service.create(product_data, store_id=STORE_ID)

        # Increase stock
        updated = await service.update_stock(
            product_id=created.id,
            quantity=5,
            movement_type="in",
            reference_type="test",
            store_id=STORE_ID,
        )

        assert updated.stock == 15

    @pytest.mark.asyncio
    async def test_list_products(self, test_session: AsyncSession):
        """Test listing products with pagination."""
        service = ProductService(test_session)

        # Create multiple products
        for i in range(5):
            await service.create(ProductCreate(
                code=f"LIST{i:03d}",
                name=f"List Product {i}",
                price=Decimal("100.00"),
            ), store_id=STORE_ID)

        products, total = await service.list(page=1, page_size=2, store_id=STORE_ID)

        assert len(products) == 2
        assert total == 5
