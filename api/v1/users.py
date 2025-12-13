"""User endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db
from models.user import User, UserResponse
from models.user_tenant import UserTenant

router = APIRouter()


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List users in the current user's tenant.
    
    Returns:
        List of users in the tenant.
    """
    try:
        # Platform admins can see all users
        if current_user.is_platform_admin:
            result = await db.execute(select(User))
            users = result.scalars().all()
            return users
        
        # Regular users require membership - get tenancy context
        from api.deps import get_tenancy_context
        from api.tenancy import TenancyContext
        
        # Get tenancy context (will raise 403 if no membership)
        tenancy: TenancyContext = await get_tenancy_context(current_user, db)
        
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

