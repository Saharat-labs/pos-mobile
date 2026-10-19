"""Expense service - business logic for expenses."""

from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from sqlalchemy import select, func, desc, extract
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Expense
from app.schemas import ExpenseCreate, ExpenseUpdate


class ExpenseService:
    """Expense business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: ExpenseCreate) -> Expense:
        """Create new expense."""
        expense = Expense(
            date=data.date or datetime.utcnow(),
            category=data.category,
            description=data.description,
            amount=data.amount,
            payment_method=data.payment_method,
            notes=data.notes,
        )
        self.db.add(expense)
        await self.db.commit()
        await self.db.refresh(expense)
        return expense

    async def get(self, expense_id: int) -> Optional[Expense]:
        """Get expense by ID."""
        result = await self.db.execute(select(Expense).where(Expense.id == expense_id))
        return result.scalar_one_or_none()

    async def list(
        self,
        page: int = 1,
        page_size: int = 50,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        category: Optional[str] = None,
    ) -> tuple[List[Expense], int]:
        """List expenses with filters."""
        query = select(Expense)

        if start_date:
            query = query.where(Expense.date >= start_date)
        if end_date:
            query = query.where(Expense.date <= end_date)
        if category:
            query = query.where(Expense.category == category)

        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        query = query.order_by(desc(Expense.date)).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return items, total

    async def update(self, expense_id: int, data: ExpenseUpdate) -> Optional[Expense]:
        """Update expense."""
        expense = await self.get(expense_id)
        if not expense:
            return None

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(expense, field, value)

        await self.db.commit()
        await self.db.refresh(expense)
        return expense

    async def delete(self, expense_id: int) -> bool:
        """Delete expense."""
        expense = await self.get(expense_id)
        if not expense:
            return False
        await self.db.delete(expense)
        await self.db.commit()
        return True

    async def get_categories(self) -> List[str]:
        """Get all unique expense categories."""
        result = await self.db.execute(select(Expense.category).distinct())
        return result.scalars().all()

    async def get_monthly_summary(self, year: int, month: int) -> dict:
        """Get monthly expense summary by category."""
        result = await self.db.execute(
            select(
                Expense.category,
                func.coalesce(func.sum(Expense.amount), 0).label("total"),
                func.count(Expense.id).label("count"),
            )
            .where(extract("year", Expense.date) == year)
            .where(extract("month", Expense.date) == month)
            .group_by(Expense.category)
            .order_by(desc("total"))
        )
        categories = [
            {"category": cat, "total": float(tot), "count": cnt}
            for cat, tot, cnt in result.all()
        ]

        total = sum(c["total"] for c in categories)
        return {"year": year, "month": month, "total": total, "categories": categories}

    async def get_yearly_summary(self, year: int) -> dict:
        """Get yearly expense summary."""
        result = await self.db.execute(
            select(
                extract("month", Expense.date).label("month"),
                func.coalesce(func.sum(Expense.amount), 0).label("total"),
            )
            .where(extract("year", Expense.date) == year)
            .group_by("month")
            .order_by("month")
        )
        months = {int(m): float(t) for m, t in result.all()}
        # Fill missing months with 0
        for m in range(1, 13):
            if m not in months:
                months[m] = 0.0

        total = sum(months.values())
        return {"year": year, "total": total, "months": months}