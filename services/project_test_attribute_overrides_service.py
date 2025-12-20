"""Service layer for project test attribute overrides (business logic)."""

from datetime import datetime, UTC
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.tenancy import TenancyContext
from models.project_test_attribute_override import (
    ProjectTestAttributeOverride,
    ProjectTestAttributeOverrideUpsert,
)
from repos import (
    project_test_attribute_overrides_repo,
    project_controls_repo,
    test_attributes_repo,
    project_control_applications_repo,
    applications_repo,
)


async def upsert_override(
    session: AsyncSession,
    *,
    membership_ctx: TenancyContext,
    project_control_id: UUID,
    test_attribute_id: UUID,
    payload: ProjectTestAttributeOverrideUpsert,
) -> ProjectTestAttributeOverride:
    """
    Create or update a project test attribute override.
    
    Business rules:
    - Validates project_control exists, tenant matches, not removed
    - Validates test_attribute exists, tenant matches, not deleted
    - Validates test_attribute.control_id matches project_control.control_id
    - If application_id provided, validates it's active in project_control_applications
    - If override exists, updates it; otherwise creates new one
    - On create: freezes base_test_attribute_version_num from test_attribute.row_version
    
    Args:
        session: Database session
        membership_ctx: Tenancy context
        project_control_id: ProjectControl ID
        test_attribute_id: TestAttribute ID
        payload: Override data (includes optional application_id)
    
    Returns:
        Created or updated ProjectTestAttributeOverride
    
    Raises:
        HTTPException: 404 if entities not found, 400 if validation fails
    """
    tenant_id = membership_ctx.tenant_id
    membership_id = membership_ctx.membership_id
    application_id = payload.application_id

    # 1. Validate project_control exists and belongs to tenant
    project_control = await project_controls_repo.get_by_id(
        session,
        tenant_id=tenant_id,
        project_control_id=project_control_id,
        include_removed=False,
    )
    if not project_control:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project control not found",
        )

    # 2. Validate test_attribute exists, belongs to tenant, not deleted
    test_attribute = await test_attributes_repo.get_by_id(
        session,
        tenant_id=tenant_id,
        test_attribute_id=test_attribute_id,
        include_deleted=False,
    )
    if not test_attribute:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test attribute not found",
        )

    # 3. Validate test_attribute.control_id matches project_control.control_id
    if test_attribute.control_id != project_control.control_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Test attribute does not belong to the same control as the project control",
        )

    # 4. If application_id provided, validate it's active in project_control_applications
    if application_id is not None:
        # Check application exists and belongs to tenant
        application = await applications_repo.get_by_id(
            session,
            tenant_id=tenant_id,
            application_id=application_id,
            include_deleted=False,
        )
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found",
            )

        # Check application is active in project_control_applications
        pca = await project_control_applications_repo.get_active(
            session,
            tenant_id=tenant_id,
            project_control_id=project_control_id,
            application_id=application_id,
        )
        if not pca:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Application is not active for this project control",
            )

    # 5. Check if override already exists
    if application_id is None:
        # Global override
        existing = await project_test_attribute_overrides_repo.get_active_global(
            session,
            tenant_id=tenant_id,
            project_control_id=project_control_id,
            test_attribute_id=test_attribute_id,
        )
    else:
        # App-specific override
        existing = await project_test_attribute_overrides_repo.get_active_app(
            session,
            tenant_id=tenant_id,
            project_control_id=project_control_id,
            application_id=application_id,
            test_attribute_id=test_attribute_id,
        )

    now = datetime.now(UTC)

    if existing:
        # Update existing override
        existing.name_override = payload.name_override
        existing.frequency_override = payload.frequency_override
        existing.procedure_override = payload.procedure_override
        existing.expected_evidence_override = payload.expected_evidence_override
        existing.notes = payload.notes
        existing.updated_at = now
        existing.updated_by_membership_id = membership_id
        existing.row_version += 1

        override = await project_test_attribute_overrides_repo.save(session, existing)
    else:
        # Create new override
        override = ProjectTestAttributeOverride(
            tenant_id=tenant_id,
            project_control_id=project_control_id,
            test_attribute_id=test_attribute_id,
            application_id=application_id,
            base_test_attribute_version_num=test_attribute.row_version,  # VERSION FREEZING
            name_override=payload.name_override,
            frequency_override=payload.frequency_override,
            procedure_override=payload.procedure_override,
            expected_evidence_override=payload.expected_evidence_override,
            notes=payload.notes,
            created_at=now,
            created_by_membership_id=membership_id,
            row_version=1,
        )
        override = await project_test_attribute_overrides_repo.create(session, override)

    await session.commit()
    await session.refresh(override)
    return override


async def delete_override(
    session: AsyncSession,
    *,
    membership_ctx: TenancyContext,
    override_id: UUID,
) -> None:
    """
    Delete (soft delete) a project test attribute override.
    
    Args:
        session: Database session
        membership_ctx: Tenancy context
        override_id: Override ID to delete
    
    Raises:
        HTTPException: 404 if override not found
    """
    tenant_id = membership_ctx.tenant_id
    membership_id = membership_ctx.membership_id

    # Get override
    override = await project_test_attribute_overrides_repo.get_by_id(
        session,
        tenant_id=tenant_id,
        override_id=override_id,
        include_deleted=False,
    )
    if not override:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Override not found",
        )

    # Soft delete
    now = datetime.now(UTC)
    override.deleted_at = now
    override.deleted_by_membership_id = membership_id
    override.updated_at = now
    override.updated_by_membership_id = membership_id
    override.row_version += 1

    await project_test_attribute_overrides_repo.save(session, override)
    await session.commit()


async def list_overrides_for_project_control(
    session: AsyncSession,
    *,
    membership_ctx: TenancyContext,
    project_control_id: UUID,
) -> list[ProjectTestAttributeOverride]:
    """
    List all active overrides for a project control.
    
    Args:
        session: Database session
        membership_ctx: Tenancy context
        project_control_id: ProjectControl ID
    
    Returns:
        List of active ProjectTestAttributeOverride instances
    
    Raises:
        HTTPException: 404 if project control not found
    """
    tenant_id = membership_ctx.tenant_id

    # Validate project_control exists
    project_control = await project_controls_repo.get_by_id(
        session,
        tenant_id=tenant_id,
        project_control_id=project_control_id,
        include_removed=False,
    )
    if not project_control:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project control not found",
        )

    return await project_test_attribute_overrides_repo.list_by_project_control(
        session,
        tenant_id=tenant_id,
        project_control_id=project_control_id,
        include_deleted=False,
    )


async def resolve_effective_test_attribute(
    session: AsyncSession,
    *,
    membership_ctx: TenancyContext,
    project_control_id: UUID,
    test_attribute_id: UUID,
    application_id: UUID | None = None,
) -> dict:
    """
    Resolve effective test attribute with precedence:
    1. App-specific override (if application_id provided)
    2. Global override (if no app-specific)
    3. Base test_attribute
    
    Args:
        session: Database session
        membership_ctx: Tenancy context
        project_control_id: ProjectControl ID
        test_attribute_id: TestAttribute ID
        application_id: Optional application ID for app-specific resolution
    
    Returns:
        Dict with merged test attribute fields and source metadata
    
    Raises:
        HTTPException: 404 if entities not found
    """
    tenant_id = membership_ctx.tenant_id

    # Validate project_control exists
    project_control = await project_controls_repo.get_by_id(
        session,
        tenant_id=tenant_id,
        project_control_id=project_control_id,
        include_removed=False,
    )
    if not project_control:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project control not found",
        )

    # Validate test_attribute exists
    test_attribute = await test_attributes_repo.get_by_id(
        session,
        tenant_id=tenant_id,
        test_attribute_id=test_attribute_id,
        include_deleted=False,
    )
    if not test_attribute:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test attribute not found",
        )

    # Precedence: app-specific > global > base
    override = None
    source = "base"

    if application_id is not None:
        # Try app-specific override first
        override = await project_test_attribute_overrides_repo.get_active_app(
            session,
            tenant_id=tenant_id,
            project_control_id=project_control_id,
            application_id=application_id,
            test_attribute_id=test_attribute_id,
        )
        if override:
            source = "project_app_override"

    # If no app-specific override, try global override
    if override is None:
        override = await project_test_attribute_overrides_repo.get_active_global(
            session,
            tenant_id=tenant_id,
            project_control_id=project_control_id,
            test_attribute_id=test_attribute_id,
        )
        if override:
            source = "project_global_override"

    # Build result
    if override:
        return {
            "test_attribute_id": test_attribute.id,
            "code": test_attribute.code,
            "name": override.name_override or test_attribute.name,
            "frequency": override.frequency_override or test_attribute.frequency,
            "test_procedure": override.procedure_override or test_attribute.test_procedure,
            "expected_evidence": override.expected_evidence_override or test_attribute.expected_evidence,
            "source": source,
            "override_id": override.id,
            "base_test_attribute_version_num": override.base_test_attribute_version_num,
        }
    else:
        return {
            "test_attribute_id": test_attribute.id,
            "code": test_attribute.code,
            "name": test_attribute.name,
            "frequency": test_attribute.frequency,
            "test_procedure": test_attribute.test_procedure,
            "expected_evidence": test_attribute.expected_evidence,
            "source": "base",
            "override_id": None,
            "base_test_attribute_version_num": test_attribute.row_version,
        }

