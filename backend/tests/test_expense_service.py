"""Tests for ExpenseService."""
import pytest
from decimal import Decimal
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.expense_service import ExpenseService
from app.schemas import ExpenseCreate, ExpenseUpdate


class TestExpenseService:
    """Test ExpenseService methods."""

    @pytest.mark.asyncio
    async def test_create_expense(self, test_session: AsyncSession):
        """Test creating an expense."""
        service = ExpenseService(test_session)

        expense_data = ExpenseCreate(
            date=datetime.utcnow(),
            category="ค่าสาธารณูปโภค",
            description="ค่าไฟฟ้าเดือนมกราคม",
            amount=Decimal("1500.00"),
            payment_method="cash",
            notes="Electric bill",
        )

        expense = await service.create(expense_data)

        assert expense.id is not None
        assert expense.category == "ค่าสาธารณูปโภค"
        assert expense.amount == Decimal("1500.00")
        assert expense.payment_method == "cash"

    @pytest.mark.asyncio
    async def test_get_expense(self, test_session: AsyncSession):
        """Test getting an expense by ID."""
        service = ExpenseService(test_session)

        expense_data = ExpenseCreate(
            date=datetime.utcnow(),
            category="ค่าเช่า",
            description="ค่าเช่าร้าน",
            amount=Decimal("10000.00"),
        )
        created = await service.create(expense_data)

        expense = await service.get(created.id)

        assert expense is not None
        assert expense.id == created.id
        assert expense.category == "ค่าเช่า"

    @pytest.mark.asyncio
    async def test_update_expense(self, test_session: AsyncSession):
        """Test updating an expense."""
        service = ExpenseService(test_session)

        expense_data = ExpenseCreate(
            date=datetime.utcnow(),
            category="ค่าอุปกรณ์",
            description="ซื้อคอมพิวเตอร์",
            amount=Decimal("25000.00"),
        )
        created = await service.create(expense_data)

        update_data = ExpenseUpdate(
            category="ค่าอุปกรณ์สำนักงาน",
            amount=Decimal("26000.00"),
        )
        updated = await service.update(created.id, update_data)

        assert updated is not None
        assert updated.category == "ค่าอุปกรณ์สำนักงาน"
        assert updated.amount == Decimal("26000.00")

    @pytest.mark.asyncio
    async def test_delete_expense(self, test_session: AsyncSession):
        """Test deleting an expense."""
        service = ExpenseService(test_session)

        expense_data = ExpenseCreate(
            date=datetime.utcnow(),
            category="ค่าต่างๆ",
            description="รายจ่ายทั่วไป",
            amount=Decimal("500.00"),
        )
        created = await service.create(expense_data)

        result = await service.delete(created.id)

        assert result is True

        # Verify deleted
        deleted = await service.get(created.id)
        assert deleted is None

    @pytest.mark.asyncio
    async def test_list_expenses(self, test_session: AsyncSession):
        """Test listing expenses with filters."""
        service = ExpenseService(test_session)

        now = datetime.utcnow()
        for i in range(5):
            await service.create(ExpenseCreate(
                date=now,
                category=f"Category {i % 3}",
                description=f"Expense {i}",
                amount=Decimal(f"{100 * (i + 1)}.00"),
            ))

        expenses, total = await service.list(page=1, page_size=2)

        assert len(expenses) == 2
        assert total == 5

    @pytest.mark.asyncio
    async def test_list_expenses_with_filters(self, test_session: AsyncSession):
        """Test listing expenses with date and category filters."""
        service = ExpenseService(test_session)

        now = datetime.utcnow()
        await service.create(ExpenseCreate(
            date=now,
            category="ค่าอาหาร",
            description="Lunch",
            amount=Decimal("200.00"),
        ))
        await service.create(ExpenseCreate(
            date=now,
            category="ค่าขนส่ง",
            description="Taxi",
            amount=Decimal("100.00"),
        ))

        # Filter by category
        expenses, total = await service.list(category="ค่าอาหาร")

        assert total == 1
        assert expenses[0].category == "ค่าอาหาร"

    @pytest.mark.asyncio
    async def test_get_categories(self, test_session: AsyncSession):
        """Test getting unique expense categories."""
        service = ExpenseService(test_session)

        await service.create(ExpenseCreate(
            date=datetime.utcnow(),
            category="ค่าอาหาร",
            description="Lunch",
            amount=Decimal("200.00"),
        ))
        await service.create(ExpenseCreate(
            date=datetime.utcnow(),
            category="ค่าขนส่ง",
            description="Taxi",
            amount=Decimal("100.00"),
        ))
        await service.create(ExpenseCreate(
            date=datetime.utcnow(),
            category="ค่าอาหาร",
            description="Dinner",
            amount=Decimal("300.00"),
        ))

        categories = await service.get_categories()

        assert "ค่าอาหาร" in categories
        assert "ค่าขนส่ง" in categories
        assert len(categories) == 2

    @pytest.mark.asyncio
    async def test_monthly_summary(self, test_session: AsyncSession):
        """Test monthly expense summary."""
        service = ExpenseService(test_session)

        now = datetime.utcnow()
        await service.create(ExpenseCreate(
            date=now,
            category="ค่าอาหาร",
            description="Lunch",
            amount=Decimal("200.00"),
        ))
        await service.create(ExpenseCreate(
            date=now,
            category="ค่าขนส่ง",
            description="Taxi",
            amount=Decimal("100.00"),
        ))

        summary = await service.get_monthly_summary(now.year, now.month)

        assert "total" in summary
        assert "categories" in summary
        assert summary["total"] == 300.0
        # categories is a list of {category, total, count}
        by_cat = {c["category"]: c["total"] for c in summary["categories"]}
        assert by_cat["ค่าอาหาร"] == 200.0
        assert by_cat["ค่าขนส่ง"] == 100.0

    @pytest.mark.asyncio
    async def test_yearly_summary(self, test_session: AsyncSession):
        """Test yearly expense summary."""
        service = ExpenseService(test_session)

        now = datetime.utcnow()
        await service.create(ExpenseCreate(
            date=now,
            category="ค่าอาหาร",
            description="Lunch",
            amount=Decimal("200.00"),
        ))

        summary = await service.get_yearly_summary(now.year)

        assert "total" in summary
        assert "months" in summary
        assert summary["total"] == 200.0
        # months is {month: total} with string keys
        assert summary["months"][str(now.month)] == 200.0