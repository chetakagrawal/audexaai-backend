"""PBC requests v2 endpoints - manage PBC requests with line item snapshots."""

from datetime import date
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db, get_tenancy_context
from api.tenancy import TenancyContext
from models.pbc_request import PbcRequestResponse, PbcRequestUpdate
from models.pbc_request_item import PbcRequestItemCreate, PbcRequestItemResponse, PbcRequestItemUpdate
from models.user import User
from services.pbc_service import (
    create_pbc_request_item,
    generate_pbc,
    get_pbc_request,
    list_pbc_requests,
    update_pbc_request,
    update_pbc_request_item,
)

router = APIRouter()


class PbcGenerateRequest(BaseModel):
    """Schema for generating PBC requests."""

    mode: str = "new"  # "new" | "replace_drafts"
    group_mode: str = "single_request"  # "single_request" only for now
    control_id: UUID | None = None
    title: str | None = None
    due_date: date | None = None
    instructions: str | None = None


class PbcGenerateResponse(BaseModel):
    """Schema for PBC generation response."""

    pbc_request_id: UUID
    items_created: int


@router.post(
    "/projects/{project_id}/pbc/generate",
    response_model=PbcGenerateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_pbc_endpoint(
    project_id: UUID,
    payload: PbcGenerateRequest,
    current_user: User = Depends(get_current_user),
    tenancy: TenancyContext = Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate PBC request(s) from project's resolved line items.
    
    Args:
        project_id: Project ID
        payload: Generation parameters
    
    Returns:
        PBC request ID and items created count
    
    Raises:
        404 if project not found
        400 if no line items found
    """
    try:
        result = await generate_pbc(
            db,
            membership_ctx=tenancy,
            project_id=project_id,
            group_mode=payload.group_mode,
            control_id=payload.control_id,
            title=payload.title,
            due_date=payload.due_date,
            instructions=payload.instructions,
            mode=payload.mode,
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PBC request: {str(e)}",
        )


@router.get(
    "/projects/{project_id}/pbc",
    response_model=List[PbcRequestResponse],
)
async def list_pbc_requests_endpoint(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    tenancy: TenancyContext = Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    List all PBC requests for a project.
    
    Args:
        project_id: Project ID
    
    Returns:
        List of PBC requests
    
    Raises:
        404 if project not found
    """
    try:
        requests = await list_pbc_requests(
            db,
            membership_ctx=tenancy,
            project_id=project_id,
        )
        return requests
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list PBC requests: {str(e)}",
        )


@router.get(
    "/pbc/{pbc_request_id}",
    response_model=PbcRequestResponse,
)
async def get_pbc_request_endpoint(
    pbc_request_id: UUID,
    current_user: User = Depends(get_current_user),
    tenancy: TenancyContext = Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific PBC request by ID.
    
    Args:
        pbc_request_id: PBC request ID
    
    Returns:
        PBC request
    
    Raises:
        404 if request not found
    """
    try:
        request = await get_pbc_request(
            db,
            membership_ctx=tenancy,
            pbc_request_id=pbc_request_id,
        )
        return request
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch PBC request: {str(e)}",
        )


@router.get(
    "/pbc/{pbc_request_id}/items",
    response_model=List[PbcRequestItemResponse],
)
async def list_pbc_request_items_endpoint(
    pbc_request_id: UUID,
    current_user: User = Depends(get_current_user),
    tenancy: TenancyContext = Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    List all items for a PBC request.
    
    Args:
        pbc_request_id: PBC request ID
    
    Returns:
        List of PBC request items
    
    Raises:
        404 if request not found
    """
    try:
        from repos import pbc_repo

        # Verify request exists
        request = await get_pbc_request(
            db,
            membership_ctx=tenancy,
            pbc_request_id=pbc_request_id,
        )

        items = await pbc_repo.list_items_by_request(
            db,
            tenant_id=tenancy.tenant_id,
            pbc_request_id=pbc_request_id,
            include_deleted=False,
        )
        return items
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list PBC request items: {str(e)}",
        )


@router.post(
    "/pbc/{pbc_request_id}/items",
    response_model=PbcRequestItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_pbc_request_item_endpoint(
    pbc_request_id: UUID,
    payload: PbcRequestItemCreate,
    current_user: User = Depends(get_current_user),
    tenancy: TenancyContext = Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new PBC request item with FK-based entity references.

    Args:
        pbc_request_id: Parent PBC request ID
        payload: Item creation data with FKs

    Returns:
        Created PBC request item

    Raises:
        400 if validation fails (invalid FKs, cross-tenant, etc.)
        404 if referenced entities not found
    """
    try:
        item = await create_pbc_request_item(
            db,
            membership_ctx=tenancy,
            pbc_request_id=pbc_request_id,
            project_control_id=payload.project_control_id,
            control_id=payload.control_id,
            application_id=payload.application_id,
            test_attribute_id=payload.test_attribute_id,
            status=payload.status,
            assignee_membership_id=payload.assignee_membership_id,
            instructions_extra=payload.instructions_extra,
            notes=payload.notes,
        )
        return item
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create PBC request item: {str(e)}",
        )


@router.patch(
    "/pbc/{pbc_request_id}",
    response_model=PbcRequestResponse,
)
async def update_pbc_request_endpoint(
    pbc_request_id: UUID,
    payload: PbcRequestUpdate,
    current_user: User = Depends(get_current_user),
    tenancy: TenancyContext = Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Update PBC request metadata (title/due_date/status/instructions).
    
    Args:
        pbc_request_id: PBC request ID
        payload: Update fields
    
    Returns:
        Updated PBC request
    
    Raises:
        404 if request not found
    """
    try:
        request = await update_pbc_request(
            db,
            membership_ctx=tenancy,
            pbc_request_id=pbc_request_id,
            title=payload.title,
            due_date=payload.due_date,
            status=payload.status,
            instructions=payload.instructions,
        )
        return request
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update PBC request: {str(e)}",
        )


@router.patch(
    "/pbc/items/{item_id}",
    response_model=PbcRequestItemResponse,
)
async def update_pbc_request_item_endpoint(
    item_id: UUID,
    payload: PbcRequestItemUpdate,
    current_user: User = Depends(get_current_user),
    tenancy: TenancyContext = Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Update PBC request item workflow fields (status/assignee/instructions_extra/notes).
    
    Args:
        item_id: Item ID
        payload: Update fields
    
    Returns:
        Updated PBC request item
    
    Raises:
        404 if item not found
    """
    try:
        item = await update_pbc_request_item(
            db,
            membership_ctx=tenancy,
            item_id=item_id,
            status=payload.status,
            assignee_membership_id=payload.assignee_membership_id,
            instructions_extra=payload.instructions_extra,
            notes=payload.notes,
        )
        return item
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update PBC request item: {str(e)}",
        )

