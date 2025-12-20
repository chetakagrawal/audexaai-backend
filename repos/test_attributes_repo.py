"""Repository for TestAttribute database operations."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.test_attribute import TestAttribute


async def get_by_id(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    test_attribute_id: UUID,
    include_deleted: bool = False,
) -> TestAttribute | None:
    """
    Get a test attribute by ID.
    
    Args:
        session: Database session
        tenant_id: Tenant ID to filter by
        test_attribute_id: Test attribute ID to fetch
        include_deleted: If True, include soft-deleted test attributes
    
    Returns:
        TestAttribute if found, None otherwise
    """
    query = select(TestAttribute).where(
        TestAttribute.id == test_attribute_id,
        TestAttribute.tenant_id == tenant_id,
    )
    
    if not include_deleted:
        query = query.where(TestAttribute.deleted_at.is_(None))
    
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def list_by_control(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    control_id: UUID,
    include_deleted: bool = False,
) -> list[TestAttribute]:
    """
    List all test attributes for a control.
    
    Args:
        session: Database session
        tenant_id: Tenant ID to filter by
        control_id: Control ID to fetch test attributes for
        include_deleted: If True, include soft-deleted test attributes
    
    Returns:
        List of test attributes
    """
    query = select(TestAttribute).where(
        TestAttribute.tenant_id == tenant_id,
        TestAttribute.control_id == control_id,
    )
    
    if not include_deleted:
        query = query.where(TestAttribute.deleted_at.is_(None))
    
    result = await session.execute(query)
    return list(result.scalars().all())


async def create(session: AsyncSession, test_attribute: TestAttribute) -> TestAttribute:
    """
    Create a new test attribute.
    
    Args:
        session: Database session
        test_attribute: TestAttribute instance to create
    
    Returns:
        Created test attribute
    """
    session.add(test_attribute)
    await session.flush()
    await session.refresh(test_attribute)
    return test_attribute


async def save(session: AsyncSession, test_attribute: TestAttribute) -> TestAttribute:
    """
    Save (update) an existing test attribute.
    
    Args:
        session: Database session
        test_attribute: TestAttribute instance to save
    
    Returns:
        Saved test attribute
    """
    await session.flush()
    await session.refresh(test_attribute)
    return test_attribute

