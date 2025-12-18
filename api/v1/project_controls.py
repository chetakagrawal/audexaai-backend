"""Project controls endpoints - manage control mappings for projects."""

from typing import List
from uuid import UUID
from datetime import datetime

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
            # If soft-deleted, restore it
            if existing.deleted_at is not None:
                existing.deleted_at = None
                existing.deleted_by_membership_id = None
                existing.updated_at = datetime.utcnow()
                existing.updated_by_membership_id = tenancy.membership_id
                # Update override fields if provided
                if control_data.is_key_override is not None:
                    existing.is_key_override = control_data.is_key_override
                if control_data.frequency_override is not None:
                    existing.frequency_override = control_data.frequency_override
                if control_data.notes is not None:
                    existing.notes = control_data.notes
                await db.commit()
                await db.refresh(existing)
                return existing
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
            updated_by_membership_id=tenancy.membership_id,
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
        
        # List all controls for this project (excluding soft-deleted ones)
        query = select(ProjectControl).where(
            ProjectControl.project_id == project_id,
            ProjectControl.deleted_at.is_(None)  # Exclude soft-deleted records
        )
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


@router.post(
    "/projects/{project_id}/controls/bulk",
    response_model=List[ProjectControlResponse],
    status_code=status.HTTP_201_CREATED,
)
async def attach_controls_to_project_bulk(
    project_id: UUID,
    control_ids: List[UUID],
    current_user: User = Depends(get_current_user),
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Attach multiple controls to a project in bulk.
    
    Creates project_controls rows linking the project to each control.
    Skips controls that are already attached (idempotent).
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
        
        # Verify all controls exist and belong to tenant
        if control_ids:
            control_query = select(Control).where(Control.id.in_(control_ids))
            if not current_user.is_platform_admin:
                control_query = control_query.where(Control.tenant_id == tenancy.tenant_id)
            
            result = await db.execute(control_query)
            controls = result.scalars().all()
            
            # Check if all requested controls were found
            found_ids = {control.id for control in controls}
            missing_ids = set(control_ids) - found_ids
            if missing_ids:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Controls not found: {missing_ids}",
                )
            
            # Verify all controls belong to same tenant as project
            for control in controls:
                if control.tenant_id != project.tenant_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Control {control.id} must belong to the same tenant as the project",
                    )
        
        # Get existing project-control mappings to skip duplicates (excluding soft-deleted)
        existing_query = select(ProjectControl).where(
            ProjectControl.project_id == project_id,
            ProjectControl.deleted_at.is_(None)  # Exclude soft-deleted records
        )
        if control_ids:
            existing_query = existing_query.where(
                ProjectControl.control_id.in_(control_ids)
            )
        if not current_user.is_platform_admin:
            existing_query = existing_query.where(
                ProjectControl.tenant_id == tenancy.tenant_id
            )
        
        result = await db.execute(existing_query)
        existing_mappings = result.scalars().all()
        existing_control_ids = {mapping.control_id for mapping in existing_mappings}
        
        # Create new mappings for controls that don't already exist
        created_mappings = list(existing_mappings)  # Start with existing ones
        for control_id in control_ids:
            if control_id not in existing_control_ids:
                project_control = ProjectControl(
                    tenant_id=tenancy.tenant_id,
                    project_id=project_id,
                    control_id=control_id,
                    is_key_override=None,
                    frequency_override=None,
                    notes=None,
                    updated_by_membership_id=tenancy.membership_id,
                )
                db.add(project_control)
                created_mappings.append(project_control)
        
        await db.commit()
        
        # Refresh all created mappings
        for mapping in created_mappings:
            await db.refresh(mapping)
        
        return created_mappings
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to attach controls to project: {str(e)}",
        )


@router.delete(
    "/projects/{project_id}/controls/{project_control_id}",
    response_model=ProjectControlResponse,
)
async def delete_project_control(
    project_id: UUID,
    project_control_id: UUID,
    current_user: User = Depends(get_current_user),
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Soft delete a project control (mark as deleted, don't actually delete).
    
    Sets deleted_at and deleted_by_membership_id to track who deleted it and when.
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
        
        # Get the project control
        query = select(ProjectControl).where(
            ProjectControl.id == project_control_id,
            ProjectControl.project_id == project_id,
        )
        if not current_user.is_platform_admin:
            query = query.where(ProjectControl.tenant_id == tenancy.tenant_id)
        
        result = await db.execute(query)
        project_control = result.scalar_one_or_none()
        
        if not project_control:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project control not found",
            )
        
        # Check if already deleted
        if project_control.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project control is already deleted",
            )
        
        # Soft delete: set deleted_at and deleted_by_membership_id
        project_control.deleted_at = datetime.utcnow()
        project_control.deleted_by_membership_id = tenancy.membership_id
        
        await db.commit()
        await db.refresh(project_control)
        
        return project_control
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete project control: {str(e)}",
        )
