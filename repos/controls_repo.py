"""Repository for Control database operations."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.control import Control


async def get_by_id(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    control_id: UUID,
    include_deleted: bool = False,
) -> Control | None:
    """
    Get a control by ID.
    
    Args:
        session: Database session
        tenant_id: Tenant ID to filter by
        control_id: Control ID to fetch
        include_deleted: If True, include soft-deleted controls
    
    Returns:
        Control if found, None otherwise
    """
    query = select(Control).where(
        Control.id == control_id,
        Control.tenant_id == tenant_id,
    )
    
    if not include_deleted:
        # Filter out soft-deleted records
        query = query.where(Control.deleted_at.is_(None))
    
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def list(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    include_deleted: bool = False,
) -> list[Control]:
    """
    List all controls for a tenant.
    
    Args:
        session: Database session
        tenant_id: Tenant ID to filter by
        include_deleted: If True, include soft-deleted controls
    
    Returns:
        List of controls
    """
    query = select(Control).where(Control.tenant_id == tenant_id)
    
    if not include_deleted:
        # Filter out soft-deleted records
        query = query.where(Control.deleted_at.is_(None))
    
    result = await session.execute(query)
    return [control for control in result.scalars().all()]


async def create(session: AsyncSession, control: Control) -> Control:
    """
    Create a new control.
    
    Args:
        session: Database session
        control: Control instance to create
    
    Returns:
        Created control
    """
    session.add(control)
    await session.flush()
    await session.refresh(control)
    return control

