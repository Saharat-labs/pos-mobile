"""Product service - business logic for products."""

from typing import Optional, List
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models import Product, SaleItem, StockMovement
from app.schemas import ProductCreate, ProductUpdate, ProductResponse


class ProductService:
    """Product business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: ProductCreate) -> Product:
        """Create new product."""
        product = Product(**data.model_dump())
        self.db.add(product)
        await self.db.commit()
        await self.db.refresh(product)
        return product

    async def get(self, product_id: int) -> Optional[Product]:
        """Get product by ID."""
        result = await self.db.execute(select(Product).where(Product.id == product_id))
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Optional[Product]:
        """Get product by code."""
        result = await self.db.execute(select(Product).where(Product.code == code))
        return result.scalar_one_or_none()

    async def get_by_barcode(self, barcode: str) -> Optional[Product]:
        """Get product by barcode."""
        result = await self.db.execute(select(Product).where(Product.barcode == barcode))
        return result.scalar_one_or_none()

    async def list(
        self,
        page: int = 1,
        page_size: int = 50,
        search: Optional[str] = None,
        category: Optional[str] = None,
        stock_filter: Optional[str] = None,
        active_only: bool = True,
    ) -> tuple[List[Product], int]:
        """List products with filters."""
        query = select(Product)

        if active_only:
            query = query.where(Product.is_active == True)

        if search:
            query = query.where(
                or_(
                    Product.code.ilike(f"%{search}%"),
                    Product.name.ilike(f"%{search}%"),
                    Product.barcode.ilike(f"%{search}%"),
                )
            )

        if category:
            query = query.where(Product.category == category)

        if stock_filter:
            if stock_filter == "available":
                query = query.where(Product.stock > 0)
            elif stock_filter == "low":
                query = query.where(Product.stock > 0, Product.stock <= Product.min_stock)
            elif stock_filter == "out":
                query = query.where(Product.stock == 0)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        # Paginate
        query = query.offset((page - 1) * page_size).limit(page_size)
        query = query.order_by(Product.code)

        result = await self.db.execute(query)
        items = result.scalars().all()

        return items, total

    async def update(self, product_id: int, data: ProductUpdate) -> Optional[Product]:
        """Update product."""
        product = await self.get(product_id)
        if not product:
            return None

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(product, field, value)

        await self.db.commit()
        await self.db.refresh(product)
        return product

    async def update_stock(self, product_id: int, quantity: int, movement_type: str, reference_type: str = None, reference_id: int = None, notes: str = None) -> Optional[Product]:
        """Update product stock and create movement record."""
        product = await self.get(product_id)
        if not product:
            return None

        old_stock = product.stock
        product.stock += quantity

        # Create stock movement
        movement = StockMovement(
            product_id=product_id,
            movement_type=movement_type,
            quantity=abs(quantity),
            reference_type=reference_type,
            reference_id=reference_id,
            notes=notes or f"Stock {movement_type}: {old_stock} -> {product.stock}",
        )
        self.db.add(movement)

        await self.db.commit()
        await self.db.refresh(product)
        return product

    async def get_low_stock(self) -> List[Product]:
        """Get products with low stock."""
        result = await self.db.execute(
            select(Product)
            .where(Product.is_active == True)
            .where(Product.stock <= Product.min_stock)
            .where(Product.min_stock > 0)
        )
        return result.scalars().all()

    async def get_expiring_soon(self, days: int = 30) -> List[Product]:
        """Get products expiring soon."""
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() + timedelta(days=days)
        result = await self.db.execute(
            select(Product)
            .where(Product.is_active == True)
            .where(Product.expiry_date != None)
            .where(Product.expiry_date <= cutoff)
            .order_by(Product.expiry_date)
        )
        return result.scalars().all()

    async def delete(self, product_id: int) -> bool:
        """Soft delete product (set inactive)."""
        product = await self.get(product_id)
        if not product:
            return False
        product.is_active = False
        await self.db.commit()
        return True

    async def get_categories(self) -> List[str]:
        """Get all unique categories."""
        result = await self.db.execute(
            select(Product.category).where(Product.category != None).distinct()
        )
        return [c for c in result.scalars().all() if c]

    async def bulk_create(self, products: List[ProductCreate]) -> List[Product]:
        """Bulk create products (upsert by code)."""
        created = []
        for p_data in products:
            existing = await self.get_by_code(p_data.code)
            if existing:
                # Update existing
                for field, value in p_data.model_dump().items():
                    setattr(existing, field, value)
                created.append(existing)
            else:
                product = Product(**p_data.model_dump())
                self.db.add(product)
                created.append(product)
        await self.db.commit()
        for p in created:
            await self.db.refresh(p)
        return created