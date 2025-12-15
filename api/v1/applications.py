"""Application endpoints with tenant isolation."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db, get_tenancy_context
from models.application import Application, ApplicationBase, ApplicationCreate, ApplicationResponse
from models.user import User
from models.user_tenant import UserTenant

router = APIRouter()


@router.get("/applications", response_model=List[ApplicationResponse])
async def list_applications(
    current_user: User = Depends(get_current_user),
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    List applications in the current user's tenant.
    
    Returns:
        List of applications in the tenant.
    """
    try:
        # Platform admins can see all applications
        if current_user.is_platform_admin:
            result = await db.execute(select(Application))
        else:
            # Regular users: filter by tenant_id
            result = await db.execute(
                select(Application).where(Application.tenant_id == tenancy.tenant_id)
            )
        
        applications = result.scalars().all()
        return applications
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch applications: {str(e)}",
        )


@router.get("/applications/{application_id}", response_model=ApplicationResponse)
async def get_application(
    application_id: UUID,
    current_user: User = Depends(get_current_user),
    tenancy=Depends(get_tenancy_context),
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
        # Build query with tenant filtering
        query = select(Application).where(Application.id == application_id)
        
        if not current_user.is_platform_admin:
            # Regular users: must filter by tenant_id
            query = query.where(Application.tenant_id == tenancy.tenant_id)
        
        result = await db.execute(query)
        application = result.scalar_one_or_none()
        
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found",
            )
        
        return application
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch application: {str(e)}",
        )


@router.post("/applications", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
async def create_application(
    application_data: ApplicationCreate,
    current_user: User = Depends(get_current_user),
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new application.
    
    Note: tenant_id in request is ignored - uses tenant from membership context.
    Validates that business_owner_membership_id and it_owner_membership_id belong to the tenant.
    """
    try:
        # Validate business owner membership belongs to tenant (if provided)
        if application_data.business_owner_membership_id:
            business_owner_query = select(UserTenant).where(
                UserTenant.id == application_data.business_owner_membership_id
            )
            if not current_user.is_platform_admin:
                business_owner_query = business_owner_query.where(
                    UserTenant.tenant_id == tenancy.tenant_id
                )
            
            result = await db.execute(business_owner_query)
            business_owner = result.scalar_one_or_none()
            
            if not business_owner:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Business owner membership not found",
                )
            
            if business_owner.tenant_id != tenancy.tenant_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Business owner must belong to the same tenant",
                )
        
        # Validate IT owner membership belongs to tenant (if provided)
        if application_data.it_owner_membership_id:
            it_owner_query = select(UserTenant).where(
                UserTenant.id == application_data.it_owner_membership_id
            )
            if not current_user.is_platform_admin:
                it_owner_query = it_owner_query.where(
                    UserTenant.tenant_id == tenancy.tenant_id
                )
            
            result = await db.execute(it_owner_query)
            it_owner = result.scalar_one_or_none()
            
            if not it_owner:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="IT owner membership not found",
                )
            
            if it_owner.tenant_id != tenancy.tenant_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="IT owner must belong to the same tenant",
                )
        
        # Override tenant_id from membership context (security: never trust client)
        application = Application(
            tenant_id=tenancy.tenant_id,
            name=application_data.name,
            category=application_data.category,
            scope_rationale=application_data.scope_rationale,
            business_owner_membership_id=application_data.business_owner_membership_id,
            it_owner_membership_id=application_data.it_owner_membership_id,
        )
        
        db.add(application)
        await db.commit()
        await db.refresh(application)
        
        return application
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create application: {str(e)}",
        )
