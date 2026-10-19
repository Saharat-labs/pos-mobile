"""API routes package."""

from app.api import products, sales, purchases, debts, expenses, stock_movements, hold_bills, settings, sync
from fastapi import APIRouter

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(products.router)
api_router.include_router(sales.router)
api_router.include_router(purchases.router)
api_router.include_router(debts.router)
api_router.include_router(expenses.router)
api_router.include_router(stock_movements.router)
api_router.include_router(hold_bills.router)
api_router.include_router(settings.router)
api_router.include_router(sync.router)

__all__ = ["api_router"]