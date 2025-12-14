"""FastAPI dependencies for authentication and database."""

from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import config
from auth.jwt import decode_token
from db import get_db as get_db_session
from models.user import User
from models.user_tenant import UserTenant

# HTTP Bearer token security scheme
security = HTTPBearer()


async def get_db() -> AsyncSession:
    """
    Dependency to get database session.
    Reuses the get_db function from db.py.
    """
    async for session in get_db_session():
        yield session


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency to get the current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer token from Authorization header
        db: Database session

    Returns:
        User: The authenticated user with active_tenant_id, active_role, and active_membership_id attached

    Raises:
        HTTPException: If token is invalid, expired, or user not found
    """
    token = credentials.credentials

    try:
        # Decode JWT token
        token_payload = decode_token(token)
        user_id = UUID(token_payload.sub)
        tenant_id = UUID(token_payload.tenant_id) if token_payload.tenant_id else None
        role = token_payload.role
        is_platform_admin = token_payload.is_platform_admin

    except (JWTError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
        )

    # Load user from database
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )

    # Verify platform admin flag matches
    if user.is_platform_admin != is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token claims do not match user",
        )

    # If not platform admin, verify tenant membership
    if not is_platform_admin:
        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Non-platform admin must have tenant_id in token",
            )

        # Verify user is member of the tenant with the specified role
        result = await db.execute(
            select(UserTenant).where(
                UserTenant.user_id == user_id,
                UserTenant.tenant_id == tenant_id,
            )
        )
        user_tenant = result.scalar_one_or_none()

        if not user_tenant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not a member of the specified tenant",
            )

        # Verify role matches
        if user_tenant.role != role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Token role does not match user tenant role",
            )

        # Attach active tenant, role, and membership_id to user object
        user.active_tenant_id = tenant_id
        user.active_role = role
        user.active_membership_id = user_tenant.id  # Store membership ID
    else:
        # Platform admin - no tenant required
        user.active_tenant_id = None
        user.active_role = None
        user.active_membership_id = None

    return user


async def get_tenancy_context(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    x_membership_id: str | None = Header(None, alias="X-Membership-Id"),
):
    """
    Dependency to get tenancy context for tenant-scoped operations.
    
    Reads X-Membership-Id header to determine active membership.

    UI flow for tenant-scoped operations:
    1. User logs in → receives JWT token and next_url
    2. Call GET /api/v1/me/memberships → get all memberships and default_membership_id
    3. Pick default_membership_id (or let user choose) and send it as X-Membership-Id header
       on all tenant-scoped API calls
    4. Navigate to next_url from login response

    Args:
        current_user: Current authenticated user
        db: Database session
        x_membership_id: X-Membership-Id header value (UserTenant.id)

    Returns:
        TenancyContext: Tenant context with membership_id, tenant_id, and role

    Raises:
        HTTPException: 403 if header is missing or membership is invalid
    """
    # Lazy import to avoid circular dependency
    from api.tenancy import require_membership, TenancyContext
    
    # Require X-Membership-Id header for tenant-scoped endpoints
    if not x_membership_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="X-Membership-Id header is required for tenant-scoped operations",
        )
    
    try:
        membership_id = UUID(x_membership_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid X-Membership-Id format (must be UUID)",
        )

    # Verify membership belongs to the authenticated user
    membership = await require_membership(membership_id, current_user.id, db)

    return TenancyContext(
        membership_id=membership.id,
        tenant_id=membership.tenant_id,
        role=membership.role,
    )
