"""Service layer for Control version history."""

from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.tenancy import TenancyContext
from repos import entity_versions_repo
from repos import controls_repo


async def get_control_versions(
    session: AsyncSession,
    *,
    membership_ctx: TenancyContext,
    control_id: UUID,
) -> list[dict]:
    """
    Get all version snapshots for a control.
    
    Args:
        session: Database session
        membership_ctx: Tenancy context
        control_id: Control ID to fetch versions for
    
    Returns:
        List of version snapshots (dicts with version metadata and data)
    
    Raises:
        HTTPException: 404 if control not found
    """
    # Verify control exists and belongs to tenant
    control = await controls_repo.get_by_id(
        session,
        tenant_id=membership_ctx.tenant_id,
        control_id=control_id,
        include_deleted=True,  # Allow viewing history of deleted controls
    )
    
    if not control:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Control not found",
        )
    
    # Fetch versions
    versions = await entity_versions_repo.list_versions(
        session,
        tenant_id=membership_ctx.tenant_id,
        entity_type="controls",
        entity_id=control_id,
    )
    
    # Convert to dict format
    result = []
    for version in versions:
        result.append({
            "id": version.id,
            "version_num": version.version_num,
            "operation": version.operation,
            "valid_from": version.valid_from,
            "valid_to": version.valid_to,
            "changed_at": version.changed_at,
            "changed_by_membership_id": version.changed_by_membership_id,
            "data": version.data,
        })
    
    return result


async def get_control_as_of(
    session: AsyncSession,
    *,
    membership_ctx: TenancyContext,
    control_id: UUID,
    as_of: datetime,
) -> dict:
    """
    Get control state as it existed at a specific point in time.
    
    This function:
    1. Checks if a version snapshot exists for the given time
    2. If found, returns the snapshot data
    3. If not found, returns the current control state (if it existed at that time)
    
    Args:
        session: Database session
        membership_ctx: Tenancy context
        control_id: Control ID
        as_of: Point in time to query
    
    Returns:
        Control data as dict (from snapshot or current state)
    
    Raises:
        HTTPException: 404 if control not found or didn't exist at that time
    """
    # Verify control exists and belongs to tenant
    control = await controls_repo.get_by_id(
        session,
        tenant_id=membership_ctx.tenant_id,
        control_id=control_id,
        include_deleted=True,
    )
    
    if not control:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Control not found",
        )
    
    # Check if control existed at the given time
    if control.created_at > as_of:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Control did not exist at the specified time",
        )
    
    # Find the version snapshot that was valid at the given time
    # We look for versions where valid_from <= as_of < valid_to
    from sqlalchemy import select, and_
    from models.entity_version import EntityVersion
    
    version_query = (
        select(EntityVersion)
        .where(
            EntityVersion.tenant_id == membership_ctx.tenant_id,
            EntityVersion.entity_type == "controls",
            EntityVersion.entity_id == control_id,
            EntityVersion.valid_from <= as_of,
            EntityVersion.valid_to > as_of,
        )
        .order_by(EntityVersion.version_num.desc())
        .limit(1)
    )
    
    result = await session.execute(version_query)
    version = result.scalar_one_or_none()
    
    if version:
        # Return snapshot data
        return version.data
    
    # No snapshot found - return current state if it was valid at that time
    # (This handles the case where the control hasn't been updated since creation)
    if control.created_at <= as_of:
        # Convert control to dict
        from models.control import Control
        control_dict = {
            "id": control.id,
            "tenant_id": control.tenant_id,
            "created_by_membership_id": control.created_by_membership_id,
            "control_code": control.control_code,
            "name": control.name,
            "category": control.category,
            "risk_rating": control.risk_rating,
            "control_type": control.control_type,
            "frequency": control.frequency,
            "is_key": control.is_key,
            "is_automated": control.is_automated,
            "created_at": control.created_at,
            "updated_at": control.updated_at,
            "updated_by_membership_id": control.updated_by_membership_id,
            "deleted_at": control.deleted_at,
            "deleted_by_membership_id": control.deleted_by_membership_id,
            "row_version": control.row_version,
        }
        return control_dict
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Control did not exist at the specified time",
    )

