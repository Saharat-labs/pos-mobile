"""Settings API routes."""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.setting_service import SettingService, CategoryMappingService
from app.schemas import SettingCreate, SettingUpdate, SettingResponse, CategoryMappingCreate, CategoryMappingUpdate, CategoryMappingResponse
from app.api.validation import validate_page_params, MAX_PAGE_SIZE, MAX_BULK_ITEMS
from app.auth import get_current_store
from app.models import Store

router = APIRouter(prefix="/settings", tags=["Settings"])
# Separate router for category mappings so it is registered BEFORE the
# catch-all "/{key}" routes and does not get shadowed by them.
mappings_router = APIRouter(prefix="/settings", tags=["Category Mappings"])


def get_setting_service(db: AsyncSession = Depends(get_db)) -> SettingService:
    return SettingService(db)


def get_mapping_service(db: AsyncSession = Depends(get_db)) -> CategoryMappingService:
    return CategoryMappingService(db)


# ==================== Category Mappings (must come before /{key}) ====================
@mappings_router.get("/mappings", response_model=List[CategoryMappingResponse])
async def list_category_mappings(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=MAX_PAGE_SIZE),
    service: CategoryMappingService = Depends(get_mapping_service),
):
    """List all category mappings with pagination."""
    page, page_size = validate_page_params(page, page_size)
    mappings = await service.list()
    start = (page - 1) * page_size
    end = start + page_size
    return mappings[start:end]


@mappings_router.post("/mappings", response_model=CategoryMappingResponse, status_code=201)
async def create_category_mapping(data: CategoryMappingCreate, service: CategoryMappingService = Depends(get_mapping_service)):
    """Create new category mapping."""
    if not data.code_prefix or len(data.code_prefix) > 20:
        raise HTTPException(status_code=400, detail="code_prefix must be 1-20 characters")
    if not data.category or len(data.category) > 100:
        raise HTTPException(status_code=400, detail="category must be 1-100 characters")
    existing = await service.get(data.code_prefix)
    if existing:
        raise HTTPException(status_code=400, detail=f"Mapping for prefix {data.code_prefix} already exists")
    return await service.create(data)


@mappings_router.post("/mappings/bulk", response_model=List[CategoryMappingResponse], status_code=201)
async def bulk_create_mappings(data: List[CategoryMappingCreate], service: CategoryMappingService = Depends(get_mapping_service)):
    """Bulk create/update category mappings."""
    if len(data) > MAX_BULK_ITEMS:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_BULK_ITEMS} items allowed in bulk operation")
    for item in data:
        if not item.code_prefix or len(item.code_prefix) > 20:
            raise HTTPException(status_code=400, detail="code_prefix must be 1-20 characters")
        if not item.category or len(item.category) > 100:
            raise HTTPException(status_code=400, detail="category must be 1-100 characters")
    return await service.bulk_create(data)


@mappings_router.get("/mappings/{code_prefix}", response_model=CategoryMappingResponse)
async def get_category_mapping(code_prefix: str, service: CategoryMappingService = Depends(get_mapping_service)):
    """Get category mapping by code prefix."""
    mapping = await service.get(code_prefix)
    if not mapping:
        raise HTTPException(status_code=404, detail="Category mapping not found")
    return mapping


@mappings_router.put("/mappings/{code_prefix}", response_model=CategoryMappingResponse)
async def update_category_mapping(code_prefix: str, data: CategoryMappingUpdate, service: CategoryMappingService = Depends(get_mapping_service)):
    """Update category mapping."""
    if data.category is not None and (not data.category or len(data.category) > 100):
        raise HTTPException(status_code=400, detail="category must be 1-100 characters")
    mapping = await service.update(code_prefix, data)
    if not mapping:
        raise HTTPException(status_code=404, detail="Category mapping not found")
    return mapping


@mappings_router.delete("/mappings/{code_prefix}", status_code=204)
async def delete_category_mapping(code_prefix: str, service: CategoryMappingService = Depends(get_mapping_service)):
    """Delete category mapping."""
    success = await service.delete(code_prefix)
    if not success:
        raise HTTPException(status_code=404, detail="Category mapping not found")
    return


# ==================== Settings ====================
@router.get("", response_model=List[SettingResponse])
async def list_settings(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=MAX_PAGE_SIZE),
    service: SettingService = Depends(get_setting_service),
    current_store: Store = Depends(get_current_store),
):
    """List all settings with pagination (scoped to the current store)."""
    page, page_size = validate_page_params(page, page_size)
    settings = await service.list(store_id=current_store.id)
    # Simple pagination for settings
    start = (page - 1) * page_size
    end = start + page_size
    return settings[start:end]


@router.post("", response_model=SettingResponse, status_code=201)
async def create_setting(
    data: SettingCreate,
    service: SettingService = Depends(get_setting_service),
    current_store: Store = Depends(get_current_store),
):
    """Create or update setting (scoped to the current store)."""
    return await service.set(data.key, data.value, data.description, store_id=current_store.id)


@router.get("/{key}", response_model=SettingResponse)
async def get_setting(
    key: str,
    service: SettingService = Depends(get_setting_service),
    current_store: Store = Depends(get_current_store),
):
    """Get setting by key (scoped to the current store)."""
    setting = await service.get(key, store_id=current_store.id)
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    return setting


@router.put("/{key}", response_model=SettingResponse)
async def update_setting(
    key: str,
    data: SettingUpdate,
    service: SettingService = Depends(get_setting_service),
    current_store: Store = Depends(get_current_store),
):
    """Update setting value and/or description (scoped to the current store)."""
    existing = await service.get(key, store_id=current_store.id)
    if not existing:
        raise HTTPException(status_code=404, detail="Setting not found")
    new_value = data.value if data.value is not None else existing.value
    new_desc = data.description if data.description is not None else existing.description
    return await service.set(key, new_value, new_desc, store_id=current_store.id)


@router.delete("/{key}", status_code=204)
async def delete_setting(
    key: str,
    service: SettingService = Depends(get_setting_service),
    current_store: Store = Depends(get_current_store),
):
    """Delete setting (scoped to the current store)."""
    success = await service.delete(key, store_id=current_store.id)
    if not success:
        raise HTTPException(status_code=404, detail="Setting not found")
    return
