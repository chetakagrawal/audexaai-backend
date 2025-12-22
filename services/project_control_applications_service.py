"""Service layer for project control applications (business logic)."""

from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.tenancy import TenancyContext
from models.application import Application, ApplicationResponse
from models.project_control import ProjectControl
from models.project_control_application import ProjectControlApplication
from repos import (
    project_control_applications_repo,
    project_controls_repo,
    applications_repo,
)


async def add_application_to_project_control(
    session: AsyncSession,
    *,
    membership_ctx: TenancyContext,
    project_control_id: UUID,
    application_id: UUID,
) -> ProjectControlApplication:
    """
    Add an application to a project control with version freezing.
    
    Business rules:
    - Validates project_control exists and belongs to tenant (and is not removed)
    - Validates application exists, belongs to tenant, and is not deleted
    - Freezes application version at current applications.row_version
    - Idempotent: returns existing active mapping if it exists
    
    Args:
        session: Database session
        membership_ctx: Membership context (tenant_id, membership_id)
        project_control_id: ProjectControl ID
        application_id: Application ID
    
    Returns:
        ProjectControlApplication mapping
    
    Raises:
        HTTPException: 404 if project_control or application not found, 400/409 if validation fails
    """
    tenant_id = membership_ctx.tenant_id
    membership_id = membership_ctx.membership_id
    
    # 1. Validate project_control exists and belongs to tenant (and is not removed)
    # First check if it exists at all (including removed)
    project_control = await project_controls_repo.get_by_id(
        session,
        tenant_id=tenant_id,
        project_control_id=project_control_id,
        include_removed=True,
    )
    if not project_control:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project control not found",
        )
    
    # Check if project_control is removed
    if project_control.removed_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add applications to a removed project control",
        )
    
    # 2. Validate application exists, belongs to tenant, and is not deleted
    application = await applications_repo.get_by_id(
        session,
        tenant_id=tenant_id,
        application_id=application_id,
        include_deleted=False,
    )
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )
    
    # 3. Check if active mapping already exists (idempotent behavior)
    existing = await project_control_applications_repo.get_active(
        session,
        tenant_id=tenant_id,
        project_control_id=project_control_id,
        application_id=application_id,
    )
    if existing:
        # Idempotent: return existing mapping
        return existing
    
    # 4. Create new mapping with frozen version
    # KEY: Freeze application version at current applications.row_version
    pca = ProjectControlApplication(
        tenant_id=tenant_id,
        project_control_id=project_control_id,
        application_id=application_id,
        application_version_num=application.row_version,  # VERSION FREEZING
        source="manual",
        added_at=datetime.utcnow(),
        added_by_membership_id=membership_id,
        removed_at=None,
        removed_by_membership_id=None,
    )
    
    return await project_control_applications_repo.create(session, pca)


async def remove_application_from_project_control(
    session: AsyncSession,
    *,
    membership_ctx: TenancyContext,
    pca_id: UUID,
) -> None:
    """
    Remove (soft delete) an application from a project control.
    
    Business rules:
    - Soft delete: sets removed_at and removed_by_membership_id
    - Does NOT hard delete the row
    - Idempotent: removing twice is a no-op (no error)
    
    Args:
        session: Database session
        membership_ctx: Membership context
        pca_id: ProjectControlApplication ID
    
    Raises:
        HTTPException: 404 if project control application not found
    """
    tenant_id = membership_ctx.tenant_id
    membership_id = membership_ctx.membership_id
    
    # Get existing mapping (include removed to make it idempotent)
    pca = await project_control_applications_repo.get_by_id(
        session,
        tenant_id=tenant_id,
        pca_id=pca_id,
        include_removed=True,
    )
    if not pca:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project control application not found",
        )
    
    # Idempotent: if already removed, do nothing
    if pca.removed_at is not None:
        return
    
    # Soft delete
    pca.removed_at = datetime.utcnow()
    pca.removed_by_membership_id = membership_id
    
    await project_control_applications_repo.save(session, pca)


async def remove_application_from_project_control_by_ids(
    session: AsyncSession,
    *,
    membership_ctx: TenancyContext,
    project_control_id: UUID,
    application_id: UUID,
) -> None:
    """
    Remove (soft delete) an application from a project control by project_control_id and application_id.
    
    Business rules:
    - Soft delete: sets removed_at and removed_by_membership_id
    - Does NOT hard delete the row
    - Idempotent: removing twice is a no-op (no error)
    
    Args:
        session: Database session
        membership_ctx: Membership context
        project_control_id: ProjectControl ID
        application_id: Application ID
    
    Raises:
        HTTPException: 404 if project control application not found
    """
    tenant_id = membership_ctx.tenant_id
    membership_id = membership_ctx.membership_id
    
    # Get existing active mapping
    pca = await project_control_applications_repo.get_active(
        session,
        tenant_id=tenant_id,
        project_control_id=project_control_id,
        application_id=application_id,
    )
    
    # Idempotent: if not found or already removed, do nothing
    if not pca:
        return
    
    # Soft delete
    pca.removed_at = datetime.utcnow()
    pca.removed_by_membership_id = membership_id
    
    await project_control_applications_repo.save(session, pca)


async def list_applications_for_project_control(
    session: AsyncSession,
    *,
    membership_ctx: TenancyContext,
    project_control_id: UUID,
) -> list[ApplicationResponse]:
    """
    List all active applications for a project control.
    
    Business rules:
    - Returns only ACTIVE mappings
    - Fetches Application objects and returns as responses
    - Validates project_control exists and belongs to tenant
    
    Args:
        session: Database session
        membership_ctx: Membership context
        project_control_id: ProjectControl ID
    
    Returns:
        List of ApplicationResponse objects
    
    Raises:
        HTTPException: 404 if project control not found
    """
    tenant_id = membership_ctx.tenant_id
    
    # Validate project_control exists
    project_control = await project_controls_repo.get_by_id(
        session,
        tenant_id=tenant_id,
        project_control_id=project_control_id,
        include_removed=False,
    )
    if not project_control:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project control not found",
        )
    
    # List active mappings only
    pca_list = await project_control_applications_repo.list_active_by_project_control(
        session,
        tenant_id=tenant_id,
        project_control_id=project_control_id,
    )
    
    # Fetch Application objects and convert to responses
    applications = []
    for pca in pca_list:
        application = await applications_repo.get_by_id(
            session,
            tenant_id=tenant_id,
            application_id=pca.application_id,
            include_deleted=False,
        )
        if application:
            applications.append(ApplicationResponse.model_validate(application))
    
    return applications

