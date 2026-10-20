"""Store API routes for multi-store support."""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.store_service import StoreService
from app.schemas import StoreCreate, StoreUpdate, StoreResponse, StoreListResponse
from app.auth import get_current_user, require_admin
from app.models import User


router = APIRouter(prefix="/stores", tags=["Stores"])


def get_service(db: AsyncSession = Depends(get_db)) -> StoreService:
    return StoreService(db)


@router.post("", response_model=StoreResponse, status_code=201)
async def create_store(
    data: StoreCreate,
    service: StoreService = Depends(get_service),
    current_user: User = Depends(require_admin),
):
    """Create new store (admin only)."""
    try:
        return await service.create(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=StoreListResponse)
async def list_stores(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    is_active: Optional[bool] = None,
    service: StoreService = Depends(get_service),
    current_user: User = Depends(get_current_user),
):
    """List stores."""
    items, total = await service.list(page=page, page_size=page_size, is_active=is_active)
    return StoreListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/default", response_model=StoreResponse)
async def get_default_store(
    service: StoreService = Depends(get_service),
    current_user: User = Depends(get_current_user),
):
    """Get default store."""
    store = await service.get_default()
    if not store:
        raise HTTPException(status_code=404, detail="No default store found")
    return store


@router.get("/{store_id}", response_model=StoreResponse)
async def get_store(
    store_id: int,
    service: StoreService = Depends(get_service),
    current_user: User = Depends(get_current_user),
):
    """Get store by ID."""
    store = await service.get(store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    return store


@router.put("/{store_id}", response_model=StoreResponse)
async def update_store(
    store_id: int,
    data: StoreUpdate,
    service: StoreService = Depends(get_service),
    current_user: User = Depends(require_admin),
):
    """Update store (admin only)."""
    store = await service.update(store_id, data)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    return store


@router.delete("/{store_id}")
async def delete_store(
    store_id: int,
    service: StoreService = Depends(get_service),
    current_user: User = Depends(require_admin),
):
    """Delete store (admin only)."""
    try:
        success = await service.delete(store_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not success:
        raise HTTPException(status_code=404, detail="Store not found")
    return {"message": "Store deleted"}


@router.get("/{store_id}/stats")
async def get_store_stats(
    store_id: int,
    service: StoreService = Depends(get_service),
    current_user: User = Depends(get_current_user),
):
    """Get store statistics."""
    stats = await service.get_store_stats(store_id)
    return stats
