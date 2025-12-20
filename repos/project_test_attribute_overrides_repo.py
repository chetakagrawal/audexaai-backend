"""Repository for ProjectTestAttributeOverride database operations (DB-only layer)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.project_test_attribute_override import ProjectTestAttributeOverride


async def get_active_global(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    project_control_id: UUID,
    test_attribute_id: UUID,
) -> ProjectTestAttributeOverride | None:
    """
    Get an active global override (application_id IS NULL).
    
    Args:
        session: Database session
        tenant_id: Tenant ID to filter by
        project_control_id: ProjectControl ID
        test_attribute_id: TestAttribute ID
    
    Returns:
        ProjectTestAttributeOverride if found, None otherwise
    """
    query = select(ProjectTestAttributeOverride).where(
        ProjectTestAttributeOverride.tenant_id == tenant_id,
        ProjectTestAttributeOverride.project_control_id == project_control_id,
        ProjectTestAttributeOverride.test_attribute_id == test_attribute_id,
        ProjectTestAttributeOverride.application_id.is_(None),
        ProjectTestAttributeOverride.deleted_at.is_(None),
    )
    
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def get_active_app(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    project_control_id: UUID,
    application_id: UUID,
    test_attribute_id: UUID,
) -> ProjectTestAttributeOverride | None:
    """
    Get an active app-specific override (application_id IS NOT NULL).
    
    Args:
        session: Database session
        tenant_id: Tenant ID to filter by
        project_control_id: ProjectControl ID
        application_id: Application ID
        test_attribute_id: TestAttribute ID
    
    Returns:
        ProjectTestAttributeOverride if found, None otherwise
    """
    query = select(ProjectTestAttributeOverride).where(
        ProjectTestAttributeOverride.tenant_id == tenant_id,
        ProjectTestAttributeOverride.project_control_id == project_control_id,
        ProjectTestAttributeOverride.application_id == application_id,
        ProjectTestAttributeOverride.test_attribute_id == test_attribute_id,
        ProjectTestAttributeOverride.deleted_at.is_(None),
    )
    
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def get_by_id(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    override_id: UUID,
    include_deleted: bool = False,
) -> ProjectTestAttributeOverride | None:
    """
    Get a project test attribute override by ID.
    
    Args:
        session: Database session
        tenant_id: Tenant ID to filter by
        override_id: Override ID to fetch
        include_deleted: If True, include soft-deleted overrides
    
    Returns:
        ProjectTestAttributeOverride if found, None otherwise
    """
    query = select(ProjectTestAttributeOverride).where(
        ProjectTestAttributeOverride.id == override_id,
        ProjectTestAttributeOverride.tenant_id == tenant_id,
    )
    
    if not include_deleted:
        query = query.where(ProjectTestAttributeOverride.deleted_at.is_(None))
    
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def list_by_project_control(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    project_control_id: UUID,
    include_deleted: bool = False,
) -> list[ProjectTestAttributeOverride]:
    """
    List all overrides for a project control.
    
    Args:
        session: Database session
        tenant_id: Tenant ID to filter by
        project_control_id: ProjectControl ID to filter by
        include_deleted: If True, include soft-deleted overrides
    
    Returns:
        List of ProjectTestAttributeOverride instances
    """
    query = select(ProjectTestAttributeOverride).where(
        ProjectTestAttributeOverride.tenant_id == tenant_id,
        ProjectTestAttributeOverride.project_control_id == project_control_id,
    )
    
    if not include_deleted:
        query = query.where(ProjectTestAttributeOverride.deleted_at.is_(None))
    
    result = await session.execute(query)
    return list(result.scalars().all())


async def create(
    session: AsyncSession,
    override: ProjectTestAttributeOverride,
) -> ProjectTestAttributeOverride:
    """
    Create a new project test attribute override.
    
    Args:
        session: Database session
        override: ProjectTestAttributeOverride instance to create
    
    Returns:
        Created ProjectTestAttributeOverride
    """
    session.add(override)
    await session.flush()
    await session.refresh(override)
    return override


async def save(
    session: AsyncSession,
    override: ProjectTestAttributeOverride,
) -> ProjectTestAttributeOverride:
    """
    Save (update) an existing project test attribute override.
    
    Args:
        session: Database session
        override: ProjectTestAttributeOverride instance to save
    
    Returns:
        Updated ProjectTestAttributeOverride
    """
    await session.flush()
    await session.refresh(override)
    return override

