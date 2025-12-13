"""Tenant endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db
from models.tenant import Tenant, TenantResponse
from models.user import User

router = APIRouter()


@router.get("/tenants", response_model=List[TenantResponse])
async def list_tenants(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List tenants accessible to the current user.
    
    For regular users: Returns only their tenant (requires membership).
    For platform admins: Returns all tenants.
    
    Returns:
        List of accessible tenants.
    """
    try:
        # Platform admins can see all tenants
        if current_user.is_platform_admin:
            result = await db.execute(select(Tenant))
        else:
            # Regular users require membership - get tenancy context
            from api.deps import get_tenancy_context
            from api.tenancy import TenancyContext
            
            # Get tenancy context (will raise 403 if no membership)
            tenancy: TenancyContext = await get_tenancy_context(current_user, db)
            # Regular users can only see their tenant
            query = select(Tenant).where(Tenant.id == tenancy.tenant_id)
            result = await db.execute(query)
        
        tenants = result.scalars().all()
        return tenants
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch tenants: {str(e)}",
        )

