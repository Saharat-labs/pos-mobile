"""Expenses API routes."""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.expense_service import ExpenseService
from app.schemas import ExpenseCreate, ExpenseUpdate, ExpenseResponse, ExpenseListResponse
from app.api.validation import validate_page_params, validate_date_range, MAX_PAGE_SIZE
from app.auth import get_current_store
from app.models import Store

router = APIRouter(prefix="/expenses", tags=["Expenses"])


def get_service(db: AsyncSession = Depends(get_db)) -> ExpenseService:
    return ExpenseService(db)


@router.post("", response_model=ExpenseResponse, status_code=201)
async def create_expense(
    data: ExpenseCreate,
    service: ExpenseService = Depends(get_service),
    current_store: Store = Depends(get_current_store),
):
    """Create new expense."""
    return await service.create(data, current_store.id)


@router.get("", response_model=ExpenseListResponse)
async def list_expenses(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=MAX_PAGE_SIZE),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    category: Optional[str] = None,
    service: ExpenseService = Depends(get_service),
    current_store: Store = Depends(get_current_store),
):
    """List expenses with filters."""
    page, page_size = validate_page_params(page, page_size)
    start_date, end_date = validate_date_range(start_date, end_date)
    items, total = await service.list(page, page_size, start_date, end_date, category, current_store.id)
    return ExpenseListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/categories", response_model=List[str])
async def get_expense_categories(
    service: ExpenseService = Depends(get_service),
    current_store: Store = Depends(get_current_store),
):
    """Get all expense categories."""
    return await service.get_categories(current_store.id)


@router.get("/summary/monthly")
async def monthly_summary(
    year: int,
    month: int,
    service: ExpenseService = Depends(get_service),
    current_store: Store = Depends(get_current_store),
):
    """Get monthly expense summary."""
    if not (1 <= month <= 12):
        raise HTTPException(status_code=400, detail="Month must be between 1 and 12")
    if year < 2000 or year > 2100:
        raise HTTPException(status_code=400, detail="Year must be between 2000 and 2100")
    return await service.get_monthly_summary(year, month, current_store.id)


@router.get("/summary/yearly")
async def yearly_summary(
    year: int,
    service: ExpenseService = Depends(get_service),
    current_store: Store = Depends(get_current_store),
):
    """Get yearly expense summary."""
    if year < 2000 or year > 2100:
        raise HTTPException(status_code=400, detail="Year must be between 2000 and 2100")
    return await service.get_yearly_summary(year, current_store.id)


@router.get("/{expense_id}", response_model=ExpenseResponse)
async def get_expense(
    expense_id: int,
    service: ExpenseService = Depends(get_service),
    current_store: Store = Depends(get_current_store),
):
    """Get expense by ID."""
    expense = await service.get(expense_id, current_store.id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    return expense


@router.put("/{expense_id}", response_model=ExpenseResponse)
async def update_expense(
    expense_id: int,
    data: ExpenseUpdate,
    service: ExpenseService = Depends(get_service),
    current_store: Store = Depends(get_current_store),
):
    """Update expense."""
    expense = await service.update(expense_id, data, current_store.id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    return expense


@router.delete("/{expense_id}", status_code=204)
async def delete_expense(
    expense_id: int,
    service: ExpenseService = Depends(get_service),
    current_store: Store = Depends(get_current_store),
):
    """Delete expense."""
    success = await service.delete(expense_id, current_store.id)
    if not success:
        raise HTTPException(status_code=404, detail="Expense not found")
