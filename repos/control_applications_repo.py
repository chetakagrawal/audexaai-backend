"""Repository for ControlApplication database operations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.control_application import ControlApplication


async def list_active_by_control(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    control_id: UUID,
) -> list[ControlApplication]:
    """
    List all active control-application mappings for a control.
    
    Args:
        session: Database session
        tenant_id: Tenant ID to filter by
        control_id: Control ID to fetch mappings for
    
    Returns:
        List of active ControlApplication mappings (removed_at IS NULL)
    """
    query = select(ControlApplication).where(
        ControlApplication.tenant_id == tenant_id,
        ControlApplication.control_id == control_id,
        ControlApplication.removed_at.is_(None),  # Only active mappings
    )
    
    result = await session.execute(query)
    return [mapping for mapping in result.scalars().all()]


async def get_active(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    control_id: UUID,
    application_id: UUID,
) -> ControlApplication | None:
    """
    Get an active control-application mapping.
    
    Args:
        session: Database session
        tenant_id: Tenant ID to filter by
        control_id: Control ID
        application_id: Application ID
    
    Returns:
        Active ControlApplication mapping if found, None otherwise
    """
    query = select(ControlApplication).where(
        ControlApplication.tenant_id == tenant_id,
        ControlApplication.control_id == control_id,
        ControlApplication.application_id == application_id,
        ControlApplication.removed_at.is_(None),  # Only active mappings
    )
    
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def create(session: AsyncSession, mapping: ControlApplication) -> ControlApplication:
    """
    Create a new control-application mapping.
    
    Args:
        session: Database session
        mapping: ControlApplication instance to create
    
    Returns:
        Created ControlApplication mapping
    """
    session.add(mapping)
    await session.flush()
    await session.refresh(mapping)
    return mapping


async def soft_remove(
    session: AsyncSession,
    mapping: ControlApplication,
    *,
    removed_at: datetime,
    removed_by_membership_id: UUID,
) -> ControlApplication:
    """
    Soft remove a control-application mapping (set removed_at and removed_by_membership_id).
    
    Args:
        session: Database session
        mapping: ControlApplication instance to soft remove
        removed_at: Timestamp when removed
        removed_by_membership_id: Membership ID of user who removed it
    
    Returns:
        Updated ControlApplication mapping
    """
    mapping.removed_at = removed_at
    mapping.removed_by_membership_id = removed_by_membership_id
    await session.flush()
    await session.refresh(mapping)
    return mapping

