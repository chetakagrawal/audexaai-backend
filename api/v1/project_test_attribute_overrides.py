"""Project test attribute overrides endpoints - manage project-level test attribute customizations."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db, get_tenancy_context
from api.tenancy import TenancyContext
from models.project_test_attribute_override import (
    ProjectTestAttributeOverrideUpsert,
    ProjectTestAttributeOverrideResponse,
    EffectiveTestAttributeResponse,
)
from models.user import User
from services.project_test_attribute_overrides_service import (
    upsert_override,
    delete_override,
    list_overrides_for_project_control,
    resolve_effective_test_attribute,
)

router = APIRouter()


@router.post(
    "/project-controls/{project_control_id}/test-attributes/{test_attribute_id}/override",
    response_model=ProjectTestAttributeOverrideResponse,
    status_code=status.HTTP_200_OK,
)
async def upsert_test_attribute_override(
    project_control_id: UUID,
    test_attribute_id: UUID,
    override_data: ProjectTestAttributeOverrideUpsert,
    current_user: User = Depends(get_current_user),
    tenancy: TenancyContext = Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Create or update a project-level test attribute override.
    
    This endpoint is idempotent - if an override already exists for the same scope,
    it will be updated; otherwise a new one will be created.
    
    Scope:
    - If application_id is NULL: applies to all apps for this project_control (global)
    - If application_id is set: applies only to that specific app (app-specific)
    
    Raises:
        404 if project_control, test_attribute, or application not found
        400 if validation fails (e.g., test_attribute not for same control)
    """
    return await upsert_override(
        db,
        membership_ctx=tenancy,
        project_control_id=project_control_id,
        test_attribute_id=test_attribute_id,
        payload=override_data,
    )


@router.delete(
    "/project-test-attribute-overrides/{override_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_test_attribute_override(
    override_id: UUID,
    current_user: User = Depends(get_current_user),
    tenancy: TenancyContext = Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete (soft delete) a project test attribute override.
    
    Raises:
        404 if override not found or user doesn't have access.
    """
    await delete_override(
        db,
        membership_ctx=tenancy,
        override_id=override_id,
    )


@router.get(
    "/project-controls/{project_control_id}/test-attributes/overrides",
    response_model=List[ProjectTestAttributeOverrideResponse],
)
async def list_project_control_test_attribute_overrides(
    project_control_id: UUID,
    current_user: User = Depends(get_current_user),
    tenancy: TenancyContext = Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    List all active test attribute overrides for a project control.
    
    Returns both global (application_id=NULL) and app-specific overrides.
    
    Raises:
        404 if project_control not found or user doesn't have access.
    """
    return await list_overrides_for_project_control(
        db,
        membership_ctx=tenancy,
        project_control_id=project_control_id,
    )


@router.get(
    "/project-controls/{project_control_id}/test-attributes/{test_attribute_id}/effective",
    response_model=EffectiveTestAttributeResponse,
)
async def get_effective_test_attribute(
    project_control_id: UUID,
    test_attribute_id: UUID,
    application_id: UUID | None = None,
    current_user: User = Depends(get_current_user),
    tenancy: TenancyContext = Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the effective (resolved) test attribute with overrides applied.
    
    Precedence:
    1. App-specific override (if application_id provided)
    2. Global override (if no app-specific)
    3. Base test_attribute
    
    Query params:
        application_id: Optional. If provided, resolves for that specific app.
    
    Returns:
        Merged test attribute with 'source' indicating which override was applied.
    
    Raises:
        404 if project_control or test_attribute not found.
    """
    return await resolve_effective_test_attribute(
        db,
        membership_ctx=tenancy,
        project_control_id=project_control_id,
        test_attribute_id=test_attribute_id,
        application_id=application_id,
    )

