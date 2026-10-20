"""Tests for PurchaseService."""
import pytest
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.purchase_service import PurchaseService
from app.services.product_service import ProductService
from app.schemas import PurchaseCreate, PurchaseItemCreate, ProductCreate


class TestPurchaseService:
    """Test PurchaseService methods."""

    @pytest.mark.asyncio
    async def test_create_purchase(self, test_session: AsyncSession):
        """Test creating a purchase order."""
        product_service = ProductService(test_session)
        purchase_service = PurchaseService(test_session)

        # Create a product first
        product = await product_service.create(ProductCreate(
            code="PUR001",
            name="Purchase Product",
            price=Decimal("150.00"),
            cost=Decimal("80.00"),
            stock=10,
        ))

        # Create purchase
        purchase_data = PurchaseCreate(
            supplier_name="Test Supplier",
            supplier_phone="0898765432",
            status="pending",
            notes="Test purchase",
            items=[
                PurchaseItemCreate(
                    product_id=product.id,
                    product_code=product.code,
                    product_name=product.name,
                    unit="ชิ้น",
                    quantity=5,
                    unit_cost=Decimal("80.00"),
                    line_total=Decimal("400.00"),
                )
            ],
        )

        purchase = await purchase_service.create(purchase_data)

        assert purchase.id is not None
        assert purchase.po_no.startswith("PO-")
        assert purchase.supplier_name == "Test Supplier"
        assert purchase.status == "pending"
        assert purchase.total == Decimal("400.00")

    @pytest.mark.asyncio
    async def test_receive_purchase(self, test_session: AsyncSession):
        """Test receiving a purchase (adds stock)."""
        product_service = ProductService(test_session)
        purchase_service = PurchaseService(test_session)

        product = await product_service.create(ProductCreate(
            code="PUR002",
            name="Receive Product",
            price=Decimal("200.00"),
            cost=Decimal("100.00"),
            stock=5,
        ))

        purchase_data = PurchaseCreate(
            supplier_name="Supplier 2",
            items=[
                PurchaseItemCreate(
                    product_id=product.id,
                    product_code=product.code,
                    product_name=product.name,
                    unit="ชิ้น",
                    quantity=10,
                    unit_cost=Decimal("100.00"),
                    line_total=Decimal("1000.00"),
                )
            ],
        )
        purchase = await purchase_service.create(purchase_data)

        # Receive the purchase (all items fully received)
        received = await purchase_service.receive(purchase.id, [
            {"item_id": purchase.items[0].id, "received_qty": 10}
        ])

        assert received.status == "received"
        assert received.received_date is not None

        # Check stock increased
        updated_product = await product_service.get(product.id)
        assert updated_product.stock == 15  # 5 + 10

    @pytest.mark.asyncio
    async def test_get_purchase(self, test_session: AsyncSession):
        """Test getting a purchase by ID."""
        product_service = ProductService(test_session)
        purchase_service = PurchaseService(test_session)

        product = await product_service.create(ProductCreate(
            code="PUR003",
            name="Get Purchase Product",
            price=Decimal("100.00"),
        ))

        purchase_data = PurchaseCreate(
            items=[
                PurchaseItemCreate(
                    product_id=product.id,
                    product_code=product.code,
                    product_name=product.name,
                    unit="ชิ้น",
                    quantity=3,
                    unit_cost=Decimal("50.00"),
                    line_total=Decimal("150.00"),
                )
            ],
        )
        created = await purchase_service.create(purchase_data)

        purchase = await purchase_service.get(created.id)

        assert purchase is not None
        assert purchase.id == created.id
        assert len(purchase.items) == 1

    @pytest.mark.asyncio
    async def test_get_purchase_by_po_no(self, test_session: AsyncSession):
        """Test getting a purchase by PO number."""
        product_service = ProductService(test_session)
        purchase_service = PurchaseService(test_session)

        product = await product_service.create(ProductCreate(
            code="PUR004",
            name="PO Number Product",
            price=Decimal("100.00"),
        ))

        purchase_data = PurchaseCreate(
            items=[
                PurchaseItemCreate(
                    product_id=product.id,
                    product_code=product.code,
                    product_name=product.name,
                    unit="ชิ้น",
                    quantity=1,
                    unit_cost=Decimal("50.00"),
                    line_total=Decimal("50.00"),
                )
            ],
        )
        created = await purchase_service.create(purchase_data)

        purchase = await purchase_service.get_by_po_no(created.po_no)

        assert purchase is not None
        assert purchase.po_no == created.po_no

    @pytest.mark.asyncio
    async def test_list_purchases(self, test_session: AsyncSession):
        """Test listing purchases with pagination."""
        product_service = ProductService(test_session)
        purchase_service = PurchaseService(test_session)

        product = await product_service.create(ProductCreate(
            code="PUR005",
            name="List Purchase Product",
            price=Decimal("100.00"),
            stock=20,
        ))

        for i in range(3):
            await purchase_service.create(PurchaseCreate(
                supplier_name=f"Supplier {i}",
                items=[
                    PurchaseItemCreate(
                        product_id=product.id,
                        product_code=product.code,
                        product_name=product.name,
                        unit="ชิ้น",
                        quantity=1,
                        unit_cost=Decimal("50.00"),
                        line_total=Decimal("50.00"),
                    )
                ],
            ))

        purchases, total = await purchase_service.list(page=1, page_size=2)

        assert len(purchases) == 2
        assert total == 3

    @pytest.mark.asyncio
    async def test_update_purchase(self, test_session: AsyncSession):
        """Test updating a purchase."""
        product_service = ProductService(test_session)
        purchase_service = PurchaseService(test_session)

        product = await product_service.create(ProductCreate(
            code="PUR006",
            name="Update Purchase Product",
            price=Decimal("100.00"),
        ))

        purchase_data = PurchaseCreate(
            supplier_name="Original Supplier",
            items=[
                PurchaseItemCreate(
                    product_id=product.id,
                    product_code=product.code,
                    product_name=product.name,
                    unit="ชิ้น",
                    quantity=1,
                    unit_cost=Decimal("50.00"),
                    line_total=Decimal("50.00"),
                )
            ],
        )
        created = await purchase_service.create(purchase_data)

        from app.schemas import PurchaseUpdate
        update_data = PurchaseUpdate(
            supplier_name="Updated Supplier",
            notes="Updated notes"
        )
        updated = await purchase_service.update(created.id, update_data)

        assert updated is not None
        assert updated.supplier_name == "Updated Supplier"
        assert updated.notes == "Updated notes"