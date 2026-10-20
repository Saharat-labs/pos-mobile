"""Test configuration and fixtures."""
import asyncio
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add backend to path
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.models import Base, Store
from app.database import get_db
from app.main import app
from app.config import settings


# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_session(test_engine):
    """Create test database session with default store (id=1)."""
    async_session = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        # Create default store for multi-store tests
        default_store = Store(id=1, name="Test Store", code="TEST001", is_active=True, is_default=True)
        session.add(default_store)
        await session.commit()
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(test_session):
    """Create test client with overridden database."""
    from httpx import AsyncClient, ASGITransport
    
    async def override_get_db():
        yield test_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()