"""Tests for SyncService."""
import pytest
from decimal import Decimal
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.sync_service import SyncService
from app.services.product_service import ProductService
from app.services.sale_service import SaleService
from app.services.setting_service import SettingService
from app.schemas import (
    SyncRequest, ProductCreate, SaleCreate, SaleItemCreate,
    PurchaseCreate, PurchaseItemCreate, DebtCreate,
    ExpenseCreate, StockMovementCreate, HoldBillCreate,
    SettingCreate, CategoryMappingCreate
)


class TestSyncService:
    """Test SyncService methods."""

    @pytest.mark.asyncio
    async def test_sync_products(self, test_session: AsyncSession):
        """Test syncing products from client."""
        service = SyncService(test_session)

        sync_data = SyncRequest(
            products=[
                ProductCreate(
                    code="SYNC001",
                    name="Synced Product",
                    price=Decimal("150.00"),
                    stock=20,
                ),
                ProductCreate(
                    code="SYNC002",
                    name="Another Product",
                    price=Decimal("200.00"),
                    stock=10,
                ),
            ]
        )

        result = await service.sync_from_client(sync_data)

        assert result.success is True
        assert result.counts["products"] == 2

        # Verify products created
        product_service = ProductService(test_session)
        p1 = await product_service.get_by_code("SYNC001")
        p2 = await product_service.get_by_code("SYNC002")
        assert p1 is not None
        assert p2 is not None
        assert p1.name == "Synced Product"
        assert p2.stock == 10

    @pytest.mark.asyncio
    async def test_sync_sales(self, test_session: AsyncSession):
        """Test syncing sales from client."""
        product_service = ProductService(test_session)
        setting_service = SettingService(test_session)
        await setting_service.set("vat", "exclude", "VAT mode")

        # Create product first
        product = await product_service.create(ProductCreate(
            code="SYNC003",
            name="Sale Sync Product",
            price=Decimal("100.00"),
            stock=50,
        ))

        service = SyncService(test_session)

        sync_data = SyncRequest(
            sales=[
                SaleCreate(
                    customer_name="Sync Customer",
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
            ]
        )

        result = await service.sync_from_client(sync_data)

        assert result.success is True
        assert result.counts["sales"] == 1

        # Verify sale created
        sale_service = SaleService(test_session)
        sales, total = await sale_service.list(store_id=1)
        assert total == 1
        assert sales[0].customer_name == "Sync Customer"

    @pytest.mark.asyncio
    async def test_sync_purchases(self, test_session: AsyncSession):
        """Test syncing purchases from client."""
        product_service = ProductService(test_session)
        await product_service.create(ProductCreate(
            code="SYNC004",
            name="Purchase Sync Product",
            price=Decimal("100.00"),
        ))

        service = SyncService(test_session)

        sync_data = SyncRequest(
            purchases=[
                PurchaseCreate(
                    supplier_name="Sync Supplier",
                    items=[
                        PurchaseItemCreate(
                            product_id=1,  # Will be matched by code
                            product_code="SYNC004",
                            product_name="Purchase Sync Product",
                            unit="ชิ้น",
                            quantity=10,
                            unit_cost=Decimal("50.00"),
                            line_total=Decimal("500.00"),
                        )
                    ],
                )
            ]
        )

        result = await service.sync_from_client(sync_data)

        assert result.success is True
        assert result.counts["purchases"] == 1

    @pytest.mark.asyncio
    async def test_sync_debts(self, test_session: AsyncSession):
        """Test syncing debts from client."""
        service = SyncService(test_session)

        sync_data = SyncRequest(
            debts=[
                DebtCreate(
                    customer_name="Sync Debt Customer",
                    customer_phone="0812345678",
                    total_debt=Decimal("500.00"),
                    paid_amount=Decimal("100.00"),
                    notes="Synced debt",
                )
            ]
        )

        result = await service.sync_from_client(sync_data)

        assert result.success is True
        assert result.counts["debts"] == 1

    @pytest.mark.asyncio
    async def test_sync_expenses(self, test_session: AsyncSession):
        """Test syncing expenses from client."""
        service = SyncService(test_session)

        sync_data = SyncRequest(
            expenses=[
                ExpenseCreate(
                    date=datetime.utcnow(),
                    category="Synced Expense",
                    description="Test expense",
                    amount=Decimal("250.00"),
                    payment_method="cash",
                )
            ]
        )

        result = await service.sync_from_client(sync_data)

        assert result.success is True
        assert result.counts["expenses"] == 1

    @pytest.mark.asyncio
    async def test_sync_stock_movements(self, test_session: AsyncSession):
        """Test syncing stock movements from client."""
        product_service = ProductService(test_session)
        await product_service.create(ProductCreate(
            code="SYNC005",
            name="Stock Sync Product",
            price=Decimal("100.00"),
        ))

        service = SyncService(test_session)

        sync_data = SyncRequest(
            stock_movements=[
                StockMovementCreate(
                    product_id=1,
                    movement_type="in",
                    quantity=5,
                    reference_type="manual",
                    notes="Manual adjustment",
                )
            ]
        )

        result = await service.sync_from_client(sync_data)

        assert result.success is True
        assert result.counts["stock_movements"] == 1

    @pytest.mark.asyncio
    async def test_sync_hold_bills(self, test_session: AsyncSession):
        """Test syncing hold bills from client."""
        service = SyncService(test_session)

        import json
        items = [{"product_id": 1, "quantity": 2}]

        sync_data = SyncRequest(
            hold_bills=[
                HoldBillCreate(
                    bill_no="SYNC-HOLD-001",
                    items=json.dumps(items),
                    subtotal=Decimal("200.00"),
                    total=Decimal("200.00"),
                )
            ]
        )

        result = await service.sync_from_client(sync_data)

        assert result.success is True
        assert result.counts["hold_bills"] == 1

    @pytest.mark.asyncio
    async def test_sync_settings(self, test_session: AsyncSession):
        """Test syncing settings from client."""
        service = SyncService(test_session)

        sync_data = SyncRequest(
            settings=[
                SettingCreate(key="synced_key_1", value="value_1"),
                SettingCreate(key="synced_key_2", value="value_2"),
            ]
        )

        result = await service.sync_from_client(sync_data)

        assert result.success is True
        assert result.counts["settings"] == 2

    @pytest.mark.asyncio
    async def test_sync_category_mappings(self, test_session: AsyncSession):
        """Test syncing category mappings from client."""
        service = SyncService(test_session)

        sync_data = SyncRequest(
            category_mappings=[
                CategoryMappingCreate(code_prefix="99", category="Synced Category"),
            ]
        )

        result = await service.sync_from_client(sync_data)

        assert result.success is True
        assert result.counts["category_mappings"] == 1

    @pytest.mark.asyncio
    async def test_full_sync(self, test_session: AsyncSession):
        """Test syncing all data types at once."""
        product_service = ProductService(test_session)
        setting_service = SettingService(test_session)
        await setting_service.set("vat", "exclude", "VAT mode")

        await product_service.create(ProductCreate(
            code="FULL001",
            name="Full Sync Product",
            price=Decimal("100.00"),
            stock=100,
        ))

        service = SyncService(test_session)

        import json
        sync_data = SyncRequest(
            products=[
                ProductCreate(code="FULL002", name="New Product", price=Decimal("50.00")),
            ],
            sales=[
                SaleCreate(
                    payment_method="cash",
                    paid_amount=Decimal("100.00"),
                    items=[
                        SaleItemCreate(
                            product_id=1,
                            product_code="FULL001",
                            product_name="Full Sync Product",
                            unit="ชิ้น",
                            quantity=1,
                            unit_price=Decimal("100.00"),
                            discount=Decimal("0.00"),
                            line_total=Decimal("100.00"),
                        )
                    ],
                )
            ],
            settings=[
                SettingCreate(key="full_sync_test", value="test_value"),
            ],
        )

        result = await service.sync_from_client(sync_data)

        assert result.success is True
        assert result.counts["products"] == 1
        assert result.counts["sales"] == 1
        assert result.counts["settings"] == 1

    @pytest.mark.asyncio
    async def test_backup(self, test_session: AsyncSession):
        """Test creating a full backup."""
        product_service = ProductService(test_session)
        await product_service.create(ProductCreate(
            code="BACKUP001",
            name="Backup Product",
            price=Decimal("100.00"),
        ))

        service = SyncService(test_session)
        backup = await service.full_backup()

        assert "products" in backup
        assert len(backup["products"]) >= 1
        # Backup dict includes code of the created product
        assert any(p["code"] == "BACKUP001" for p in backup["products"])

    @pytest.mark.asyncio
    async def test_restore(self, test_session: AsyncSession):
        """Test restoring from backup."""
        product_service = ProductService(test_session)
        await product_service.create(ProductCreate(
            code="RESTORE001",
            name="Original",
            price=Decimal("100.00"),
        ))

        service = SyncService(test_session)
        backup = await service.full_backup()

        # Delete the product
        from app.models import Product
        from sqlalchemy import select
        result = await test_session.execute(select(Product).where(Product.code == "RESTORE001"))
        product = result.scalar_one_or_none()
        if product:
            await test_session.delete(product)
            await test_session.commit()

        # Restore
        restore_result = await service.restore_backup(backup)

        assert restore_result.success is True
        assert restore_result.counts["products"] >= 1

        # Verify restored
        restored = await product_service.get_by_code("RESTORE001")
        assert restored is not None

    @pytest.mark.asyncio
    async def test_sync_sales_does_not_double_deduct_stock(self, test_session: AsyncSession):
        """🔴A: stock ใน payload เป็นค่าปัจจุบัน — sync sales ห้ามตัด stock ซ้ำ"""
        product_service = ProductService(test_session)
        await product_service.create(ProductCreate(
            code="NODEDUCT01",
            name="No Deduct",
            price=Decimal("50.00"),
            stock=10,
        ))

        service = SyncService(test_session)
        sync_data = SyncRequest(
            products=[ProductCreate(
                code="NODEDUCT01",
                name="No Deduct",
                price=Decimal("50.00"),
                stock=10,
            )],
            sales=[SaleCreate(
                customer_name="Sync A",
                payment_method="cash",
                paid_amount=Decimal("150.00"),
                items=[SaleItemCreate(
                    product_id=999999,  # id เก่าปลอม — ต้องผูกใหม่ด้วย code
                    product_code="NODEDUCT01",
                    product_name="No Deduct",
                    quantity=3,
                    unit_price=Decimal("50.00"),
                    line_total=Decimal("150.00"),
                )],
            )],
        )

        result = await service.sync_from_client(sync_data)

        assert result.success is True
        assert result.counts["sales"] == 1
        # stock ต้องเท่ากับค่าใน payload (10) ไม่ใช่ 10-3=7
        restored_product = await product_service.get_by_code("NODEDUCT01")
        assert restored_product.stock == 10

        # sale item ต้องผูก product ใหม่ถูกต้องด้วย product_code
        sales, total = await SaleService(test_session).list(store_id=1)
        assert total == 1
        sale_detail = await SaleService(test_session).get(sales[0].id, store_id=1)
        assert sale_detail.items[0].product_id == restored_product.id

    @pytest.mark.asyncio
    async def test_restore_with_sales_keeps_stock(self, test_session: AsyncSession):
        """🔴A: restore backup ที่มีขาย ต้องสำเร็จ + stock คงค่าเดิม (ไม่ตัดซ้ำ)"""
        product_service = ProductService(test_session)
        sale_service = SaleService(test_session)

        product = await product_service.create(ProductCreate(
            code="RESTORE002",
            name="Restore Kit",
            price=Decimal("100.00"),
            stock=5,
        ))
        # ขายจริง 4 ชิ้น → stock เหลือ 1
        await sale_service.create(SaleCreate(
            customer_name="Restore B",
            payment_method="cash",
            paid_amount=Decimal("400.00"),
            items=[SaleItemCreate(
                product_id=product.id,
                product_code="RESTORE002",
                product_name="Restore Kit",
                quantity=4,
                unit_price=Decimal("100.00"),
                line_total=Decimal("400.00"),
            )],
        ), store_id=1)

        service = SyncService(test_session)
        backup = await service.full_backup()
        # เงื่อนไขที่เคยทำให้ล้มเหลว: stock ใน backup = 1 แต่ sale ย้อนหลัง qty = 4 (1 < 4)
        # -> โค้ดเดิม ValueError → snapshot กู้ซ้ำก็ล้ม → ข้อมูลหาย
        restore_result = await service.restore_backup(backup)

        assert restore_result.success is True
        assert restore_result.counts["sales"] == 1

        restored_product = await product_service.get_by_code("RESTORE002")
        assert restored_product.stock == 1  # คงค่าจาก backup ไม่ถูกหักซ้ำ (1-4 ติดลบ)
        _, total = await sale_service.list(store_id=1)
        assert total == 1

    @pytest.mark.asyncio
    async def test_health_check(self, test_session: AsyncSession):
        """Test health check endpoint (route function, no service method)."""
        from app.api.sync import health_check

        health = await health_check()

        assert health["status"] == "healthy"
        assert health["database"] == "connected"
        assert "timestamp" in health