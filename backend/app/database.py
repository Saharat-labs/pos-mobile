"""Database setup and session management."""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config import settings
from app.base import Base


# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncSession:
    """Dependency for getting DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database - create all tables + default store (id=1).

    ผู้ใช้ทุกคน (รวม dev user ตอน AUTH_ENABLED=false) ผูกกับ store_id=1 เป็นค่า default
    ถ้าเริ่มด้วย `python run.py` บนฐานข้อมูลใหม่โดยไม่รัน alembic ก่อน จะไม่มีร้านเลย
    และทุก endpoint ตอบ 404 "Store not found" — จึงสร้างร้านเริ่มต้นให้เมื่อยังไม่มีร้านใด
    """
    from sqlalchemy import select, func
    from app.models import Store

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if not await conn.scalar(select(func.count()).select_from(Store.__table__)):
            await conn.execute(Store.__table__.insert().values(
                id=1, name="ร้านค้าเริ่มต้น", code="STORE001", is_active=True, is_default=True,
            ))


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()