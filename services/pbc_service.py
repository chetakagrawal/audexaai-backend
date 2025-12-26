"""Service layer for PBC requests v2 (business logic)."""

from datetime import date, datetime, UTC
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.tenancy import TenancyContext
from models.pbc_request import PbcRequest
from models.pbc_request_item import PbcRequestItem
from repos import (
    pbc_repo,
    projects_repo,
    project_controls_repo,
    controls_repo,
    applications_repo,
    test_attributes_repo,
)
from services.line_items_resolver import resolve_line_items, ResolvedLineItem


async def generate_pbc(
    session: AsyncSession,
    *,
    membership_ctx: TenancyContext,
    project_id: UUID,
    group_mode: str = "single_request",
    control_id: UUID | None = None,
    title: str | None = None,
    due_date: date | None = None,
    instructions: str | None = None,
    mode: str = "new",
) -> dict:
    """
    Generate PBC request(s) from project's resolved line items.
    
    Args:
        session: Database session
        membership_ctx: Tenancy context
        project_id: Project ID
        group_mode: How to group items ("single_request" only for now)
        control_id: Optional control ID to filter line items
        title: Optional title for the request (defaults to generated title)
        due_date: Optional due date
        instructions: Optional instructions
        mode: "new" (always create) or "replace_drafts" (soft delete existing drafts first)
    
    Returns:
        Dict with pbc_request_id and items_created count
    
    Raises:
        HTTPException: 404 if project not found
    """
    tenant_id = membership_ctx.tenant_id
    membership_id = membership_ctx.membership_id

    # Validate project exists
    project = await projects_repo.get_by_id(
        session,
        tenant_id=tenant_id,
        project_id=project_id,
        include_deleted=False,
    )
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Handle replace_drafts mode
    if mode == "replace_drafts":
        draft_requests = await pbc_repo.list_draft_requests_by_project(
            session,
            tenant_id=tenant_id,
            project_id=project_id,
        )
        now = datetime.now(UTC)
        for draft in draft_requests:
            draft.deleted_at = now
            draft.deleted_by_membership_id = membership_id
            draft.updated_at = now
            draft.updated_by_membership_id = membership_id
            draft.row_version += 1
            await pbc_repo.save_request(session, draft)

            # Also soft delete items
            items = await pbc_repo.list_items_by_request(
                session,
                tenant_id=tenant_id,
                pbc_request_id=draft.id,
                include_deleted=False,
            )
            for item in items:
                item.deleted_at = now
                item.deleted_by_membership_id = membership_id
                item.updated_at = now
                item.updated_by_membership_id = membership_id
                item.row_version += 1
                await pbc_repo.save_item(session, item)

    # Resolve line items
    resolved_items = await resolve_line_items(
        session,
        membership_ctx=membership_ctx,
        project_id=project_id,
        control_id=control_id,
    )

    if not resolved_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No line items found for this project" + (f" and control {control_id}" if control_id else ""),
        )

    # Generate title if not provided
    if not title:
        if control_id:
            # Use control name from first item
            control_name = resolved_items[0].control_name
            title = f"PBC Request - {control_name}"
        else:
            title = f"PBC Request - {project.name}"

    # Create PBC request
    now = datetime.now(UTC)
    pbc_request = PbcRequest(
        tenant_id=tenant_id,
        project_id=project_id,
        title=title,
        due_date=due_date,
        status="draft",
        instructions=instructions,
        created_at=now,
        created_by_membership_id=membership_id,
        row_version=1,
    )
    pbc_request = await pbc_repo.create_request(session, pbc_request)

    # Create items from resolved line items
    pbc_items = []
    for resolved_item in resolved_items:
        item = PbcRequestItem(
            tenant_id=tenant_id,
            project_id=project_id,
            pbc_request_id=pbc_request.id,
            project_control_id=resolved_item.project_control_id,
            application_id=resolved_item.application_id,
            test_attribute_id=resolved_item.test_attribute_id,
            # Snapshot fields
            pinned_control_version_num=resolved_item.pinned_control_version_num,
            pinned_test_attribute_version_num=resolved_item.pinned_test_attribute_version_num,
            effective_procedure_snapshot=resolved_item.effective_procedure,
            effective_evidence_snapshot=resolved_item.effective_evidence,
            source_snapshot=resolved_item.source,
            override_id_snapshot=resolved_item.override_id,
            # Workflow fields
            status="not_started",
            created_at=now,
            created_by_membership_id=membership_id,
            row_version=1,
        )
        pbc_items.append(item)

    # Bulk insert items
    await pbc_repo.bulk_create_items(session, pbc_items)

    await session.commit()
    await session.refresh(pbc_request)

    return {
        "pbc_request_id": pbc_request.id,
        "items_created": len(pbc_items),
    }


async def list_pbc_requests(
    session: AsyncSession,
    *,
    membership_ctx: TenancyContext,
    project_id: UUID,
) -> list[PbcRequest]:
    """
    List all PBC requests for a project.
    
    Args:
        session: Database session
        membership_ctx: Tenancy context
        project_id: Project ID
    
    Returns:
        List of PbcRequest instances
    
    Raises:
        HTTPException: 404 if project not found
    """
    tenant_id = membership_ctx.tenant_id

    # Validate project exists
    project = await projects_repo.get_by_id(
        session,
        tenant_id=tenant_id,
        project_id=project_id,
        include_deleted=False,
    )
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    return await pbc_repo.list_requests_by_project(
        session,
        tenant_id=tenant_id,
        project_id=project_id,
        include_deleted=False,
    )


async def get_pbc_request(
    session: AsyncSession,
    *,
    membership_ctx: TenancyContext,
    pbc_request_id: UUID,
) -> PbcRequest:
    """
    Get a PBC request by ID.
    
    Args:
        session: Database session
        membership_ctx: Tenancy context
        pbc_request_id: PBC request ID
    
    Returns:
        PbcRequest instance
    
    Raises:
        HTTPException: 404 if request not found
    """
    tenant_id = membership_ctx.tenant_id

    request = await pbc_repo.get_request_by_id(
        session,
        tenant_id=tenant_id,
        pbc_request_id=pbc_request_id,
        include_deleted=False,
    )
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PBC request not found",
        )

    return request


async def update_pbc_request(
    session: AsyncSession,
    *,
    membership_ctx: TenancyContext,
    pbc_request_id: UUID,
    title: str | None = None,
    due_date: date | None = None,
    status: str | None = None,
    instructions: str | None = None,
) -> PbcRequest:
    """
    Update PBC request metadata.
    
    Args:
        session: Database session
        membership_ctx: Tenancy context
        pbc_request_id: PBC request ID
        title: Optional new title
        due_date: Optional new due date
        status: Optional new status
        instructions: Optional new instructions
    
    Returns:
        Updated PbcRequest instance
    
    Raises:
        HTTPException: 404 if request not found
    """
    tenant_id = membership_ctx.tenant_id
    membership_id = membership_ctx.membership_id

    request = await pbc_repo.get_request_by_id(
        session,
        tenant_id=tenant_id,
        pbc_request_id=pbc_request_id,
        include_deleted=False,
    )
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PBC request not found",
        )

    now = datetime.now(UTC)
    if title is not None:
        request.title = title
    if due_date is not None:
        request.due_date = due_date
    if status is not None:
        request.status = status
    if instructions is not None:
        request.instructions = instructions

    request.updated_at = now
    request.updated_by_membership_id = membership_id
    request.row_version += 1

    await pbc_repo.save_request(session, request)
    await session.commit()
    await session.refresh(request)

    return request


async def create_pbc_request_item(
    session: AsyncSession,
    *,
    membership_ctx: TenancyContext,
    pbc_request_id: UUID,
    project_control_id: UUID | None = None,
    control_id: UUID | None = None,
    application_id: UUID | None = None,
    test_attribute_id: UUID | None = None,
    status: str = "not_started",
    assignee_membership_id: UUID | None = None,
    instructions_extra: str | None = None,
    notes: str | None = None,
) -> PbcRequestItem:
    """
    Create a new PBC request item with FK-based entity references.

    Args:
        session: Database session
        membership_ctx: Tenancy context
        pbc_request_id: Parent PBC request ID
        project_control_id: Project control ID (preferred)
        control_id: Control ID (alternative to project_control_id)
        application_id: Application ID
        test_attribute_id: Test attribute ID
        status: Workflow status
        assignee_membership_id: Assignee membership ID
        instructions_extra: Extra instructions
        notes: Notes

    Returns:
        Created PbcRequestItem instance

    Raises:
        HTTPException: 400 if validation fails, 404 if entities not found
    """
    tenant_id = membership_ctx.tenant_id
    membership_id = membership_ctx.membership_id

    # Validate PBC request exists and belongs to tenant
    pbc_request = await pbc_repo.get_request_by_id(
        session,
        tenant_id=tenant_id,
        pbc_request_id=pbc_request_id,
        include_deleted=False,
    )
    if not pbc_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PBC request not found",
        )

    # Validate at least one control reference is provided
    if not project_control_id and not control_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either project_control_id or control_id must be provided",
        )

    # Validate project_control_id if provided
    if project_control_id:
        project_control = await project_controls_repo.get_by_id(
            session,
            tenant_id=tenant_id,
            project_control_id=project_control_id,
            include_deleted=False,
        )
        if not project_control:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project control not found",
            )
        # Ensure project_control belongs to the same project as the PBC request
        if project_control.project_id != pbc_request.project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project control must belong to the same project as the PBC request",
            )

    # Validate control_id if provided
    if control_id:
        control = await controls_repo.get_by_id(
            session,
            tenant_id=tenant_id,
            control_id=control_id,
            include_deleted=False,
        )
        if not control:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Control not found",
            )

    # Validate application_id if provided
    if application_id:
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

    # Validate test_attribute_id if provided
    if test_attribute_id:
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
        # Ensure test_attribute belongs to the referenced control
        referenced_control_id = None
        if project_control_id:
            # Get control_id from project_control
            project_control = await project_controls_repo.get_by_id(
                session,
                tenant_id=tenant_id,
                project_control_id=project_control_id,
                include_deleted=False,
            )
            referenced_control_id = project_control.control_id
        elif control_id:
            referenced_control_id = control_id

        if referenced_control_id and test_attribute.control_id != referenced_control_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Test attribute must belong to the referenced control",
            )

    # Create the item
    now = datetime.now(UTC)
    item = PbcRequestItem(
        tenant_id=tenant_id,
        project_id=pbc_request.project_id,
        pbc_request_id=pbc_request_id,
        project_control_id=project_control_id,
        control_id=control_id,
        application_id=application_id,
        test_attribute_id=test_attribute_id,
        status=status,
        assignee_membership_id=assignee_membership_id,
        instructions_extra=instructions_extra,
        notes=notes,
        created_at=now,
        created_by_membership_id=membership_id,
        row_version=1,
    )

    item = await pbc_repo.create_item(session, item)
    await session.commit()
    await session.refresh(item)

    return item


async def update_pbc_request_item(
    session: AsyncSession,
    *,
    membership_ctx: TenancyContext,
    item_id: UUID,
    status: str | None = None,
    assignee_membership_id: UUID | None = None,
    instructions_extra: str | None = None,
    notes: str | None = None,
) -> PbcRequestItem:
    """
    Update PBC request item workflow fields.
    
    Args:
        session: Database session
        membership_ctx: Tenancy context
        item_id: Item ID
        status: Optional new status
        assignee_membership_id: Optional new assignee
        instructions_extra: Optional extra instructions
        notes: Optional notes
    
    Returns:
        Updated PbcRequestItem instance
    
    Raises:
        HTTPException: 404 if item not found
    """
    tenant_id = membership_ctx.tenant_id
    membership_id = membership_ctx.membership_id

    item = await pbc_repo.get_item_by_id(
        session,
        tenant_id=tenant_id,
        item_id=item_id,
        include_deleted=False,
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PBC request item not found",
        )

    now = datetime.now(UTC)
    if status is not None:
        item.status = status
    if assignee_membership_id is not None:
        item.assignee_membership_id = assignee_membership_id
    if instructions_extra is not None:
        item.instructions_extra = instructions_extra
    if notes is not None:
        item.notes = notes

    item.updated_at = now
    item.updated_by_membership_id = membership_id
    item.row_version += 1

    await pbc_repo.save_item(session, item)
    await session.commit()
    await session.refresh(item)

    return item

