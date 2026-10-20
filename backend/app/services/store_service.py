"""Store service - business logic for multi-store support."""

from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Store, User, Product, Sale, Purchase, Debt, Expense, StockMovement, HoldBill, Setting
from app.schemas import StoreCreate, StoreUpdate, StoreResponse


class StoreService:
    """Store business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: StoreCreate) -> Store:
        """Create new store."""
        # Check if code already exists
        result = await self.db.execute(select(Store).where(Store.code == data.code))
        if result.scalar_one_or_none():
            raise ValueError(f"Store with code '{data.code}' already exists")

        # If this is set as default, unset other defaults
        if data.is_default:
            await self.db.execute(
                select(Store).where(Store.is_default == True)
            )
            # Use raw SQL for update to avoid loading all stores
            from sqlalchemy import update
            await self.db.execute(update(Store).where(Store.is_default == True).values(is_default=False))

        store = Store(**data.model_dump())
        self.db.add(store)
        await self.db.commit()
        await self.db.refresh(store)
        return store

    async def get(self, store_id: int) -> Optional[Store]:
        """Get store by ID."""
        result = await self.db.execute(select(Store).where(Store.id == store_id))
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Optional[Store]:
        """Get store by code."""
        result = await self.db.execute(select(Store).where(Store.code == code))
        return result.scalar_one_or_none()

    async def get_default(self) -> Optional[Store]:
        """Get default store."""
        result = await self.db.execute(select(Store).where(Store.is_default == True))
        return result.scalar_one_or_none()

    async def update(self, store_id: int, data: StoreUpdate) -> Optional[Store]:
        """Update store."""
        store = await self.get(store_id)
        if not store:
            return None

        # Check if code is being changed and already exists
        if data.code and data.code != store.code:
            existing = await self.get_by_code(data.code)
            if existing:
                raise ValueError(f"Store with code '{data.code}' already exists")

        # If setting as default, unset other defaults
        if data.is_default:
            from sqlalchemy import update
            await self.db.execute(update(Store).where(Store.is_default == True).values(is_default=False))

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(store, field, value)

        await self.db.commit()
        await self.db.refresh(store)
        return store

    async def delete(self, store_id: int) -> bool:
        """Delete store (and all related data)."""
        store = await self.get(store_id)
        if not store:
            return False

        # Prevent deleting the only store
        result = await self.db.execute(select(func.count()).select_from(Store))
        count = result.scalar() or 0
        if count <= 1:
            raise ValueError("Cannot delete the only store")

        await self.db.delete(store)
        await self.db.commit()
        return True

    async def list(
        self,
        page: int = 1,
        page_size: int = 50,
        is_active: Optional[bool] = None,
    ) -> tuple[List[Store], int]:
        """List stores with filters."""
        query = select(Store)

        if is_active is not None:
            query = query.where(Store.is_active == is_active)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        # Paginate
        query = query.order_by(Store.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return items, total

    async def get_store_stats(self, store_id: int) -> dict:
        """Get statistics for a store."""
        from sqlalchemy import select as sel

        # Count products
        product_count = await self.db.scalar(
            sel(func.count()).select_from(Product).where(Product.store_id == store_id)
        ) or 0

        # Count sales
        sale_count = await self.db.scalar(
            sel(func.count()).select_from(Sale).where(Sale.store_id == store_id)
        ) or 0

        # Count purchases
        purchase_count = await self.db.scalar(
            sel(func.count()).select_from(Purchase).where(Purchase.store_id == store_id)
        ) or 0

        # Count debts
        debt_count = await self.db.scalar(
            sel(func.count()).select_from(Debt).where(Debt.store_id == store_id)
        ) or 0

        # Count expenses
        expense_count = await self.db.scalar(
            sel(func.count()).select_from(Expense).where(Expense.store_id == store_id)
        ) or 0

        return {
            "store_id": store_id,
            "product_count": product_count,
            "sale_count": sale_count,
            "purchase_count": purchase_count,
            "debt_count": debt_count,
            "expense_count": expense_count,
        }
