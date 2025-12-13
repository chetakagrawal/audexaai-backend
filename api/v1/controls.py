"""Control endpoints with tenant isolation."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db, get_tenancy_context
from models.control import Control, ControlBase, ControlResponse
from models.user import User

router = APIRouter()


@router.get("/controls", response_model=List[ControlResponse])
async def list_controls(
    current_user: User = Depends(get_current_user),
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    List controls in the current user's tenant.
    
    Returns:
        List of controls in the tenant.
    """
    try:
        # Platform admins can see all controls
        if current_user.is_platform_admin:
            result = await db.execute(select(Control))
        else:
            # Regular users: filter by tenant_id
            result = await db.execute(
                select(Control).where(Control.tenant_id == tenancy.tenant_id)
            )
        
        controls = result.scalars().all()
        return controls
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch controls: {str(e)}",
        )


@router.get("/controls/{control_id}", response_model=ControlResponse)
async def get_control(
    control_id: UUID,
    current_user: User = Depends(get_current_user),
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific control by ID.
    
    Returns:
        Control if found and user has access.
    
    Raises:
        404 if control not found or user doesn't have access.
    """
    try:
        # Build query with tenant filtering
        query = select(Control).where(Control.id == control_id)
        
        if not current_user.is_platform_admin:
            # Regular users: must filter by tenant_id
            query = query.where(Control.tenant_id == tenancy.tenant_id)
        
        result = await db.execute(query)
        control = result.scalar_one_or_none()
        
        if not control:
            raise HTTPException(
                status_code=404,
                detail="Control not found",
            )
        
        return control
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch control: {str(e)}",
        )


@router.post("/controls", response_model=ControlResponse)
async def create_control(
    control_data: ControlBase,
    current_user: User = Depends(get_current_user),
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new control.
    
    Note: tenant_id is set from membership context (never from client input).
    """
    try:
        # Override tenant_id and created_by_membership_id from membership context (security: never trust client)
        control = Control(
            tenant_id=tenancy.tenant_id,
            created_by_membership_id=tenancy.membership_id,
            control_code=control_data.control_code,
            name=control_data.name,
            category=control_data.category,
            risk_rating=control_data.risk_rating,
            control_type=control_data.control_type,
            frequency=control_data.frequency,
            is_key=control_data.is_key,
            is_automated=control_data.is_automated,
        )
        
        db.add(control)
        await db.commit()
        await db.refresh(control)
        
        return control
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create control: {str(e)}",
        )

