"""User endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from api.deps import get_current_user, get_db, get_tenancy_context
from api.tenancy import TenancyContext
from models.user import User, UserResponse
from models.user_tenant import UserTenant

router = APIRouter()


class MembershipResponse(BaseModel):
    """Response schema for membership with user info."""
    
    id: str
    user_id: str
    tenant_id: str
    role: str
    is_default: bool
    user_name: str
    user_email: str
    created_at: str


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    tenancy: TenancyContext | None = Depends(get_tenancy_context),
):
    """
    List users in the current user's tenant.
    
    For regular users: Returns users in their tenant (requires X-Membership-Id header).
    For platform admins: Returns all users (X-Membership-Id optional).
    
    Returns:
        List of users in the tenant.
    """
    try:
        # Platform admins can see all users
        if current_user.is_platform_admin:
            result = await db.execute(select(User))
            users = result.scalars().all()
            return users
        
        # Regular users require membership - use tenancy context
        if not tenancy:
            raise HTTPException(
                status_code=403,
                detail="X-Membership-Id header is required for tenant-scoped operations",
            )
        
        # Get all user memberships for this tenant
        result = await db.execute(
            select(UserTenant).where(UserTenant.tenant_id == tenancy.tenant_id)
        )
        memberships = result.scalars().all()
        
        # Get user IDs
        user_ids = [m.user_id for m in memberships]
        
        if not user_ids:
            return []
        
        # Fetch users
        result = await db.execute(select(User).where(User.id.in_(user_ids)))
        users = result.scalars().all()
        
        return users
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch users: {str(e)}",
        )


@router.get("/memberships", response_model=List[MembershipResponse])
async def list_memberships(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    tenancy: TenancyContext | None = Depends(get_tenancy_context),
):
    """
    List all memberships (user_tenants) in the current tenant.
    
    Returns memberships with user information for dropdown selection.
    For regular users: Returns memberships in their tenant (requires X-Membership-Id header).
    For platform admins: Requires X-Membership-Id to specify which tenant.
    
    Returns:
        List of memberships in the tenant with user details.
    """
    try:
        # Require tenancy context (even for platform admins, we need to know which tenant)
        if not tenancy:
            raise HTTPException(
                status_code=403,
                detail="X-Membership-Id header is required to specify tenant",
            )
        
        # Get all memberships for this tenant
        result = await db.execute(
            select(UserTenant).where(UserTenant.tenant_id == tenancy.tenant_id)
        )
        memberships = result.scalars().all()
        
        if not memberships:
            return []
        
        # Get user IDs
        user_ids = [m.user_id for m in memberships]
        
        # Fetch users
        result = await db.execute(select(User).where(User.id.in_(user_ids)))
        users = result.scalars().all()
        
        # Create a user lookup map
        user_map = {user.id: user for user in users}
        
        # Build response with user info
        response = []
        for membership in memberships:
            user = user_map.get(membership.user_id)
            if user:
                response.append(MembershipResponse(
                    id=str(membership.id),
                    user_id=str(membership.user_id),
                    tenant_id=str(membership.tenant_id),
                    role=membership.role,
                    is_default=membership.is_default,
                    user_name=user.name,
                    user_email=user.primary_email,
                    created_at=membership.created_at.isoformat(),
                ))
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch memberships: {str(e)}",
        )

