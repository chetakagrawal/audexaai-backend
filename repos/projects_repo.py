"""Repository for Project database operations."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.project import Project


async def get_by_id(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    project_id: UUID,
    include_deleted: bool = False,
) -> Project | None:
    """
    Get a project by ID.
    
    Args:
        session: Database session
        tenant_id: Tenant ID to filter by
        project_id: Project ID to fetch
        include_deleted: If True, include soft-deleted projects
    
    Returns:
        Project if found, None otherwise
    """
    query = select(Project).where(
        Project.id == project_id,
        Project.tenant_id == tenant_id,
    )
    
    if not include_deleted:
        # Filter out soft-deleted records
        query = query.where(Project.deleted_at.is_(None))
    
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def list(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    include_deleted: bool = False,
) -> list[Project]:
    """
    List all projects for a tenant.
    
    Args:
        session: Database session
        tenant_id: Tenant ID to filter by
        include_deleted: If True, include soft-deleted projects
    
    Returns:
        List of projects
    """
    query = select(Project).where(Project.tenant_id == tenant_id)
    
    if not include_deleted:
        # Filter out soft-deleted records
        query = query.where(Project.deleted_at.is_(None))
    
    result = await session.execute(query)
    return [project for project in result.scalars().all()]


async def create(session: AsyncSession, project: Project) -> Project:
    """
    Create a new project.
    
    Args:
        session: Database session
        project: Project instance to create
    
    Returns:
        Created project
    """
    session.add(project)
    await session.flush()
    await session.refresh(project)
    return project

