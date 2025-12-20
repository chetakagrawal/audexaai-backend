"""Service layer for project controls (business logic)."""

from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from models.project import Project
from models.control import Control
from models.project_control import ProjectControl
from repos import project_controls_repo, projects_repo, controls_repo


async def add_control_to_project(
    session: AsyncSession,
    *,
    membership_ctx,
    project_id: UUID,
    control_id: UUID,
    is_key_override: bool | None = None,
    frequency_override: str | None = None,
    notes: str | None = None,
) -> ProjectControl:
    """
    Add a control to a project with version freezing.
    
    Business rules:
    - Validates project exists and belongs to tenant
    - Validates control exists, belongs to tenant, and is not deleted
    - Freezes control version at current controls.row_version
    - Idempotent: returns existing active mapping if it exists
    
    Args:
        session: Database session
        membership_ctx: Membership context (tenant_id, membership_id)
        project_id: Project ID
        control_id: Control ID
        is_key_override: Optional override for is_key field
        frequency_override: Optional override for frequency field
        notes: Optional notes
    
    Returns:
        ProjectControl mapping
    
    Raises:
        HTTPException: 404 if project or control not found, 400 if validation fails
    """
    tenant_id = membership_ctx.tenant_id
    membership_id = membership_ctx.membership_id
    
    # 1. Validate project exists and belongs to tenant
    project = await projects_repo.get_by_id(
        session,
        tenant_id=tenant_id,
        project_id=project_id,
        include_deleted=False,
    )
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    # 2. Validate control exists, belongs to tenant, and is not deleted
    control = await controls_repo.get_by_id(
        session,
        tenant_id=tenant_id,
        control_id=control_id,
        include_deleted=False,
    )
    if not control:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Control not found",
        )
    
    # 3. Check if active mapping already exists (idempotent behavior)
    existing = await project_controls_repo.get_active(
        session,
        tenant_id=tenant_id,
        project_id=project_id,
        control_id=control_id,
    )
    if existing:
        # Idempotent: return existing mapping
        return existing
    
    # 4. Create new mapping with frozen version
    # KEY: Freeze control version at current controls.row_version
    pc = ProjectControl(
        tenant_id=tenant_id,
        project_id=project_id,
        control_id=control_id,
        control_version_num=control.row_version,  # VERSION FREEZING
        is_key_override=is_key_override,
        frequency_override=frequency_override,
        notes=notes,
        added_at=datetime.utcnow(),
        added_by_membership_id=membership_id,
        removed_at=None,
        removed_by_membership_id=None,
    )
    
    return await project_controls_repo.create(session, pc)


async def update_project_control_overrides(
    session: AsyncSession,
    *,
    membership_ctx,
    project_control_id: UUID,
    is_key_override: bool | None = None,
    frequency_override: str | None = None,
    notes: str | None = None,
) -> ProjectControl:
    """
    Update project-control override fields.
    
    Business rules:
    - Only updates override fields (is_key_override, frequency_override, notes)
    - Does NOT change control_id or control_version_num (immutable)
    - Does NOT change removed_at/removed_by
    
    Args:
        session: Database session
        membership_ctx: Membership context
        project_control_id: ProjectControl ID
        is_key_override: Optional override for is_key field
        frequency_override: Optional override for frequency field
        notes: Optional notes
    
    Returns:
        Updated ProjectControl
    
    Raises:
        HTTPException: 404 if project control not found
    """
    tenant_id = membership_ctx.tenant_id
    membership_id = membership_ctx.membership_id
    
    # Get existing mapping
    pc = await project_controls_repo.get_by_id(
        session,
        tenant_id=tenant_id,
        project_control_id=project_control_id,
        include_removed=False,
    )
    if not pc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project control not found",
        )
    
    # Update only override fields
    if is_key_override is not None:
        pc.is_key_override = is_key_override
    if frequency_override is not None:
        pc.frequency_override = frequency_override
    if notes is not None:
        pc.notes = notes
    
    pc.updated_at = datetime.utcnow()
    pc.updated_by_membership_id = membership_id
    
    return await project_controls_repo.save(session, pc)


async def remove_control_from_project(
    session: AsyncSession,
    *,
    membership_ctx,
    project_control_id: UUID,
) -> None:
    """
    Remove (soft delete) a control from a project.
    
    Business rules:
    - Soft delete: sets removed_at and removed_by_membership_id
    - Does NOT hard delete the row
    - Idempotent: removing twice is a no-op (no error)
    
    Args:
        session: Database session
        membership_ctx: Membership context
        project_control_id: ProjectControl ID
    
    Raises:
        HTTPException: 404 if project control not found
    """
    tenant_id = membership_ctx.tenant_id
    membership_id = membership_ctx.membership_id
    
    # Get existing mapping (include removed to make it idempotent)
    pc = await project_controls_repo.get_by_id(
        session,
        tenant_id=tenant_id,
        project_control_id=project_control_id,
        include_removed=True,
    )
    if not pc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project control not found",
        )
    
    # Idempotent: if already removed, do nothing
    if pc.removed_at is not None:
        return
    
    # Soft delete
    pc.removed_at = datetime.utcnow()
    pc.removed_by_membership_id = membership_id
    
    await project_controls_repo.save(session, pc)


async def list_project_controls(
    session: AsyncSession,
    *,
    membership_ctx,
    project_id: UUID,
) -> list[ProjectControl]:
    """
    List all active controls for a project.
    
    Args:
        session: Database session
        membership_ctx: Membership context
        project_id: Project ID
    
    Returns:
        List of active ProjectControl mappings
    
    Raises:
        HTTPException: 404 if project not found
    """
    tenant_id = membership_ctx.tenant_id
    
    # Validate project exists
    project = await projects_repo.get_by_id(
        session,
        tenant_id=tenant_id,
        project_id=project_id,
        include_deleted=False,
    )
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    # List active mappings only
    return await project_controls_repo.list_by_project(
        session,
        tenant_id=tenant_id,
        project_id=project_id,
        include_removed=False,
    )


async def get_project_control(
    session: AsyncSession,
    *,
    membership_ctx,
    project_control_id: UUID,
) -> ProjectControl:
    """
    Get a project-control mapping by ID.
    
    Args:
        session: Database session
        membership_ctx: Membership context
        project_control_id: ProjectControl ID
    
    Returns:
        ProjectControl mapping
    
    Raises:
        HTTPException: 404 if not found
    """
    tenant_id = membership_ctx.tenant_id
    
    pc = await project_controls_repo.get_by_id(
        session,
        tenant_id=tenant_id,
        project_control_id=project_control_id,
        include_removed=False,
    )
    if not pc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project control not found",
        )
    
    return pc

