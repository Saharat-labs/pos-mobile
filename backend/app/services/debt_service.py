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

    async def create(self, data: DebtCreate, store_id: int = 1) -> Debt:
        """Create new debt record (initial total_debt allowed)."""
        initial = data.total_debt or Decimal(0)
        debt = Debt(
            store_id=store_id,
            customer_name=data.customer_name,
            customer_phone=data.customer_phone,
            total_debt=initial,
            paid_amount=Decimal(0),
            remaining=initial,
            status="open",
            notes=data.notes,
        )
        self.db.add(debt)
        await self.db.commit()
        # Re-fetch with eager-loaded payments to avoid lazy-load in async context
        result = await self.db.execute(
            select(Debt).options(selectinload(Debt.payments)).where(Debt.id == debt.id)
        )
        return result.scalar_one()

    async def get(self, debt_id: int, store_id: int = 1) -> Optional[Debt]:
        """Get debt by ID with payments."""
        result = await self.db.execute(
            select(Debt).options(selectinload(Debt.payments))
            .where(Debt.id == debt_id, Debt.store_id == store_id)
        )
        return result.scalar_one_or_none()

    async def get_by_customer(self, customer_name: str, store_id: int = 1) -> Optional[Debt]:
        """Get open debt by customer name (most recent first)."""
        result = await self.db.execute(
            select(Debt)
            .options(selectinload(Debt.payments))
            .where(Debt.customer_name == customer_name)
            .where(Debt.store_id == store_id)
            .where(Debt.status != "paid")
            .order_by(desc(Debt.id))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        page: int = 1,
        page_size: int = 50,
        status: Optional[str] = None,
        search: Optional[str] = None,
        store_id: int = 1,
    ) -> tuple[List[Debt], int]:
        """List debts with filters."""
        query = select(Debt).options(selectinload(Debt.payments)).where(Debt.store_id == store_id)

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

    async def add_payment(self, debt_id: int, data: DebtPaymentCreate, store_id: int = 1) -> Optional[DebtPayment]:
        """Add payment to debt."""
        debt = await self.get(debt_id, store_id)
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

    async def update(self, debt_id: int, data: DebtUpdate, store_id: int = 1) -> Optional[Debt]:
        """Update debt info."""
        debt = await self.get(debt_id, store_id)
        if not debt:
            return None

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(debt, field, value)

        await self.db.commit()
        # Re-fetch with eager-loaded payments
        result = await self.db.execute(
            select(Debt).options(selectinload(Debt.payments)).where(Debt.id == debt_id)
        )
        return result.scalar_one()

    async def create_from_sale(self, sale: Sale) -> Debt:
        """Create debt from credit sale."""
        existing = await self.get_by_customer(sale.customer_name, sale.store_id)
        if existing:
            existing.total_debt += sale.total
            existing.remaining = existing.total_debt - existing.paid_amount
            existing.status = "partial" if existing.paid_amount > 0 else "open"
            await self.db.commit()
            await self.db.refresh(existing)
            return existing

        debt = Debt(
            store_id=sale.store_id,
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

    async def get_total_outstanding(self, store_id: int = 1) -> Decimal:
        """Get total outstanding debt."""
        result = await self.db.execute(
            select(func.coalesce(func.sum(Debt.remaining), 0))
            .where(Debt.status != "paid")
            .where(Debt.store_id == store_id)
        )
        return result.scalar() or Decimal(0)

    async def get_summary(self, store_id: int = 1) -> dict:
        """Get debt summary: customers, total debt, paid, remaining."""
        result = await self.db.execute(
            select(
                func.count(Debt.id).label("total_customers"),
                func.coalesce(func.sum(Debt.total_debt), 0).label("total_debt"),
                func.coalesce(func.sum(Debt.paid_amount), 0).label("total_paid"),
                func.coalesce(func.sum(Debt.remaining), 0).label("total_remaining"),
            ).where(Debt.store_id == store_id)
        )
        row = result.one()
        return {
            "total_customers": row.total_customers,
            "total_debt": float(row.total_debt),
            "total_paid": float(row.total_paid),
            "total_remaining": float(row.total_remaining),
        }