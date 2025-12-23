"""Repository for PBC request database operations (DB-only layer)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.pbc_request import PbcRequest
from models.pbc_request_item import PbcRequestItem


async def get_request_by_id(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    pbc_request_id: UUID,
    include_deleted: bool = False,
) -> PbcRequest | None:
    """
    Get a PBC request by ID.
    
    Args:
        session: Database session
        tenant_id: Tenant ID to filter by
        pbc_request_id: PBC request ID to fetch
        include_deleted: If True, include soft-deleted requests
    
    Returns:
        PbcRequest if found, None otherwise
    """
    query = select(PbcRequest).where(
        PbcRequest.id == pbc_request_id,
        PbcRequest.tenant_id == tenant_id,
    )
    
    if not include_deleted:
        query = query.where(PbcRequest.deleted_at.is_(None))
    
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def list_requests_by_project(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    project_id: UUID,
    include_deleted: bool = False,
) -> list[PbcRequest]:
    """
    List all PBC requests for a project.
    
    Args:
        session: Database session
        tenant_id: Tenant ID to filter by
        project_id: Project ID to filter by
        include_deleted: If True, include soft-deleted requests
    
    Returns:
        List of PbcRequest instances
    """
    query = select(PbcRequest).where(
        PbcRequest.tenant_id == tenant_id,
        PbcRequest.project_id == project_id,
    )
    
    if not include_deleted:
        query = query.where(PbcRequest.deleted_at.is_(None))
    
    result = await session.execute(query)
    return list(result.scalars().all())


async def list_draft_requests_by_project(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    project_id: UUID,
) -> list[PbcRequest]:
    """
    List all draft PBC requests for a project (for replace_drafts mode).
    
    Args:
        session: Database session
        tenant_id: Tenant ID to filter by
        project_id: Project ID to filter by
    
    Returns:
        List of draft PbcRequest instances
    """
    query = select(PbcRequest).where(
        PbcRequest.tenant_id == tenant_id,
        PbcRequest.project_id == project_id,
        PbcRequest.status == "draft",
        PbcRequest.deleted_at.is_(None),
    )
    
    result = await session.execute(query)
    return list(result.scalars().all())


async def create_request(
    session: AsyncSession,
    request: PbcRequest,
) -> PbcRequest:
    """
    Create a new PBC request.
    
    Args:
        session: Database session
        request: PbcRequest instance to create
    
    Returns:
        Created PbcRequest
    """
    session.add(request)
    await session.flush()
    await session.refresh(request)
    return request


async def save_request(
    session: AsyncSession,
    request: PbcRequest,
) -> PbcRequest:
    """
    Save (update) an existing PBC request.
    
    Args:
        session: Database session
        request: PbcRequest instance to save
    
    Returns:
        Updated PbcRequest
    """
    await session.flush()
    await session.refresh(request)
    return request


async def bulk_create_items(
    session: AsyncSession,
    items: list[PbcRequestItem],
) -> list[PbcRequestItem]:
    """
    Bulk create PBC request items.
    
    Args:
        session: Database session
        items: List of PbcRequestItem instances to create
    
    Returns:
        List of created PbcRequestItem instances
    """
    session.add_all(items)
    await session.flush()
    for item in items:
        await session.refresh(item)
    return items


async def get_item_by_id(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    item_id: UUID,
    include_deleted: bool = False,
) -> PbcRequestItem | None:
    """
    Get a PBC request item by ID.
    
    Args:
        session: Database session
        tenant_id: Tenant ID to filter by
        item_id: Item ID to fetch
        include_deleted: If True, include soft-deleted items
    
    Returns:
        PbcRequestItem if found, None otherwise
    """
    query = select(PbcRequestItem).where(
        PbcRequestItem.id == item_id,
        PbcRequestItem.tenant_id == tenant_id,
    )
    
    if not include_deleted:
        query = query.where(PbcRequestItem.deleted_at.is_(None))
    
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def list_items_by_request(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    pbc_request_id: UUID,
    include_deleted: bool = False,
) -> list[PbcRequestItem]:
    """
    List all items for a PBC request.
    
    Args:
        session: Database session
        tenant_id: Tenant ID to filter by
        pbc_request_id: PBC request ID to filter by
        include_deleted: If True, include soft-deleted items
    
    Returns:
        List of PbcRequestItem instances
    """
    query = select(PbcRequestItem).where(
        PbcRequestItem.tenant_id == tenant_id,
        PbcRequestItem.pbc_request_id == pbc_request_id,
    )
    
    if not include_deleted:
        query = query.where(PbcRequestItem.deleted_at.is_(None))
    
    result = await session.execute(query)
    return list(result.scalars().all())


async def save_item(
    session: AsyncSession,
    item: PbcRequestItem,
) -> PbcRequestItem:
    """
    Save (update) an existing PBC request item.
    
    Args:
        session: Database session
        item: PbcRequestItem instance to save
    
    Returns:
        Updated PbcRequestItem
    """
    await session.flush()
    await session.refresh(item)
    return item

