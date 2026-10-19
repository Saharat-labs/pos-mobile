"""Stock Movements API routes."""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.stock_service import StockMovementService
from app.schemas import StockMovementCreate, StockMovementResponse

router = APIRouter(prefix="/stock-movements", tags=["Stock Movements"])


def get_service(db: AsyncSession = Depends(get_db)) -> StockMovementService:
    return StockMovementService(db)


@router.post("", response_model=StockMovementResponse, status_code=201)
async def create_stock_movement(data: StockMovementCreate, service: StockMovementService = Depends(get_service)):
    """Create stock movement (adjusts product stock)."""
    return await service.create(data)


@router.get("", response_model=List[StockMovementResponse])
async def list_stock_movements(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    product_id: Optional[int] = None,
    movement_type: Optional[str] = Query(None, pattern="^(in|out|adjust|waste|return)$"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    service: StockMovementService = Depends(get_service),
):
    """List stock movements with filters."""
    items, total = await service.list(page, page_size, product_id, movement_type, start_date, end_date)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/product/{product_id}", response_model=List[StockMovementResponse])
async def get_product_history(product_id: int, limit: int = Query(50, ge=1, le=200), service: StockMovementService = Depends(get_service)):
    """Get stock history for a product."""
    return await service.get_product_history(product_id, limit)