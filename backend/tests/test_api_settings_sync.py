"""Tests for Settings and Sync APIs."""
import pytest
from httpx import AsyncClient


class TestSettingsAPI:
    """Test Settings API endpoints."""

    @pytest.mark.asyncio
    async def test_create_setting(self, client: AsyncClient):
        """Test POST /api/v1/settings."""
        setting_data = {
            "key": "test_setting",
            "value": "test_value",
            "description": "Test setting",
        }

        response = await client.post("/api/v1/settings", json=setting_data)

        assert response.status_code == 201
        data = response.json()
        assert data["key"] == "test_setting"
        assert data["value"] == "test_value"
        assert data["description"] == "Test setting"

    @pytest.mark.asyncio
    async def test_get_setting(self, client: AsyncClient):
        """Test GET /api/v1/settings/{key}."""
        await client.post("/api/v1/settings", json={
            "key": "get_setting",
            "value": "get_value",
        })

        response = await client.get("/api/v1/settings/get_setting")

        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "get_setting"
        assert data["value"] == "get_value"

    @pytest.mark.asyncio
    async def test_update_setting(self, client: AsyncClient):
        """Test PUT /api/v1/settings/{key}."""
        await client.post("/api/v1/settings", json={
            "key": "update_setting",
            "value": "original",
        })

        response = await client.put("/api/v1/settings/update_setting", json={
            "value": "updated",
            "description": "Updated description",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["value"] == "updated"
        assert data["description"] == "Updated description"

    @pytest.mark.asyncio
    async def test_delete_setting(self, client: AsyncClient):
        """Test DELETE /api/v1/settings/{key}."""
        await client.post("/api/v1/settings", json={
            "key": "delete_setting",
            "value": "to_delete",
        })

        response = await client.delete("/api/v1/settings/delete_setting")

        assert response.status_code == 200

        # Verify deleted
        get_resp = await client.get("/api/v1/settings/delete_setting")
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_list_settings(self, client: AsyncClient):
        """Test GET /api/v1/settings."""
        await client.post("/api/v1/settings", json={"key": "list_a", "value": "a"})
        await client.post("/api/v1/settings", json={"key": "list_b", "value": "b"})

        response = await client.get("/api/v1/settings")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
        keys = [s["key"] for s in data]
        assert "list_a" in keys
        assert "list_b" in keys


class TestCategoryMappingsAPI:
    """Test Category Mappings API endpoints."""

    @pytest.mark.asyncio
    async def test_create_mapping(self, client: AsyncClient):
        """Test POST /api/v1/settings/mappings."""
        mapping_data = {
            "code_prefix": "99",
            "category": "API Category",
        }

        response = await client.post("/api/v1/settings/mappings", json=mapping_data)

        assert response.status_code == 201
        data = response.json()
        assert data["code_prefix"] == "99"
        assert data["category"] == "API Category"

    @pytest.mark.asyncio
    async def test_get_mapping(self, client: AsyncClient):
        """Test GET /api/v1/settings/mappings/{code_prefix}."""
        await client.post("/api/v1/settings/mappings", json={
            "code_prefix": "88",
            "category": "Get Category",
        })

        response = await client.get("/api/v1/settings/mappings/88")

        assert response.status_code == 200
        data = response.json()
        assert data["code_prefix"] == "88"
        assert data["category"] == "Get Category"

    @pytest.mark.asyncio
    async def test_update_mapping(self, client: AsyncClient):
        """Test PUT /api/v1/settings/mappings/{code_prefix}."""
        await client.post("/api/v1/settings/mappings", json={
            "code_prefix": "77",
            "category": "Original",
        })

        response = await client.put("/api/v1/settings/mappings/77", json={
            "category": "Updated",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "Updated"

    @pytest.mark.asyncio
    async def test_delete_mapping(self, client: AsyncClient):
        """Test DELETE /api/v1/settings/mappings/{code_prefix}."""
        await client.post("/api/v1/settings/mappings", json={
            "code_prefix": "66",
            "category": "To Delete",
        })

        response = await client.delete("/api/v1/settings/mappings/66")

        assert response.status_code == 200

        get_resp = await client.get("/api/v1/settings/mappings/66")
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_list_mappings(self, client: AsyncClient):
        """Test GET /api/v1/settings/mappings."""
        await client.post("/api/v1/settings/mappings", json={"code_prefix": "55", "category": "Cat 55"})
        await client.post("/api/v1/settings/mappings", json={"code_prefix": "44", "category": "Cat 44"})

        response = await client.get("/api/v1/settings/mappings")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2

    @pytest.mark.asyncio
    async def test_bulk_create_mappings(self, client: AsyncClient):
        """Test POST /api/v1/settings/mappings/bulk."""
        mappings_data = [
            {"code_prefix": "33", "category": "Bulk 33"},
            {"code_prefix": "22", "category": "Bulk 22"},
        ]

        response = await client.post("/api/v1/settings/mappings/bulk", json=mappings_data)

        assert response.status_code == 201
        data = response.json()
        assert len(data) == 2


class TestSyncAPI:
    """Test Sync API endpoints."""

    @pytest.mark.asyncio
    async def test_sync(self, client: AsyncClient):
        """Test POST /api/v1/sync."""
        # Create product first
        await client.post("/api/v1/products", json={
            "code": "SYNCAPI001",
            "name": "Sync Product",
            "price": "100.00",
        })

        sync_data = {
            "products": [
                {"code": "SYNCAPI002", "name": "Synced Product", "price": "150.00"},
            ],
            "settings": [
                {"key": "synced_key", "value": "synced_value"},
            ],
        }

        response = await client.post("/api/v1/sync", json=sync_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["counts"]["products"] == 1
        assert data["counts"]["settings"] == 1

    @pytest.mark.asyncio
    async def test_backup(self, client: AsyncClient):
        """Test GET /api/v1/sync/backup."""
        await client.post("/api/v1/products", json={
            "code": "BACKUPAPI001",
            "name": "Backup Product",
            "price": "100.00",
        })

        response = await client.get("/api/v1/sync/backup")

        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data
        assert "version" in data
        assert "data" in data
        assert "products" in data["data"]
        assert len(data["data"]["products"]) >= 1

    @pytest.mark.asyncio
    async def test_restore(self, client: AsyncClient):
        """Test POST /api/v1/sync/restore."""
        # First create backup
        await client.post("/api/v1/products", json={
            "code": "RESTOREAPI001",
            "name": "Original Product",
            "price": "100.00",
        })

        backup_resp = await client.get("/api/v1/sync/backup")
        backup_data = backup_resp.json()["data"]

        # Delete product
        prod_resp = await client.get("/api/v1/products/code/RESTOREAPI001")
        prod_id = prod_resp.json()["id"]
        await client.delete(f"/api/v1/products/{prod_id}")

        # Restore
        response = await client.post("/api/v1/sync/restore", json=backup_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["counts"]["products"] >= 1

        # Verify restored
        restored = await client.get("/api/v1/products/code/RESTOREAPI001")
        assert restored.status_code == 200

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test GET /api/v1/sync/health."""
        response = await client.get("/api/v1/sync/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"