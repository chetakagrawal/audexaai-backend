"""Service layer for ControlApplication business logic."""

from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.tenancy import TenancyContext
from models.application import ApplicationResponse
from models.control_application import ControlApplication
from repos import applications_repo, control_applications_repo, controls_repo


async def add_application_to_control(
    session: AsyncSession,
    *,
    membership_ctx: TenancyContext,
    control_id: UUID,
    application_id: UUID,
) -> ControlApplication:
    """
    Add an application to a control (create active mapping).
    
    Business rules:
    - Validates control exists and belongs to tenant
    - Validates application exists and belongs to tenant
    - If active mapping already exists => idempotent success (returns existing)
    - Otherwise creates new mapping with tenant_id and added_by_membership_id
    
    Args:
        session: Database session
        membership_ctx: Tenancy context
        control_id: Control ID
        application_id: Application ID
    
    Returns:
        ControlApplication mapping (existing or newly created)
    
    Raises:
        HTTPException: 404 if control or application not found
    """
    # Validate control exists and belongs to tenant
    control = await controls_repo.get_by_id(
        session,
        tenant_id=membership_ctx.tenant_id,
        control_id=control_id,
        include_deleted=False,
    )
    
    if not control:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Control not found",
        )
    
    # Validate application exists and belongs to tenant
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
    
    # Check if active mapping already exists (idempotent)
    existing = await control_applications_repo.get_active(
        session,
        tenant_id=membership_ctx.tenant_id,
        control_id=control_id,
        application_id=application_id,
    )
    
    if existing:
        # Idempotent: return existing mapping
        return existing
    
    # Create new mapping
    mapping = ControlApplication(
        tenant_id=membership_ctx.tenant_id,
        control_id=control_id,
        application_id=application_id,
        added_at=datetime.utcnow(),
        added_by_membership_id=membership_ctx.membership_id,
    )
    
    try:
        mapping = await control_applications_repo.create(session, mapping)
        await session.commit()
        await session.refresh(mapping)
        return mapping
    except Exception as e:
        await session.rollback()
        # Check if it's a unique constraint violation (shouldn't happen due to check above, but be safe)
        error_str = str(e)
        if 'ux_control_apps_active' in error_str.lower() or 'unique constraint' in error_str.lower():
            # Race condition: another request created it between our check and insert
            # Fetch and return the existing one
            existing = await control_applications_repo.get_active(
                session,
                tenant_id=membership_ctx.tenant_id,
                control_id=control_id,
                application_id=application_id,
            )
            if existing:
                return existing
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add application to control: {error_str}",
        )


async def remove_application_from_control(
    session: AsyncSession,
    *,
    membership_ctx: TenancyContext,
    control_id: UUID,
    application_id: UUID,
) -> None:
    """
    Remove an application from a control (soft remove).
    
    Business rules:
    - Finds active mapping; if none => idempotent success (no-op)
    - Sets removed_at and removed_by_membership_id
    
    Args:
        session: Database session
        membership_ctx: Tenancy context
        control_id: Control ID
        application_id: Application ID
    
    Raises:
        HTTPException: 404 if control not found (for consistency)
    """
    # Validate control exists (for consistency with add)
    control = await controls_repo.get_by_id(
        session,
        tenant_id=membership_ctx.tenant_id,
        control_id=control_id,
        include_deleted=False,
    )
    
    if not control:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Control not found",
        )
    
    # Find active mapping
    mapping = await control_applications_repo.get_active(
        session,
        tenant_id=membership_ctx.tenant_id,
        control_id=control_id,
        application_id=application_id,
    )
    
    if not mapping:
        # Idempotent: already removed or never existed
        return
    
    # Soft remove
    await control_applications_repo.soft_remove(
        session,
        mapping,
        removed_at=datetime.utcnow(),
        removed_by_membership_id=membership_ctx.membership_id,
    )
    
    await session.commit()
    await session.refresh(mapping)


async def list_control_applications(
    session: AsyncSession,
    *,
    membership_ctx: TenancyContext,
    control_id: UUID,
) -> list[ApplicationResponse]:
    """
    List all active applications for a control.
    
    Returns list of ApplicationResponse objects for applications that are
    currently mapped to the control (removed_at IS NULL).
    
    Args:
        session: Database session
        membership_ctx: Tenancy context
        control_id: Control ID
    
    Returns:
        List of ApplicationResponse objects
    
    Raises:
        HTTPException: 404 if control not found
    """
    # Validate control exists
    control = await controls_repo.get_by_id(
        session,
        tenant_id=membership_ctx.tenant_id,
        control_id=control_id,
        include_deleted=False,
    )
    
    if not control:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Control not found",
        )
    
    # Get active mappings
    mappings = await control_applications_repo.list_active_by_control(
        session,
        tenant_id=membership_ctx.tenant_id,
        control_id=control_id,
    )
    
    if not mappings:
        return []
    
    # Fetch applications in batch
    application_ids = [m.application_id for m in mappings]
    all_applications = await applications_repo.list(
        session,
        tenant_id=membership_ctx.tenant_id,
        include_deleted=False,
    )
    
    # Filter to only applications that are in our mapping list
    application_map = {app.id: app for app in all_applications if app.id in application_ids}
    applications = [application_map[app_id] for app_id in application_ids if app_id in application_map]
    
    # Convert to ApplicationResponse
    return [ApplicationResponse.model_validate(app) for app in applications]

