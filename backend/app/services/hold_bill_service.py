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
        """Generate unique hold bill number (timestamp + microseconds + random)."""
        import random
        ts = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        return f"HOLD-{ts}-{random.randint(1000, 9999)}"

    async def create(self, data: HoldBillCreate, store_id: int = 1) -> HoldBill:
        """Create new hold bill (uses client bill_no if given, else generates)."""
        bill = HoldBill(
            store_id=store_id,
            bill_no=data.bill_no or self._generate_bill_no(),
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

    async def get(self, bill_id: int, store_id: int = 1) -> Optional[HoldBill]:
        """Get hold bill by ID."""
        result = await self.db.execute(
            select(HoldBill).where(HoldBill.id == bill_id, HoldBill.store_id == store_id)
        )
        return result.scalar_one_or_none()

    async def get_by_bill_no(self, bill_no: str, store_id: int = 1) -> Optional[HoldBill]:
        """Get hold bill by bill number."""
        result = await self.db.execute(
            select(HoldBill).where(HoldBill.bill_no == bill_no, HoldBill.store_id == store_id)
        )
        return result.scalar_one_or_none()

    async def list(self, page: int = 1, page_size: int = 50, store_id: int = 1) -> tuple[List[HoldBill], int]:
        """List hold bills."""
        query = select(HoldBill).where(HoldBill.store_id == store_id)

        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        query = query.order_by(desc(HoldBill.created_at)).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return items, total

    async def delete(self, bill_id: int, store_id: int = 1) -> bool:
        """Delete hold bill."""
        bill = await self.get(bill_id, store_id)
        if not bill:
            return False
        await self.db.delete(bill)
        await self.db.commit()
        return True