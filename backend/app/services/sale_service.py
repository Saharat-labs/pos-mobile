"""Sale service - business logic for sales."""

from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models import Sale, SaleItem, Product, StockMovement
from app.schemas import SaleCreate, SaleUpdate, SaleItemCreate
from app.services.product_service import ProductService


class SaleService:
    """Sale business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.product_service = ProductService(db)

    def _generate_bill_no(self) -> str:
        """Generate unique bill number."""
        from datetime import datetime
        return f"POS-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

    def _calculate_totals(self, items: List[SaleItemCreate], discount: Decimal, vat: Decimal) -> tuple:
        """Calculate subtotal, discount, vat, total."""
        subtotal = sum(item.line_total for item in items)
        total = subtotal - discount + vat
        return subtotal, total

    async def create(self, data: SaleCreate) -> Sale:
        """Create new sale with items."""
        # Calculate totals
        subtotal, total = self._calculate_totals(data.items, data.discount, data.vat)
        change = max(data.paid_amount - total, Decimal(0))

        # Create sale
        sale = Sale(
            bill_no=self._generate_bill_no(),
            customer_name=data.customer_name,
            customer_phone=data.customer_phone,
            subtotal=subtotal,
            discount=data.discount,
            vat=data.vat,
            total=total,
            payment_method=data.payment_method,
            paid_amount=data.paid_amount,
            change_amount=change,
            status="completed" if data.payment_method != "credit" else "completed",
            notes=data.notes,
        )
        self.db.add(sale)
        await self.db.flush()

        # Create sale items and update stock
        for item_data in data.items:
            line_total = (item_data.unit_price * item_data.quantity) - item_data.discount
            item = SaleItem(
                sale_id=sale.id,
                product_id=item_data.product_id,
                product_code=item_data.product_code,
                product_name=item_data.product_name,
                unit=item_data.unit,
                quantity=item_data.quantity,
                unit_price=item_data.unit_price,
                discount=item_data.discount,
                line_total=line_total,
            )
            self.db.add(item)

            # Update stock (out)
            await self.product_service.update_stock(
                product_id=item_data.product_id,
                quantity=-item_data.quantity,
                movement_type="out",
                reference_type="sale",
                reference_id=sale.id,
            )

        await self.db.commit()
        await self.db.refresh(sale)

        # Load items
        result = await self.db.execute(
            select(Sale).options(selectinload(Sale.items)).where(Sale.id == sale.id)
        )
        return result.scalar_one()

    async def get(self, sale_id: int) -> Optional[Sale]:
        """Get sale by ID with items."""
        result = await self.db.execute(
            select(Sale).options(selectinload(Sale.items)).where(Sale.id == sale_id)
        )
        return result.scalar_one_or_none()

    async def get_by_bill_no(self, bill_no: str) -> Optional[Sale]:
        """Get sale by bill number."""
        result = await self.db.execute(
            select(Sale).options(selectinload(Sale.items)).where(Sale.bill_no == bill_no)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        page: int = 1,
        page_size: int = 50,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        payment_method: Optional[str] = None,
        status: Optional[str] = None,
    ) -> tuple[List[Sale], int]:
        """List sales with filters."""
        query = select(Sale).options(selectinload(Sale.items))

        if start_date:
            query = query.where(Sale.created_at >= start_date)
        if end_date:
            query = query.where(Sale.created_at <= end_date)
        if payment_method:
            query = query.where(Sale.payment_method == payment_method)
        if status:
            query = query.where(Sale.status == status)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        # Paginate
        query = query.order_by(desc(Sale.created_at)).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return items, total

    async def update(self, sale_id: int, data: SaleUpdate) -> Optional[Sale]:
        """Update sale (limited fields)."""
        sale = await self.get(sale_id)
        if not sale:
            return None

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(sale, field, value)

        await self.db.commit()
        await self.db.refresh(sale)
        return sale

    async def get_daily_summary(self, date: datetime) -> dict:
        """Get daily sales summary."""
        from datetime import timedelta
        start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)

        result = await self.db.execute(
            select(
                func.count(Sale.id).label("count"),
                func.coalesce(func.sum(Sale.total), 0).label("total"),
                func.coalesce(func.sum(Sale.subtotal), 0).label("subtotal"),
                func.coalesce(func.sum(Sale.discount), 0).label("discount"),
                func.coalesce(func.sum(Sale.vat), 0).label("vat"),
            ).where(Sale.created_at >= start).where(Sale.created_at < end)
        )
        row = result.one()

        # Payment method breakdown
        pm_result = await self.db.execute(
            select(Sale.payment_method, func.count(Sale.id), func.coalesce(func.sum(Sale.total), 0))
            .where(Sale.created_at >= start).where(Sale.created_at < end)
            .group_by(Sale.payment_method)
        )
        payment_methods = {pm: {"count": cnt, "total": float(tot)} for pm, cnt, tot in pm_result.all()}

        return {
            "date": date.date().isoformat(),
            "count": row.count,
            "total": float(row.total),
            "subtotal": float(row.subtotal),
            "discount": float(row.discount),
            "vat": float(row.vat),
            "payment_methods": payment_methods,
        }

    async def get_top_products(self, start_date: datetime, end_date: datetime, limit: int = 10) -> List[dict]:
        """Get top selling products."""
        result = await self.db.execute(
            select(
                SaleItem.product_id,
                SaleItem.product_code,
                SaleItem.product_name,
                func.sum(SaleItem.quantity).label("total_qty"),
                func.sum(SaleItem.line_total).label("total_amount"),
            )
            .join(Sale, Sale.id == SaleItem.sale_id)
            .where(Sale.created_at >= start_date)
            .where(Sale.created_at <= end_date)
            .group_by(SaleItem.product_id, SaleItem.product_code, SaleItem.product_name)
            .order_by(desc("total_qty"))
            .limit(limit)
        )
        return [
            {"product_id": pid, "product_code": pc, "product_name": pn, "quantity": int(qty), "amount": float(amt)}
            for pid, pc, pn, qty, amt in result.all()
        ]