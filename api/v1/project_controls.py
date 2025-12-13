"""Project controls endpoints - manage control mappings for projects."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db, get_tenancy_context
from models.control import Control
from models.project import Project
from models.project_control import (
    ProjectControl,
    ProjectControlBase,
    ProjectControlCreate,
    ProjectControlResponse,
)
from models.user import User

router = APIRouter()


@router.post(
    "/projects/{project_id}/controls",
    response_model=ProjectControlResponse,
    status_code=status.HTTP_201_CREATED,
)
async def attach_control_to_project(
    project_id: UUID,
    control_data: ProjectControlCreate,
    current_user: User = Depends(get_current_user),
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Attach a control to a project with optional override fields.
    
    Creates a project_controls row linking the project to the control.
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
        
        # Verify control exists and belongs to tenant
        # Note: control_id comes from request body, but we validate it belongs to tenant
        control_query = select(Control).where(Control.id == control_data.control_id)
        if not current_user.is_platform_admin:
            control_query = control_query.where(Control.tenant_id == tenancy.tenant_id)
        
        result = await db.execute(control_query)
        control = result.scalar_one_or_none()
        
        if not control:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Control not found",
            )
        
        # Verify control belongs to same tenant as project
        if control.tenant_id != project.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Control must belong to the same tenant as the project",
            )
        
        # Check if mapping already exists
        existing_query = select(ProjectControl).where(
            ProjectControl.project_id == project_id,
            ProjectControl.control_id == control_data.control_id,
        )
        if not current_user.is_platform_admin:
            existing_query = existing_query.where(
                ProjectControl.tenant_id == tenancy.tenant_id
            )
        
        result = await db.execute(existing_query)
        existing = result.scalar_one_or_none()
        
        if existing:
            # Idempotent: return existing mapping
            return existing
        
        # Create new mapping
        project_control = ProjectControl(
            tenant_id=tenancy.tenant_id,
            project_id=project_id,
            control_id=control_data.control_id,
            is_key_override=control_data.is_key_override,
            frequency_override=control_data.frequency_override,
            notes=control_data.notes,
        )
        
        db.add(project_control)
        await db.commit()
        await db.refresh(project_control)
        
        return project_control
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to attach control to project: {str(e)}",
        )


@router.get(
    "/projects/{project_id}/controls",
    response_model=List[ProjectControlResponse],
)
async def list_project_controls(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    List all controls attached to a project.
    
    Returns project-control mappings including override fields.
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
        
        # List all controls for this project
        query = select(ProjectControl).where(ProjectControl.project_id == project_id)
        if not current_user.is_platform_admin:
            query = query.where(ProjectControl.tenant_id == tenancy.tenant_id)
        
        result = await db.execute(query)
        project_controls = result.scalars().all()
        
        return project_controls
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list project controls: {str(e)}",
        )

