"""Sync/Backup API routes."""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.sync_service import SyncService
from app.schemas import SyncRequest, SyncResponse, BackupResponse
from app.auth import get_current_store
from app.models import Store

router = APIRouter(prefix="/sync", tags=["Sync/Backup"])


def get_service(db: AsyncSession = Depends(get_db)) -> SyncService:
    return SyncService(db)


@router.post("", response_model=SyncResponse)
async def sync_from_client(
    data: SyncRequest,
    service: SyncService = Depends(get_service),
    current_store: Store = Depends(get_current_store),
):
    """Sync data from client (localStorage) to backend — scoped to current store."""
    return await service.sync_from_client(data, store_id=current_store.id)


@router.get("/backup", response_model=BackupResponse)
async def full_backup(
    service: SyncService = Depends(get_service),
    current_store: Store = Depends(get_current_store),
):
    """Get full backup of the current store's data."""
    data = await service.full_backup(store_id=current_store.id)
    return BackupResponse(
        timestamp=datetime.utcnow(),
        version="1.0.0",
        data=data
    )


@router.post("/restore", response_model=SyncResponse)
async def restore_backup(
    data: dict,
    service: SyncService = Depends(get_service),
    current_store: Store = Depends(get_current_store),
):
    """Restore backup data into the current store (replaces this store's data).

    ไฟล์ผิดรูปจะได้ 400 และข้อมูลเดิมไม่ถูกแตะ; ถ้ากู้คืนล้มกลางทาง service
    จะย้อนข้อมูลเดิมกลับให้ แล้วส่ง 500 พร้อมข้อความอธิบาย
    """
    try:
        return await service.restore_backup(data, store_id=current_store.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "database": "connected", "timestamp": datetime.utcnow().isoformat()}