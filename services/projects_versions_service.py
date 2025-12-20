"""Service layer for Project version history."""

from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.tenancy import TenancyContext
from models.entity_version import EntityVersion
from repos import entity_versions_repo, projects_repo


async def get_project_versions(
    session: AsyncSession,
    *,
    membership_ctx: TenancyContext,
    project_id: UUID,
) -> list[dict]:
    """
    Get all version snapshots for a project.
    
    Args:
        session: Database session
        membership_ctx: Tenancy context
        project_id: Project ID to fetch versions for
    
    Returns:
        List of version snapshots (dicts with version metadata and data)
    
    Raises:
        HTTPException: 404 if project not found
    """
    # Verify project exists and belongs to tenant
    project = await projects_repo.get_by_id(
        session,
        tenant_id=membership_ctx.tenant_id,
        project_id=project_id,
        include_deleted=True,  # Allow viewing history of deleted projects
    )
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    # Fetch versions
    versions = await entity_versions_repo.list_versions(
        session,
        tenant_id=membership_ctx.tenant_id,
        entity_type="projects",
        entity_id=project_id,
    )
    
    # Convert to dict format
    result = []
    for version in versions:
        result.append({
            "id": version.id,
            "version_num": version.version_num,
            "operation": version.operation,
            "valid_from": version.valid_from,
            "valid_to": version.valid_to,
            "changed_at": version.changed_at,
            "changed_by_membership_id": version.changed_by_membership_id,
            "data": version.data,
        })
    
    return result


async def get_project_as_of(
    session: AsyncSession,
    *,
    membership_ctx: TenancyContext,
    project_id: UUID,
    as_of: datetime,
) -> dict:
    """
    Get project state as it existed at a specific point in time.
    
    This function:
    1. Checks if a version snapshot exists for the given time
    2. If found, returns the snapshot data
    3. If not found, returns the current project state (if it existed at that time)
    
    Args:
        session: Database session
        membership_ctx: Tenancy context
        project_id: Project ID
        as_of: Point in time to query
    
    Returns:
        Project data as dict (from snapshot or current state)
    
    Raises:
        HTTPException: 404 if project not found or didn't exist at that time
    """
    # Verify project exists and belongs to tenant
    project = await projects_repo.get_by_id(
        session,
        tenant_id=membership_ctx.tenant_id,
        project_id=project_id,
        include_deleted=True,
    )
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    # Check if project existed at the given time
    if project.created_at > as_of:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project did not exist at the specified time",
        )
    
    # Find the version snapshot that was valid at the given time
    # We look for versions where valid_from <= as_of < valid_to
    version_query = (
        select(EntityVersion)
        .where(
            EntityVersion.tenant_id == membership_ctx.tenant_id,
            EntityVersion.entity_type == "projects",
            EntityVersion.entity_id == project_id,
            EntityVersion.valid_from <= as_of,
            EntityVersion.valid_to > as_of,
        )
        .order_by(EntityVersion.version_num.desc())
        .limit(1)
    )
    
    result = await session.execute(version_query)
    version = result.scalar_one_or_none()
    
    if version:
        # Return snapshot data
        return version.data
    
    # No snapshot found - return current state if it was valid at that time
    # (This handles the case where the project hasn't been updated since creation)
    if project.created_at <= as_of:
        # Convert project to dict (dates will serialize properly via Pydantic/JSON)
        project_dict = {
            "id": project.id,
            "tenant_id": project.tenant_id,
            "created_by_membership_id": project.created_by_membership_id,
            "name": project.name,
            "status": project.status,
            "period_start": project.period_start,
            "period_end": project.period_end,
            "created_at": project.created_at,
            "updated_at": project.updated_at,
            "updated_by_membership_id": project.updated_by_membership_id,
            "deleted_at": project.deleted_at,
            "deleted_by_membership_id": project.deleted_by_membership_id,
            "row_version": project.row_version,
        }
        return project_dict
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Project did not exist at the specified time",
    )

