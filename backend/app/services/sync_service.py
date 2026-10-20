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

    async def sync_from_client(self, data: SyncRequest) -> SyncResponse:
        """Sync data from client (localStorage) to backend."""
        counts = {}

        # Sync category mappings first (needed for product auto-categorization)
        if data.category_mappings:
            await self.category_mappings.bulk_create(data.category_mappings)
            counts["category_mappings"] = len(data.category_mappings)

        # Sync settings
        if data.settings:
            await self.settings.bulk_set(data.settings)
            counts["settings"] = len(data.settings)

        # Sync products
        if data.products:
            await self.products.bulk_create(data.products)
            counts["products"] = len(data.products)

        # Sync sales
        if data.sales:
            for sale_data in data.sales:
                await self.sales.create(sale_data, store_id=1)  # TODO: multi-store sync (Phase 2)
            counts["sales"] = len(data.sales)

        # Sync purchases
        if data.purchases:
            for po_data in data.purchases:
                await self.purchases.create(po_data)
            counts["purchases"] = len(data.purchases)

        # Sync debts
        if data.debts:
            for debt_data in data.debts:
                await self.debts.create(debt_data)
            counts["debts"] = len(data.debts)

        # Sync expenses
        if data.expenses:
            for exp_data in data.expenses:
                await self.expenses.create(exp_data)
            counts["expenses"] = len(data.expenses)

        # Sync stock movements
        if data.stock_movements:
            for mov_data in data.stock_movements:
                await self.stock_movements.create(mov_data)
            counts["stock_movements"] = len(data.stock_movements)

        # Sync hold bills
        if data.hold_bills:
            for bill_data in data.hold_bills:
                await self.hold_bills.create(bill_data)
            counts["hold_bills"] = len(data.hold_bills)

        return SyncResponse(
            success=True,
            message=f"Synced {sum(counts.values())} records",
            counts=counts
        )

    async def full_backup(self) -> dict:
        """Create full backup of all data."""
        # Get all data (default store for now — TODO: multi-store backup in Phase 2)
        products, _ = await self.products.list(page=1, page_size=10000, active_only=False, store_id=1)
        sales, _ = await self.sales.list(page=1, page_size=10000, store_id=1)
        purchases, _ = await self.purchases.list(page=1, page_size=10000)
        debts, _ = await self.debts.list(page=1, page_size=10000)
        expenses, _ = await self.expenses.list(page=1, page_size=10000)
        stock_movements, _ = await self.stock_movements.list(page=1, page_size=10000)
        hold_bills, _ = await self.hold_bills.list(page=1, page_size=10000)
        settings = await self.settings.list()
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

    async def restore_backup(self, data: dict) -> SyncResponse:
        """Restore from backup data (replaces all data)."""
        # Clear existing data (in reverse dependency order)
        await self.db.execute(delete(SaleItem))
        await self.db.execute(delete(Sale))
        await self.db.execute(delete(PurchaseItem))
        await self.db.execute(delete(Purchase))
        await self.db.execute(delete(DebtPayment))
        await self.db.execute(delete(Debt))
        await self.db.execute(delete(Expense))
        await self.db.execute(delete(StockMovement))
        await self.db.execute(delete(HoldBill))
        await self.db.execute(delete(Product))
        await self.db.execute(delete(Setting))
        await self.db.execute(delete(CategoryMapping))
        await self.db.commit()

        # Restore from backup
        sync_request = SyncRequest(**data)
        return await self.sync_from_client(sync_request)