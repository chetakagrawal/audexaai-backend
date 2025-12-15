"""Project applications endpoints - manage application mappings for projects."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db, get_tenancy_context
from models.application import Application
from models.project import Project
from models.project_application import (
    ProjectApplication,
    ProjectApplicationCreate,
    ProjectApplicationResponse,
)
from models.user import User

router = APIRouter()


@router.post(
    "/projects/{project_id}/applications",
    response_model=ProjectApplicationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def attach_application_to_project(
    project_id: UUID,
    application_data: ProjectApplicationCreate,
    current_user: User = Depends(get_current_user),
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Attach an application to a project.
    
    Creates a project_applications row linking the project to the application.
    Note: tenant_id and project_id are derived from context, not client input.
    """
    try:
        # Verify project exists and belongs to tenant
        project_query = select(Project).where(Project.id == project_id)
        if not current_user.is_platform_admin:
            project_query = project_query.where(Project.tenant_id == tenancy.tenant_id)
        
        result = await db.execute(project_query)
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )
        
        # Verify application exists and belongs to tenant
        application_query = select(Application).where(Application.id == application_data.application_id)
        if not current_user.is_platform_admin:
            application_query = application_query.where(Application.tenant_id == tenancy.tenant_id)
        
        result = await db.execute(application_query)
        application = result.scalar_one_or_none()
        
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found",
            )
        
        # Verify application belongs to same tenant as project
        if application.tenant_id != project.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Application must belong to the same tenant as the project",
            )
        
        # Check if mapping already exists
        existing_query = select(ProjectApplication).where(
            ProjectApplication.project_id == project_id,
            ProjectApplication.application_id == application_data.application_id,
        )
        if not current_user.is_platform_admin:
            existing_query = existing_query.where(
                ProjectApplication.tenant_id == tenancy.tenant_id
            )
        
        result = await db.execute(existing_query)
        existing = result.scalar_one_or_none()
        
        if existing:
            # Idempotent: return existing mapping
            return existing
        
        # Create new mapping
        project_application = ProjectApplication(
            tenant_id=tenancy.tenant_id,
            project_id=project_id,
            application_id=application_data.application_id,
        )
        
        db.add(project_application)
        await db.commit()
        await db.refresh(project_application)
        
        return project_application
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to attach application to project: {str(e)}",
        )


@router.get(
    "/projects/{project_id}/applications",
    response_model=List[ProjectApplicationResponse],
)
async def list_project_applications(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    List all applications attached to a project.
    
    Returns project-application mappings.
    """
    try:
        # Verify project exists and belongs to tenant
        project_query = select(Project).where(Project.id == project_id)
        if not current_user.is_platform_admin:
            project_query = project_query.where(Project.tenant_id == tenancy.tenant_id)
        
        result = await db.execute(project_query)
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )
        
        # List all applications for this project
        query = select(ProjectApplication).where(ProjectApplication.project_id == project_id)
        if not current_user.is_platform_admin:
            query = query.where(ProjectApplication.tenant_id == tenancy.tenant_id)
        
        result = await db.execute(query)
        project_applications = result.scalars().all()
        
        return project_applications
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list project applications: {str(e)}",
        )
