"""Setting service - business logic for app settings."""

from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Setting, CategoryMapping
from app.schemas import SettingCreate, SettingUpdate, CategoryMappingCreate, CategoryMappingUpdate


class SettingService:
    """Setting business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, key: str, store_id: int = 1) -> Optional[Setting]:
        """Get setting by key (scoped to store)."""
        result = await self.db.execute(
            select(Setting).where(Setting.key == key, Setting.store_id == store_id)
        )
        return result.scalar_one_or_none()

    async def get_value(self, key: str, default: str = "", store_id: int = 1) -> str:
        """Get setting value or default."""
        setting = await self.get(key, store_id)
        return setting.value if setting else default

    async def set(self, key: str, value: str, description: str = None, store_id: int = 1) -> Setting:
        """Set setting value (upsert, scoped to store)."""
        setting = await self.get(key, store_id)
        if setting:
            setting.value = value
            if description:
                setting.description = description
        else:
            setting = Setting(key=key, value=value, description=description, store_id=store_id)
            self.db.add(setting)
        await self.db.commit()
        await self.db.refresh(setting)
        return setting

    async def list(self, store_id: int = 1) -> List[Setting]:
        """List all settings (scoped to store)."""
        result = await self.db.execute(
            select(Setting).where(Setting.store_id == store_id).order_by(Setting.key)
        )
        return result.scalars().all()

    async def delete(self, key: str, store_id: int = 1) -> bool:
        """Delete setting (scoped to store)."""
        setting = await self.get(key, store_id)
        if not setting:
            return False
        await self.db.delete(setting)
        await self.db.commit()
        return True

    async def bulk_set(self, settings: List[SettingCreate], store_id: int = 1) -> List[Setting]:
        """Bulk set settings."""
        result = []
        for s in settings:
            setting = await self.set(s.key, s.value, s.description, store_id)
            result.append(setting)
        return result


class CategoryMappingService:
    """Category mapping business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, code_prefix: str) -> Optional[CategoryMapping]:
        """Get category mapping by code prefix."""
        result = await self.db.execute(
            select(CategoryMapping).where(CategoryMapping.code_prefix == code_prefix)
        )
        return result.scalar_one_or_none()

    async def get_category(self, code: str) -> Optional[str]:
        """Get category for product code (longest prefix match)."""
        # Try exact match first
        mapping = await self.get(code[:3]) if len(code) >= 3 else None
        if mapping:
            return mapping.category

        # Try shorter prefixes
        for length in [2, 1]:
            if len(code) >= length:
                mapping = await self.get(code[:length])
                if mapping:
                    return mapping.category
        return None

    async def create(self, data: CategoryMappingCreate) -> CategoryMapping:
        """Create new category mapping."""
        mapping = CategoryMapping(code_prefix=data.code_prefix, category=data.category)
        self.db.add(mapping)
        await self.db.commit()
        await self.db.refresh(mapping)
        return mapping

    async def update(self, code_prefix: str, data: CategoryMappingUpdate) -> Optional[CategoryMapping]:
        """Update category mapping."""
        mapping = await self.get(code_prefix)
        if not mapping:
            return None
        if data.category:
            mapping.category = data.category
        await self.db.commit()
        await self.db.refresh(mapping)
        return mapping

    async def delete(self, code_prefix: str) -> bool:
        """Delete category mapping."""
        mapping = await self.get(code_prefix)
        if not mapping:
            return False
        await self.db.delete(mapping)
        await self.db.commit()
        return True

    async def list(self) -> List[CategoryMapping]:
        """List all category mappings."""
        result = await self.db.execute(select(CategoryMapping).order_by(CategoryMapping.code_prefix))
        return result.scalars().all()

    async def bulk_create(self, mappings: List[CategoryMappingCreate]) -> List[CategoryMapping]:
        """Bulk create category mappings (upsert)."""
        result = []
        for m in mappings:
            existing = await self.get(m.code_prefix)
            if existing:
                existing.category = m.category
                result.append(existing)
            else:
                mapping = CategoryMapping(code_prefix=m.code_prefix, category=m.category)
                self.db.add(mapping)
                result.append(mapping)
        await self.db.commit()
        for m in result:
            await self.db.refresh(m)
        return result