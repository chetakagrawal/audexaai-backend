"""Repository for Application database operations."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.application import Application


async def get_by_id(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    application_id: UUID,
    include_deleted: bool = False,
) -> Application | None:
    """
    Get an application by ID.
    
    Args:
        session: Database session
        tenant_id: Tenant ID to filter by
        application_id: Application ID to fetch
        include_deleted: If True, include soft-deleted applications
    
    Returns:
        Application if found, None otherwise
    """
    query = select(Application).where(
        Application.id == application_id,
        Application.tenant_id == tenant_id,
    )
    
    if not include_deleted:
        # Filter out soft-deleted records
        query = query.where(Application.deleted_at.is_(None))
    
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def list(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    include_deleted: bool = False,
) -> list[Application]:
    """
    List all applications for a tenant.
    
    Args:
        session: Database session
        tenant_id: Tenant ID to filter by
        include_deleted: If True, include soft-deleted applications
    
    Returns:
        List of applications
    """
    query = select(Application).where(Application.tenant_id == tenant_id)
    
    if not include_deleted:
        # Filter out soft-deleted records
        query = query.where(Application.deleted_at.is_(None))
    
    result = await session.execute(query)
    return [application for application in result.scalars().all()]


async def create(session: AsyncSession, application: Application) -> Application:
    """
    Create a new application.
    
    Args:
        session: Database session
        application: Application instance to create
    
    Returns:
        Created application
    """
    session.add(application)
    await session.flush()
    await session.refresh(application)
    return application


async def save(session: AsyncSession, application: Application) -> Application:
    """
    Save (update) an existing application.
    
    Args:
        session: Database session
        application: Application instance to save
    
    Returns:
        Saved application
    """
    await session.flush()
    await session.refresh(application)
    return application

