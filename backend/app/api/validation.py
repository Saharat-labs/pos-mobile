"""Shared validation utilities for API endpoints."""

from typing import Optional
from datetime import datetime
from fastapi import Query, HTTPException
from pydantic import BaseModel, field_validator


# Common query parameter validations
DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100
MAX_BULK_ITEMS = 1000

# Enum-like validations
VALID_PAYMENT_METHODS = ["cash", "transfer", "card", "credit"]
VALID_SALE_STATUSES = ["completed", "held", "cancelled"]
VALID_PURCHASE_STATUSES = ["pending", "received", "cancelled"]
VALID_DEBT_STATUSES = ["open", "partial", "paid"]
VALID_STOCK_MOVEMENT_TYPES = ["in", "out", "adjust", "waste", "return"]
VALID_STOCK_FILTERS = ["available", "low", "out"]


def validate_page_params(
    page: int = Query(DEFAULT_PAGE, ge=1, description="Page number (1-based)"),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Items per page"),
) -> tuple[int, int]:
    """Validate and return page and page_size."""
    return page, page_size


def validate_date_range(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> tuple[Optional[datetime], Optional[datetime]]:
    """Validate date range - start_date must be before end_date."""
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date must be before or equal to end_date")
    return start_date, end_date


def validate_payment_method(payment_method: str) -> str:
    """Validate payment method."""
    if payment_method not in VALID_PAYMENT_METHODS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid payment_method. Must be one of: {', '.join(VALID_PAYMENT_METHODS)}"
        )
    return payment_method


def validate_sale_status(status: str) -> str:
    """Validate sale status."""
    if status not in VALID_SALE_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(VALID_SALE_STATUSES)}"
        )
    return status


def validate_purchase_status(status: str) -> str:
    """Validate purchase status."""
    if status not in VALID_PURCHASE_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(VALID_PURCHASE_STATUSES)}"
        )
    return status


def validate_debt_status(status: str) -> str:
    """Validate debt status."""
    if status not in VALID_DEBT_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(VALID_DEBT_STATUSES)}"
        )
    return status


def validate_stock_movement_type(movement_type: str) -> str:
    """Validate stock movement type."""
    if movement_type not in VALID_STOCK_MOVEMENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid movement_type. Must be one of: {', '.join(VALID_STOCK_MOVEMENT_TYPES)}"
        )
    return movement_type


def validate_positive_quantity(quantity: int) -> int:
    """Validate quantity is positive."""
    if quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")
    return quantity


def validate_positive_amount(amount: float) -> float:
    """Validate amount is positive."""
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    return amount


class PaginationParams(BaseModel):
    """Pagination parameters model."""
    page: int = DEFAULT_PAGE
    page_size: int = DEFAULT_PAGE_SIZE

    @field_validator("page")
    @classmethod
    def page_ge_1(cls, v: int) -> int:
        if v < 1:
            raise ValueError("page must be >= 1")
        return v

    @field_validator("page_size")
    @classmethod
    def page_size_range(cls, v: int) -> int:
        if v < 1 or v > MAX_PAGE_SIZE:
            raise ValueError(f"page_size must be between 1 and {MAX_PAGE_SIZE}")
        return v


class DateRangeParams(BaseModel):
    """Date range parameters model."""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, v: Optional[datetime], info) -> Optional[datetime]:
        if v is not None and info.data.get("start_date") is not None:
            if info.data["start_date"] > v:
                raise ValueError("end_date must be after or equal to start_date")
        return v


# Dependency functions for FastAPI
async def get_pagination(
    page: int = Query(DEFAULT_PAGE, ge=1, le=10000, description="Page number"),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Items per page"),
) -> PaginationParams:
    """Get validated pagination params."""
    return PaginationParams(page=page, page_size=page_size)


async def get_date_range(
    start_date: Optional[datetime] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="End date (ISO format)"),
) -> DateRangeParams:
    """Get validated date range params."""
    return DateRangeParams(start_date=start_date, end_date=end_date)