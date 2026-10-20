"""Sync/Backup API routes."""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.sync_service import SyncService
from app.schemas import SyncRequest, SyncResponse, BackupResponse

router = APIRouter(prefix="/sync", tags=["Sync/Backup"])


def get_service(db: AsyncSession = Depends(get_db)) -> SyncService:
    return SyncService(db)


@router.post("", response_model=SyncResponse)
async def sync_from_client(data: SyncRequest, service: SyncService = Depends(get_service)):
    """Sync data from client (localStorage) to backend."""
    return await service.sync_from_client(data)


@router.get("/backup", response_model=BackupResponse)
async def full_backup(service: SyncService = Depends(get_service)):
    """Get full backup of all data."""
    data = await service.full_backup()
    return BackupResponse(
        timestamp=datetime.utcnow(),
        version="1.0.0",
        data=data
    )


@router.post("/restore", response_model=SyncResponse)
async def restore_backup(data: dict, service: SyncService = Depends(get_service)):
    """Restore from backup data (replaces all data)."""
    return await service.restore_backup(data)


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "database": "connected", "timestamp": datetime.utcnow().isoformat()}