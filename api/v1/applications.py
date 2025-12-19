"""Application endpoints with tenant isolation."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db, get_tenancy_context
from api.tenancy import TenancyContext
from models.application import ApplicationCreate, ApplicationResponse, ApplicationUpdate
from models.user import User
from services.applications_service import (
    create_application,
    delete_application,
    get_application,
    list_applications,
    update_application,
)

router = APIRouter()


@router.get("/applications", response_model=List[ApplicationResponse])
async def list_applications_endpoint(
    current_user: User = Depends(get_current_user),
    tenancy: TenancyContext = Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    List applications in the current user's tenant.
    
    Returns:
        List of applications in the tenant.
    """
    try:
        # Platform admins can see all applications
        applications = await list_applications(
            db,
            membership_ctx=tenancy,
            is_platform_admin=current_user.is_platform_admin,
        )
        
        return [ApplicationResponse.model_validate(app) for app in applications]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch applications: {str(e)}",
        )


@router.get("/applications/{application_id}", response_model=ApplicationResponse)
async def get_application_endpoint(
    application_id: UUID,
    current_user: User = Depends(get_current_user),
    tenancy: TenancyContext = Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific application by ID.
    
    Returns:
        Application if found and user has access.
    
    Raises:
        404 if application not found or user doesn't have access.
    """
    try:
        application = await get_application(
            db,
            membership_ctx=tenancy,
            application_id=application_id,
            is_platform_admin=current_user.is_platform_admin,
        )
        
        return ApplicationResponse.model_validate(application)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch application: {str(e)}",
        )


@router.post("/applications", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
async def create_application_endpoint(
    application_data: ApplicationCreate,
    current_user: User = Depends(get_current_user),
    tenancy: TenancyContext = Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new application.
    
    Note: tenant_id in request is ignored - uses tenant from membership context.
    Validates that business_owner_membership_id and it_owner_membership_id belong to the tenant.
    """
    try:
        application = await create_application(
            db,
            membership_ctx=tenancy,
            payload=application_data,
        )
        
        return ApplicationResponse.model_validate(application)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create application: {str(e)}",
        )


@router.put("/applications/{application_id}", response_model=ApplicationResponse)
async def update_application_endpoint(
    application_id: UUID,
    application_data: ApplicationUpdate,
    current_user: User = Depends(get_current_user),
    tenancy: TenancyContext = Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Update an existing application.
    
    Only provided fields will be updated. Validates that business_owner_membership_id 
    and it_owner_membership_id belong to the tenant.
    """
    try:
        application = await update_application(
            db,
            membership_ctx=tenancy,
            application_id=application_id,
            payload=application_data,
        )
        
        return ApplicationResponse.model_validate(application)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update application: {str(e)}",
        )


@router.delete("/applications/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_application_endpoint(
    application_id: UUID,
    current_user: User = Depends(get_current_user),
    tenancy: TenancyContext = Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete an application.
    
    Note: In Sub-stage A, this is a hard delete. In Sub-stage B, this will be a soft delete.
    """
    try:
        await delete_application(
            db,
            membership_ctx=tenancy,
            application_id=application_id,
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete application: {str(e)}",
        )
