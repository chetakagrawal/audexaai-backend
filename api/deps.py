"""FastAPI dependencies for authentication and database."""

from uuid import UUID

from fastapi import Depends, HTTPException, status
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
        User: The authenticated user with active_tenant_id and active_role attached

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

        # Attach active tenant and role to user object
        user.active_tenant_id = tenant_id
        user.active_role = role
    else:
        # Platform admin - no tenant required
        user.active_tenant_id = None
        user.active_role = None

    return user
