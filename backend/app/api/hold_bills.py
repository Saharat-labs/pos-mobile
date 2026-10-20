"""Hold Bills API routes."""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.hold_bill_service import HoldBillService
from app.schemas import HoldBillCreate, HoldBillResponse, HoldBillListResponse
from app.api.validation import validate_page_params, MAX_PAGE_SIZE

router = APIRouter(prefix="/hold-bills", tags=["Hold Bills"])


def get_service(db: AsyncSession = Depends(get_db)) -> HoldBillService:
    return HoldBillService(db)


@router.post("", response_model=HoldBillResponse, status_code=201)
async def create_hold_bill(data: HoldBillCreate, service: HoldBillService = Depends(get_service)):
    """Create new hold bill."""
    return await service.create(data)


@router.get("", response_model=HoldBillListResponse)
async def list_hold_bills(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=MAX_PAGE_SIZE),
    service: HoldBillService = Depends(get_service),
):
    """List hold bills."""
    page, page_size = validate_page_params(page, page_size)
    items, total = await service.list(page, page_size)
    return HoldBillListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{bill_id}", response_model=HoldBillResponse)
async def get_hold_bill(bill_id: int, service: HoldBillService = Depends(get_service)):
    """Get hold bill by ID."""
    bill = await service.get(bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Hold bill not found")
    return bill


@router.get("/bill/{bill_no}", response_model=HoldBillResponse)
async def get_hold_bill_by_no(bill_no: str, service: HoldBillService = Depends(get_service)):
    """Get hold bill by bill number."""
    bill = await service.get_by_bill_no(bill_no)
    if not bill:
        raise HTTPException(status_code=404, detail="Hold bill not found")
    return bill


@router.delete("/{bill_id}", status_code=204)
async def delete_hold_bill(bill_id: int, service: HoldBillService = Depends(get_service)):
    """Delete hold bill."""
    success = await service.delete(bill_id)
    if not success:
        raise HTTPException(status_code=404, detail="Hold bill not found")