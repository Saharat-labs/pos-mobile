"""Debts API routes."""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.debt_service import DebtService
from app.schemas import DebtCreate, DebtUpdate, DebtPaymentCreate, DebtResponse, DebtListResponse, DebtPaymentResponse
from app.api.validation import validate_page_params, validate_debt_status, MAX_PAGE_SIZE

router = APIRouter(prefix="/debts", tags=["Debts"])


def get_service(db: AsyncSession = Depends(get_db)) -> DebtService:
    return DebtService(db)


@router.post("", response_model=DebtResponse, status_code=201)
async def create_debt(data: DebtCreate, service: DebtService = Depends(get_service)):
    """Create new debt record."""
    return await service.create(data)


@router.get("", response_model=DebtListResponse)
async def list_debts(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=MAX_PAGE_SIZE),
    status: Optional[str] = Query(None, pattern="^(open|partial|paid)$"),
    search: Optional[str] = None,
    service: DebtService = Depends(get_service),
):
    """List debts with filters."""
    page, page_size = validate_page_params(page, page_size)
    if status:
        validate_debt_status(status)
    items, total = await service.list(page, page_size, status, search)
    return DebtListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/summary")
async def get_debt_summary(service: DebtService = Depends(get_service)):
    """Get total outstanding debt."""
    total = await service.get_total_outstanding()
    return {"total_outstanding": float(total)}


@router.get("/{debt_id}", response_model=DebtResponse)
async def get_debt(debt_id: int, service: DebtService = Depends(get_service)):
    """Get debt by ID."""
    debt = await service.get(debt_id)
    if not debt:
        raise HTTPException(status_code=404, detail="Debt not found")
    return debt


@router.get("/customer/{customer_name}", response_model=DebtResponse)
async def get_debt_by_customer(customer_name: str, service: DebtService = Depends(get_service)):
    """Get open debt by customer name."""
    debt = await service.get_by_customer(customer_name)
    if not debt:
        raise HTTPException(status_code=404, detail="Debt not found")
    return debt


@router.put("/{debt_id}", response_model=DebtResponse)
async def update_debt(debt_id: int, data: DebtUpdate, service: DebtService = Depends(get_service)):
    """Update debt info."""
    debt = await service.update(debt_id, data)
    if not debt:
        raise HTTPException(status_code=404, detail="Debt not found")
    return debt


@router.post("/{debt_id}/payments", response_model=DebtPaymentResponse, status_code=201)
async def add_payment(debt_id: int, data: DebtPaymentCreate, service: DebtService = Depends(get_service)):
    """Add payment to debt."""
    if data.amount <= 0:
        raise HTTPException(status_code=400, detail="Payment amount must be positive")
    payment = await service.add_payment(debt_id, data)
    if not payment:
        raise HTTPException(status_code=404, detail="Debt not found")
    return payment