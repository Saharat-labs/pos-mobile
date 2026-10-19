"""Debt service - business logic for customer debts."""

from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models import Debt, DebtPayment, Sale
from app.schemas import DebtCreate, DebtUpdate, DebtPaymentCreate


class DebtService:
    """Debt business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: DebtCreate) -> Debt:
        """Create new debt record."""
        debt = Debt(
            customer_name=data.customer_name,
            customer_phone=data.customer_phone,
            total_debt=Decimal(0),
            paid_amount=Decimal(0),
            remaining=Decimal(0),
            status="open",
            notes=data.notes,
        )
        self.db.add(debt)
        await self.db.commit()
        await self.db.refresh(debt)
        return debt

    async def get(self, debt_id: int) -> Optional[Debt]:
        """Get debt by ID with payments."""
        result = await self.db.execute(
            select(Debt).options(selectinload(Debt.payments)).where(Debt.id == debt_id)
        )
        return result.scalar_one_or_none()

    async def get_by_customer(self, customer_name: str) -> Optional[Debt]:
        """Get open debt by customer name."""
        result = await self.db.execute(
            select(Debt)
            .options(selectinload(Debt.payments))
            .where(Debt.customer_name == customer_name)
            .where(Debt.status != "paid")
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        page: int = 1,
        page_size: int = 50,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> tuple[List[Debt], int]:
        """List debts with filters."""
        query = select(Debt).options(selectinload(Debt.payments))

        if status:
            query = query.where(Debt.status == status)
        if search:
            query = query.where(
                Debt.customer_name.ilike(f"%{search}%") |
                Debt.customer_phone.ilike(f"%{search}%")
            )

        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        query = query.order_by(desc(Debt.created_at)).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return items, total

    async def add_payment(self, debt_id: int, data: DebtPaymentCreate) -> Optional[DebtPayment]:
        """Add payment to debt."""
        debt = await self.get(debt_id)
        if not debt:
            return None

        payment = DebtPayment(
            debt_id=debt_id,
            amount=data.amount,
            payment_method=data.payment_method,
            notes=data.notes,
        )
        self.db.add(payment)

        # Update debt totals
        debt.paid_amount += data.amount
        debt.remaining = debt.total_debt - debt.paid_amount

        if debt.remaining <= 0:
            debt.status = "paid"
            debt.remaining = Decimal(0)
        elif debt.paid_amount > 0:
            debt.status = "partial"

        await self.db.commit()
        await self.db.refresh(payment)
        await self.db.refresh(debt)
        return payment

    async def update(self, debt_id: int, data: DebtUpdate) -> Optional[Debt]:
        """Update debt info."""
        debt = await self.get(debt_id)
        if not debt:
            return None

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(debt, field, value)

        await self.db.commit()
        await self.db.refresh(debt)
        return debt

    async def create_from_sale(self, sale: Sale) -> Debt:
        """Create debt from credit sale."""
        existing = await self.get_by_customer(sale.customer_name)
        if existing:
            existing.total_debt += sale.total
            existing.remaining = existing.total_debt - existing.paid_amount
            existing.status = "partial" if existing.paid_amount > 0 else "open"
            await self.db.commit()
            await self.db.refresh(existing)
            return existing

        debt = Debt(
            customer_name=sale.customer_name,
            customer_phone=sale.customer_phone,
            total_debt=sale.total,
            paid_amount=Decimal(0),
            remaining=sale.total,
            status="open",
            notes=f"จากบิล {sale.bill_no}",
        )
        self.db.add(debt)
        await self.db.commit()
        await self.db.refresh(debt)
        return debt

    async def get_total_outstanding(self) -> Decimal:
        """Get total outstanding debt."""
        result = await self.db.execute(
            select(func.coalesce(func.sum(Debt.remaining), 0)).where(Debt.status != "paid")
        )
        return result.scalar() or Decimal(0)