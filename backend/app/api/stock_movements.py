"""Stock Movements API routes."""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.stock_service import StockMovementService
from app.schemas import StockMovementCreate, StockMovementResponse, StockMovementListResponse
from app.api.validation import (
    validate_page_params, validate_date_range, validate_stock_movement_type, MAX_PAGE_SIZE
)
from app.auth import get_current_store
from app.models import Store

router = APIRouter(prefix="/stock-movements", tags=["Stock Movements"])


def get_service(db: AsyncSession = Depends(get_db)) -> StockMovementService:
    return StockMovementService(db)


@router.post("", response_model=StockMovementResponse, status_code=201)
async def create_stock_movement(
    data: StockMovementCreate,
    service: StockMovementService = Depends(get_service),
    current_store: Store = Depends(get_current_store),
):
    """Create stock movement (adjusts product stock)."""
    validate_stock_movement_type(data.movement_type)
    if data.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")
    return await service.create(data, current_store.id)


@router.get("", response_model=StockMovementListResponse)
async def list_stock_movements(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=MAX_PAGE_SIZE),
    product_id: Optional[int] = None,
    movement_type: Optional[str] = Query(None, pattern="^(in|out|adjust|waste|return)$"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    service: StockMovementService = Depends(get_service),
    current_store: Store = Depends(get_current_store),
):
    """List stock movements with filters."""
    page, page_size = validate_page_params(page, page_size)
    start_date, end_date = validate_date_range(start_date, end_date)
    if movement_type:
        validate_stock_movement_type(movement_type)
    items, total = await service.list(
        page, page_size, product_id, movement_type, start_date, end_date, current_store.id
    )
    return StockMovementListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/product/{product_id}", response_model=List[StockMovementResponse])
async def get_product_history(
    product_id: int,
    limit: int = Query(50, ge=1, le=MAX_PAGE_SIZE),
    service: StockMovementService = Depends(get_service),
    current_store: Store = Depends(get_current_store),
):
    """Get stock history for a product."""
    return await service.get_product_history(product_id, limit, current_store.id)
