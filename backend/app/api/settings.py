"""Settings API routes."""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.setting_service import SettingService, CategoryMappingService
from app.schemas import SettingCreate, SettingUpdate, SettingResponse, CategoryMappingCreate, CategoryMappingUpdate, CategoryMappingResponse

router = APIRouter(prefix="/settings", tags=["Settings"])


def get_setting_service(db: AsyncSession = Depends(get_db)) -> SettingService:
    return SettingService(db)


def get_mapping_service(db: AsyncSession = Depends(get_db)) -> CategoryMappingService:
    return CategoryMappingService(db)


# Settings
@router.get("", response_model=List[SettingResponse])
async def list_settings(service: SettingService = Depends(get_setting_service)):
    """List all settings."""
    return await service.list()


@router.get("/{key}", response_model=SettingResponse)
async def get_setting(key: str, service: SettingService = Depends(get_setting_service)):
    """Get setting by key."""
    setting = await service.get(key)
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    return setting


@router.post("", response_model=SettingResponse, status_code=201)
async def create_setting(data: SettingCreate, service: SettingService = Depends(get_setting_service)):
    """Create or update setting."""
    return await service.set(data.key, data.value, data.description)


@router.put("/{key}", response_model=SettingResponse)
async def update_setting(key: str, data: SettingUpdate, service: SettingService = Depends(get_setting_service)):
    """Update setting value."""
    setting = await service.set(key, data.value) if data.value is not None else await service.get(key)
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    return setting


@router.delete("/{key}", status_code=204)
async def delete_setting(key: str, service: SettingService = Depends(get_setting_service)):
    """Delete setting."""
    success = await service.delete(key)
    if not success:
        raise HTTPException(status_code=404, detail="Setting not found")


# Category Mappings
@router.get("/mappings", response_model=List[CategoryMappingResponse], tags=["Category Mappings"])
async def list_category_mappings(service: CategoryMappingService = Depends(get_mapping_service)):
    """List all category mappings."""
    return await service.list()


@router.post("/mappings", response_model=CategoryMappingResponse, status_code=201, tags=["Category Mappings"])
async def create_category_mapping(data: CategoryMappingCreate, service: CategoryMappingService = Depends(get_mapping_service)):
    """Create new category mapping."""
    existing = await service.get(data.code_prefix)
    if existing:
        raise HTTPException(status_code=400, detail=f"Mapping for prefix {data.code_prefix} already exists")
    return await service.create(data)


@router.put("/mappings/{code_prefix}", response_model=CategoryMappingResponse, tags=["Category Mappings"])
async def update_category_mapping(code_prefix: str, data: CategoryMappingUpdate, service: CategoryMappingService = Depends(get_mapping_service)):
    """Update category mapping."""
    mapping = await service.update(code_prefix, data)
    if not mapping:
        raise HTTPException(status_code=404, detail="Category mapping not found")
    return mapping


@router.delete("/mappings/{code_prefix}", status_code=204, tags=["Category Mappings"])
async def delete_category_mapping(code_prefix: str, service: CategoryMappingService = Depends(get_mapping_service)):
    """Delete category mapping."""
    success = await service.delete(code_prefix)
    if not success:
        raise HTTPException(status_code=404, detail="Category mapping not found")


@router.post("/mappings/bulk", response_model=List[CategoryMappingResponse], tags=["Category Mappings"])
async def bulk_create_mappings(data: List[CategoryMappingCreate], service: CategoryMappingService = Depends(get_mapping_service)):
    """Bulk create/update category mappings."""
    return await service.bulk_create(data)