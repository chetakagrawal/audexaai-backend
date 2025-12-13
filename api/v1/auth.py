"""Authentication endpoints (DEV-ONLY)."""

from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import config
from api.deps import get_db
from auth.jwt import create_dev_token
from models.auth_identity import AuthIdentity
from models.tenant import Tenant
from models.user import User
from models.user_tenant import UserTenant

router = APIRouter()


class DevLoginRequest(BaseModel):
    """Request schema for dev login."""

    email: EmailStr
    tenant_slug: str
    name: str | None = None
    role: str = "admin"


class DevLoginResponse(BaseModel):
    """Response schema for dev login."""

    access_token: str
    token_type: str = "bearer"
    user_id: str
    tenant_id: str | None
    role: str
    is_platform_admin: bool


@router.post("/auth/dev-login", response_model=DevLoginResponse)
async def dev_login(
    request: DevLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    DEV-ONLY endpoint to create/find tenant and user, then return JWT token.

    This endpoint:
    - Finds or creates a tenant by slug
    - Finds or creates a user by email
    - Creates/finds AuthIdentity with provider="dev"
    - Creates/finds UserTenant relationship
    - Returns a signed JWT with user_id, tenant_id, role, is_platform_admin

    Args:
        request: Login request with email, tenant_slug, optional name and role
        db: Database session

    Returns:
        DevLoginResponse: JWT token and user information
    """
    # Check if dev environment
    if config.settings.APP_ENV == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dev login is not available in production",
        )

    # Find or create tenant
    result = await db.execute(
        select(Tenant).where(Tenant.slug == request.tenant_slug)
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        # Create new tenant
        tenant = Tenant(
            id=uuid4(),
            name=request.tenant_slug.replace("-", " ").title(),
            slug=request.tenant_slug,
            status="active",
        )
        db.add(tenant)
        await db.flush()  # Flush to get tenant.id

    # Find or create user by primary_email
    result = await db.execute(
        select(User).where(User.primary_email == request.email)
    )
    user = result.scalar_one_or_none()

    if not user:
        # Create new user
        user_name = request.name or request.email.split("@")[0].replace(".", " ").title()
        user = User(
            id=uuid4(),
            primary_email=request.email,
            name=user_name,
            is_platform_admin=False,  # Dev login doesn't create platform admins
            is_active=True,
        )
        db.add(user)
        await db.flush()  # Flush to get user.id

    # Find or create auth identity
    result = await db.execute(
        select(AuthIdentity).where(
            AuthIdentity.provider == "dev",
            AuthIdentity.provider_subject == request.email,
        )
    )
    auth_identity = result.scalar_one_or_none()

    if not auth_identity:
        # Create new auth identity
        auth_identity = AuthIdentity(
            id=uuid4(),
            user_id=user.id,
            provider="dev",
            provider_subject=request.email,
            email=request.email,
            email_verified=True,  # Dev login assumes verified
        )
        db.add(auth_identity)

    # Update last login
    auth_identity.last_login_at = datetime.utcnow()

    # Find or create user-tenant relationship
    result = await db.execute(
        select(UserTenant).where(
            UserTenant.user_id == user.id,
            UserTenant.tenant_id == tenant.id,
        )
    )
    user_tenant = result.scalar_one_or_none()

    if not user_tenant:
        # Create new user-tenant relationship
        # Check if this is the user's first tenant (make it default)
        result = await db.execute(
            select(UserTenant).where(UserTenant.user_id == user.id)
        )
        existing_tenants = result.scalars().all()
        is_default = len(existing_tenants) == 0

        user_tenant = UserTenant(
            id=uuid4(),
            user_id=user.id,
            tenant_id=tenant.id,
            role=request.role,
            is_default=is_default,
        )
        db.add(user_tenant)
    else:
        # Update role if provided
        if request.role:
            user_tenant.role = request.role

    await db.commit()

    # Create JWT token
    access_token = create_dev_token(
        user_id=user.id,
        tenant_id=tenant.id,
        role=user_tenant.role,
        is_platform_admin=user.is_platform_admin,
    )

    return DevLoginResponse(
        access_token=access_token,
        user_id=str(user.id),
        tenant_id=str(tenant.id),
        role=user_tenant.role,
        is_platform_admin=user.is_platform_admin,
    )
