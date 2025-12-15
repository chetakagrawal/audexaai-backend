"""Control applications endpoints - manage application mappings for controls."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db, get_tenancy_context
from models.application import Application
from models.control import Control
from models.control_application import (
    ControlApplication,
    ControlApplicationCreate,
    ControlApplicationResponse,
)
from models.user import User

router = APIRouter()


@router.post(
    "/controls/{control_id}/applications/bulk",
    response_model=List[ControlApplicationResponse],
    status_code=status.HTTP_201_CREATED,
)
async def attach_applications_to_control_bulk(
    control_id: UUID,
    application_ids: List[UUID],
    current_user: User = Depends(get_current_user),
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Attach multiple applications to a control in bulk.
    
    Creates control_applications rows linking the control to each application.
    Note: tenant_id and control_id are derived from context, not client input.
    """
    try:
        # Verify control exists and belongs to tenant
        control_query = select(Control).where(Control.id == control_id)
        if not current_user.is_platform_admin:
            control_query = control_query.where(Control.tenant_id == tenancy.tenant_id)
        
        result = await db.execute(control_query)
        control = result.scalar_one_or_none()
        
        if not control:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Control not found",
            )
        
        # Verify all applications exist and belong to tenant
        application_query = select(Application).where(Application.id.in_(application_ids))
        if not current_user.is_platform_admin:
            application_query = application_query.where(Application.tenant_id == tenancy.tenant_id)
        
        result = await db.execute(application_query)
        applications = result.scalars().all()
        
        # Check if all requested applications were found
        found_ids = {app.id for app in applications}
        missing_ids = set(application_ids) - found_ids
        if missing_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Applications not found: {missing_ids}",
            )
        
        # Verify all applications belong to same tenant as control
        for app in applications:
            if app.tenant_id != control.tenant_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Application {app.id} must belong to the same tenant as the control",
                )
        
        # Create control_applications records (skip existing ones)
        created_mappings = []
        for application_id in application_ids:
            # Check if mapping already exists
            existing_query = select(ControlApplication).where(
                ControlApplication.control_id == control_id,
                ControlApplication.application_id == application_id,
            )
            if not current_user.is_platform_admin:
                existing_query = existing_query.where(
                    ControlApplication.tenant_id == tenancy.tenant_id
                )
            
            result = await db.execute(existing_query)
            existing = result.scalar_one_or_none()
            
            if existing:
                # Idempotent: return existing mapping
                created_mappings.append(existing)
            else:
                # Create new mapping
                control_application = ControlApplication(
                    tenant_id=tenancy.tenant_id,
                    control_id=control_id,
                    application_id=application_id,
                )
                db.add(control_application)
                created_mappings.append(control_application)
        
        await db.commit()
        
        # Refresh all created mappings
        for mapping in created_mappings:
            await db.refresh(mapping)
        
        return created_mappings
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to attach applications to control: {str(e)}",
        )


@router.post(
    "/controls/{control_id}/applications",
    response_model=ControlApplicationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def attach_application_to_control(
    control_id: UUID,
    application_data: ControlApplicationCreate,
    current_user: User = Depends(get_current_user),
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Attach an application to a control.
    
    Creates a control_applications row linking the control to the application.
    Note: tenant_id and control_id are derived from context, not client input.
    """
    try:
        # Verify control exists and belongs to tenant
        control_query = select(Control).where(Control.id == control_id)
        if not current_user.is_platform_admin:
            control_query = control_query.where(Control.tenant_id == tenancy.tenant_id)
        
        result = await db.execute(control_query)
        control = result.scalar_one_or_none()
        
        if not control:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Control not found",
            )
        
        # Verify application exists and belongs to tenant
        application_query = select(Application).where(Application.id == application_data.application_id)
        if not current_user.is_platform_admin:
            application_query = application_query.where(Application.tenant_id == tenancy.tenant_id)
        
        result = await db.execute(application_query)
        application = result.scalar_one_or_none()
        
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found",
            )
        
        # Verify application belongs to same tenant as control
        if application.tenant_id != control.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Application must belong to the same tenant as the control",
            )
        
        # Check if mapping already exists
        existing_query = select(ControlApplication).where(
            ControlApplication.control_id == control_id,
            ControlApplication.application_id == application_data.application_id,
        )
        if not current_user.is_platform_admin:
            existing_query = existing_query.where(
                ControlApplication.tenant_id == tenancy.tenant_id
            )
        
        result = await db.execute(existing_query)
        existing = result.scalar_one_or_none()
        
        if existing:
            # Idempotent: return existing mapping
            return existing
        
        # Create new mapping
        control_application = ControlApplication(
            tenant_id=tenancy.tenant_id,
            control_id=control_id,
            application_id=application_data.application_id,
        )
        
        db.add(control_application)
        await db.commit()
        await db.refresh(control_application)
        
        return control_application
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to attach application to control: {str(e)}",
        )


@router.get(
    "/controls/{control_id}/applications",
    response_model=List[ControlApplicationResponse],
)
async def list_control_applications(
    control_id: UUID,
    current_user: User = Depends(get_current_user),
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    List all applications attached to a control.
    
    Returns control-application mappings.
    """
    try:
        # Verify control exists and belongs to tenant
        control_query = select(Control).where(Control.id == control_id)
        if not current_user.is_platform_admin:
            control_query = control_query.where(Control.tenant_id == tenancy.tenant_id)
        
        result = await db.execute(control_query)
        control = result.scalar_one_or_none()
        
        if not control:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Control not found",
            )
        
        # List all applications for this control
        query = select(ControlApplication).where(ControlApplication.control_id == control_id)
        if not current_user.is_platform_admin:
            query = query.where(ControlApplication.tenant_id == tenancy.tenant_id)
        
        result = await db.execute(query)
        control_applications = result.scalars().all()
        
        return control_applications
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list control applications: {str(e)}",
        )
