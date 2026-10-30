"""Sync/Backup service - sync localStorage data with backend."""

from datetime import datetime
from typing import List, Optional
from decimal import Decimal
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import (
    Product, Sale, SaleItem, Purchase, PurchaseItem,
    Debt, DebtPayment, Expense, StockMovement,
    HoldBill, Setting, CategoryMapping
)
from app.schemas import SyncRequest, SyncResponse
from app.services import (
    ProductService, SaleService, PurchaseService,
    DebtService, ExpenseService, StockMovementService,
    HoldBillService, SettingService, CategoryMappingService
)


class SyncService:
    """Sync business logic for localStorage <-> backend."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.products = ProductService(db)
        self.sales = SaleService(db)
        self.purchases = PurchaseService(db)
        self.debts = DebtService(db)
        self.expenses = ExpenseService(db)
        self.stock_movements = StockMovementService(db)
        self.hold_bills = HoldBillService(db)
        self.settings = SettingService(db)
        self.category_mappings = CategoryMappingService(db)

    async def sync_from_client(self, data: SyncRequest, store_id: int = 1) -> SyncResponse:
        """Sync data from client (localStorage) to backend (scoped to store_id)."""
        counts = {}

        # Sync category mappings first (needed for product auto-categorization)
        if data.category_mappings:
            await self.category_mappings.bulk_create(data.category_mappings)
            counts["category_mappings"] = len(data.category_mappings)

        # Sync settings
        if data.settings:
            await self.settings.bulk_set(data.settings, store_id=store_id)
            counts["settings"] = len(data.settings)

        # Sync products
        if data.products:
            await self.products.bulk_create(data.products, store_id=store_id)
            counts["products"] = len(data.products)

        # Sync sales — บันทึกเป็นประวัติอย่างเดียว ห้ามตัด stock ซ้ำ
        # (stock ใน payload มากับค่าปัจจุบันอยู่แล้ว + id สินค้าเปลี่ยนหลัง restore
        #  จึงผูก sale item ใหม่ด้วย product_code ก่อนเสมอ)
        if data.sales:
            code_to_id = {}
            rows = await self.db.execute(
                select(Product.id, Product.code).where(Product.store_id == store_id)
            )
            for pid, pcode in rows.all():
                code_to_id[pcode] = pid
            # คงเลขบิลเดิมจาก backup ถ้ายังว่าง (bill_no unique ทั้งระบบ) ไม่งั้นออกเลขใหม่
            wanted = [s.bill_no for s in data.sales if s.bill_no]
            taken = set()
            if wanted:
                taken = set((await self.db.execute(
                    select(Sale.bill_no).where(Sale.bill_no.in_(wanted))
                )).scalars().all())
            for sale_data in data.sales:
                for item in sale_data.items:
                    if item.product_code in code_to_id:
                        item.product_id = code_to_id[item.product_code]
                bill_no = sale_data.bill_no if sale_data.bill_no not in taken else None
                if bill_no:
                    taken.add(bill_no)
                await self.sales.create(
                    sale_data, store_id=store_id, deduct_stock=False, bill_no=bill_no
                )
            counts["sales"] = len(data.sales)

        # Sync purchases
        if data.purchases:
            # id สินค้าเปลี่ยนหลัง restore — ผูก purchase item ใหม่ด้วย product_code เหมือน sale
            rows = await self.db.execute(
                select(Product.id, Product.code).where(Product.store_id == store_id)
            )
            code_to_id = {pcode: pid for pid, pcode in rows.all()}
            for po_data in data.purchases:
                for item in po_data.items:
                    if item.product_code in code_to_id:
                        item.product_id = code_to_id[item.product_code]
                await self.purchases.create(po_data, store_id=store_id)
            counts["purchases"] = len(data.purchases)

        # Sync debts
        if data.debts:
            for debt_data in data.debts:
                await self.debts.create(debt_data, store_id=store_id)
            counts["debts"] = len(data.debts)

        # Sync expenses
        if data.expenses:
            for exp_data in data.expenses:
                await self.expenses.create(exp_data, store_id=store_id)
            counts["expenses"] = len(data.expenses)

        # Sync stock movements — บันทึกเป็นประวัติอย่างเดียว ห้ามบวก/ลบ stock ซ้ำ
        if data.stock_movements:
            for mov_data in data.stock_movements:
                await self.stock_movements.create(mov_data, store_id=store_id, deduct_stock=False)
            counts["stock_movements"] = len(data.stock_movements)

        # Sync hold bills
        if data.hold_bills:
            for bill_data in data.hold_bills:
                await self.hold_bills.create(bill_data, store_id=store_id)
            counts["hold_bills"] = len(data.hold_bills)

        return SyncResponse(
            success=True,
            message=f"Synced {sum(counts.values())} records",
            counts=counts
        )

    async def full_backup(self, store_id: int = 1) -> dict:
        """Create full backup of all data (scoped to store_id)."""
        products, _ = await self.products.list(page=1, page_size=10000, active_only=False, store_id=store_id)
        sales, _ = await self.sales.list(page=1, page_size=10000, store_id=store_id)
        purchases, _ = await self.purchases.list(page=1, page_size=10000, store_id=store_id)
        debts, _ = await self.debts.list(page=1, page_size=10000, store_id=store_id)
        expenses, _ = await self.expenses.list(page=1, page_size=10000, store_id=store_id)
        stock_movements, _ = await self.stock_movements.list(page=1, page_size=10000, store_id=store_id)
        hold_bills, _ = await self.hold_bills.list(page=1, page_size=10000, store_id=store_id)
        settings = await self.settings.list(store_id=store_id)
        category_mappings = await self.category_mappings.list()

        return {
            "products": [
                {
                    "code": p.code,
                    "barcode": p.barcode,
                    "name": p.name,
                    "category": p.category,
                    "unit": p.unit,
                    "price": float(p.price),
                    "cost": float(p.cost),
                    "stock": p.stock,
                    "min_stock": p.min_stock,
                    "expiry_date": p.expiry_date.isoformat() if p.expiry_date else None,
                    "description": p.description,
                    "is_active": p.is_active,
                }
                for p in products
            ],
            "sales": [
                {
                    "bill_no": s.bill_no,
                    "customer_name": s.customer_name,
                    "customer_phone": s.customer_phone,
                    "subtotal": float(s.subtotal),
                    "discount": float(s.discount),
                    "vat": float(s.vat),
                    "total": float(s.total),
                    "payment_method": s.payment_method,
                    "paid_amount": float(s.paid_amount),
                    "change_amount": float(s.change_amount),
                    "status": s.status,
                    "notes": s.notes,
                    "created_at": s.created_at.isoformat(),
                    "items": [
                        {
                            "product_id": i.product_id,
                            "product_code": i.product_code,
                            "product_name": i.product_name,
                            "unit": i.unit,
                            "quantity": i.quantity,
                            "unit_price": float(i.unit_price),
                            "discount": float(i.discount),
                            "line_total": float(i.line_total),
                        }
                        for i in s.items
                    ],
                }
                for s in sales
            ],
            "purchases": [
                {
                    "po_no": p.po_no,
                    "supplier_name": p.supplier_name,
                    "supplier_phone": p.supplier_phone,
                    "total": float(p.total),
                    "status": p.status,
                    "notes": p.notes,
                    "expected_date": p.expected_date.isoformat() if p.expected_date else None,
                    "received_date": p.received_date.isoformat() if p.received_date else None,
                    "created_at": p.created_at.isoformat(),
                    "items": [
                        {
                            "product_id": i.product_id,
                            "product_code": i.product_code,
                            "product_name": i.product_name,
                            "unit": i.unit,
                            "quantity": i.quantity,
                            "unit_cost": float(i.unit_cost),
                            "line_total": float(i.line_total),
                            "received_qty": i.received_qty,
                        }
                        for i in p.items
                    ],
                }
                for p in purchases
            ],
            "debts": [
                {
                    "customer_name": d.customer_name,
                    "customer_phone": d.customer_phone,
                    "total_debt": float(d.total_debt),
                    "paid_amount": float(d.paid_amount),
                    "remaining": float(d.remaining),
                    "status": d.status,
                    "notes": d.notes,
                    "created_at": d.created_at.isoformat(),
                    "payments": [
                        {
                            "amount": float(p.amount),
                            "payment_method": p.payment_method,
                            "notes": p.notes,
                            "created_at": p.created_at.isoformat(),
                        }
                        for p in d.payments
                    ],
                }
                for d in debts
            ],
            "expenses": [
                {
                    "date": e.date.isoformat(),
                    "category": e.category,
                    "description": e.description,
                    "amount": float(e.amount),
                    "payment_method": e.payment_method,
                    "notes": e.notes,
                }
                for e in expenses
            ],
            "stock_movements": [
                {
                    "product_id": m.product_id,
                    "movement_type": m.movement_type,
                    "quantity": m.quantity,
                    "reference_type": m.reference_type,
                    "reference_id": m.reference_id,
                    "notes": m.notes,
                    "created_at": m.created_at.isoformat(),
                }
                for m in stock_movements
            ],
            "hold_bills": [
                {
                    "bill_no": h.bill_no,
                    "items": h.items,
                    "customer_name": h.customer_name,
                    "customer_phone": h.customer_phone,
                    "subtotal": float(h.subtotal),
                    "discount": float(h.discount),
                    "vat": float(h.vat),
                    "total": float(h.total),
                    "created_at": h.created_at.isoformat(),
                }
                for h in hold_bills
            ],
            "settings": [
                {
                    "key": s.key,
                    "value": s.value,
                    "description": s.description,
                }
                for s in settings
            ],
            "category_mappings": [
                {
                    "code_prefix": m.code_prefix,
                    "category": m.category,
                }
                for m in category_mappings
            ],
        }

    async def restore_backup(self, data: dict, store_id: int = 1) -> SyncResponse:
        """Restore from backup data (replaces current store's data).

        ก่อนลบข้อมูลเดิม จะสำรองข้อมูลของร้านนี้ไว้ก่อน ถ้ากู้คืนล้มกลางทาง
        จะย้อนข้อมูลเดิมกลับให้อัตโนมัติ (sub-service commit เองทุกตัว จึงใช้
        transaction เดียวครอบทั้งกระบวนการไม่ได้)
        """
        # 1) validate payload ก่อนลบอะไรทั้งสิ้น — payload ผิดรูปต้องไม่ทำข้อมูลหาย
        # รับได้ทั้งไฟล์ที่ได้จาก GET /sync/backup ({timestamp, version, data:{...}})
        # และ data ด้านในโดยตรง; ถ้าไม่มี section ของ backup เลย (เช่น {} หรือไฟล์อื่น)
        # ห้ามลบข้อมูลร้าน — เดิม SyncRequest ข้าม key ที่ไม่รู้จักแล้วได้ list ว่างทั้งหมด
        if isinstance(data, dict) and isinstance(data.get("data"), dict):
            data = data["data"]
        if not isinstance(data, dict) or not set(data) & set(SyncRequest.model_fields):
            raise ValueError(
                "ไฟล์สำรองไม่ถูกต้อง: ไม่พบข้อมูล backup "
                f"(ต้องมีอย่างน้อยหนึ่งใน {sorted(SyncRequest.model_fields)})"
            )
        try:
            sync_request = SyncRequest(**data)
        except Exception as exc:
            raise ValueError(f"ไฟล์สำรองไม่ถูกต้อง: {exc}") from exc

        # 2) สำรองข้อมูลปัจจุบันของร้านนี้ (เผื่อ rollback)
        snapshot = await self.full_backup(store_id=store_id)

        # 3) ลบข้อมูลเดิมของร้านนี้ (เรียงตาม dependency จากมากไปน้อย)
        try:
            sale_ids = select(Sale.id).where(Sale.store_id == store_id)
            await self.db.execute(delete(SaleItem).where(SaleItem.sale_id.in_(sale_ids)))
            await self.db.execute(delete(Sale).where(Sale.store_id == store_id))
            purchase_ids = select(Purchase.id).where(Purchase.store_id == store_id)
            await self.db.execute(delete(PurchaseItem).where(PurchaseItem.purchase_id.in_(purchase_ids)))
            await self.db.execute(delete(Purchase).where(Purchase.store_id == store_id))
            debt_ids = select(Debt.id).where(Debt.store_id == store_id)
            await self.db.execute(delete(DebtPayment).where(DebtPayment.debt_id.in_(debt_ids)))
            await self.db.execute(delete(Debt).where(Debt.store_id == store_id))
            await self.db.execute(delete(Expense).where(Expense.store_id == store_id))
            await self.db.execute(delete(StockMovement).where(StockMovement.store_id == store_id))
            await self.db.execute(delete(HoldBill).where(HoldBill.store_id == store_id))
            await self.db.execute(delete(Product).where(Product.store_id == store_id))
            await self.db.execute(delete(Setting).where(Setting.store_id == store_id))
            await self.db.commit()
        except Exception as exc:
            await self.db.rollback()
            raise ValueError(f"ลบข้อมูลเดิมไม่สำเร็จ: {exc}") from exc

        # 4) กู้คืนข้อมูลจากไฟล์ ถ้าล้มให้ย้อนข้อมูลเดิมกลับทันที
        try:
            return await self.sync_from_client(sync_request, store_id=store_id)
        except Exception as exc:
            try:
                await self.db.rollback()
                await self._restore_snapshot(snapshot, store_id=store_id)
            except Exception as rollback_exc:  # pragma: no cover - แจ้งให้ทราบทั้งสองฝั่ง
                raise ValueError(
                    f"กู้คืนไม่สำเร็จ และย้อนข้อมูลเดิมก็ไม่สำเร็จ: {exc} / {rollback_exc}"
                ) from exc
            raise ValueError(f"กู้คืนไม่สำเร็จ ย้อนข้อมูลเดิมแล้ว: {exc}") from exc

    async def _restore_snapshot(self, snapshot: dict, store_id: int = 1) -> None:
        """เขียนข้อมูลจาก snapshot กลับเข้าร้านนี้ (ใช้ตอน rollback)"""
        await self.sync_from_client(SyncRequest(**snapshot), store_id=store_id)