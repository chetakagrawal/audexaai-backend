"""Control endpoints with tenant isolation."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db, get_tenancy_context
from api.tenancy import TenancyContext
from models.control import Control, ControlBase, ControlCreate, ControlResponse
from models.user import User
from services.controls_service import (
    create_control,
    delete_control,
    get_control,
    list_controls,
    update_control,
)

router = APIRouter()


@router.get("/controls", response_model=List[ControlResponse])
async def list_controls_endpoint(
    current_user: User = Depends(get_current_user),
    tenancy: TenancyContext = Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    List controls in the current user's tenant.
    
    Returns:
        List of controls in the tenant (excluding deleted).
    """
    try:
        controls = await list_controls(
            db,
            membership_ctx=tenancy,
            is_platform_admin=current_user.is_platform_admin,
        )
        
        # Build response (applications removed from schema)
        return [ControlResponse.model_validate(control) for control in controls]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch controls: {str(e)}",
        )


@router.get("/controls/{control_id}", response_model=ControlResponse)
async def get_control_endpoint(
    control_id: UUID,
    current_user: User = Depends(get_current_user),
    tenancy: TenancyContext = Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific control by ID.
    
    Returns:
        Control if found and user has access (excluding deleted).
    
    Raises:
        404 if control not found, deleted, or user doesn't have access.
    """
    try:
        control_uuid = control_id
        
        control = await get_control(
            db,
            membership_ctx=tenancy,
            control_id=control_uuid,
            is_platform_admin=current_user.is_platform_admin,
        )
        
        return ControlResponse.model_validate(control)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch control: {str(e)}",
        )


@router.post("/controls", response_model=ControlResponse)
async def create_control_endpoint(
    control_data: ControlCreate,
    current_user: User = Depends(get_current_user),
    tenancy: TenancyContext = Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new control.
    
    If application_ids are provided, also creates control_applications records
    in the same transaction.
    
    Note: tenant_id is set from membership context (never from client input).
    """
    try:
        control = await create_control(
            db,
            membership_ctx=tenancy,
            payload=control_data,
        )
        
        return ControlResponse.model_validate(control)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        # Log the actual error for debugging
        import logging
        logging.error(f"Error creating control: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create control: {str(e)}",
        )


@router.put("/controls/{control_id}", response_model=ControlResponse)
async def update_control_endpoint(
    control_id: UUID,
    control_data: ControlBase,
    current_user: User = Depends(get_current_user),
    tenancy: TenancyContext = Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a control.
    
    Note: tenant_id cannot be changed via this endpoint.
    Updates row_version, updated_at, and updated_by_membership_id automatically.
    """
    try:
        control_uuid = control_id
        
        control = await update_control(
            db,
            membership_ctx=tenancy,
            control_id=control_uuid,
            payload=control_data,
            is_platform_admin=current_user.is_platform_admin,
        )
        
        return ControlResponse.model_validate(control)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update control: {str(e)}",
        )


@router.delete("/controls/{control_id}", response_model=ControlResponse)
async def delete_control_endpoint(
    control_id: UUID,
    current_user: User = Depends(get_current_user),
    tenancy: TenancyContext = Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete (soft delete) a control.
    
    Sets deleted_at, deleted_by_membership_id, and increments row_version.
    Deleted controls are excluded from list/get operations by default.
    """
    try:
        control = await delete_control(
            db,
            membership_ctx=tenancy,
            control_id=control_id,
            is_platform_admin=current_user.is_platform_admin,
        )
        
        return ControlResponse.model_validate(control)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete control: {str(e)}",
        )
