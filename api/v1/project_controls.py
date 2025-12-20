"""Project controls endpoints - manage control mappings for projects."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db, get_tenancy_context
from models.project_control import (
    ProjectControlCreate,
    ProjectControlUpdate,
    ProjectControlResponse,
)
from services import project_controls_service

router = APIRouter()


@router.post(
    "/projects/{project_id}/controls",
    response_model=ProjectControlResponse,
    status_code=status.HTTP_201_CREATED,
)
async def attach_control_to_project(
    project_id: UUID,
    control_data: ProjectControlCreate,
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Attach a control to a project with version freezing.
    
    Creates a project_controls row linking the project to the control.
    Freezes the control version at the current controls.row_version.
    Idempotent: returns existing mapping if already attached.
    """
    result = await project_controls_service.add_control_to_project(
        db,
        membership_ctx=tenancy,
        project_id=project_id,
        control_id=control_data.control_id,
        is_key_override=control_data.is_key_override,
        frequency_override=control_data.frequency_override,
        notes=control_data.notes,
    )
    await db.commit()
    await db.refresh(result)
    return result


@router.get(
    "/projects/{project_id}/controls",
    response_model=List[ProjectControlResponse],
)
async def list_project_controls(
    project_id: UUID,
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    List all active controls attached to a project.
    
    Returns project-control mappings including override fields and frozen versions.
    """
    return await project_controls_service.list_project_controls(
        db,
        membership_ctx=tenancy,
        project_id=project_id,
    )


@router.get(
    "/project-controls/{project_control_id}",
    response_model=ProjectControlResponse,
)
async def get_project_control(
    project_control_id: UUID,
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific project-control mapping by ID.
    """
    return await project_controls_service.get_project_control(
        db,
        membership_ctx=tenancy,
        project_control_id=project_control_id,
    )


@router.patch(
    "/project-controls/{project_control_id}",
    response_model=ProjectControlResponse,
)
async def update_project_control_overrides(
    project_control_id: UUID,
    update_data: ProjectControlUpdate,
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Update project-control override fields.
    
    Only updates override fields (is_key_override, frequency_override, notes).
    Does NOT change control_id or control_version_num (immutable).
    """
    result = await project_controls_service.update_project_control_overrides(
        db,
        membership_ctx=tenancy,
        project_control_id=project_control_id,
        is_key_override=update_data.is_key_override,
        frequency_override=update_data.frequency_override,
        notes=update_data.notes,
    )
    await db.commit()
    await db.refresh(result)
    return result


@router.delete(
    "/project-controls/{project_control_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_project_control(
    project_control_id: UUID,
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Remove (soft delete) a control from a project.
    
    Sets removed_at and removed_by_membership_id.
    Idempotent: removing twice is a no-op.
    """
    await project_controls_service.remove_control_from_project(
        db,
        membership_ctx=tenancy,
        project_control_id=project_control_id,
    )
    await db.commit()
