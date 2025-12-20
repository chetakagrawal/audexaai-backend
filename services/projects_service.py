"""Service layer for Project business logic."""

from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.tenancy import TenancyContext
from models.project import Project, ProjectBase, ProjectUpdate
from repos import projects_repo


async def list_projects(
    session: AsyncSession,
    *,
    membership_ctx: TenancyContext,
    is_platform_admin: bool = False,
) -> list[Project]:
    """
    List all projects for a tenant.
    
    Args:
        session: Database session
        membership_ctx: Tenancy context
        is_platform_admin: If True, allow access to any tenant's projects
    
    Returns:
        List of projects
    """
    if is_platform_admin:
        # Platform admins can see all projects (would need a different query, but keeping simple for now)
        # For now, just use tenant scope
        projects = await projects_repo.list(
            session,
            tenant_id=membership_ctx.tenant_id,
            include_deleted=False,
        )
    else:
        projects = await projects_repo.list(
            session,
            tenant_id=membership_ctx.tenant_id,
            include_deleted=False,
        )
    
    return projects


async def get_project(
    session: AsyncSession,
    *,
    membership_ctx: TenancyContext,
    project_id: UUID,
    is_platform_admin: bool = False,
) -> Project:
    """
    Get a project by ID.
    
    Args:
        session: Database session
        membership_ctx: Tenancy context
        project_id: Project ID to fetch
        is_platform_admin: If True, allow access to any tenant's project
    
    Returns:
        Project if found
    
    Raises:
        HTTPException: 404 if project not found
    """
    project = await projects_repo.get_by_id(
        session,
        tenant_id=membership_ctx.tenant_id,
        project_id=project_id,
        include_deleted=False,
    )
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    return project


async def create_project(
    session: AsyncSession,
    *,
    membership_ctx: TenancyContext,
    payload: ProjectBase,
) -> Project:
    """
    Create a new project.
    
    Args:
        session: Database session
        membership_ctx: Tenancy context with membership_id, tenant_id, role
        payload: Project creation data
    
    Returns:
        Created project
    """
    # Create project instance
    project = Project(
        tenant_id=membership_ctx.tenant_id,
        created_by_membership_id=membership_ctx.membership_id,
        name=payload.name,
        status=payload.status,
        period_start=payload.period_start,
        period_end=payload.period_end,
        row_version=1,  # Start at version 1
    )
    
    # Create via repository
    created_project = await projects_repo.create(session, project)
    await session.commit()
    await session.refresh(created_project)
    
    return created_project


async def update_project(
    session: AsyncSession,
    *,
    membership_ctx: TenancyContext,
    project_id: UUID,
    payload: ProjectUpdate,
    is_platform_admin: bool = False,
) -> Project:
    """
    Update an existing project.
    
    Args:
        session: Database session
        membership_ctx: Tenancy context
        project_id: Project ID to update
        payload: Project update data (only provided fields will be updated)
        is_platform_admin: If True, allow access to any tenant's project
    
    Returns:
        Updated project
    
    Raises:
        HTTPException: 404 if project not found
    """
    # Get existing project
    project = await projects_repo.get_by_id(
        session,
        tenant_id=membership_ctx.tenant_id,
        project_id=project_id,
        include_deleted=False,
    )
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    # Update only provided fields
    if payload.name is not None:
        project.name = payload.name
    if payload.status is not None:
        project.status = payload.status
    if payload.period_start is not None:
        project.period_start = payload.period_start
    if payload.period_end is not None:
        project.period_end = payload.period_end
    
    # Update audit metadata (following the same pattern as controls/applications)
    project.updated_at = datetime.utcnow()
    project.updated_by_membership_id = membership_ctx.membership_id
    project.row_version += 1
    
    await session.commit()
    await session.refresh(project)
    
    return project

