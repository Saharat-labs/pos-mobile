"""Purchase service - business logic for purchases."""

from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models import Purchase, PurchaseItem, Product, StockMovement
from app.schemas import PurchaseCreate, PurchaseUpdate, PurchaseItemCreate
from app.services.product_service import ProductService


class PurchaseService:
    """Purchase business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.product_service = ProductService(db)

    def _generate_po_no(self) -> str:
        """Generate unique PO number (timestamp + microseconds + random)."""
        import random
        ts = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        return f"PO-{ts}-{random.randint(1000, 9999)}"

    def _calculate_total(self, items: List[PurchaseItemCreate]) -> Decimal:
        """Calculate total from items (unit_cost * quantity — same as each item's
        line_total; don't trust the optional client-sent line_total, default 0)."""
        return sum(item.unit_cost * item.quantity for item in items)

    async def create(self, data: PurchaseCreate, store_id: int = 1) -> Purchase:
        """Create new purchase order."""
        total = self._calculate_total(data.items)

        purchase = Purchase(
            store_id=store_id,
            po_no=self._generate_po_no(),
            supplier_name=data.supplier_name,
            supplier_phone=data.supplier_phone,
            total=total,
            status=data.status,
            notes=data.notes,
            expected_date=data.expected_date,
        )
        self.db.add(purchase)
        await self.db.flush()

        for item_data in data.items:
            line_total = item_data.unit_cost * item_data.quantity
            item = PurchaseItem(
                purchase_id=purchase.id,
                product_id=item_data.product_id,
                product_code=item_data.product_code,
                product_name=item_data.product_name,
                unit=item_data.unit,
                quantity=item_data.quantity,
                unit_cost=item_data.unit_cost,
                line_total=line_total,
                received_qty=0,
            )
            self.db.add(item)

        await self.db.commit()
        await self.db.refresh(purchase)

        result = await self.db.execute(
            select(Purchase).options(selectinload(Purchase.items)).where(Purchase.id == purchase.id)
        )
        return result.scalar_one()

    async def get(self, purchase_id: int, store_id: int = 1) -> Optional[Purchase]:
        """Get purchase by ID with items."""
        result = await self.db.execute(
            select(Purchase).options(selectinload(Purchase.items))
            .where(Purchase.id == purchase_id, Purchase.store_id == store_id)
        )
        return result.scalar_one_or_none()

    async def get_by_po_no(self, po_no: str, store_id: int = 1) -> Optional[Purchase]:
        """Get purchase by PO number."""
        result = await self.db.execute(
            select(Purchase).options(selectinload(Purchase.items))
            .where(Purchase.po_no == po_no, Purchase.store_id == store_id)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        page: int = 1,
        page_size: int = 50,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[str] = None,
        store_id: int = 1,
    ) -> tuple[List[Purchase], int]:
        """List purchases with filters."""
        query = select(Purchase).options(selectinload(Purchase.items)).where(Purchase.store_id == store_id)

        if start_date:
            query = query.where(Purchase.created_at >= start_date)
        if end_date:
            query = query.where(Purchase.created_at <= end_date)
        if status:
            query = query.where(Purchase.status == status)

        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        query = query.order_by(desc(Purchase.created_at)).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return items, total

    async def receive(self, purchase_id: int, received_items: List[dict], store_id: int = 1) -> Optional[Purchase]:
        """Receive purchase items and update stock."""
        purchase = await self.get(purchase_id, store_id)
        if not purchase:
            return None

        for received in received_items:
            item_id = received.get("item_id")
            qty = received.get("received_qty", 0)
            if qty <= 0:
                continue

            result = await self.db.execute(
                select(PurchaseItem).where(PurchaseItem.id == item_id).where(PurchaseItem.purchase_id == purchase_id)
            )
            item = result.scalar_one_or_none()
            if not item:
                continue

            item.received_qty += qty

            # Update product stock (in)
            await self.product_service.update_stock(
                product_id=item.product_id,
                quantity=qty,
                movement_type="in",
                reference_type="purchase",
                reference_id=purchase_id,
                store_id=store_id,
            )

        # Check if fully received
        all_received = all(item.received_qty >= item.quantity for item in purchase.items)
        if all_received:
            purchase.status = "received"
            purchase.received_date = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(purchase)
        return purchase

    async def update(self, purchase_id: int, data: PurchaseUpdate, store_id: int = 1) -> Optional[Purchase]:
        """Update purchase."""
        purchase = await self.get(purchase_id, store_id)
        if not purchase:
            return None

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(purchase, field, value)

        await self.db.commit()
        await self.db.refresh(purchase)
        return purchase