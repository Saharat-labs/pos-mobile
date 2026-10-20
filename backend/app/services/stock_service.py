"""Stock movement service - business logic for stock adjustments."""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models import StockMovement, Product
from app.schemas import StockMovementCreate
from app.services.product_service import ProductService


class StockMovementService:
    """Stock movement business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.product_service = ProductService(db)

    async def create(self, data: StockMovementCreate) -> StockMovement:
        """Create stock movement and update product stock."""
        movement = StockMovement(
            product_id=data.product_id,
            movement_type=data.movement_type,
            quantity=data.quantity,
            reference_type=data.reference_type,
            reference_id=data.reference_id,
            notes=data.notes,
        )
        self.db.add(movement)

        # Update product stock (internal, no duplicate movement)
        qty_change = data.quantity
        if data.movement_type in ("out", "waste"):
            qty_change = -data.quantity

        await self.product_service._update_stock_only(data.product_id, qty_change)

        await self.db.commit()
        await self.db.refresh(movement)
        return movement

    async def get(self, movement_id: int) -> Optional[StockMovement]:
        """Get stock movement by ID."""
        result = await self.db.execute(
            select(StockMovement).options(selectinload(StockMovement.product)).where(StockMovement.id == movement_id)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        page: int = 1,
        page_size: int = 50,
        product_id: Optional[int] = None,
        movement_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> tuple[List[StockMovement], int]:
        """List stock movements with filters."""
        query = select(StockMovement).options(selectinload(StockMovement.product))

        if product_id:
            query = query.where(StockMovement.product_id == product_id)
        if movement_type:
            query = query.where(StockMovement.movement_type == movement_type)
        if start_date:
            query = query.where(StockMovement.created_at >= start_date)
        if end_date:
            query = query.where(StockMovement.created_at <= end_date)

        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        query = query.order_by(desc(StockMovement.created_at)).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return items, total

    async def get_product_history(self, product_id: int, limit: int = 50) -> List[StockMovement]:
        """Get stock history for a product."""
        result = await self.db.execute(
            select(StockMovement)
            .where(StockMovement.product_id == product_id)
            .order_by(desc(StockMovement.created_at))
            .limit(limit)
        )
        return result.scalars().all()