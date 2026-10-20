"""Authentication - JWT + API Key based auth for POS-MOBILE API.

Features:
- User registration/login with email/password
- JWT access + refresh tokens (rotation)
- API Keys for service-to-service auth
- Role-based access control (admin, manager, staff)
- Password hashing with bcrypt

Config via .env:
- AUTH_ENABLED=true/false (default: false for dev)
- JWT_SECRET=secret-key (required for production)
- JWT_ALGORITHM=HS256
- ACCESS_TOKEN_EXPIRE_MINUTES=15
- REFRESH_TOKEN_EXPIRE_DAYS=7
"""

import os
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from functools import wraps

import jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.config import settings
from app.models import User, APIKey, RefreshToken, Store
from app.database import get_db


# ─── Password Hashing ───
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash password with bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ─── API Key Helpers ───
def generate_api_key() -> tuple[str, str, str]:
    """Generate new API key.
    
    Returns:
        (raw_key, key_hash, key_prefix)
        - raw_key: full key to give to user (only shown once)
        - key_hash: bcrypt hash for DB storage
        - key_prefix: first 8 chars for display
    """
    raw = f"pos_{secrets.token_urlsafe(32)}"
    key_hash = hash_password(raw)
    prefix = raw[:12]  # pos_xxxxxx...
    return raw, key_hash, prefix


def verify_api_key(raw_key: str, key_hash: str) -> bool:
    """Verify API key against hash."""
    return verify_password(raw_key, key_hash)


# ─── JWT Configuration ───
JWT_SECRET = os.environ.get("JWT_SECRET")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.environ.get("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

if not JWT_SECRET:
    if settings.AUTH_ENABLED:
        raise ValueError("JWT_SECRET must be set when AUTH_ENABLED=true")
    # Dev fallback
    JWT_SECRET = "dev-secret-change-in-production"


security = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


# ─── Token Creation ───
def create_access_token(data: dict, expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    """Create JWT access token."""
    payload = data.copy()
    now = datetime.now(timezone.utc)
    payload["exp"] = now + timedelta(minutes=expires_minutes)
    payload["iat"] = now
    payload["type"] = "access"
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(data: dict, expires_days: int = REFRESH_TOKEN_EXPIRE_DAYS) -> str:
    """Create JWT refresh token with unique jti for rotation."""
    import uuid
    payload = data.copy()
    now = datetime.now(timezone.utc)
    payload["exp"] = now + timedelta(days=expires_days)
    payload["iat"] = now
    payload["type"] = "refresh"
    payload["jti"] = str(uuid.uuid4())  # Unique token ID for rotation
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate JWT token."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# ─── Token Storage (DB) ───
async def store_refresh_token(
    db: AsyncSession,
    user_id: int,
    token: str,
    request: Request = None,
) -> RefreshToken:
    """Store refresh token hash in DB."""
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    rt = RefreshToken(
        token_hash=token_hash,
        user_id=user_id,
        expires_at=expires_at,
        user_agent=request.headers.get("user-agent") if request else None,
        ip_address=request.client.host if request else None,
    )
    db.add(rt)
    await db.commit()
    await db.refresh(rt)
    return rt


async def revoke_refresh_token(db: AsyncSession, token: str) -> bool:
    """Revoke a refresh token."""
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    rt = result.scalar_one_or_none()
    if rt:
        rt.revoked_at = datetime.now(timezone.utc)
        await db.commit()
        return True
    return False


async def revoke_all_user_tokens(db: AsyncSession, user_id: int) -> int:
    """Revoke all refresh tokens for a user."""
    result = await db.execute(
        select(RefreshToken).where(
            and_(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        )
    )
    tokens = result.scalars().all()
    count = 0
    for rt in tokens:
        rt.revoked_at = datetime.now(timezone.utc)
        count += 1
    if count > 0:
        await db.commit()
    return count


async def validate_refresh_token(db: AsyncSession, token: str) -> Optional[RefreshToken]:
    """Validate refresh token exists and not revoked/expired."""
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    rt = result.scalar_one_or_none()
    if not rt:
        return None
    if rt.revoked_at is not None:
        return None
    # Handle both naive and aware datetimes
    now = datetime.now(timezone.utc)
    expires_at = rt.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < now:
        return None
    return rt


# ─── User Authentication ───
async def authenticate_user(
    db: AsyncSession,
    username: str,
    password: str,
) -> Optional[User]:
    """Authenticate user with username or email/password."""
    # Try email first, then username
    result = await db.execute(
        select(User).where(
            (User.email == username) | (User.username == username)
        )
    )
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """Get user by ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Get user by email."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    email: str,
    password: str,
    username: str,
    full_name: str = None,
    role: str = "staff",
    is_superuser: bool = False,
    store_id: int = 1,
) -> User:
    """Create new user."""
    # Check if email exists
    existing = await get_user_by_email(db, email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Check if username exists
    result = await db.execute(select(User).where(User.username == username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already taken")
    
    user = User(
        email=email,
        username=username,
        hashed_password=hash_password(password),
        full_name=full_name,
        role=role,
        is_superuser=is_superuser,
        is_active=True,
        store_id=store_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# ─── API Key Management ───
async def create_api_key(
    db: AsyncSession,
    user_id: int,
    name: str,
    scopes: str = "read write",
    expires_days: int = None,
) -> tuple[str, APIKey]:
    """Create new API key for user. Returns (raw_key, api_key_obj)."""
    raw_key, key_hash, prefix = generate_api_key()
    expires_at = None
    if expires_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=expires_days)
    
    api_key = APIKey(
        name=name,
        key_hash=key_hash,
        key_prefix=prefix,
        user_id=user_id,
        scopes=scopes,
        is_active=True,
        expires_at=expires_at,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    return raw_key, api_key


async def validate_api_key(db: AsyncSession, raw_key: str) -> Optional[APIKey]:
    """Validate API key and return APIKey object if valid."""
    result = await db.execute(select(APIKey).where(APIKey.is_active == True))
    api_keys = result.scalars().all()
    
    for ak in api_keys:
        if verify_api_key(raw_key, ak.key_hash):
            # Check expiration
            if ak.expires_at and ak.expires_at < datetime.now(timezone.utc):
                continue
            # Update last used
            ak.last_used_at = datetime.now(timezone.utc)
            await db.commit()
            return ak
    return None


async def get_user_api_keys(db: AsyncSession, user_id: int) -> List[APIKey]:
    """Get all API keys for a user."""
    result = await db.execute(
        select(APIKey).where(APIKey.user_id == user_id).order_by(APIKey.created_at.desc())
    )
    return result.scalars().all()


async def revoke_api_key(db: AsyncSession, key_id: int, user_id: int) -> bool:
    """Revoke (deactivate) an API key."""
    result = await db.execute(
        select(APIKey).where(and_(APIKey.id == key_id, APIKey.user_id == user_id))
    )
    ak = result.scalar_one_or_none()
    if ak:
        ak.is_active = False
        await db.commit()
        return True
    return False


# ─── Dependency Injection ───
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    api_key: Optional[str] = Depends(api_key_header),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get current authenticated user from JWT or API Key."""
    
    # Dev mode bypass
    if not settings.AUTH_ENABLED:
        # Return a dev user or first user
        result = await db.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        if not user:
            # Create dev user
            user = await create_user(db, "dev@local", "devpass", "dev", "Dev User", "admin", True)
        return user
    
    user = None
    
    # Try JWT Bearer token first
    if credentials:
        payload = decode_token(credentials.credentials)
        if payload and payload.get("type") == "access":
            user_id = payload.get("sub")
            if user_id:
                user = await get_user_by_id(db, int(user_id))
    
    # Try API Key
    if not user and api_key:
        api_key_obj = await validate_api_key(db, api_key)
        if api_key_obj:
            user = await get_user_by_id(db, api_key_obj.user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    
    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Get current user from JWT token, or None if not authenticated."""
    # Dev mode bypass
    if not settings.AUTH_ENABLED:
        result = await db.execute(select(User).limit(1))
        return result.scalar_one_or_none()
    
    if not credentials:
        return None
    
    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        return None
    
    user_id = payload.get("sub")
    if not user_id:
        return None
    
    user = await get_user_by_id(db, int(user_id))
    if not user or not user.is_active:
        return None
    return user


async def get_current_store(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Store:
    """Get current user's store."""
    result = await db.execute(select(Store).where(Store.id == current_user.store_id))
    store = result.scalar_one_or_none()
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found for current user",
        )
    if not store.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Store is inactive",
        )
    return store


def require_roles(*allowed_roles: str):
    """Dependency to require specific roles."""
    async def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.is_superuser:
            return user
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {', '.join(allowed_roles)}",
            )
        return user
    return role_checker


# Convenience role dependencies
require_admin = require_roles("admin")
require_manager = require_roles("admin", "manager")
require_staff = require_roles("admin", "manager", "staff")


# ─── Scopes for API Keys ───
def require_scopes(*required_scopes: str):
    """Dependency to check API key scopes (only works with API key auth)."""
    async def scope_checker(
        api_key: str = Depends(api_key_header),
        db: AsyncSession = Depends(get_db),
    ) -> APIKey:
        if not settings.AUTH_ENABLED:
            # Return dummy API key for dev
            return APIKey(scopes="read write")
        
        ak = await validate_api_key(db, api_key)
        if not ak:
            raise HTTPException(status_code=401, detail="Invalid API key")
        
        key_scopes = ak.scopes.split()
        for scope in required_scopes:
            if scope not in key_scopes:
                raise HTTPException(
                    status_code=403,
                    detail=f"Required scope: {scope}",
                )
        return ak
    return scope_checker