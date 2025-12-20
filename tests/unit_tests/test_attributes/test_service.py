"""Unit tests for test_attributes service layer.

These tests verify business logic, tenant scoping, and control validation.
"""

from datetime import datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.tenancy import TenancyContext
from models.test_attribute import TestAttribute, TestAttributeCreate
from models.control import Control
from models.tenant import Tenant
from models.user import User
from models.user_tenant import UserTenant
from services.test_attributes_service import (
    create_test_attribute,
    update_test_attribute,
    delete_test_attribute,
    list_test_attributes_for_control,
)


@pytest.mark.asyncio
async def test_service_create_test_attribute_sets_tenant_and_control(db_session: AsyncSession):
    """Test: Creating a test attribute sets tenant_id and control_id correctly."""
    # Setup
    tenant = Tenant(id=uuid4(), name="Test Tenant", slug="test-tenant", status="active")
    db_session.add(tenant)
    await db_session.flush()
    
    user = User(
        id=uuid4(),
        primary_email="user@example.com",
        name="Test User",
        is_platform_admin=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    
    membership = UserTenant(
        id=uuid4(),
        user_id=user.id,
        tenant_id=tenant.id,
        role="admin",
        is_default=True,
    )
    db_session.add(membership)
    await db_session.flush()
    
    control = Control(
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-001",
        name="Test Control",
        row_version=1,
    )
    db_session.add(control)
    await db_session.commit()
    
    membership_ctx = TenancyContext(
        membership_id=membership.id,
        tenant_id=tenant.id,
        role="admin",
    )
    
    # Create test attribute
    payload = TestAttributeCreate(
        code="TA-001",
        name="Test Attribute",
        frequency="Monthly",
    )
    
    test_attribute = await create_test_attribute(
        db_session,
        membership_ctx=membership_ctx,
        control_id=control.id,
        payload=payload,
    )
    
    assert test_attribute.tenant_id == tenant.id
    assert test_attribute.control_id == control.id
    assert test_attribute.code == "TA-001"
    assert test_attribute.name == "Test Attribute"


@pytest.mark.asyncio
async def test_service_create_test_attribute_rejects_different_tenant_control(db_session: AsyncSession):
    """Test: Cannot create test attribute for control from different tenant."""
    # Setup two tenants
    tenant_a = Tenant(id=uuid4(), name="Tenant A", slug="tenant-a", status="active")
    tenant_b = Tenant(id=uuid4(), name="Tenant B", slug="tenant-b", status="active")
    db_session.add(tenant_a)
    db_session.add(tenant_b)
    await db_session.flush()
    
    user_a = User(
        id=uuid4(),
        primary_email="user-a@example.com",
        name="User A",
        is_platform_admin=False,
        is_active=True,
    )
    user_b = User(
        id=uuid4(),
        primary_email="user-b@example.com",
        name="User B",
        is_platform_admin=False,
        is_active=True,
    )
    db_session.add(user_a)
    db_session.add(user_b)
    await db_session.flush()
    
    membership_a = UserTenant(
        id=uuid4(),
        user_id=user_a.id,
        tenant_id=tenant_a.id,
        role="admin",
        is_default=True,
    )
    membership_b = UserTenant(
        id=uuid4(),
        user_id=user_b.id,
        tenant_id=tenant_b.id,
        role="admin",
        is_default=True,
    )
    db_session.add(membership_a)
    db_session.add(membership_b)
    await db_session.flush()
    
    # Create control in tenant_b
    control = Control(
        tenant_id=tenant_b.id,
        created_by_membership_id=membership_b.id,
        control_code="AC-002",
        name="Test Control",
        row_version=1,
    )
    db_session.add(control)
    await db_session.commit()
    
    # Try to create test attribute with tenant_a membership
    membership_ctx_a = TenancyContext(
        membership_id=membership_a.id,
        tenant_id=tenant_a.id,
        role="admin",
    )
    
    payload = TestAttributeCreate(
        code="TA-002",
        name="Test Attribute",
    )
    
    # Should raise 404 - control not found in tenant_a
    with pytest.raises(HTTPException) as exc_info:
        await create_test_attribute(
            db_session,
            membership_ctx=membership_ctx_a,
            control_id=control.id,
            payload=payload,
        )
    
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_service_update_test_attribute(db_session: AsyncSession):
    """Test: Updating a test attribute works."""
    # Setup
    tenant = Tenant(id=uuid4(), name="Test Tenant", slug="test-tenant", status="active")
    db_session.add(tenant)
    await db_session.flush()
    
    user = User(
        id=uuid4(),
        primary_email="user@example.com",
        name="Test User",
        is_platform_admin=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    
    membership = UserTenant(
        id=uuid4(),
        user_id=user.id,
        tenant_id=tenant.id,
        role="admin",
        is_default=True,
    )
    db_session.add(membership)
    await db_session.flush()
    
    control = Control(
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-003",
        name="Test Control",
        row_version=1,
    )
    db_session.add(control)
    await db_session.flush()
    
    test_attribute = TestAttribute(
        tenant_id=tenant.id,
        control_id=control.id,
        code="TA-003",
        name="Original Name",
    )
    db_session.add(test_attribute)
    await db_session.commit()
    
    membership_ctx = TenancyContext(
        membership_id=membership.id,
        tenant_id=tenant.id,
        role="admin",
    )
    
    # Update test attribute
    payload = TestAttributeCreate(
        code="TA-003-UPDATED",
        name="Updated Name",
        frequency="Quarterly",
    )
    
    updated = await update_test_attribute(
        db_session,
        membership_ctx=membership_ctx,
        test_attribute_id=test_attribute.id,
        payload=payload,
    )
    
    assert updated.code == "TA-003-UPDATED"
    assert updated.name == "Updated Name"
    assert updated.frequency == "Quarterly"


@pytest.mark.asyncio
async def test_service_delete_test_attribute(db_session: AsyncSession):
    """Test: Deleting a test attribute works."""
    # Setup
    tenant = Tenant(id=uuid4(), name="Test Tenant", slug="test-tenant", status="active")
    db_session.add(tenant)
    await db_session.flush()
    
    user = User(
        id=uuid4(),
        primary_email="user@example.com",
        name="Test User",
        is_platform_admin=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    
    membership = UserTenant(
        id=uuid4(),
        user_id=user.id,
        tenant_id=tenant.id,
        role="admin",
        is_default=True,
    )
    db_session.add(membership)
    await db_session.flush()
    
    control = Control(
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-004",
        name="Test Control",
        row_version=1,
    )
    db_session.add(control)
    await db_session.flush()
    
    test_attribute = TestAttribute(
        tenant_id=tenant.id,
        control_id=control.id,
        code="TA-004",
        name="Test Attribute",
    )
    db_session.add(test_attribute)
    await db_session.commit()
    
    membership_ctx = TenancyContext(
        membership_id=membership.id,
        tenant_id=tenant.id,
        role="admin",
    )
    
    # Delete test attribute
    await delete_test_attribute(
        db_session,
        membership_ctx=membership_ctx,
        test_attribute_id=test_attribute.id,
    )
    
    # Verify it's deleted (hard delete for now, will be soft delete in SUB-STAGE B)
    from repos import test_attributes_repo
    deleted = await test_attributes_repo.get_by_id(
        db_session,
        tenant_id=tenant.id,
        test_attribute_id=test_attribute.id,
        include_deleted=False,
    )
    assert deleted is None


@pytest.mark.asyncio
async def test_service_list_test_attributes_for_control(db_session: AsyncSession):
    """Test: Listing test attributes for a control works."""
    # Setup
    tenant = Tenant(id=uuid4(), name="Test Tenant", slug="test-tenant", status="active")
    db_session.add(tenant)
    await db_session.flush()
    
    user = User(
        id=uuid4(),
        primary_email="user@example.com",
        name="Test User",
        is_platform_admin=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    
    membership = UserTenant(
        id=uuid4(),
        user_id=user.id,
        tenant_id=tenant.id,
        role="admin",
        is_default=True,
    )
    db_session.add(membership)
    await db_session.flush()
    
    control = Control(
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-005",
        name="Test Control",
        row_version=1,
    )
    db_session.add(control)
    await db_session.flush()
    
    # Create test attributes
    ta1 = TestAttribute(
        tenant_id=tenant.id,
        control_id=control.id,
        code="TA-005-1",
        name="Test Attribute 1",
    )
    ta2 = TestAttribute(
        tenant_id=tenant.id,
        control_id=control.id,
        code="TA-005-2",
        name="Test Attribute 2",
    )
    db_session.add(ta1)
    db_session.add(ta2)
    await db_session.commit()
    
    membership_ctx = TenancyContext(
        membership_id=membership.id,
        tenant_id=tenant.id,
        role="admin",
    )
    
    # List test attributes
    test_attributes = await list_test_attributes_for_control(
        db_session,
        membership_ctx=membership_ctx,
        control_id=control.id,
    )
    
    assert len(test_attributes) == 2
    codes = {ta.code for ta in test_attributes}
    assert "TA-005-1" in codes
    assert "TA-005-2" in codes

