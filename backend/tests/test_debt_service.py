"""Tests for DebtService."""
import pytest
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.debt_service import DebtService
from app.schemas import DebtCreate, DebtUpdate, DebtPaymentCreate


class TestDebtService:
    """Test DebtService methods."""

    @pytest.mark.asyncio
    async def test_create_debt(self, test_session: AsyncSession):
        """Test creating a debt record (starts at 0, add payments after)."""
        service = DebtService(test_session)

        debt_data = DebtCreate(
            customer_name="Debt Customer",
            customer_phone="0811112222",
            notes="Initial debt",
        )

        debt = await service.create(debt_data)

        assert debt.id is not None
        assert debt.customer_name == "Debt Customer"
        # Manual debt starts at 0 — amount is added via payments
        assert debt.total_debt == Decimal("0")
        assert debt.paid_amount == Decimal("0")
        assert debt.remaining == Decimal("0")
        assert debt.status == "open"

    @pytest.mark.asyncio
    async def test_get_debt(self, test_session: AsyncSession):
        """Test getting a debt by ID."""
        service = DebtService(test_session)

        created = await service.create(DebtCreate(
            customer_name="Get Debt Customer",
        ))

        debt = await service.get(created.id)

        assert debt is not None
        assert debt.id == created.id
        assert debt.customer_name == "Get Debt Customer"

    @pytest.mark.asyncio
    async def test_get_debt_by_customer(self, test_session: AsyncSession):
        """Test getting open debt by customer name (returns single or None)."""
        service = DebtService(test_session)

        await service.create(DebtCreate(customer_name="Solo Customer"))

        debt = await service.get_by_customer("Solo Customer")

        assert debt is not None
        assert debt.customer_name == "Solo Customer"

        # Nonexistent customer returns None
        missing = await service.get_by_customer("Nobody")
        assert missing is None

    @pytest.mark.asyncio
    async def test_add_payment(self, test_session: AsyncSession):
        """Test adding a payment to a debt updates totals."""
        service = DebtService(test_session)

        debt = await service.create(DebtCreate(customer_name="Payment Customer"))

        # Seed total_debt via update then add payment
        await service.update(debt.id, DebtUpdate(customer_name="Payment Customer"))
        debt.total_debt = Decimal("1000.00")
        debt.remaining = Decimal("1000.00")
        await test_session.commit()

        payment = await service.add_payment(debt.id, DebtPaymentCreate(
            amount=Decimal("300.00"),
            payment_method="cash",
            notes="Partial payment",
        ))

        assert payment.id is not None
        assert payment.amount == Decimal("300.00")
        assert payment.payment_method == "cash"

        updated_debt = await service.get(debt.id)
        assert updated_debt.paid_amount == Decimal("300.00")
        assert updated_debt.remaining == Decimal("700.00")
        assert updated_debt.status == "partial"

    @pytest.mark.asyncio
    async def test_update_debt(self, test_session: AsyncSession):
        """Test updating a debt."""
        service = DebtService(test_session)

        created = await service.create(DebtCreate(
            customer_name="Original Name",
            notes="Original notes",
        ))

        updated = await service.update(created.id, DebtUpdate(
            customer_name="Updated Name",
            notes="Updated notes",
        ))

        assert updated is not None
        assert updated.customer_name == "Updated Name"
        assert updated.notes == "Updated notes"

    @pytest.mark.asyncio
    async def test_list_debts(self, test_session: AsyncSession):
        """Test listing debts with pagination."""
        service = DebtService(test_session)

        for i in range(5):
            await service.create(DebtCreate(customer_name=f"List Customer {i}"))

        debts, total = await service.list(page=1, page_size=2)

        assert len(debts) == 2
        assert total == 5

    @pytest.mark.asyncio
    async def test_total_outstanding(self, test_session: AsyncSession):
        """Test total outstanding debt sum."""
        service = DebtService(test_session)

        debt1 = await service.create(DebtCreate(customer_name="Out Customer 1"))
        debt2 = await service.create(DebtCreate(customer_name="Out Customer 2"))

        # Set total_debt directly on each
        debt1.total_debt = Decimal("100.00")
        debt1.remaining = Decimal("100.00")
        debt2.total_debt = Decimal("200.00")
        debt2.remaining = Decimal("200.00")
        await test_session.commit()

        total = await service.get_total_outstanding()

        assert total == Decimal("300.00")
