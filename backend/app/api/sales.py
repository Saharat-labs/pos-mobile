"""Sales API routes."""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.sale_service import SaleService
from app.schemas import SaleCreate, SaleUpdate, SaleResponse, SaleListResponse

router = APIRouter(prefix="/sales", tags=["Sales"])


def get_service(db: AsyncSession = Depends(get_db)) -> SaleService:
    return SaleService(db)


@router.post("", response_model=SaleResponse, status_code=201)
async def create_sale(data: SaleCreate, service: SaleService = Depends(get_service)):
    """Create new sale."""
    if not data.items:
        raise HTTPException(status_code=400, detail="Sale must have at least one item")
    return await service.create(data)


@router.get("", response_model=SaleListResponse)
async def list_sales(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    payment_method: Optional[str] = None,
    status: Optional[str] = None,
    service: SaleService = Depends(get_service),
):
    """List sales with filters."""
    items, total = await service.list(page, page_size, start_date, end_date, payment_method, status)
    return SaleListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/summary/daily")
async def daily_summary(date: Optional[datetime] = None, service: SaleService = Depends(get_service)):
    """Get daily sales summary."""
    if date is None:
        date = datetime.utcnow()
    return await service.get_daily_summary(date)


@router.get("/summary/top-products")
async def top_products(
    start_date: datetime,
    end_date: datetime,
    limit: int = Query(10, ge=1, le=100),
    service: SaleService = Depends(get_service),
):
    """Get top selling products."""
    return await service.get_top_products(start_date, end_date, limit)


@router.get("/{sale_id}", response_model=SaleResponse)
async def get_sale(sale_id: int, service: SaleService = Depends(get_service)):
    """Get sale by ID."""
    sale = await service.get(sale_id)
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    return sale


@router.get("/bill/{bill_no}", response_model=SaleResponse)
async def get_sale_by_bill_no(bill_no: str, service: SaleService = Depends(get_service)):
    """Get sale by bill number."""
    sale = await service.get_by_bill_no(bill_no)
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    return sale


@router.put("/{sale_id}", response_model=SaleResponse)
async def update_sale(sale_id: int, data: SaleUpdate, service: SaleService = Depends(get_service)):
    """Update sale."""
    sale = await service.update(sale_id, data)
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    return sale