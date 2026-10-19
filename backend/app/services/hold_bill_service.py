"""Hold bill service - business logic for suspended bills."""

from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import HoldBill
from app.schemas import HoldBillCreate


class HoldBillService:
    """Hold bill business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _generate_bill_no(self) -> str:
        """Generate unique hold bill number."""
        return f"HOLD-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

    async def create(self, data: HoldBillCreate) -> HoldBill:
        """Create new hold bill."""
        bill = HoldBill(
            bill_no=self._generate_bill_no(),
            items=data.items,
            customer_name=data.customer_name,
            customer_phone=data.customer_phone,
            subtotal=data.subtotal,
            discount=data.discount,
            vat=data.vat,
            total=data.total,
        )
        self.db.add(bill)
        await self.db.commit()
        await self.db.refresh(bill)
        return bill

    async def get(self, bill_id: int) -> Optional[HoldBill]:
        """Get hold bill by ID."""
        result = await self.db.execute(select(HoldBill).where(HoldBill.id == bill_id))
        return result.scalar_one_or_none()

    async def get_by_bill_no(self, bill_no: str) -> Optional[HoldBill]:
        """Get hold bill by bill number."""
        result = await self.db.execute(select(HoldBill).where(HoldBill.bill_no == bill_no))
        return result.scalar_one_or_none()

    async def list(self, page: int = 1, page_size: int = 50) -> tuple[List[HoldBill], int]:
        """List hold bills."""
        query = select(HoldBill)

        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        query = query.order_by(desc(HoldBill.created_at)).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return items, total

    async def delete(self, bill_id: int) -> bool:
        """Delete hold bill."""
        bill = await self.get(bill_id)
        if not bill:
            return False
        await self.db.delete(bill)
        await self.db.commit()
        return True