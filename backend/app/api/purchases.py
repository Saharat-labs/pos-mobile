"""Purchases API routes."""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.purchase_service import PurchaseService
from app.schemas import PurchaseCreate, PurchaseUpdate, PurchaseResponse, PurchaseListResponse

router = APIRouter(prefix="/purchases", tags=["Purchases"])


def get_service(db: AsyncSession = Depends(get_db)) -> PurchaseService:
    return PurchaseService(db)


@router.post("", response_model=PurchaseResponse, status_code=201)
async def create_purchase(data: PurchaseCreate, service: PurchaseService = Depends(get_service)):
    """Create new purchase order."""
    if not data.items:
        raise HTTPException(status_code=400, detail="Purchase must have at least one item")
    return await service.create(data)


@router.get("", response_model=PurchaseListResponse)
async def list_purchases(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    status: Optional[str] = None,
    service: PurchaseService = Depends(get_service),
):
    """List purchases with filters."""
    items, total = await service.list(page, page_size, start_date, end_date, status)
    return PurchaseListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{purchase_id}", response_model=PurchaseResponse)
async def get_purchase(purchase_id: int, service: PurchaseService = Depends(get_service)):
    """Get purchase by ID."""
    purchase = await service.get(purchase_id)
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase not found")
    return purchase


@router.get("/po/{po_no}", response_model=PurchaseResponse)
async def get_purchase_by_po_no(po_no: str, service: PurchaseService = Depends(get_service)):
    """Get purchase by PO number."""
    purchase = await service.get_by_po_no(po_no)
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase not found")
    return purchase


@router.put("/{purchase_id}", response_model=PurchaseResponse)
async def update_purchase(purchase_id: int, data: PurchaseUpdate, service: PurchaseService = Depends(get_service)):
    """Update purchase."""
    purchase = await service.update(purchase_id, data)
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase not found")
    return purchase


@router.post("/{purchase_id}/receive", response_model=PurchaseResponse)
async def receive_purchase(
    purchase_id: int,
    received_items: List[dict],
    service: PurchaseService = Depends(get_service),
):
    """Receive purchase items."""
    purchase = await service.receive(purchase_id, received_items)
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase not found")
    return purchase