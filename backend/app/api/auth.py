"""Auth routes — register, login, refresh, API keys, user management."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime, timezone, timedelta

from app.auth import (
    authenticate_user,
    create_user,
    get_current_user,
    get_user_by_email,
    get_user_by_id,
    create_access_token,
    create_refresh_token,
    store_refresh_token,
    validate_refresh_token,
    revoke_refresh_token,
    revoke_all_user_tokens,
    create_api_key,
    get_user_api_keys,
    revoke_api_key,
    require_admin,
    require_manager,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
)
from app.api.validation import DEFAULT_PAGE, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.config import settings
from app.database import get_db
from app.models import User
from sqlalchemy import select


router = APIRouter(prefix="/auth", tags=["Auth"])


# ─── Schemas ───
class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=100)
    full_name: Optional[str] = None
    role: str = Field(default="staff", pattern="^(admin|manager|staff)$")


class LoginRequest(BaseModel):
    username: str  # Can be email or username
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)


class APIKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    scopes: str = Field(default="read write", pattern="^(read|write|admin)( (read|write|admin))*$")
    expires_days: Optional[int] = Field(None, ge=1, le=3650)


class APIKeyResponse(BaseModel):
    id: int
    name: str
    key_prefix: str
    scopes: str
    is_active: bool
    expires_at: Optional[str]
    last_used_at: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


class APIKeyCreateResponse(BaseModel):
    """Response when creating API key - includes raw key (only shown once)."""
    api_key: str
    name: str
    key_prefix: str
    scopes: str
    expires_at: Optional[str]


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    full_name: Optional[str]
    role: str
    is_active: bool
    is_superuser: bool
    last_login: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = Field(None, pattern="^(admin|manager|staff)$")
    is_active: Optional[bool] = None


# ─── Auth Endpoints ───

@router.post("/register", response_model=UserResponse, status_code=201)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register new user (admin only in production)."""
    # In dev mode, allow registration
    if settings.AUTH_ENABLED:
        # Check if requesting user is admin
        # For now, only allow if no users exist (first admin)
        result = await db.execute(select(User).limit(1))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Registration requires admin privileges")
    
    user = await create_user(
        db=db,
        email=data.email,
        password=data.password,
        username=data.username,
        full_name=data.full_name,
        role=data.role,
    )
    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        last_login=user.last_login.isoformat() if user.last_login else None,
        created_at=user.created_at.isoformat(),
    )


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Login with username/email + password — returns access + refresh tokens."""
    user = await authenticate_user(db, data.username, data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login
    user.last_login = datetime.now(timezone.utc)
    await db.commit()
    
    # Create tokens
    token_data = {"sub": str(user.id), "email": user.email, "role": user.role}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    # Store refresh token
    await store_refresh_token(db, user.id, refresh_token, request)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Refresh access token using refresh token (rotation)."""
    rt = await validate_refresh_token(db, data.refresh_token)
    if not rt:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    
    user = await get_user_by_id(db, rt.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    
    # Revoke old refresh token
    await revoke_refresh_token(db, data.refresh_token)
    
    # Create new tokens
    token_data = {"sub": str(user.id), "email": user.email, "role": user.role}
    access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data)
    
    # Store new refresh token
    await store_refresh_token(db, user.id, new_refresh_token, request)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout")
async def logout(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Logout — revoke refresh token."""
    await revoke_refresh_token(db, data.refresh_token)
    return {"message": "Logged out successfully"}


@router.post("/logout-all")
async def logout_all(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Logout from all devices — revoke all refresh tokens."""
    count = await revoke_all_user_tokens(db, current_user.id)
    return {"message": f"Revoked {count} refresh tokens"}


@router.post("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change password."""
    from app.auth import verify_password, hash_password
    
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    current_user.hashed_password = hash_password(data.new_password)
    await db.commit()
    
    # Revoke all sessions for security
    await revoke_all_user_tokens(db, current_user.id)
    
    return {"message": "Password changed. Please login again."}


# ─── API Key Management ───

@router.post("/api-keys", response_model=APIKeyCreateResponse, status_code=201)
async def create_api_key_endpoint(
    data: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create new API key for current user."""
    raw_key, api_key = await create_api_key(
        db=db,
        user_id=current_user.id,
        name=data.name,
        scopes=data.scopes,
        expires_days=data.expires_days,
    )
    return APIKeyCreateResponse(
        api_key=raw_key,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        scopes=api_key.scopes,
        expires_at=api_key.expires_at.isoformat() if api_key.expires_at else None,
    )


@router.get("/api-keys", response_model=List[APIKeyResponse])
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all API keys for current user."""
    keys = await get_user_api_keys(db, current_user.id)
    return [
        APIKeyResponse(
            id=k.id,
            name=k.name,
            key_prefix=k.key_prefix,
            scopes=k.scopes,
            is_active=k.is_active,
            expires_at=k.expires_at.isoformat() if k.expires_at else None,
            last_used_at=k.last_used_at.isoformat() if k.last_used_at else None,
            created_at=k.created_at.isoformat(),
        )
        for k in keys
    ]


@router.delete("/api-keys/{key_id}")
async def revoke_api_key_endpoint(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke (deactivate) an API key."""
    success = await revoke_api_key(db, key_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"message": "API key revoked"}


# ─── User Management (Admin) ───

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user profile."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        last_login=current_user.last_login.isoformat() if current_user.last_login else None,
        created_at=current_user.created_at.isoformat(),
    )


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    page: int = Query(DEFAULT_PAGE, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all users (admin only)."""
    from sqlalchemy import select
    offset = (page - 1) * page_size
    result = await db.execute(
        select(User).offset(offset).limit(page_size).order_by(User.created_at.desc())
    )
    users = result.scalars().all()
    return [
        UserResponse(
            id=u.id,
            email=u.email,
            username=u.username,
            full_name=u.full_name,
            role=u.role,
            is_active=u.is_active,
            is_superuser=u.is_superuser,
            last_login=u.last_login.isoformat() if u.last_login else None,
            created_at=u.created_at.isoformat(),
        )
        for u in users
    ]


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get user by ID (admin only)."""
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        last_login=user.last_login.isoformat() if user.last_login else None,
        created_at=user.created_at.isoformat(),
    )


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    data: UserUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update user (admin only)."""
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent self-demotion
    if user.id == current_user.id and data.role and data.role != "admin":
        raise HTTPException(status_code=400, detail="Cannot change your own admin role")
    
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete user (admin only)."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await db.delete(user)
    await db.commit()
    return {"message": "User deleted"}


# ─── Health / Debug ───

@router.get("/health")
async def auth_health(current_user: User = Depends(get_current_user)):
    """Check auth status."""
    return {
        "authenticated": True,
        "user": current_user.email,
        "role": current_user.role,
    }