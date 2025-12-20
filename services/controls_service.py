"""Service layer for Control business logic."""

from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.tenancy import TenancyContext
from models.application import Application
from models.control import Control, ControlBase, ControlCreate
from models.control_application import ControlApplication
from repos import controls_repo


async def get_applications_for_controls(
    session: AsyncSession,
    *,
    control_ids: list[UUID],
    membership_ctx: TenancyContext,
    is_platform_admin: bool = False,
) -> dict[UUID, list[Application]]:
    """
    Get applications for a list of controls.
    
    Returns a mapping of control_id -> list of applications.
    
    Args:
        session: Database session
        control_ids: List of control IDs
        membership_ctx: Tenancy context
        is_platform_admin: If True, allow access to any tenant's applications
    
    Returns:
        Dictionary mapping control_id to list of applications
    """
    if not control_ids:
        return {}
    
    # Get all control_applications for these controls
    control_apps_query = select(ControlApplication).where(
        ControlApplication.control_id.in_(control_ids)
    )
    if not is_platform_admin:
        control_apps_query = control_apps_query.where(
            ControlApplication.tenant_id == membership_ctx.tenant_id
        )
    
    control_apps_result = await session.execute(control_apps_query)
    control_applications = control_apps_result.scalars().all()
    
    # Get all unique application IDs
    application_ids = list(set(ca.application_id for ca in control_applications))
    
    # Fetch all applications
    applications_map = {}
    if application_ids:
        apps_query = select(Application).where(Application.id.in_(application_ids))
        if not is_platform_admin:
            apps_query = apps_query.where(Application.tenant_id == membership_ctx.tenant_id)
        
        apps_result = await session.execute(apps_query)
        applications = apps_result.scalars().all()
        applications_map = {app.id: app for app in applications}
    
    # Build a map of control_id -> list of applications
    control_applications_map: dict[UUID, list[Application]] = {}
    for ca in control_applications:
        if ca.control_id not in control_applications_map:
            control_applications_map[ca.control_id] = []
        if ca.application_id in applications_map:
            control_applications_map[ca.control_id].append(applications_map[ca.application_id])
    
    return control_applications_map


async def create_control(
    session: AsyncSession,
    *,
    membership_ctx: TenancyContext,
    payload: ControlCreate,
) -> Control:
    """
    Create a new control with optional application associations.
    
    Args:
        session: Database session
        membership_ctx: Tenancy context with membership_id, tenant_id, role
        payload: Control creation data
    
    Returns:
        Created control
    
    Raises:
        HTTPException: 404 if applications not found or belong to different tenant
    """
    # Create control instance
    control = Control(
        tenant_id=membership_ctx.tenant_id,
        created_by_membership_id=membership_ctx.membership_id,
        control_code=payload.control_code,
        name=payload.name,
        description=payload.description,
        category=payload.category,
        risk_rating=payload.risk_rating,
        control_type=payload.control_type,
        frequency=payload.frequency,
        is_key=payload.is_key,
        is_automated=payload.is_automated,
        row_version=1,  # Initial version
        # updated_at and updated_by_membership_id are None on creation (only set on updates)
    )
    
    # Create control in database (with error handling for uniqueness)
    try:
        control = await controls_repo.create(session, control)
    except IntegrityError as e:
        await session.rollback()
        # Check if it's a unique constraint violation on control_code
        error_str = str(e.orig) if hasattr(e, 'orig') else str(e)
        error_msg_lower = error_str.lower()
        
        # Check PostgreSQL error code for unique violation (23505)
        is_unique_violation = False
        if hasattr(e, 'orig') and hasattr(e.orig, 'pgcode'):
            is_unique_violation = e.orig.pgcode == '23505'
        
        # Check for various constraint name patterns and PostgreSQL error messages
        if is_unique_violation or any(pattern in error_msg_lower for pattern in [
            'ux_controls_tenant_code_active',
            'uq_controls_tenant_code',
            'uq_controls_tenant_id_control_code',
            'unique constraint',
            'duplicate key',
            'violates unique constraint',
            'already exists',
        ]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Control code '{payload.control_code}' already exists for this tenant",
            )
        # Re-raise with more context for debugging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {error_str}",
        )
    
    # If application_ids are provided, create control_applications records
    if payload.application_ids:
        # Verify all applications exist and belong to the same tenant
        application_query = select(Application).where(
            Application.id.in_(payload.application_ids)
        )
        application_query = application_query.where(
            Application.tenant_id == membership_ctx.tenant_id
        )
        
        result = await session.execute(application_query)
        applications = result.scalars().all()
        
        # Check if all requested applications were found
        found_ids = {app.id for app in applications}
        missing_ids = set(payload.application_ids) - found_ids
        if missing_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Applications not found: {missing_ids}",
            )
        
        # Verify all applications belong to the same tenant
        for app in applications:
            if app.tenant_id != membership_ctx.tenant_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Application {app.id} does not belong to the same tenant",
                )
        
        # Create control_applications records
        for application_id in payload.application_ids:
            # Check if mapping already exists (shouldn't, but be safe)
            existing_query = select(ControlApplication).where(
                ControlApplication.control_id == control.id,
                ControlApplication.application_id == application_id,
            )
            result = await session.execute(existing_query)
            existing = result.scalar_one_or_none()
            
            if not existing:
                control_application = ControlApplication(
                    tenant_id=membership_ctx.tenant_id,
                    control_id=control.id,
                    application_id=application_id,
                )
                session.add(control_application)
    
    try:
        await session.commit()
        await session.refresh(control)
    except IntegrityError as e:
        await session.rollback()
        # Check if it's a unique constraint violation on control_code
        # PostgreSQL error format: "duplicate key value violates unique constraint..."
        error_str = str(e.orig) if hasattr(e, 'orig') else str(e)
        error_msg_lower = error_str.lower()
        
        # Check PostgreSQL error code for unique violation (23505)
        is_unique_violation = False
        if hasattr(e, 'orig') and hasattr(e.orig, 'pgcode'):
            is_unique_violation = e.orig.pgcode == '23505'
        
        # Check for various constraint name patterns and PostgreSQL error messages
        if is_unique_violation or any(pattern in error_msg_lower for pattern in [
            'ux_controls_tenant_code_active',
            'uq_controls_tenant_code',
            'uq_controls_tenant_id_control_code',
            'unique constraint',
            'duplicate key',
            'violates unique constraint',
            'already exists',
        ]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Control code '{payload.control_code}' already exists for this tenant",
            )
        # Re-raise with more context for debugging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {error_str}",
        )
    
    return control


async def update_control(
    session: AsyncSession,
    *,
    membership_ctx: TenancyContext,
    control_id: UUID,
    payload: ControlBase,
    is_platform_admin: bool = False,
) -> Control:
    """
    Update an existing control.
    
    Args:
        session: Database session
        membership_ctx: Tenancy context with membership_id, tenant_id, role
        control_id: Control ID to update
        payload: Control update data
        is_platform_admin: If True, allow update of any tenant's control
    
    Returns:
        Updated control
    
    Raises:
        HTTPException: 404 if control not found or deleted
    """
    if is_platform_admin:
        from sqlalchemy import select
        from models.control import Control as ControlModel
        result = await session.execute(
            select(ControlModel).where(
                ControlModel.id == control_id,
                ControlModel.deleted_at.is_(None),  # Exclude deleted
            )
        )
        control = result.scalar_one_or_none()
    else:
        control = await controls_repo.get_by_id(
            session,
            tenant_id=membership_ctx.tenant_id,
            control_id=control_id,
            include_deleted=False,  # Exclude deleted by default
        )
    
    if not control:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Control not found",
        )
    
    # Update control fields
    control.control_code = payload.control_code
    control.name = payload.name
    control.description = payload.description
    control.category = payload.category
    control.risk_rating = payload.risk_rating
    control.control_type = payload.control_type
    control.frequency = payload.frequency
    control.is_key = payload.is_key
    control.is_automated = payload.is_automated
    
    # Update audit metadata
    control.updated_at = datetime.utcnow()
    control.updated_by_membership_id = membership_ctx.membership_id
    control.row_version += 1
    
    await session.commit()
    await session.refresh(control)
    
    return control


async def delete_control(
    session: AsyncSession,
    *,
    membership_ctx: TenancyContext,
    control_id: UUID,
    is_platform_admin: bool = False,
) -> Control:
    """
    Delete (soft delete) a control.
    
    Args:
        session: Database session
        membership_ctx: Tenancy context with membership_id, tenant_id, role
        control_id: Control ID to delete
        is_platform_admin: If True, allow delete of any tenant's control
    
    Returns:
        Deleted control
    
    Raises:
        HTTPException: 404 if control not found or already deleted
    """
    if is_platform_admin:
        from sqlalchemy import select
        from models.control import Control as ControlModel
        result = await session.execute(
            select(ControlModel).where(
                ControlModel.id == control_id,
                ControlModel.deleted_at.is_(None),  # Only delete if not already deleted
            )
        )
        control = result.scalar_one_or_none()
    else:
        control = await controls_repo.get_by_id(
            session,
            tenant_id=membership_ctx.tenant_id,
            control_id=control_id,
            include_deleted=False,  # Only delete if not already deleted
        )
    
    if not control:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Control not found",
        )
    
    # Soft delete: set deleted_at and deleted_by_membership_id
    control.deleted_at = datetime.utcnow()
    control.deleted_by_membership_id = membership_ctx.membership_id
    # Also update updated_at and updated_by
    control.updated_at = datetime.utcnow()
    control.updated_by_membership_id = membership_ctx.membership_id
    # Increment row_version
    control.row_version += 1
    
    await session.commit()
    await session.refresh(control)
    
    return control


async def get_control(
    session: AsyncSession,
    *,
    membership_ctx: TenancyContext,
    control_id: UUID,
    is_platform_admin: bool = False,
) -> Control:
    """
    Get a control by ID (excluding deleted by default).
    
    Args:
        session: Database session
        membership_ctx: Tenancy context with membership_id, tenant_id, role
        control_id: Control ID to fetch
        is_platform_admin: If True, allow access to any tenant's control
    
    Returns:
        Control if found
    
    Raises:
        HTTPException: 404 if control not found or deleted
    """
    if is_platform_admin:
        from sqlalchemy import select
        from models.control import Control as ControlModel
        result = await session.execute(
            select(ControlModel).where(
                ControlModel.id == control_id,
                ControlModel.deleted_at.is_(None),  # Exclude deleted
            )
        )
        control = result.scalar_one_or_none()
    else:
        control = await controls_repo.get_by_id(
            session,
            tenant_id=membership_ctx.tenant_id,
            control_id=control_id,
            include_deleted=False,  # Exclude deleted by default
        )
    
    if not control:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Control not found",
        )
    
    return control


async def list_controls(
    session: AsyncSession,
    *,
    membership_ctx: TenancyContext,
    is_platform_admin: bool = False,
) -> list[Control]:
    """
    List all controls for the tenant (excluding deleted by default).
    
    Args:
        session: Database session
        membership_ctx: Tenancy context with membership_id, tenant_id, role
        is_platform_admin: If True, list all controls (no tenant filter)
    
    Returns:
        List of controls (excluding deleted)
    """
    if is_platform_admin:
        # Platform admins can see all controls (excluding deleted)
        from sqlalchemy import select
        from models.control import Control as ControlModel
        result = await session.execute(
            select(ControlModel).where(ControlModel.deleted_at.is_(None))
        )
        return list(result.scalars().all())
    else:
        return await controls_repo.list(
            session,
            tenant_id=membership_ctx.tenant_id,
            include_deleted=False,
        )

