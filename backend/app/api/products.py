"""Product API routes."""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.product_service import ProductService
from app.schemas import (
    ProductCreate, ProductUpdate, ProductResponse, ProductListResponse
)

router = APIRouter(prefix="/products", tags=["Products"])


def get_service(db: AsyncSession = Depends(get_db)) -> ProductService:
    return ProductService(db)


@router.post("", response_model=ProductResponse, status_code=201)
async def create_product(data: ProductCreate, service: ProductService = Depends(get_service)):
    """Create new product."""
    existing = await service.get_by_code(data.code)
    if existing:
        raise HTTPException(status_code=400, detail=f"Product with code {data.code} already exists")
    if data.barcode:
        existing = await service.get_by_barcode(data.barcode)
        if existing:
            raise HTTPException(status_code=400, detail=f"Product with barcode {data.barcode} already exists")
    return await service.create(data)


@router.get("", response_model=ProductListResponse)
async def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    category: Optional[str] = None,
    stock_filter: Optional[str] = Query(None, pattern="^(available|low|out)$"),
    active_only: bool = True,
    service: ProductService = Depends(get_service),
):
    """List products with filters."""
    items, total = await service.list(page, page_size, search, category, stock_filter, active_only)
    return ProductListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/categories", response_model=List[str])
async def get_categories(service: ProductService = Depends(get_service)):
    """Get all product categories."""
    return await service.get_categories()


@router.get("/low-stock", response_model=List[ProductResponse])
async def get_low_stock(service: ProductService = Depends(get_service)):
    """Get products with low stock."""
    return await service.get_low_stock()


@router.get("/expiring", response_model=List[ProductResponse])
async def get_expiring(days: int = Query(30, ge=1), service: ProductService = Depends(get_service)):
    """Get products expiring soon."""
    return await service.get_expiring_soon(days)


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int, service: ProductService = Depends(get_service)):
    """Get product by ID."""
    product = await service.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.get("/code/{code}", response_model=ProductResponse)
async def get_product_by_code(code: str, service: ProductService = Depends(get_service)):
    """Get product by code."""
    product = await service.get_by_code(code)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.get("/barcode/{barcode}", response_model=ProductResponse)
async def get_product_by_barcode(barcode: str, service: ProductService = Depends(get_service)):
    """Get product by barcode."""
    product = await service.get_by_barcode(barcode)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(product_id: int, data: ProductUpdate, service: ProductService = Depends(get_service)):
    """Update product."""
    product = await service.update(product_id, data)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.delete("/{product_id}", status_code=204)
async def delete_product(product_id: int, service: ProductService = Depends(get_service)):
    """Soft delete product (set inactive)."""
    success = await service.delete(product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Product not found")


@router.post("/bulk", response_model=List[ProductResponse])
async def bulk_create_products(data: List[ProductCreate], service: ProductService = Depends(get_service)):
    """Bulk create/update products."""
    return await service.bulk_create(data)


@router.post("/{product_id}/stock", response_model=ProductResponse)
async def adjust_stock(
    product_id: int,
    quantity: int,
    movement_type: str = "adjust",
    reference_type: Optional[str] = None,
    reference_id: Optional[int] = None,
    notes: Optional[str] = None,
    service: ProductService = Depends(get_service),
):
    """Adjust product stock."""
    product = await service.update_stock(product_id, quantity, movement_type, reference_type, reference_id, notes)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product