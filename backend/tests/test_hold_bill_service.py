"""Tests for HoldBillService."""
import pytest
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.hold_bill_service import HoldBillService
from app.schemas import HoldBillCreate


class TestHoldBillService:
    """Test HoldBillService methods."""

    @pytest.mark.asyncio
    async def test_create_hold_bill(self, test_session: AsyncSession):
        """Test creating a held bill."""
        service = HoldBillService(test_session)

        import json
        items = [
            {"product_id": 1, "product_code": "TEST001", "product_name": "Test Product", "quantity": 2, "unit_price": "100.00"}
        ]

        hold_data = HoldBillCreate(
            bill_no="HOLD-001",
            items=json.dumps(items),
            customer_name="Hold Customer",
            customer_phone="0812345678",
            subtotal=Decimal("200.00"),
            discount=Decimal("10.00"),
            vat=Decimal("13.30"),
            total=Decimal("203.30"),
        )

        hold_bill = await service.create(hold_data)

        assert hold_bill.id is not None
        assert hold_bill.bill_no.startswith("HOLD-")
        assert hold_bill.customer_name == "Hold Customer"
        assert hold_bill.total == Decimal("203.30")

    @pytest.mark.asyncio
    async def test_get_hold_bill(self, test_session: AsyncSession):
        """Test getting a held bill by ID."""
        service = HoldBillService(test_session)

        import json
        items = [{"product_id": 1, "quantity": 1}]

        hold_data = HoldBillCreate(
            bill_no="HOLD-002",
            items=json.dumps(items),
            subtotal=Decimal("100.00"),
            total=Decimal("100.00"),
        )
        created = await service.create(hold_data)

        hold_bill = await service.get(created.id)

        assert hold_bill is not None
        assert hold_bill.id == created.id
        # Service generates its own bill_no (client-sent value is ignored)
        assert hold_bill.bill_no == created.bill_no
        assert hold_bill.bill_no.startswith("HOLD-")

    @pytest.mark.asyncio
    async def test_get_hold_bill_by_bill_no(self, test_session: AsyncSession):
        """Test getting a held bill by bill number."""
        service = HoldBillService(test_session)

        import json
        items = [{"product_id": 1, "quantity": 1}]

        hold_data = HoldBillCreate(
            bill_no="HOLD-003",
            items=json.dumps(items),
            subtotal=Decimal("100.00"),
            total=Decimal("100.00"),
        )
        created = await service.create(hold_data)

        hold_bill = await service.get_by_bill_no(created.bill_no)

        assert hold_bill is not None
        assert hold_bill.bill_no == created.bill_no

    @pytest.mark.asyncio
    async def test_list_hold_bills(self, test_session: AsyncSession):
        """Test listing held bills."""
        service = HoldBillService(test_session)

        import json
        items = [{"product_id": 1, "quantity": 1}]

        for i in range(3):
            await service.create(HoldBillCreate(
                bill_no=f"HOLD-LIST-{i:03d}",
                items=json.dumps(items),
                subtotal=Decimal("100.00"),
                total=Decimal("100.00"),
            ))

        bills, total = await service.list(page=1, page_size=2)

        assert len(bills) == 2
        assert total == 3

    @pytest.mark.asyncio
    async def test_delete_hold_bill(self, test_session: AsyncSession):
        """Test deleting a held bill."""
        service = HoldBillService(test_session)

        import json
        items = [{"product_id": 1, "quantity": 1}]

        hold_data = HoldBillCreate(
            bill_no="HOLD-DELETE",
            items=json.dumps(items),
            subtotal=Decimal("100.00"),
            total=Decimal("100.00"),
        )
        created = await service.create(hold_data)

        result = await service.delete(created.id)

        assert result is True

        # Verify deleted
        deleted = await service.get(created.id)
        assert deleted is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_hold_bill(self, test_session: AsyncSession):
        """Test deleting a non-existent held bill returns False."""
        service = HoldBillService(test_session)

        result = await service.delete(99999)

        assert result is False