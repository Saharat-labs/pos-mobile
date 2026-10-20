"""Tests for SaleService."""
import pytest
from decimal import Decimal
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.sale_service import SaleService
from app.services.product_service import ProductService
from app.services.setting_service import SettingService
from app.schemas import SaleCreate, SaleItemCreate, ProductCreate

STORE_ID = 1  # Default test store (created in conftest)


class TestSaleService:
    """Test SaleService methods."""

    @pytest.mark.asyncio
    async def test_create_sale_cash(self, test_session: AsyncSession):
        """Test creating a cash sale."""
        product_service = ProductService(test_session)
        sale_service = SaleService(test_session)
        setting_service = SettingService(test_session)

        # Set VAT mode to 'exclude' (VAT added on top)
        await setting_service.set("vat", "exclude", "VAT mode: exclude=added on top, include=included in price, no=no VAT", store_id=STORE_ID)

        # Create a product first
        product = await product_service.create(ProductCreate(
            code="SALE001",
            name="Sale Product",
            price=Decimal("100.00"),
            cost=Decimal("50.00"),
            stock=10,
        ), store_id=STORE_ID)

        # Create sale
        sale_data = SaleCreate(
            customer_name="Test Customer",
            customer_phone="0812345678",
            discount=Decimal("10.00"),
            vat=Decimal("6.30"),  # This will be recalculated by backend
            payment_method="cash",
            paid_amount=Decimal("100.00"),
            notes="Test sale",
            items=[
                SaleItemCreate(
                    product_id=product.id,
                    product_code=product.code,
                    product_name=product.name,
                    unit="ชิ้น",
                    quantity=1,
                    unit_price=Decimal("100.00"),
                    discount=Decimal("10.00"),
                    line_total=Decimal("90.00"),
                )
            ],
        )

        sale = await sale_service.create(sale_data, store_id=STORE_ID)

        assert sale.id is not None
        assert sale.bill_no.startswith("POS-")
        assert sale.customer_name == "Test Customer"
        assert sale.payment_method == "cash"
        assert sale.status == "completed"
        assert sale.subtotal == Decimal("90.00")
        assert sale.discount == Decimal("10.00")
        # Backend calculates VAT: (90 - 10) * 0.07 = 5.60
        assert sale.vat == Decimal("5.60")
        assert sale.total == Decimal("85.60")
        assert sale.store_id == STORE_ID

        # Check stock was reduced
        updated_product = await product_service.get(product.id, store_id=STORE_ID)
        assert updated_product.stock == 9

    @pytest.mark.asyncio
    async def test_create_sale_credit(self, test_session: AsyncSession):
        """Test creating a credit sale (should be held)."""
        product_service = ProductService(test_session)
        sale_service = SaleService(test_session)
        setting_service = SettingService(test_session)

        await setting_service.set("vat", "exclude", "VAT mode", store_id=STORE_ID)

        product = await product_service.create(ProductCreate(
            code="SALE002",
            name="Credit Product",
            price=Decimal("200.00"),
            stock=5,
        ), store_id=STORE_ID)

        sale_data = SaleCreate(
            customer_name="Credit Customer",
            payment_method="credit",
            paid_amount=Decimal("0.00"),
            items=[
                SaleItemCreate(
                    product_id=product.id,
                    product_code=product.code,
                    product_name=product.name,
                    unit="ชิ้น",
                    quantity=1,
                    unit_price=Decimal("200.00"),
                    discount=Decimal("0.00"),
                    line_total=Decimal("200.00"),
                )
            ],
        )

        sale = await sale_service.create(sale_data, store_id=STORE_ID)

        assert sale.status == "held"
        assert sale.payment_method == "credit"

    @pytest.mark.asyncio
    async def test_get_sale(self, test_session: AsyncSession):
        """Test getting a sale by ID."""
        product_service = ProductService(test_session)
        sale_service = SaleService(test_session)
        setting_service = SettingService(test_session)

        await setting_service.set("vat", "exclude", "VAT mode", store_id=STORE_ID)

        product = await product_service.create(ProductCreate(
            code="SALE003",
            name="Get Sale Product",
            price=Decimal("150.00"),
            stock=10,
        ), store_id=STORE_ID)

        sale_data = SaleCreate(
            payment_method="cash",
            paid_amount=Decimal("150.00"),
            items=[
                SaleItemCreate(
                    product_id=product.id,
                    product_code=product.code,
                    product_name=product.name,
                    unit="ชิ้น",
                    quantity=1,
                    unit_price=Decimal("150.00"),
                    discount=Decimal("0.00"),
                    line_total=Decimal("150.00"),
                )
            ],
        )
        created = await sale_service.create(sale_data, store_id=STORE_ID)

        sale = await sale_service.get(created.id, store_id=STORE_ID)

        assert sale is not None
        assert sale.id == created.id
        assert len(sale.items) == 1

    @pytest.mark.asyncio
    async def test_get_sale_by_bill_no(self, test_session: AsyncSession):
        """Test getting a sale by bill number."""
        product_service = ProductService(test_session)
        sale_service = SaleService(test_session)
        setting_service = SettingService(test_session)

        await setting_service.set("vat", "exclude", "VAT mode", store_id=STORE_ID)

        product = await product_service.create(ProductCreate(
            code="SALE004",
            name="Bill No Product",
            price=Decimal("100.00"),
            stock=10,
        ), store_id=STORE_ID)

        sale_data = SaleCreate(
            payment_method="cash",
            paid_amount=Decimal("100.00"),
            items=[
                SaleItemCreate(
                    product_id=product.id,
                    product_code=product.code,
                    product_name=product.name,
                    unit="ชิ้น",
                    quantity=1,
                    unit_price=Decimal("100.00"),
                    discount=Decimal("0.00"),
                    line_total=Decimal("100.00"),
                )
            ],
        )
        created = await sale_service.create(sale_data, store_id=STORE_ID)

        sale = await sale_service.get_by_bill_no(created.bill_no, store_id=STORE_ID)

        assert sale is not None
        assert sale.bill_no == created.bill_no

    @pytest.mark.asyncio
    async def test_list_sales(self, test_session: AsyncSession):
        """Test listing sales with filters."""
        product_service = ProductService(test_session)
        sale_service = SaleService(test_session)
        setting_service = SettingService(test_session)

        await setting_service.set("vat", "exclude", "VAT mode", store_id=STORE_ID)

        product = await product_service.create(ProductCreate(
            code="SALE005",
            name="List Sale Product",
            price=Decimal("100.00"),
            stock=20,
        ), store_id=STORE_ID)

        # Create multiple sales
        for i in range(3):
            await sale_service.create(SaleCreate(
                payment_method="cash",
                paid_amount=Decimal("100.00"),
                items=[
                    SaleItemCreate(
                        product_id=product.id,
                        product_code=product.code,
                        product_name=product.name,
                        unit="ชิ้น",
                        quantity=1,
                        unit_price=Decimal("100.00"),
                        discount=Decimal("0.00"),
                        line_total=Decimal("100.00"),
                    )
                ],
            ), store_id=STORE_ID)

        sales, total = await sale_service.list(page=1, page_size=2, store_id=STORE_ID)

        assert len(sales) == 2
        assert total == 3

    @pytest.mark.asyncio
    async def test_daily_summary(self, test_session: AsyncSession):
        """Test daily sales summary."""
        product_service = ProductService(test_session)
        sale_service = SaleService(test_session)
        setting_service = SettingService(test_session)

        await setting_service.set("vat", "exclude", "VAT mode", store_id=STORE_ID)

        product = await product_service.create(ProductCreate(
            code="SALE006",
            name="Summary Product",
            price=Decimal("100.00"),
            stock=10,
        ), store_id=STORE_ID)

        await sale_service.create(SaleCreate(
            payment_method="cash",
            paid_amount=Decimal("100.00"),
            items=[
                SaleItemCreate(
                    product_id=product.id,
                    product_code=product.code,
                    product_name=product.name,
                    unit="ชิ้น",
                    quantity=1,
                    unit_price=Decimal("100.00"),
                    discount=Decimal("0.00"),
                    line_total=Decimal("100.00"),
                )
            ],
        ), store_id=STORE_ID)

        summary = await sale_service.get_daily_summary(datetime.utcnow(), store_id=STORE_ID)

        assert summary["count"] == 1
        # With VAT exclude mode: 100 + (100 * 0.07) = 107
        assert summary["total"] == 107.00
