"""Tests for Auth (register/login/refresh) + WebSocket routes."""
import pytest
from httpx import AsyncClient


class TestAuthFlow:
    """POST /api/v1/auth/register + /login + /refresh"""

    @pytest.mark.asyncio
    async def test_register_and_login(self, client: AsyncClient):
        """Register แล้ว login สำเร็จ ได้ access + refresh token."""
        reg = await client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "username": "testuser",
            "password": "password123",
            "full_name": "Test User",
            "role": "admin",
        })
        assert reg.status_code == 201, reg.text
        assert reg.json()["username"] == "testuser"

        login = await client.post("/api/v1/auth/login", json={
            "username": "testuser",
            "password": "password123",
        })
        assert login.status_code == 200, login.text
        data = login.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient):
        """รหัสผ่านผิด → 401."""
        await client.post("/api/v1/auth/register", json={
            "email": "wrong@example.com", "username": "wronguser",
            "password": "password123", "role": "staff",
        })
        resp = await client.post("/api/v1/auth/login", json={
            "username": "wronguser", "password": "badpassword",
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_token(self, client: AsyncClient):
        """ใช้ refresh token แลก access token ใหม่ได้."""
        await client.post("/api/v1/auth/register", json={
            "email": "refresh@example.com", "username": "refreshuser",
            "password": "password123", "role": "staff",
        })
        login = await client.post("/api/v1/auth/login", json={
            "username": "refreshuser", "password": "password123",
        })
        refresh_token = login.json()["refresh_token"]

        resp = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token,
        })
        assert resp.status_code == 200, resp.text
        assert "access_token" in resp.json()

    @pytest.mark.asyncio
    async def test_token_decode(self, client: AsyncClient):
        """access token ถอดรหัสได้ มี claim sub/type."""
        from app.auth import decode_token
        await client.post("/api/v1/auth/register", json={
            "email": "decode@example.com", "username": "decodeuser",
            "password": "password123", "role": "staff",
        })
        login = await client.post("/api/v1/auth/login", json={
            "username": "decodeuser", "password": "password123",
        })
        payload = decode_token(login.json()["access_token"])
        assert payload is not None
        assert payload["type"] == "access"
        assert payload["email"] == "decode@example.com"

    @pytest.mark.asyncio
    async def test_bad_token_rejected(self):
        """token ปลอม/expired คืน None."""
        from app.auth import decode_token
        assert decode_token("not.a.token") is None

    @pytest.mark.asyncio
    async def test_me_dev_mode(self, client: AsyncClient):
        """AUTH_ENABLED=false → /auth/me ทำงาน without token (dev user)."""
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 200
        assert "username" in resp.json()

    @pytest.mark.asyncio
    async def test_api_works_without_token_in_dev(self, client: AsyncClient):
        """AUTH_ENABLED=false → เรียก API ได้โดยไม่ต้องมี token."""
        resp = await client.get("/api/v1/products")
        assert resp.status_code == 200


class TestWebSocketRoute:
    """WebSocket /api/v1/ws"""

    @pytest.mark.asyncio
    async def test_ws_route_registered(self):
        """route /api/v1/ws มีอยู่ใน app."""
        from app.main import app
        paths = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/api/v1/ws" in paths

    @pytest.mark.asyncio
    async def test_ws_manager_broadcast_no_connections(self):
        """manager.broadcast ไม่ error เมื่อไม่มี connection."""
        from app.websocket import manager
        await manager.broadcast({"type": "test"})

    @pytest.mark.asyncio
    async def test_notify_data_change(self):
        """notify_data_change ไม่ error."""
        from app.websocket import notify_data_change
        await notify_data_change("products", "create", {"id": 1})
