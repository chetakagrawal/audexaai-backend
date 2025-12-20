"""Repository for ProjectControl database operations (DB-only layer)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.project_control import ProjectControl


async def get_active(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    project_id: UUID,
    control_id: UUID,
) -> ProjectControl | None:
    """
    Get an active (non-removed) project-control mapping.
    
    Args:
        session: Database session
        tenant_id: Tenant ID to filter by
        project_id: Project ID
        control_id: Control ID
    
    Returns:
        ProjectControl if active mapping exists, None otherwise
    """
    query = select(ProjectControl).where(
        ProjectControl.tenant_id == tenant_id,
        ProjectControl.project_id == project_id,
        ProjectControl.control_id == control_id,
        ProjectControl.removed_at.is_(None),
    )
    
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def get_by_id(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    project_control_id: UUID,
    include_removed: bool = False,
) -> ProjectControl | None:
    """
    Get a project-control mapping by ID.
    
    Args:
        session: Database session
        tenant_id: Tenant ID to filter by
        project_control_id: ProjectControl ID to fetch
        include_removed: If True, include removed mappings
    
    Returns:
        ProjectControl if found, None otherwise
    """
    query = select(ProjectControl).where(
        ProjectControl.id == project_control_id,
        ProjectControl.tenant_id == tenant_id,
    )
    
    if not include_removed:
        query = query.where(ProjectControl.removed_at.is_(None))
    
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def list_by_project(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    project_id: UUID,
    include_removed: bool = False,
) -> list[ProjectControl]:
    """
    List all project-control mappings for a project.
    
    Args:
        session: Database session
        tenant_id: Tenant ID to filter by
        project_id: Project ID to filter by
        include_removed: If True, include removed mappings
    
    Returns:
        List of ProjectControl mappings
    """
    query = select(ProjectControl).where(
        ProjectControl.tenant_id == tenant_id,
        ProjectControl.project_id == project_id,
    )
    
    if not include_removed:
        query = query.where(ProjectControl.removed_at.is_(None))
    
    result = await session.execute(query)
    return [pc for pc in result.scalars().all()]


async def create(session: AsyncSession, pc: ProjectControl) -> ProjectControl:
    """
    Create a new project-control mapping.
    
    Args:
        session: Database session
        pc: ProjectControl instance to create
    
    Returns:
        Created ProjectControl
    """
    session.add(pc)
    await session.flush()
    await session.refresh(pc)
    return pc


async def save(session: AsyncSession, pc: ProjectControl) -> ProjectControl:
    """
    Save (update) an existing project-control mapping.
    
    Args:
        session: Database session
        pc: ProjectControl instance to save
    
    Returns:
        Updated ProjectControl
    """
    await session.flush()
    await session.refresh(pc)
    return pc

