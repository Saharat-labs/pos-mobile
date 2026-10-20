"""Tests for SettingService and CategoryMappingService."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.setting_service import SettingService, CategoryMappingService
from app.schemas import SettingCreate, SettingUpdate, CategoryMappingCreate, CategoryMappingUpdate


class TestSettingService:
    """Test SettingService methods."""

    @pytest.mark.asyncio
    async def test_get_setting(self, test_session: AsyncSession):
        """Test getting a setting by key."""
        service = SettingService(test_session)

        # Set a setting first
        await service.set("test_key", "test_value", "Test description")

        setting = await service.get("test_key")

        assert setting is not None
        assert setting.key == "test_key"
        assert setting.value == "test_value"
        assert setting.description == "Test description"

    @pytest.mark.asyncio
    async def test_get_nonexistent_setting(self, test_session: AsyncSession):
        """Test getting a non-existent setting returns None."""
        service = SettingService(test_session)

        setting = await service.get("nonexistent")

        assert setting is None

    @pytest.mark.asyncio
    async def test_get_value_with_default(self, test_session: AsyncSession):
        """Test getting setting value with default."""
        service = SettingService(test_session)

        # Not set yet
        value = await service.get_value("missing_key", "default_value")
        assert value == "default_value"

        # Set it
        await service.set("existing_key", "existing_value")
        value = await service.get_value("existing_key", "default_value")
        assert value == "existing_value"

    @pytest.mark.asyncio
    async def test_set_setting(self, test_session: AsyncSession):
        """Test setting a value (upsert)."""
        service = SettingService(test_session)

        # Create new
        setting = await service.set("new_key", "new_value", "New description")
        assert setting.key == "new_key"
        assert setting.value == "new_value"
        assert setting.description == "New description"

        # Update existing
        setting = await service.set("new_key", "updated_value", "Updated description")
        assert setting.value == "updated_value"
        assert setting.description == "Updated description"

    @pytest.mark.asyncio
    async def test_list_settings(self, test_session: AsyncSession):
        """Test listing all settings."""
        service = SettingService(test_session)

        await service.set("key_a", "value_a")
        await service.set("key_b", "value_b")
        await service.set("key_c", "value_c")

        settings = await service.list()

        assert len(settings) == 3
        keys = [s.key for s in settings]
        assert "key_a" in keys
        assert "key_b" in keys
        assert "key_c" in keys

    @pytest.mark.asyncio
    async def test_delete_setting(self, test_session: AsyncSession):
        """Test deleting a setting."""
        service = SettingService(test_session)

        await service.set("delete_me", "value")
        result = await service.delete("delete_me")

        assert result is True

        # Verify deleted
        setting = await service.get("delete_me")
        assert setting is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_setting(self, test_session: AsyncSession):
        """Test deleting non-existent setting returns False."""
        service = SettingService(test_session)

        result = await service.delete("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_bulk_set_settings(self, test_session: AsyncSession):
        """Test bulk setting multiple settings."""
        service = SettingService(test_session)

        settings_data = [
            SettingCreate(key="bulk_1", value="value_1", description="Bulk 1"),
            SettingCreate(key="bulk_2", value="value_2", description="Bulk 2"),
        ]

        result = await service.bulk_set(settings_data)

        assert len(result) == 2
        assert result[0].key == "bulk_1"
        assert result[1].key == "bulk_2"


class TestCategoryMappingService:
    """Test CategoryMappingService methods."""

    @pytest.mark.asyncio
    async def test_create_mapping(self, test_session: AsyncSession):
        """Test creating a category mapping."""
        service = CategoryMappingService(test_session)

        mapping_data = CategoryMappingCreate(
            code_prefix="01",
            category="เครื่องดื่ม",
        )

        mapping = await service.create(mapping_data)

        assert mapping.id is not None
        assert mapping.code_prefix == "01"
        assert mapping.category == "เครื่องดื่ม"

    @pytest.mark.asyncio
    async def test_get_mapping(self, test_session: AsyncSession):
        """Test getting a mapping by code prefix."""
        service = CategoryMappingService(test_session)

        await service.create(CategoryMappingCreate(
            code_prefix="02",
            category="อาหารแห้ง",
        ))

        mapping = await service.get("02")

        assert mapping is not None
        assert mapping.code_prefix == "02"
        assert mapping.category == "อาหารแห้ง"

    @pytest.mark.asyncio
    async def test_get_category_prefix_match(self, test_session: AsyncSession):
        """Test getting category by product code (prefix matching)."""
        service = CategoryMappingService(test_session)

        await service.create(CategoryMappingCreate(
            code_prefix="01", category="เครื่องดื่ม"
        ))
        await service.create(CategoryMappingCreate(
            code_prefix="012", category="น้ำอัดลม"
        ))
        await service.create(CategoryMappingCreate(
            code_prefix="0123", category="โค้ก"
        ))

        # Longest prefix match
        assert await service.get_category("0123456") == "โค้ก"
        assert await service.get_category("0129999") == "น้ำอัดลม"
        assert await service.get_category("0199999") == "เครื่องดื่ม"
        assert await service.get_category("9999999") is None

    @pytest.mark.asyncio
    async def test_update_mapping(self, test_session: AsyncSession):
        """Test updating a category mapping."""
        service = CategoryMappingService(test_session)

        await service.create(CategoryMappingCreate(
            code_prefix="03",
            category="Original Category",
        ))

        update_data = CategoryMappingUpdate(category="Updated Category")
        updated = await service.update("03", update_data)

        assert updated is not None
        assert updated.category == "Updated Category"

    @pytest.mark.asyncio
    async def test_delete_mapping(self, test_session: AsyncSession):
        """Test deleting a category mapping."""
        service = CategoryMappingService(test_session)

        await service.create(CategoryMappingCreate(
            code_prefix="04",
            category="To Delete",
        ))

        result = await service.delete("04")

        assert result is True

        mapping = await service.get("04")
        assert mapping is None

    @pytest.mark.asyncio
    async def test_list_mappings(self, test_session: AsyncSession):
        """Test listing all category mappings."""
        service = CategoryMappingService(test_session)

        await service.create(CategoryMappingCreate(code_prefix="10", category="Cat 10"))
        await service.create(CategoryMappingCreate(code_prefix="20", category="Cat 20"))
        await service.create(CategoryMappingCreate(code_prefix="30", category="Cat 30"))

        mappings = await service.list()

        assert len(mappings) == 3
        prefixes = [m.code_prefix for m in mappings]
        assert "10" in prefixes
        assert "20" in prefixes
        assert "30" in prefixes

    @pytest.mark.asyncio
    async def test_bulk_create_mappings(self, test_session: AsyncSession):
        """Test bulk creating/updating mappings."""
        service = CategoryMappingService(test_session)

        mappings_data = [
            CategoryMappingCreate(code_prefix="50", category="Bulk 50"),
            CategoryMappingCreate(code_prefix="60", category="Bulk 60"),
        ]

        result = await service.bulk_create(mappings_data)

        assert len(result) == 2
        assert result[0].code_prefix == "50"
        assert result[1].code_prefix == "60"

        # Update existing via bulk
        mappings_data_update = [
            CategoryMappingCreate(code_prefix="50", category="Updated 50"),
        ]
        result = await service.bulk_create(mappings_data_update)

        assert len(result) == 1
        assert result[0].category == "Updated 50"