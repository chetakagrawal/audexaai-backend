"""Project endpoints with tenant isolation."""

from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db, get_tenancy_context
from api.tenancy import TenancyContext
from models.project import ProjectBase, ProjectResponse, ProjectUpdate
from models.user import User
from services.projects_service import create_project, get_project, list_projects, update_project
from services.projects_versions_service import get_project_as_of, get_project_versions

router = APIRouter()


@router.get("/projects", response_model=List[ProjectResponse])
async def list_projects_endpoint(
    current_user: User = Depends(get_current_user),
    tenancy: TenancyContext = Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    List projects in the current user's tenant.
    
    Returns:
        List of projects in the tenant.
    """
    try:
        projects = await list_projects(
            db,
            membership_ctx=tenancy,
            is_platform_admin=current_user.is_platform_admin,
        )
        return projects
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch projects: {str(e)}",
        )


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project_endpoint(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    tenancy: TenancyContext = Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific project by ID.
    
    Returns:
        Project if found and user has access.
    
    Raises:
        404 if project not found or user doesn't have access.
    """
    try:
        project = await get_project(
            db,
            membership_ctx=tenancy,
            project_id=project_id,
            is_platform_admin=current_user.is_platform_admin,
        )
        return project
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch project: {str(e)}",
        )


@router.post("/projects", response_model=ProjectResponse)
async def create_project_endpoint(
    project_data: ProjectBase,
    current_user: User = Depends(get_current_user),
    tenancy: TenancyContext = Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new project.
    
    Note: tenant_id in request is ignored - uses tenant from membership context.
    """
    try:
        project = await create_project(
            db,
            membership_ctx=tenancy,
            payload=project_data,
        )
        return project
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create project: {str(e)}",
        )


@router.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project_endpoint(
    project_id: UUID,
    project_data: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    tenancy: TenancyContext = Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Update an existing project.
    
    Only provided fields will be updated.
    """
    try:
        project = await update_project(
            db,
            membership_ctx=tenancy,
            project_id=project_id,
            payload=project_data,
            is_platform_admin=current_user.is_platform_admin,
        )
        return project
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update project: {str(e)}",
        )


@router.get("/projects/{project_id}/versions")
async def get_project_versions_endpoint(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    tenancy: TenancyContext = Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all version snapshots for a project.
    
    Returns:
        List of version snapshots with metadata and data.
    
    Raises:
        404 if project not found or user doesn't have access.
    """
    try:
        versions = await get_project_versions(
            db,
            membership_ctx=tenancy,
            project_id=project_id,
        )
        return versions
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch project versions: {str(e)}",
        )


@router.get("/projects/{project_id}/versions/as-of")
async def get_project_as_of_endpoint(
    project_id: UUID,
    as_of: datetime = Query(..., description="Point in time to query (ISO format datetime)"),
    current_user: User = Depends(get_current_user),
    tenancy: TenancyContext = Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Get project state as it existed at a specific point in time.
    
    Args:
        project_id: Project ID
        as_of: Point in time to query (ISO format datetime)
    
    Returns:
        Project data as dict (from snapshot or current state)
    
    Raises:
        404 if project not found, user doesn't have access, or project didn't exist at that time.
    """
    try:
        project_data = await get_project_as_of(
            db,
            membership_ctx=tenancy,
            project_id=project_id,
            as_of=as_of,
        )
        return project_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch project state: {str(e)}",
        )

