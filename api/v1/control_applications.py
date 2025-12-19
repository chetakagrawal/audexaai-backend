"""Control applications endpoints - manage application mappings for controls."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db, get_tenancy_context
from api.tenancy import TenancyContext
from models.application import Application, ApplicationResponse
from models.control import Control, ControlResponse
from models.control_application import (
    ControlApplication,
    ControlApplicationCreate,
    ControlApplicationResponse,
)
from models.user import User
from sqlalchemy import select
from services import control_applications_service

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
    tenancy: TenancyContext = Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Attach an application to a control.
    
    Creates a control_applications row linking the control to the application.
    Note: tenant_id and control_id are derived from context, not client input.
    """
    # Router is thin - delegate to service
    return await control_applications_service.add_application_to_control(
        session=db,
        membership_ctx=tenancy,
        control_id=control_id,
        application_id=application_data.application_id,
    )


@router.get(
    "/controls/{control_id}/applications",
    response_model=List[ApplicationResponse],
)
async def list_control_applications(
    control_id: UUID,
    current_user: User = Depends(get_current_user),
    tenancy: TenancyContext = Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    List all active applications attached to a control.
    
    Returns ApplicationResponse objects for applications currently mapped to the control.
    """
    # Router is thin - delegate to service
    return await control_applications_service.list_control_applications(
        session=db,
        membership_ctx=tenancy,
        control_id=control_id,
    )


@router.delete(
    "/controls/{control_id}/applications/{application_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_application_from_control(
    control_id: UUID,
    application_id: UUID,
    current_user: User = Depends(get_current_user),
    tenancy: TenancyContext = Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Remove an application from a control (soft remove).
    
    Sets removed_at and removed_by_membership_id on the active mapping.
    Note: tenant_id and control_id are derived from context, not client input.
    """
    # Router is thin - delegate to service
    await control_applications_service.remove_application_from_control(
        session=db,
        membership_ctx=tenancy,
        control_id=control_id,
        application_id=application_id,
    )
    return None


@router.put(
    "/controls/{control_id}/applications/bulk",
    response_model=List[ControlApplicationResponse],
)
async def replace_control_applications_bulk(
    control_id: UUID,
    application_ids: List[UUID],
    current_user: User = Depends(get_current_user),
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Replace all applications for a control (removes old, adds new).
    
    This endpoint:
    1. Removes all existing control_applications for this control
    2. Creates new control_applications for the provided application_ids
    
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
        if application_ids:
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
        
        # Remove all existing control_applications for this control
        existing_query = select(ControlApplication).where(
            ControlApplication.control_id == control_id
        )
        if not current_user.is_platform_admin:
            existing_query = existing_query.where(
                ControlApplication.tenant_id == tenancy.tenant_id
            )
        
        result = await db.execute(existing_query)
        existing_mappings = result.scalars().all()
        
        for mapping in existing_mappings:
            await db.delete(mapping)
        
        # Create new control_applications records
        created_mappings = []
        for application_id in application_ids:
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
            detail=f"Failed to replace control applications: {str(e)}",
        )


@router.get(
    "/applications/{application_id}/controls",
    response_model=List[ControlResponse],
)
async def list_application_controls(
    application_id: UUID,
    current_user: User = Depends(get_current_user),
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    List all controls attached to an application (reverse lookup).
    
    Returns control details for controls mapped to the given application.
    """
    try:
        # Verify application exists and belongs to tenant
        application_query = select(Application).where(Application.id == application_id)
        if not current_user.is_platform_admin:
            application_query = application_query.where(Application.tenant_id == tenancy.tenant_id)
        
        result = await db.execute(application_query)
        application = result.scalar_one_or_none()
        
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found",
            )
        
        # Get all control_applications for this application
        query = select(ControlApplication).where(ControlApplication.application_id == application_id)
        if not current_user.is_platform_admin:
            query = query.where(ControlApplication.tenant_id == tenancy.tenant_id)
        
        result = await db.execute(query)
        control_applications = result.scalars().all()
        
        if not control_applications:
            return []
        
        # Get control IDs
        control_ids = [ca.control_id for ca in control_applications]
        
        # Fetch the actual controls
        controls_query = select(Control).where(Control.id.in_(control_ids))
        if not current_user.is_platform_admin:
            controls_query = controls_query.where(Control.tenant_id == tenancy.tenant_id)
        
        result = await db.execute(controls_query)
        controls = result.scalars().all()
        
        # For each control, fetch its applications (similar to list_controls)
        control_ids_list = [control.id for control in controls]
        if control_ids_list:
            control_apps_query = select(ControlApplication).where(
                ControlApplication.control_id.in_(control_ids_list)
            )
            if not current_user.is_platform_admin:
                control_apps_query = control_apps_query.where(
                    ControlApplication.tenant_id == tenancy.tenant_id
                )
            
            result = await db.execute(control_apps_query)
            all_control_apps = result.scalars().all()
            
            # Group applications by control_id
            apps_by_control: dict[UUID, list[Application]] = {}
            for ca in all_control_apps:
                if ca.control_id not in apps_by_control:
                    apps_by_control[ca.control_id] = []
            
            # Fetch application details
            app_ids = {ca.application_id for ca in all_control_apps}
            if app_ids:
                apps_query = select(Application).where(Application.id.in_(app_ids))
                if not current_user.is_platform_admin:
                    apps_query = apps_query.where(Application.tenant_id == tenancy.tenant_id)
                
                result = await db.execute(apps_query)
                applications = result.scalars().all()
                app_dict = {app.id: app for app in applications}
                
                # Map applications to controls
                for ca in all_control_apps:
                    if ca.control_id in apps_by_control and ca.application_id in app_dict:
                        apps_by_control[ca.control_id].append(app_dict[ca.application_id])
        
        # Build response with applications included
        response = []
        for control in controls:
            control_dict = {
                "id": control.id,
                "tenant_id": control.tenant_id,
                "created_by_membership_id": control.created_by_membership_id,
                "control_code": control.control_code,
                "name": control.name,
                "category": control.category,
                "risk_rating": control.risk_rating,
                "control_type": control.control_type,
                "frequency": control.frequency,
                "is_key": control.is_key,
                "is_automated": control.is_automated,
                "created_at": control.created_at,
                "applications": apps_by_control.get(control.id, []),
            }
            response.append(control_dict)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list application controls: {str(e)}",
        )