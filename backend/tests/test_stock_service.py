"""Tests for StockMovementService."""
import pytest
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.stock_service import StockMovementService
from app.services.product_service import ProductService
from app.schemas import StockMovementCreate, ProductCreate


class TestStockMovementService:
    """Test StockMovementService methods."""

    @pytest.mark.asyncio
    async def test_create_stock_movement(self, test_session: AsyncSession):
        """Test creating a stock movement."""
        product_service = ProductService(test_session)
        stock_service = StockMovementService(test_session)

        product = await product_service.create(ProductCreate(
            code="STOCK001",
            name="Stock Product",
            price=Decimal("100.00"),
            stock=10,
        ))

        movement_data = StockMovementCreate(
            product_id=product.id,
            movement_type="in",
            quantity=5,
            reference_type="purchase",
            reference_id=1,
            notes="Stock in from purchase",
        )

        movement = await stock_service.create(movement_data)

        assert movement.id is not None
        assert movement.product_id == product.id
        assert movement.movement_type == "in"
        assert movement.quantity == 5

    @pytest.mark.asyncio
    async def test_get_stock_movement(self, test_session: AsyncSession):
        """Test getting a stock movement by ID."""
        product_service = ProductService(test_session)
        stock_service = StockMovementService(test_session)

        product = await product_service.create(ProductCreate(
            code="STOCK002",
            name="Get Movement Product",
            price=Decimal("100.00"),
        ))

        movement_data = StockMovementCreate(
            product_id=product.id,
            movement_type="out",
            quantity=3,
            reference_type="sale",
        )
        created = await stock_service.create(movement_data)

        movement = await stock_service.get(created.id)

        assert movement is not None
        assert movement.id == created.id
        assert movement.movement_type == "out"

    @pytest.mark.asyncio
    async def test_list_stock_movements(self, test_session: AsyncSession):
        """Test listing stock movements."""
        product_service = ProductService(test_session)
        stock_service = StockMovementService(test_session)

        product = await product_service.create(ProductCreate(
            code="STOCK003",
            name="List Movement Product",
            price=Decimal("100.00"),
        ))

        for i in range(5):
            await stock_service.create(StockMovementCreate(
                product_id=product.id,
                movement_type="in" if i % 2 == 0 else "out",
                quantity=i + 1,
            ))

        movements, total = await stock_service.list(page=1, page_size=2)

        assert len(movements) == 2
        assert total == 5

    @pytest.mark.asyncio
    async def test_list_by_product(self, test_session: AsyncSession):
        """Test listing stock movements for a specific product."""
        product_service = ProductService(test_session)
        stock_service = StockMovementService(test_session)

        product1 = await product_service.create(ProductCreate(
            code="STOCK004",
            name="Product 1",
            price=Decimal("100.00"),
        ))
        product2 = await product_service.create(ProductCreate(
            code="STOCK005",
            name="Product 2",
            price=Decimal("200.00"),
        ))

        await stock_service.create(StockMovementCreate(
            product_id=product1.id,
            movement_type="in",
            quantity=10,
        ))
        await stock_service.create(StockMovementCreate(
            product_id=product2.id,
            movement_type="in",
            quantity=5,
        ))

        movements = await stock_service.get_product_history(product1.id)

        assert len(movements) == 1
        assert movements[0].product_id == product1.id

    @pytest.mark.asyncio
    async def test_list_by_product_and_type(self, test_session: AsyncSession):
        """Test listing stock movements filtered by type."""
        product_service = ProductService(test_session)
        stock_service = StockMovementService(test_session)

        product = await product_service.create(ProductCreate(
            code="STOCK006",
            name="Filter Type Product",
            price=Decimal("100.00"),
        ))

        await stock_service.create(StockMovementCreate(
            product_id=product.id,
            movement_type="in",
            quantity=10,
        ))
        await stock_service.create(StockMovementCreate(
            product_id=product.id,
            movement_type="out",
            quantity=3,
        ))
        await stock_service.create(StockMovementCreate(
            product_id=product.id,
            movement_type="adjust",
            quantity=2,
        ))

        in_items, _ = await stock_service.list(product_id=product.id, movement_type="in")
        out_items, _ = await stock_service.list(product_id=product.id, movement_type="out")

        assert len(in_items) == 1
        assert in_items[0].quantity == 10
        assert len(out_items) == 1
        assert out_items[0].quantity == 3