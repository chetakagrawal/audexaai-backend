"""Service layer for Application version history."""

from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.tenancy import TenancyContext
from repos import entity_versions_repo
from repos import applications_repo


async def get_application_versions(
    session: AsyncSession,
    *,
    membership_ctx: TenancyContext,
    application_id: UUID,
) -> list[dict]:
    """
    Get all version snapshots for an application.
    
    Args:
        session: Database session
        membership_ctx: Tenancy context
        application_id: Application ID to fetch versions for
    
    Returns:
        List of version snapshots (dicts with version metadata and data)
    
    Raises:
        HTTPException: 404 if application not found
    """
    # Verify application exists and belongs to tenant
    application = await applications_repo.get_by_id(
        session,
        tenant_id=membership_ctx.tenant_id,
        application_id=application_id,
        include_deleted=True,  # Allow viewing history of deleted applications
    )
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )
    
    # Fetch versions
    versions = await entity_versions_repo.list_versions(
        session,
        tenant_id=membership_ctx.tenant_id,
        entity_type="applications",
        entity_id=application_id,
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


async def get_application_as_of(
    session: AsyncSession,
    *,
    membership_ctx: TenancyContext,
    application_id: UUID,
    as_of: datetime,
) -> dict:
    """
    Get application state as it existed at a specific point in time.
    
    This function:
    1. Checks if a version snapshot exists for the given time
    2. If found, returns the snapshot data
    3. If not found, returns the current application state (if it existed at that time)
    
    Args:
        session: Database session
        membership_ctx: Tenancy context
        application_id: Application ID
        as_of: Point in time to query
    
    Returns:
        Application data as dict (from snapshot or current state)
    
    Raises:
        HTTPException: 404 if application not found or didn't exist at that time
    """
    # Verify application exists and belongs to tenant
    application = await applications_repo.get_by_id(
        session,
        tenant_id=membership_ctx.tenant_id,
        application_id=application_id,
        include_deleted=True,
    )
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )
    
    # Check if application existed at the given time
    if application.created_at > as_of:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application did not exist at the specified time",
        )
    
    # Find the version snapshot that was valid at the given time
    # We look for versions where valid_from <= as_of < valid_to
    from sqlalchemy import select, and_
    from models.entity_version import EntityVersion
    
    version_query = (
        select(EntityVersion)
        .where(
            EntityVersion.tenant_id == membership_ctx.tenant_id,
            EntityVersion.entity_type == "applications",
            EntityVersion.entity_id == application_id,
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
    # (This handles the case where the application hasn't been updated since creation)
    if application.created_at <= as_of:
        # Convert application to dict
        from models.application import Application
        application_dict = {
            "id": application.id,
            "tenant_id": application.tenant_id,
            "name": application.name,
            "category": application.category,
            "scope_rationale": application.scope_rationale,
            "business_owner_membership_id": application.business_owner_membership_id,
            "it_owner_membership_id": application.it_owner_membership_id,
            "created_at": application.created_at,
            "created_by_membership_id": application.created_by_membership_id,
            "updated_at": application.updated_at,
            "updated_by_membership_id": application.updated_by_membership_id,
            "deleted_at": application.deleted_at,
            "deleted_by_membership_id": application.deleted_by_membership_id,
            "row_version": application.row_version,
        }
        return application_dict
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Application did not exist at the specified time",
    )

