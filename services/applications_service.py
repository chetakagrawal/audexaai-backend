"""Service layer for Application business logic."""

from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.tenancy import TenancyContext
from models.application import Application, ApplicationCreate, ApplicationUpdate
from models.user_tenant import UserTenant
from repos import applications_repo


async def create_application(
    session: AsyncSession,
    *,
    membership_ctx: TenancyContext,
    payload: ApplicationCreate,
) -> Application:
    """
    Create a new application.
    
    Args:
        session: Database session
        membership_ctx: Tenancy context with membership_id, tenant_id, role
        payload: Application creation data
    
    Returns:
        Created application
    
    Raises:
        HTTPException: 404 if business/IT owner memberships not found or belong to different tenant
    """
    # Validate business owner membership belongs to tenant (if provided)
    if payload.business_owner_membership_id:
        business_owner_query = select(UserTenant).where(
            UserTenant.id == payload.business_owner_membership_id
        )
        business_owner_query = business_owner_query.where(
            UserTenant.tenant_id == membership_ctx.tenant_id
        )
        
        result = await session.execute(business_owner_query)
        business_owner = result.scalar_one_or_none()
        
        if not business_owner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business owner membership not found",
            )
        
        if business_owner.tenant_id != membership_ctx.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Business owner must belong to the same tenant",
            )
    
    # Validate IT owner membership belongs to tenant (if provided)
    if payload.it_owner_membership_id:
        it_owner_query = select(UserTenant).where(
            UserTenant.id == payload.it_owner_membership_id
        )
        it_owner_query = it_owner_query.where(
            UserTenant.tenant_id == membership_ctx.tenant_id
        )
        
        result = await session.execute(it_owner_query)
        it_owner = result.scalar_one_or_none()
        
        if not it_owner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="IT owner membership not found",
            )
        
        if it_owner.tenant_id != membership_ctx.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="IT owner must belong to the same tenant",
            )
    
    # Create application instance
    application = Application(
        tenant_id=membership_ctx.tenant_id,
        created_by_membership_id=membership_ctx.membership_id,
        name=payload.name,
        category=payload.category,
        scope_rationale=payload.scope_rationale,
        business_owner_membership_id=payload.business_owner_membership_id,
        it_owner_membership_id=payload.it_owner_membership_id,
        row_version=1,  # Initial version
        # updated_at and updated_by_membership_id are None on creation (only set on updates)
    )
    
    # Create in database (with error handling for uniqueness)
    try:
        application = await applications_repo.create(session, application)
        await session.commit()
        await session.refresh(application)
    except IntegrityError as e:
        await session.rollback()
        # Check if it's a unique constraint violation on (tenant_id, name)
        error_str = str(e.orig) if hasattr(e, 'orig') else str(e)
        error_msg_lower = error_str.lower()
        
        # Check PostgreSQL error code for unique violation (23505)
        is_unique_violation = False
        if hasattr(e, 'orig') and hasattr(e.orig, 'pgcode'):
            is_unique_violation = e.orig.pgcode == '23505'
        
        # Check for various constraint name patterns and PostgreSQL error messages
        if is_unique_violation or any(pattern in error_msg_lower for pattern in [
            'ux_applications_tenant_name_active',
            'uq_applications_tenant_name',
            'uq_applications_tenant_id_name',
            'unique constraint',
            'duplicate key',
            'violates unique constraint',
            'already exists',
        ]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Application name '{payload.name}' already exists for this tenant",
            )
        # Re-raise with more context for debugging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {error_str}",
        )
    
    return application


async def update_application(
    session: AsyncSession,
    *,
    membership_ctx: TenancyContext,
    application_id: UUID,
    payload: ApplicationUpdate,
) -> Application:
    """
    Update an existing application.
    
    Args:
        session: Database session
        membership_ctx: Tenancy context with membership_id, tenant_id, role
        application_id: Application ID to update
        payload: Application update data
    
    Returns:
        Updated application
    
    Raises:
        HTTPException: 404 if application not found
    """
    # Get application
    application = await applications_repo.get_by_id(
        session,
        tenant_id=membership_ctx.tenant_id,
        application_id=application_id,
        include_deleted=False,
    )
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )
    
    # Validate business owner membership belongs to tenant (if provided)
    if payload.business_owner_membership_id is not None:
        business_owner_query = select(UserTenant).where(
            UserTenant.id == payload.business_owner_membership_id
        )
        business_owner_query = business_owner_query.where(
            UserTenant.tenant_id == membership_ctx.tenant_id
        )
        
        result = await session.execute(business_owner_query)
        business_owner = result.scalar_one_or_none()
        
        if not business_owner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business owner membership not found",
            )
        
        if business_owner.tenant_id != membership_ctx.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Business owner must belong to the same tenant",
            )
    
    # Validate IT owner membership belongs to tenant (if provided)
    if payload.it_owner_membership_id is not None:
        it_owner_query = select(UserTenant).where(
            UserTenant.id == payload.it_owner_membership_id
        )
        it_owner_query = it_owner_query.where(
            UserTenant.tenant_id == membership_ctx.tenant_id
        )
        
        result = await session.execute(it_owner_query)
        it_owner = result.scalar_one_or_none()
        
        if not it_owner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="IT owner membership not found",
            )
        
        if it_owner.tenant_id != membership_ctx.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="IT owner must belong to the same tenant",
            )
    
    # Update only provided fields
    if payload.name is not None:
        application.name = payload.name
    if payload.category is not None:
        application.category = payload.category
    if payload.scope_rationale is not None:
        application.scope_rationale = payload.scope_rationale
    if payload.business_owner_membership_id is not None:
        application.business_owner_membership_id = payload.business_owner_membership_id
    if payload.it_owner_membership_id is not None:
        application.it_owner_membership_id = payload.it_owner_membership_id
    
    # Update audit metadata
    application.updated_at = datetime.utcnow()
    application.updated_by_membership_id = membership_ctx.membership_id
    application.row_version += 1
    
    # Save changes (with error handling for uniqueness if name changed)
    try:
        application = await applications_repo.save(session, application)
        await session.commit()
        await session.refresh(application)
    except IntegrityError as e:
        await session.rollback()
        # Check if it's a unique constraint violation on (tenant_id, name)
        error_str = str(e.orig) if hasattr(e, 'orig') else str(e)
        error_msg_lower = error_str.lower()
        
        # Check PostgreSQL error code for unique violation (23505)
        is_unique_violation = False
        if hasattr(e, 'orig') and hasattr(e.orig, 'pgcode'):
            is_unique_violation = e.orig.pgcode == '23505'
        
        # Check for various constraint name patterns and PostgreSQL error messages
        if is_unique_violation or any(pattern in error_msg_lower for pattern in [
            'ux_applications_tenant_name_active',
            'uq_applications_tenant_name',
            'uq_applications_tenant_id_name',
            'unique constraint',
            'duplicate key',
            'violates unique constraint',
            'already exists',
        ]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Application name '{payload.name or application.name}' already exists for this tenant",
            )
        # Re-raise with more context for debugging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {error_str}",
        )
    
    return application


async def delete_application(
    session: AsyncSession,
    *,
    membership_ctx: TenancyContext,
    application_id: UUID,
) -> None:
    """
    Delete an application (soft delete).
    
    Args:
        session: Database session
        membership_ctx: Tenancy context with membership_id, tenant_id, role
        application_id: Application ID to delete
    
    Raises:
        HTTPException: 404 if application not found or already deleted
    """
    # Get application
    application = await applications_repo.get_by_id(
        session,
        tenant_id=membership_ctx.tenant_id,
        application_id=application_id,
        include_deleted=False,
    )
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )
    
    # Soft delete: set deleted_at and deleted_by_membership_id
    application.deleted_at = datetime.utcnow()
    application.deleted_by_membership_id = membership_ctx.membership_id
    # Also update updated_at and updated_by
    application.updated_at = datetime.utcnow()
    application.updated_by_membership_id = membership_ctx.membership_id
    # Increment row_version
    application.row_version += 1
    
    await session.commit()
    await session.refresh(application)


async def get_application(
    session: AsyncSession,
    *,
    membership_ctx: TenancyContext,
    application_id: UUID,
    is_platform_admin: bool = False,
) -> Application:
    """
    Get an application by ID (excluding deleted by default).
    
    Args:
        session: Database session
        membership_ctx: Tenancy context with membership_id, tenant_id, role
        application_id: Application ID to fetch
        is_platform_admin: If True, allow access to any tenant's application
    
    Returns:
        Application if found
    
    Raises:
        HTTPException: 404 if application not found or deleted
    """
    if is_platform_admin:
        from sqlalchemy import select
        from models.application import Application as ApplicationModel
        result = await session.execute(
            select(ApplicationModel).where(ApplicationModel.id == application_id)
        )
        application = result.scalar_one_or_none()
    else:
        application = await applications_repo.get_by_id(
            session,
            tenant_id=membership_ctx.tenant_id,
            application_id=application_id,
            include_deleted=False,
        )
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )
    
    return application


async def list_applications(
    session: AsyncSession,
    *,
    membership_ctx: TenancyContext,
    is_platform_admin: bool = False,
) -> list[Application]:
    """
    List all applications for the tenant (excluding deleted by default).
    
    Args:
        session: Database session
        membership_ctx: Tenancy context with membership_id, tenant_id, role
        is_platform_admin: If True, list all applications (no tenant filter)
    
    Returns:
        List of applications (excluding deleted)
    """
    if is_platform_admin:
        # Platform admins can see all applications
        from sqlalchemy import select
        from models.application import Application as ApplicationModel
        result = await session.execute(select(ApplicationModel))
        return list(result.scalars().all())
    else:
        return await applications_repo.list(
            session,
            tenant_id=membership_ctx.tenant_id,
            include_deleted=False,
        )

