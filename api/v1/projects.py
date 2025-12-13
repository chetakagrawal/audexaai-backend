"""Project endpoints with tenant isolation."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db, get_tenancy_context
from models.project import Project, ProjectBase, ProjectResponse
from models.user import User

router = APIRouter()


@router.get("/projects", response_model=List[ProjectResponse])
async def list_projects(
    current_user: User = Depends(get_current_user),
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    List projects in the current user's tenant.
    
    Returns:
        List of projects in the tenant.
    """
    try:
        # Platform admins can see all projects
        if current_user.is_platform_admin:
            result = await db.execute(select(Project))
        else:
            # Regular users: filter by tenant_id
            result = await db.execute(
                select(Project).where(Project.tenant_id == tenancy.tenant_id)
            )
        
        projects = result.scalars().all()
        return projects
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch projects: {str(e)}",
        )


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    tenancy=Depends(get_tenancy_context),
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
        # Build query with tenant filtering
        query = select(Project).where(Project.id == project_id)
        
        if not current_user.is_platform_admin:
            # Regular users: must filter by tenant_id
            query = query.where(Project.tenant_id == tenancy.tenant_id)
        
        result = await db.execute(query)
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=404,
                detail="Project not found",
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
async def create_project(
    project_data: ProjectBase,
    current_user: User = Depends(get_current_user),
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new project.
    
    Note: tenant_id in request is ignored - uses tenant from membership context.
    """
    try:
        # Override tenant_id and created_by_membership_id from membership context (security: never trust client)
        project = Project(
            tenant_id=tenancy.tenant_id,
            created_by_membership_id=tenancy.membership_id,
            name=project_data.name,
            status=project_data.status,
            period_start=project_data.period_start,
            period_end=project_data.period_end,
        )
        
        db.add(project)
        await db.commit()
        await db.refresh(project)
        
        return project
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create project: {str(e)}",
        )

