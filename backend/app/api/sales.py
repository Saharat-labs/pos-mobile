"""Sales API routes."""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.sale_service import SaleService
from app.schemas import SaleCreate, SaleUpdate, SaleResponse, SaleListResponse
from app.api.validation import (
    validate_page_params, validate_date_range, validate_payment_method,
    validate_sale_status, MAX_PAGE_SIZE, VALID_PAYMENT_METHODS
)
from app.auth import get_current_store
from app.models import Store

router = APIRouter(prefix="/sales", tags=["Sales"])


def get_service(db: AsyncSession = Depends(get_db)) -> SaleService:
    return SaleService(db)


@router.post("", response_model=SaleResponse, status_code=201)
async def create_sale(
    data: SaleCreate,
    service: SaleService = Depends(get_service),
    current_store: Store = Depends(get_current_store),
):
    """Create new sale."""
    if not data.items:
        raise HTTPException(status_code=400, detail="Sale must have at least one item")
    if data.payment_method not in VALID_PAYMENT_METHODS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid payment_method. Must be one of: {', '.join(VALID_PAYMENT_METHODS)}"
        )
    # Validate each item has positive quantity
    for item in data.items:
        if item.quantity <= 0:
            raise HTTPException(status_code=400, detail="Item quantity must be positive")
    return await service.create(data, current_store.id)


@router.get("", response_model=SaleListResponse)
async def list_sales(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=MAX_PAGE_SIZE),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    payment_method: Optional[str] = Query(None, pattern="^(cash|transfer|card|credit)$"),
    status: Optional[str] = Query(None, pattern="^(completed|held|cancelled)$"),
    service: SaleService = Depends(get_service),
    current_store: Store = Depends(get_current_store),
):
    """List sales with filters."""
    page, page_size = validate_page_params(page, page_size)
    start_date, end_date = validate_date_range(start_date, end_date)
    if payment_method:
        validate_payment_method(payment_method)
    if status:
        validate_sale_status(status)
    items, total = await service.list(page, page_size, start_date, end_date, payment_method, status, current_store.id)
    return SaleListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/summary/daily")
async def daily_summary(
    date: Optional[datetime] = None,
    service: SaleService = Depends(get_service),
    current_store: Store = Depends(get_current_store),
):
    """Get daily sales summary."""
    if date is None:
        date = datetime.utcnow()
    return await service.get_daily_summary(date, current_store.id)


@router.get("/summary/top-products")
async def top_products(
    start_date: datetime,
    end_date: datetime,
    limit: int = Query(10, ge=1, le=100),
    service: SaleService = Depends(get_service),
    current_store: Store = Depends(get_current_store),
):
    """Get top selling products."""
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date must be before or equal to end_date")
    return await service.get_top_products(start_date, end_date, limit, current_store.id)


@router.get("/{sale_id}", response_model=SaleResponse)
async def get_sale(
    sale_id: int,
    service: SaleService = Depends(get_service),
    current_store: Store = Depends(get_current_store),
):
    """Get sale by ID."""
    sale = await service.get(sale_id, current_store.id)
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    return sale


@router.get("/bill/{bill_no}", response_model=SaleResponse)
async def get_sale_by_bill_no(
    bill_no: str,
    service: SaleService = Depends(get_service),
    current_store: Store = Depends(get_current_store),
):
    """Get sale by bill number."""
    sale = await service.get_by_bill_no(bill_no, current_store.id)
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    return sale


@router.put("/{sale_id}", response_model=SaleResponse)
async def update_sale(
    sale_id: int,
    data: SaleUpdate,
    service: SaleService = Depends(get_service),
    current_store: Store = Depends(get_current_store),
):
    """Update sale."""
    sale = await service.update(sale_id, data, current_store.id)
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    return sale