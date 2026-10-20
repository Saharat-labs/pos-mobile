"""Purchases API routes."""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.purchase_service import PurchaseService
from app.schemas import PurchaseCreate, PurchaseUpdate, PurchaseResponse, PurchaseListResponse
from app.api.validation import (
    validate_page_params, validate_date_range, validate_purchase_status, MAX_PAGE_SIZE
)
from app.auth import get_current_store
from app.models import Store

router = APIRouter(prefix="/purchases", tags=["Purchases"])


def get_service(db: AsyncSession = Depends(get_db)) -> PurchaseService:
    return PurchaseService(db)


@router.post("", response_model=PurchaseResponse, status_code=201)
async def create_purchase(
    data: PurchaseCreate,
    service: PurchaseService = Depends(get_service),
    current_store: Store = Depends(get_current_store),
):
    """Create new purchase order."""
    if not data.items:
        raise HTTPException(status_code=400, detail="Purchase must have at least one item")
    for item in data.items:
        if item.quantity <= 0:
            raise HTTPException(status_code=400, detail="Item quantity must be positive")
    return await service.create(data, current_store.id)


@router.get("", response_model=PurchaseListResponse)
async def list_purchases(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=MAX_PAGE_SIZE),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    status: Optional[str] = Query(None, pattern="^(pending|received|cancelled)$"),
    service: PurchaseService = Depends(get_service),
    current_store: Store = Depends(get_current_store),
):
    """List purchases with filters."""
    page, page_size = validate_page_params(page, page_size)
    start_date, end_date = validate_date_range(start_date, end_date)
    if status:
        validate_purchase_status(status)
    items, total = await service.list(page, page_size, start_date, end_date, status, current_store.id)
    return PurchaseListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{purchase_id}", response_model=PurchaseResponse)
async def get_purchase(
    purchase_id: int,
    service: PurchaseService = Depends(get_service),
    current_store: Store = Depends(get_current_store),
):
    """Get purchase by ID."""
    purchase = await service.get(purchase_id, current_store.id)
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase not found")
    return purchase


@router.get("/po/{po_no}", response_model=PurchaseResponse)
async def get_purchase_by_po_no(
    po_no: str,
    service: PurchaseService = Depends(get_service),
    current_store: Store = Depends(get_current_store),
):
    """Get purchase by PO number."""
    purchase = await service.get_by_po_no(po_no, current_store.id)
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase not found")
    return purchase


@router.put("/{purchase_id}", response_model=PurchaseResponse)
async def update_purchase(
    purchase_id: int,
    data: PurchaseUpdate,
    service: PurchaseService = Depends(get_service),
    current_store: Store = Depends(get_current_store),
):
    """Update purchase."""
    purchase = await service.update(purchase_id, data, current_store.id)
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase not found")
    return purchase


@router.post("/{purchase_id}/receive", response_model=PurchaseResponse)
async def receive_purchase(
    purchase_id: int,
    received_items: List[dict] = Body(...),
    service: PurchaseService = Depends(get_service),
    current_store: Store = Depends(get_current_store),
):
    """Receive purchase items (body: list of {item_id, received_qty})."""
    if not received_items:
        raise HTTPException(status_code=400, detail="Received items cannot be empty")
    for item in received_items:
        if not isinstance(item.get("received_qty"), int) or item["received_qty"] < 0:
            raise HTTPException(status_code=400, detail="received_qty must be a non-negative integer")
    purchase = await service.receive(purchase_id, received_items, current_store.id)
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase not found")
    return purchase