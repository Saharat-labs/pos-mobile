"""Product API routes."""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.product_service import ProductService
from app.schemas import (
    ProductCreate, ProductUpdate, ProductResponse, ProductListResponse
)
from app.api.validation import (
    validate_page_params, validate_date_range, validate_stock_movement_type,
    validate_positive_quantity, MAX_PAGE_SIZE
)
from app.auth import get_current_store
from app.models import Store

router = APIRouter(prefix="/products", tags=["Products"])


def get_service(db: AsyncSession = Depends(get_db)) -> ProductService:
    return ProductService(db)


@router.post("", response_model=ProductResponse, status_code=201)
async def create_product(
    data: ProductCreate,
    service: ProductService = Depends(get_service),
    current_store: Store = Depends(get_current_store),
):
    """Create new store."""
    existing = await service.get_by_code(data.code, current_store.id)
    if existing:
        raise HTTPException(status_code=400, detail=f"Product with code {data.code} already exists")
    if data.barcode:
        existing = await service.get_by_barcode(data.barcode, current_store.id)
        if existing:
            raise HTTPException(status_code=400, detail=f"Product with barcode {data.barcode} already exists")
    return await service.create(data, current_store.id)


@router.get("", response_model=ProductListResponse)
async def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=MAX_PAGE_SIZE),
    search: Optional[str] = None,
    category: Optional[str] = None,
    stock_filter: Optional[str] = Query(None, pattern="^(available|low|out)$"),
    active_only: bool = True,
    service: ProductService = Depends(get_service),
    current_store: Store = Depends(get_current_store),
):
    """List products with filters."""
    page, page_size = validate_page_params(page, page_size)
    items, total = await service.list(page, page_size, search, category, stock_filter, active_only, current_store.id)
    return ProductListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/categories", response_model=List[str])
async def get_categories(
    service: ProductService = Depends(get_service),
    current_store: Store = Depends(get_current_store),
):
    """Get all product categories."""
    return await service.get_categories(current_store.id)


@router.get("/low-stock", response_model=List[ProductResponse])
async def get_low_stock(
    service: ProductService = Depends(get_service),
    current_store: Store = Depends(get_current_store),
):
    """Get products with low stock."""
    return await service.get_low_stock(current_store.id)


@router.get("/expiring", response_model=List[ProductResponse])
async def get_expiring(
    days: int = Query(30, ge=1),
    service: ProductService = Depends(get_service),
    current_store: Store = Depends(get_current_store),
):
    """Get products expiring soon."""
    return await service.get_expiring_soon(days, current_store.id)


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    service: ProductService = Depends(get_service),
    current_store: Store = Depends(get_current_store),
):
    """Get product by ID."""
    product = await service.get(product_id, current_store.id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.get("/code/{code}", response_model=ProductResponse)
async def get_product_by_code(
    code: str,
    service: ProductService = Depends(get_service),
    current_store: Store = Depends(get_current_store),
):
    """Get product by code."""
    product = await service.get_by_code(code, current_store.id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.get("/barcode/{barcode}", response_model=ProductResponse)
async def get_product_by_barcode(
    barcode: str,
    service: ProductService = Depends(get_service),
    current_store: Store = Depends(get_current_store),
):
    """Get product by barcode."""
    product = await service.get_by_barcode(barcode, current_store.id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    data: ProductUpdate,
    service: ProductService = Depends(get_service),
    current_store: Store = Depends(get_current_store),
):
    """Update product."""
    product = await service.update(product_id, data, current_store.id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.delete("/{product_id}", status_code=204)
async def delete_product(
    product_id: int,
    service: ProductService = Depends(get_service),
    current_store: Store = Depends(get_current_store),
):
    """Soft delete product (set inactive)."""
    success = await service.delete(product_id, current_store.id)
    if not success:
        raise HTTPException(status_code=404, detail="Product not found")


@router.post("/bulk", response_model=List[ProductResponse])
async def bulk_create_products(
    data: List[ProductCreate],
    service: ProductService = Depends(get_service),
    current_store: Store = Depends(get_current_store),
):
    """Bulk create/update products."""
    if len(data) > 1000:
        raise HTTPException(status_code=400, detail="Maximum 1000 items allowed in bulk operation")
    return await service.bulk_create(data, current_store.id)


@router.post("/{product_id}/stock", response_model=ProductResponse)
async def adjust_stock(
    product_id: int,
    quantity: int,
    movement_type: str = "adjust",
    reference_type: Optional[str] = None,
    reference_id: Optional[int] = None,
    notes: Optional[str] = None,
    service: ProductService = Depends(get_service),
    current_store: Store = Depends(get_current_store),
):
    """Adjust product stock."""
    validate_stock_movement_type(movement_type)
    validate_positive_quantity(quantity)
    product = await service.update_stock(
        product_id, quantity, movement_type, reference_type, reference_id, notes, current_store.id
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product