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
        """Test creating a debt record."""
        service = DebtService(test_session)

        debt_data = DebtCreate(
            customer_name="Debt Customer",
            customer_phone="0811112222",
            total_debt=Decimal("500.00"),
            notes="Initial debt",
        )

        debt = await service.create(debt_data)

        assert debt.id is not None
        assert debt.customer_name == "Debt Customer"
        assert debt.total_debt == Decimal("500.00")
        assert debt.paid_amount == Decimal("0.00")
        assert debt.remaining == Decimal("500.00")
        assert debt.status == "open"

    @pytest.mark.asyncio
    async def test_get_debt(self, test_session: AsyncSession):
        """Test getting a debt by ID."""
        service = DebtService(test_session)

        debt_data = DebtCreate(
            customer_name="Get Debt Customer",
            total_debt=Decimal("300.00"),
        )
        created = await service.create(debt_data)

        debt = await service.get(created.id)

        assert debt is not None
        assert debt.id == created.id
        assert debt.customer_name == "Get Debt Customer"

    @pytest.mark.asyncio
    async def test_get_debt_by_customer(self, test_session: AsyncSession):
        """Test getting debts by customer name."""
        service = DebtService(test_session)

        # Create multiple debts for same customer
        await service.create(DebtCreate(
            customer_name="Multi Debt Customer",
            total_debt=Decimal("100.00"),
        ))
        await service.create(DebtCreate(
            customer_name="Multi Debt Customer",
            total_debt=Decimal("200.00"),
        ))
        await service.create(DebtCreate(
            customer_name="Other Customer",
            total_debt=Decimal("500.00"),
        ))

        debts = await service.get_by_customer("Multi Debt Customer")

        assert len(debts) == 2
        assert all(d.customer_name == "Multi Debt Customer" for d in debts)

    @pytest.mark.asyncio
    async def test_add_payment(self, test_session: AsyncSession):
        """Test adding a payment to a debt."""
        service = DebtService(test_session)

        debt_data = DebtCreate(
            customer_name="Payment Customer",
            total_debt=Decimal("1000.00"),
        )
        debt = await service.create(debt_data)

        # Add partial payment
        payment_data = DebtPaymentCreate(
            amount=Decimal("300.00"),
            payment_method="cash",
            notes="Partial payment",
        )
        payment = await service.add_payment(debt.id, payment_data)

        assert payment.id is not None
        assert payment.amount == Decimal("300.00")
        assert payment.payment_method == "cash"

        # Check debt updated
        updated_debt = await service.get(debt.id)
        assert updated_debt.paid_amount == Decimal("300.00")
        assert updated_debt.remaining == Decimal("700.00")
        assert updated_debt.status == "partial"

    @pytest.mark.asyncio
    async def test_full_payment(self, test_session: AsyncSession):
        """Test paying off a debt completely."""
        service = DebtService(test_session)

        debt_data = DebtCreate(
            customer_name="Full Pay Customer",
            total_debt=Decimal("250.00"),
        )
        debt = await service.create(debt_data)

        # Full payment
        payment_data = DebtPaymentCreate(
            amount=Decimal("250.00"),
            payment_method="transfer",
        )
        await service.add_payment(debt.id, payment_data)

        updated_debt = await service.get(debt.id)
        assert updated_debt.paid_amount == Decimal("250.00")
        assert updated_debt.remaining == Decimal("0.00")
        assert updated_debt.status == "paid"

    @pytest.mark.asyncio
    async def test_update_debt(self, test_session: AsyncSession):
        """Test updating a debt."""
        service = DebtService(test_session)

        debt_data = DebtCreate(
            customer_name="Original Name",
            total_debt=Decimal("400.00"),
            notes="Original notes",
        )
        created = await service.create(debt_data)

        from app.schemas import DebtUpdate
        update_data = DebtUpdate(
            customer_name="Updated Name",
            notes="Updated notes",
        )
        updated = await service.update(created.id, update_data)

        assert updated is not None
        assert updated.customer_name == "Updated Name"
        assert updated.notes == "Updated notes"

    @pytest.mark.asyncio
    async def test_list_debts(self, test_session: AsyncSession):
        """Test listing debts with pagination."""
        service = DebtService(test_session)

        for i in range(5):
            await service.create(DebtCreate(
                customer_name=f"List Customer {i}",
                total_debt=Decimal(f"{100 * (i + 1)}.00"),
            ))

        debts, total = await service.list(page=1, page_size=2)

        assert len(debts) == 2
        assert total == 5

    @pytest.mark.asyncio
    async def test_debt_summary(self, test_session: AsyncSession):
        """Test debt summary."""
        service = DebtService(test_session)

        await service.create(DebtCreate(
            customer_name="Summary Customer 1",
            total_debt=Decimal("100.00"),
        ))
        await service.create(DebtCreate(
            customer_name="Summary Customer 2",
            total_debt=Decimal("200.00"),
        ))

        # Add payment to first
        debt1 = await service.get_by_customer("Summary Customer 1")
        await service.add_payment(debt1[0].id, DebtPaymentCreate(
            amount=Decimal("50.00"),
            payment_method="cash",
        ))

        summary = await service.get_summary()

        assert summary["total_customers"] == 2
        assert summary["total_debt"] == 300.0
        assert summary["total_paid"] == 50.0
        assert summary["total_remaining"] == 250.0
        assert summary["open_count"] == 1
        assert summary["partial_count"] == 1
        assert summary["paid_count"] == 0