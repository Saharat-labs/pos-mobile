"""Sale service - business logic for sales."""

from datetime import datetime
from typing import Optional, List
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models import Sale, SaleItem, Product, StockMovement
from app.schemas import SaleCreate, SaleUpdate, SaleItemCreate
from app.services.product_service import ProductService
from app.services.setting_service import SettingService
from app.websocket_manager import broadcast_event


class SaleService:
    """Sale business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.product_service = ProductService(db)
        self.setting_service = SettingService(db)

    def _generate_bill_no(self) -> str:
        """Generate unique bill number."""
        from datetime import datetime
        import random
        # Use microseconds + random to avoid collisions in tests
        return f"POS-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}-{random.randint(1000, 9999)}"

    async def _get_vat_mode(self, store_id: int = 1) -> str:
        """Get VAT mode from settings: 'no', 'exclude', 'include'."""
        return await self.setting_service.get_value("vat", "no", store_id)

    def _calculate_vat(self, taxable_amount: Decimal, vat_mode: str) -> Decimal:
        """Calculate VAT based on mode (Thai VAT 7%)."""
        if vat_mode == "exclude":
            # VAT 7% added on top
            return (taxable_amount * Decimal("0.07")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        elif vat_mode == "include":
            # VAT 7% included in price: vat = taxable - taxable/1.07
            taxable_excl = (taxable_amount / Decimal("1.07")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            return (taxable_amount - taxable_excl).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        else:
            # 'no' or unknown: no VAT
            return Decimal("0")

    def _calculate_totals(self, items: List[SaleItemCreate], discount: Decimal, vat_mode: str) -> tuple:
        """Calculate subtotal, VAT, and total based on VAT mode."""
        # Calculate subtotal from unit_price * quantity - discount (don't trust client-sent line_total)
        subtotal = sum((item.unit_price * item.quantity) - item.discount for item in items)
        taxable = subtotal - discount
        vat = self._calculate_vat(taxable, vat_mode)
        if vat_mode == "include":
            # VAT included: total = taxable (already includes VAT)
            total = taxable
        else:
            # VAT excluded or no VAT: total = taxable + vat
            total = taxable + vat
        return subtotal, vat, total

    async def create(
        self, data: SaleCreate, store_id: int, deduct_stock: bool = True,
        bill_no: Optional[str] = None,
    ) -> Sale:
        """Create new sale with items.

        deduct_stock=False ใช้ตอน sync/restore เท่านั้น: stock ใน payload
        เป็นค่าปัจจุบันอยู่แล้ว ห้ามตัดซ้ำ (ยอดขายประวัติ = บันทึกอย่างเดียว)
        bill_no ใช้ตอน sync/restore เพื่อคงเลขบิลเดิม (ผู้เรียกต้องตรวจว่าไม่ซ้ำ)
        """
        # Validate stock availability before creating the sale
        if deduct_stock:
            for item_data in data.items:
                product = await self.product_service.get(item_data.product_id, store_id)
                if not product:
                    raise ValueError(f"Product {item_data.product_code} not found")
                if product.stock < item_data.quantity:
                    raise ValueError(
                        f"Insufficient stock for {item_data.product_name}: "
                        f"available {product.stock}, requested {item_data.quantity}"
                    )

        # Calculate totals with VAT based on backend setting
        vat_mode = await self._get_vat_mode(store_id)
        subtotal, vat, total = self._calculate_totals(data.items, data.discount, vat_mode)
        change = max(data.paid_amount - total, Decimal(0))

        # Create sale
        sale = Sale(
            store_id=store_id,
            bill_no=bill_no or self._generate_bill_no(),
            customer_name=data.customer_name,
            customer_phone=data.customer_phone,
            subtotal=subtotal,
            discount=data.discount,
            vat=vat,
            total=total,
            payment_method=data.payment_method,
            paid_amount=data.paid_amount,
            change_amount=change,
            status="completed" if data.payment_method != "credit" else "held",
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

            # Update stock (out) — ข้ามเมื่อ sync/restore (stock มาพร้อม payload แล้ว)
            if deduct_stock:
                await self.product_service.update_stock(
                    product_id=item_data.product_id,
                    quantity=-item_data.quantity,
                    movement_type="out",
                    reference_type="sale",
                    reference_id=sale.id,
                    store_id=store_id,
                )

        await self.db.commit()
        await self.db.refresh(sale)

        # Broadcast sale created event via WebSocket
        await broadcast_event("sale_created", {
            "sale_id": sale.id,
            "store_id": sale.store_id,
            "bill_no": sale.bill_no,
            "customer_name": sale.customer_name,
            "total": float(sale.total),
            "payment_method": sale.payment_method,
            "status": sale.status,
            "created_at": sale.created_at.isoformat() if sale.created_at else None,
        })

        # Load items
        result = await self.db.execute(
            select(Sale).options(selectinload(Sale.items)).where(Sale.id == sale.id)
        )
        return result.scalar_one()

    async def get(self, sale_id: int, store_id: int) -> Optional[Sale]:
        """Get sale by ID with items (scoped to store)."""
        result = await self.db.execute(
            select(Sale).options(selectinload(Sale.items))
            .where(Sale.id == sale_id, Sale.store_id == store_id)
        )
        return result.scalar_one_or_none()

    async def get_by_bill_no(self, bill_no: str, store_id: int) -> Optional[Sale]:
        """Get sale by bill number (scoped to store)."""
        result = await self.db.execute(
            select(Sale).options(selectinload(Sale.items))
            .where(Sale.bill_no == bill_no, Sale.store_id == store_id)
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
        store_id: int = None,
    ) -> tuple[List[Sale], int]:
        """List sales with filters (scoped to store)."""
        query = select(Sale).options(selectinload(Sale.items)).where(Sale.store_id == store_id)

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

    async def update(self, sale_id: int, data: SaleUpdate, store_id: int) -> Optional[Sale]:
        """Update sale (limited fields, scoped to store)."""
        sale = await self.get(sale_id, store_id)
        if not sale:
            return None

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(sale, field, value)

        await self.db.commit()
        await self.db.refresh(sale)
        return sale

    async def get_daily_summary(self, date: datetime, store_id: int) -> dict:
        """Get daily sales summary (scoped to store)."""
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
            ).where(Sale.store_id == store_id)
            .where(Sale.created_at >= start).where(Sale.created_at < end)
        )
        row = result.one()

        # Payment method breakdown
        pm_result = await self.db.execute(
            select(Sale.payment_method, func.count(Sale.id), func.coalesce(func.sum(Sale.total), 0))
            .where(Sale.store_id == store_id)
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

    async def get_top_products(self, start_date: datetime, end_date: datetime, limit: int = 10, store_id: int = None) -> List[dict]:
        """Get top selling products (scoped to store)."""
        result = await self.db.execute(
            select(
                SaleItem.product_id,
                SaleItem.product_code,
                SaleItem.product_name,
                func.sum(SaleItem.quantity).label("total_qty"),
                func.sum(SaleItem.line_total).label("total_amount"),
            )
            .join(Sale, Sale.id == SaleItem.sale_id)
            .where(Sale.store_id == store_id)
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