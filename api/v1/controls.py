"""Control endpoints with tenant isolation."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db, get_tenancy_context
from models.application import Application, ApplicationResponse
from models.control import Control, ControlBase, ControlCreate, ControlResponse
from models.control_application import ControlApplication
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
        List of controls in the tenant with their associated applications.
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
        
        # Fetch applications for all controls
        control_ids = [control.id for control in controls]
        if control_ids:
            # Get all control_applications for these controls
            control_apps_query = select(ControlApplication).where(
                ControlApplication.control_id.in_(control_ids)
            )
            if not current_user.is_platform_admin:
                control_apps_query = control_apps_query.where(
                    ControlApplication.tenant_id == tenancy.tenant_id
                )
            
            control_apps_result = await db.execute(control_apps_query)
            control_applications = control_apps_result.scalars().all()
            
            # Get all unique application IDs
            application_ids = list(set(ca.application_id for ca in control_applications))
            
            # Fetch all applications
            applications_map = {}
            if application_ids:
                apps_query = select(Application).where(Application.id.in_(application_ids))
                if not current_user.is_platform_admin:
                    apps_query = apps_query.where(Application.tenant_id == tenancy.tenant_id)
                
                apps_result = await db.execute(apps_query)
                applications = apps_result.scalars().all()
                applications_map = {app.id: app for app in applications}
            
            # Build a map of control_id -> list of applications
            control_applications_map = {}
            for ca in control_applications:
                if ca.control_id not in control_applications_map:
                    control_applications_map[ca.control_id] = []
                if ca.application_id in applications_map:
                    control_applications_map[ca.control_id].append(applications_map[ca.application_id])
        else:
            control_applications_map = {}
        
        # Build response with applications
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
                "applications": [
                    ApplicationResponse.model_validate(app)
                    for app in control_applications_map.get(control.id, [])
                ],
            }
            response.append(ControlResponse.model_validate(control_dict))
        
        return response
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
        Control if found and user has access, with associated applications.
    
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
        
        # Fetch applications for this control
        control_apps_query = select(ControlApplication).where(
            ControlApplication.control_id == control_id
        )
        if not current_user.is_platform_admin:
            control_apps_query = control_apps_query.where(
                ControlApplication.tenant_id == tenancy.tenant_id
            )
        
        control_apps_result = await db.execute(control_apps_query)
        control_applications = control_apps_result.scalars().all()
        
        # Fetch applications
        applications = []
        if control_applications:
            application_ids = [ca.application_id for ca in control_applications]
            apps_query = select(Application).where(Application.id.in_(application_ids))
            if not current_user.is_platform_admin:
                apps_query = apps_query.where(Application.tenant_id == tenancy.tenant_id)
            
            apps_result = await db.execute(apps_query)
            applications = apps_result.scalars().all()
        
        # Build response with applications
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
            "applications": [
                ApplicationResponse.model_validate(app) for app in applications
            ],
        }
        
        return ControlResponse.model_validate(control_dict)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch control: {str(e)}",
        )


@router.post("/controls", response_model=ControlResponse)
async def create_control(
    control_data: ControlCreate,
    current_user: User = Depends(get_current_user),
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new control.
    
    If application_ids are provided, also creates control_applications records
    in the same transaction.
    
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
        await db.flush()  # Flush to get the control.id without committing
        
        # If application_ids are provided, create control_applications records
        if control_data.application_ids:
            # Verify all applications exist and belong to the same tenant
            application_ids = control_data.application_ids
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
                    status_code=404,
                    detail=f"Applications not found: {missing_ids}",
                )
            
            # Verify all applications belong to the same tenant
            for app in applications:
                if app.tenant_id != tenancy.tenant_id:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Application {app.id} does not belong to the same tenant",
                    )
            
            # Create control_applications records
            for application_id in application_ids:
                # Check if mapping already exists (shouldn't, but be safe)
                existing_query = select(ControlApplication).where(
                    ControlApplication.control_id == control.id,
                    ControlApplication.application_id == application_id,
                )
                result = await db.execute(existing_query)
                existing = result.scalar_one_or_none()
                
                if not existing:
                    control_application = ControlApplication(
                        tenant_id=tenancy.tenant_id,
                        control_id=control.id,
                        application_id=application_id,
                    )
                    db.add(control_application)
        
        await db.commit()
        await db.refresh(control)
        
        # Fetch applications for the response
        control_apps_query = select(ControlApplication).where(
            ControlApplication.control_id == control.id
        )
        control_apps_result = await db.execute(control_apps_query)
        control_applications = control_apps_result.scalars().all()
        
        applications = []
        if control_applications:
            application_ids = [ca.application_id for ca in control_applications]
            apps_query = select(Application).where(Application.id.in_(application_ids))
            apps_result = await db.execute(apps_query)
            applications = apps_result.scalars().all()
        
        # Build response with applications
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
            "applications": [
                ApplicationResponse.model_validate(app) for app in applications
            ],
        }
        
        return ControlResponse.model_validate(control_dict)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create control: {str(e)}",
        )


@router.put("/controls/{control_id}", response_model=ControlResponse)
async def update_control(
    control_id: UUID,
    control_data: ControlBase,
    current_user: User = Depends(get_current_user),
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a control.
    
    Note: tenant_id cannot be changed via this endpoint.
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
        
        # Update control fields
        control.control_code = control_data.control_code
        control.name = control_data.name
        control.category = control_data.category
        control.risk_rating = control_data.risk_rating
        control.control_type = control_data.control_type
        control.frequency = control_data.frequency
        control.is_key = control_data.is_key
        control.is_automated = control_data.is_automated
        
        await db.commit()
        await db.refresh(control)
        
        # Fetch applications for the response
        control_apps_query = select(ControlApplication).where(
            ControlApplication.control_id == control_id
        )
        if not current_user.is_platform_admin:
            control_apps_query = control_apps_query.where(
                ControlApplication.tenant_id == tenancy.tenant_id
            )
        
        control_apps_result = await db.execute(control_apps_query)
        control_applications = control_apps_result.scalars().all()
        
        # Fetch applications
        applications = []
        if control_applications:
            application_ids = [ca.application_id for ca in control_applications]
            apps_query = select(Application).where(Application.id.in_(application_ids))
            if not current_user.is_platform_admin:
                apps_query = apps_query.where(Application.tenant_id == tenancy.tenant_id)
            
            apps_result = await db.execute(apps_query)
            applications = apps_result.scalars().all()
        
        # Build response with applications
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
            "applications": [
                ApplicationResponse.model_validate(app) for app in applications
            ],
        }
        
        return ControlResponse.model_validate(control_dict)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update control: {str(e)}",
        )
