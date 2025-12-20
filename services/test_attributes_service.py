"""Service layer for TestAttribute business logic."""

from datetime import datetime, UTC
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.tenancy import TenancyContext
from models.test_attribute import TestAttribute, TestAttributeCreate
from models.control import Control
from repos import test_attributes_repo
from repos import controls_repo


async def create_test_attribute(
    session: AsyncSession,
    *,
    membership_ctx: TenancyContext,
    control_id: UUID,
    payload: TestAttributeCreate,
) -> TestAttribute:
    """
    Create a new test attribute for a control.
    
    Args:
        session: Database session
        membership_ctx: Tenancy context with membership_id, tenant_id, role
        control_id: Control ID to create test attribute for
        payload: Test attribute creation data
    
    Returns:
        Created test attribute
    
    Raises:
        HTTPException: 404 if control not found or belongs to different tenant
    """
    # Verify control exists and belongs to tenant
    control = await controls_repo.get_by_id(
        session,
        tenant_id=membership_ctx.tenant_id,
        control_id=control_id,
        include_deleted=False,
    )
    
    if not control:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Control not found",
        )
    
    # Ensure membership_id is set (should always be present, but validate)
    if not membership_ctx.membership_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active membership. User must belong to a tenant.",
        )
    
    # Create test attribute instance
    test_attribute = TestAttribute(
        tenant_id=membership_ctx.tenant_id,
        control_id=control_id,
        code=payload.code,
        name=payload.name,
        frequency=payload.frequency,
        test_procedure=payload.test_procedure,
        expected_evidence=payload.expected_evidence,
        created_by_membership_id=membership_ctx.membership_id,
        row_version=1,
        # updated_at and updated_by_membership_id are None on creation (only set on updates)
    )
    
    # Create in database
    test_attribute = await test_attributes_repo.create(session, test_attribute)
    await session.commit()
    await session.refresh(test_attribute)
    
    return test_attribute


async def update_test_attribute(
    session: AsyncSession,
    *,
    membership_ctx: TenancyContext,
    test_attribute_id: UUID,
    payload: TestAttributeCreate,
) -> TestAttribute:
    """
    Update an existing test attribute.
    
    Args:
        session: Database session
        membership_ctx: Tenancy context with membership_id, tenant_id, role
        test_attribute_id: Test attribute ID to update
        payload: Test attribute update data
    
    Returns:
        Updated test attribute
    
    Raises:
        HTTPException: 404 if test attribute not found
    """
    # Get test attribute
    test_attribute = await test_attributes_repo.get_by_id(
        session,
        tenant_id=membership_ctx.tenant_id,
        test_attribute_id=test_attribute_id,
        include_deleted=False,
    )
    
    if not test_attribute:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test attribute not found",
        )
    
    # Update fields (tenant_id and control_id cannot be changed)
    test_attribute.code = payload.code
    test_attribute.name = payload.name
    test_attribute.frequency = payload.frequency
    test_attribute.test_procedure = payload.test_procedure
    test_attribute.expected_evidence = payload.expected_evidence
    
    # Update audit metadata
    now = datetime.now(UTC)
    test_attribute.updated_at = now
    test_attribute.updated_by_membership_id = membership_ctx.membership_id
    test_attribute.row_version += 1
    
    # Save changes
    test_attribute = await test_attributes_repo.save(session, test_attribute)
    await session.commit()
    await session.refresh(test_attribute)
    
    return test_attribute


async def delete_test_attribute(
    session: AsyncSession,
    *,
    membership_ctx: TenancyContext,
    test_attribute_id: UUID,
) -> None:
    """
    Delete (soft delete) a test attribute.
    
    Args:
        session: Database session
        membership_ctx: Tenancy context with membership_id, tenant_id, role
        test_attribute_id: Test attribute ID to delete
    
    Raises:
        HTTPException: 404 if test attribute not found or already deleted
    """
    # Get test attribute
    test_attribute = await test_attributes_repo.get_by_id(
        session,
        tenant_id=membership_ctx.tenant_id,
        test_attribute_id=test_attribute_id,
        include_deleted=False,
    )
    
    if not test_attribute:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test attribute not found",
        )
    
    # Check if already deleted
    if test_attribute.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test attribute not found",
        )
    
    # Soft delete
    now = datetime.now(UTC)
    test_attribute.deleted_at = now
    test_attribute.deleted_by_membership_id = membership_ctx.membership_id
    test_attribute.updated_at = now
    test_attribute.updated_by_membership_id = membership_ctx.membership_id
    test_attribute.row_version += 1
    
    # Save changes
    test_attribute = await test_attributes_repo.save(session, test_attribute)
    await session.commit()
    await session.refresh(test_attribute)


async def list_test_attributes_for_control(
    session: AsyncSession,
    *,
    membership_ctx: TenancyContext,
    control_id: UUID,
) -> list[TestAttribute]:
    """
    List all test attributes for a control.
    
    Args:
        session: Database session
        membership_ctx: Tenancy context with membership_id, tenant_id, role
        control_id: Control ID to fetch test attributes for
    
    Returns:
        List of test attributes
    
    Raises:
        HTTPException: 404 if control not found
    """
    # Verify control exists and belongs to tenant
    control = await controls_repo.get_by_id(
        session,
        tenant_id=membership_ctx.tenant_id,
        control_id=control_id,
        include_deleted=False,
    )
    
    if not control:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Control not found",
        )
    
    # List test attributes
    test_attributes = await test_attributes_repo.list_by_control(
        session,
        tenant_id=membership_ctx.tenant_id,
        control_id=control_id,
        include_deleted=False,
    )
    
    return test_attributes

