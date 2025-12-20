"""Repository for ProjectControlApplication database operations (DB-only layer)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.project_control_application import ProjectControlApplication


async def get_active(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    project_control_id: UUID,
    application_id: UUID,
) -> ProjectControlApplication | None:
    """
    Get an active (non-removed) project-control-application mapping.
    
    Args:
        session: Database session
        tenant_id: Tenant ID to filter by
        project_control_id: ProjectControl ID
        application_id: Application ID
    
    Returns:
        ProjectControlApplication if active mapping exists, None otherwise
    """
    query = select(ProjectControlApplication).where(
        ProjectControlApplication.tenant_id == tenant_id,
        ProjectControlApplication.project_control_id == project_control_id,
        ProjectControlApplication.application_id == application_id,
        ProjectControlApplication.removed_at.is_(None),
    )
    
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def get_by_id(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    pca_id: UUID,
    include_removed: bool = False,
) -> ProjectControlApplication | None:
    """
    Get a project-control-application mapping by ID.
    
    Args:
        session: Database session
        tenant_id: Tenant ID to filter by
        pca_id: ProjectControlApplication ID to fetch
        include_removed: If True, include removed mappings
    
    Returns:
        ProjectControlApplication if found, None otherwise
    """
    query = select(ProjectControlApplication).where(
        ProjectControlApplication.id == pca_id,
        ProjectControlApplication.tenant_id == tenant_id,
    )
    
    if not include_removed:
        query = query.where(ProjectControlApplication.removed_at.is_(None))
    
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def list_by_project_control(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    project_control_id: UUID,
    include_removed: bool = False,
) -> list[ProjectControlApplication]:
    """
    List all project-control-application mappings for a project control.
    
    Args:
        session: Database session
        tenant_id: Tenant ID to filter by
        project_control_id: ProjectControl ID to filter by
        include_removed: If True, include removed mappings
    
    Returns:
        List of ProjectControlApplication mappings
    """
    query = select(ProjectControlApplication).where(
        ProjectControlApplication.tenant_id == tenant_id,
        ProjectControlApplication.project_control_id == project_control_id,
    )
    
    if not include_removed:
        query = query.where(ProjectControlApplication.removed_at.is_(None))
    
    result = await session.execute(query)
    return [pca for pca in result.scalars().all()]


async def create(session: AsyncSession, pca: ProjectControlApplication) -> ProjectControlApplication:
    """
    Create a new project-control-application mapping.
    
    Args:
        session: Database session
        pca: ProjectControlApplication instance to create
    
    Returns:
        Created ProjectControlApplication
    """
    session.add(pca)
    await session.flush()
    await session.refresh(pca)
    return pca


async def save(session: AsyncSession, pca: ProjectControlApplication) -> ProjectControlApplication:
    """
    Save (update) an existing project-control-application mapping.
    
    Args:
        session: Database session
        pca: ProjectControlApplication instance to save
    
    Returns:
        Updated ProjectControlApplication
    """
    await session.flush()
    await session.refresh(pca)
    return pca

