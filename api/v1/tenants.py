"""Tenant endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db, get_tenancy_context
from api.tenancy import TenancyContext
from models.tenant import Tenant, TenantResponse
from models.user import User

router = APIRouter()


@router.get("/tenants", response_model=List[TenantResponse])
async def list_tenants(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    tenancy: TenancyContext | None = Depends(get_tenancy_context),
):
    """
    List tenants accessible to the current user.
    
    For regular users: Returns only their tenant (requires X-Membership-Id header).
    For platform admins: Returns all tenants (X-Membership-Id optional).
    
    Returns:
        List of accessible tenants.
    """
    try:
        # Platform admins can see all tenants
        if current_user.is_platform_admin:
            result = await db.execute(select(Tenant))
        else:
            # Regular users require membership - use tenancy context
            if not tenancy:
                raise HTTPException(
                    status_code=403,
                    detail="X-Membership-Id header is required for tenant-scoped operations",
                )
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

