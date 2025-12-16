"""DB-backed tests for TestAttribute model.

These tests verify model behavior, database constraints, and query patterns
for the TestAttribute model. All tests use a real database session.
"""

from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.test_attribute import TestAttribute
from models.control import Control
from models.tenant import Tenant
from models.user import User
from models.user_tenant import UserTenant


@pytest.mark.asyncio
async def test_create_test_attribute_minimal(db_session: AsyncSession):
    """Test: Can create a test attribute with minimal required fields."""
    # Create tenant and membership
    tenant = Tenant(
        id=uuid4(),
        name="Test Tenant",
        slug="test-tenant",
        status="active",
    )
    db_session.add(tenant)
    await db_session.flush()
    
    user = User(
        id=uuid4(),
        primary_email="user@example.com",
        name="User",
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
    
    # Create control
    control = Control(
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-001",
        name="Test Control",
    )
    db_session.add(control)
    await db_session.flush()
    
    # Create test attribute
    test_attribute = TestAttribute(
        id=uuid4(),
        tenant_id=tenant.id,
        control_id=control.id,
        code="TA-001",
        name="Test Attribute",
    )
    db_session.add(test_attribute)
    await db_session.commit()
    await db_session.refresh(test_attribute)
    
    assert test_attribute.id is not None
    assert test_attribute.tenant_id == tenant.id
    assert test_attribute.control_id == control.id
    assert test_attribute.code == "TA-001"
    assert test_attribute.name == "Test Attribute"
    assert test_attribute.frequency is None
    assert test_attribute.test_procedure is None
    assert test_attribute.expected_evidence is None
    assert test_attribute.created_at is not None
    assert isinstance(test_attribute.created_at, datetime)


@pytest.mark.asyncio
async def test_create_test_attribute_with_all_fields(db_session: AsyncSession):
    """Test: Can create a test attribute with all fields populated."""
    # Create tenant and membership
    tenant = Tenant(
        id=uuid4(),
        name="Test Tenant",
        slug="test-tenant",
        status="active",
    )
    db_session.add(tenant)
    await db_session.flush()
    
    user = User(
        id=uuid4(),
        primary_email="user@example.com",
        name="User",
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
    
    # Create control
    control = Control(
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-001",
        name="Test Control",
    )
    db_session.add(control)
    await db_session.flush()
    
    # Create test attribute with all fields
    test_attribute = TestAttribute(
        id=uuid4(),
        tenant_id=tenant.id,
        control_id=control.id,
        code="TA-001",
        name="Test Attribute",
        frequency="Quarterly",
        test_procedure="Review access logs and verify user permissions",
        expected_evidence="Access logs, user permission reports",
    )
    db_session.add(test_attribute)
    await db_session.commit()
    await db_session.refresh(test_attribute)
    
    assert test_attribute.code == "TA-001"
    assert test_attribute.name == "Test Attribute"
    assert test_attribute.frequency == "Quarterly"
    assert test_attribute.test_procedure == "Review access logs and verify user permissions"
    assert test_attribute.expected_evidence == "Access logs, user permission reports"


@pytest.mark.asyncio
async def test_test_attribute_query_by_control(db_session: AsyncSession):
    """Test: Can query test attributes by control_id."""
    # Create tenant and membership
    tenant = Tenant(
        id=uuid4(),
        name="Test Tenant",
        slug="test-tenant",
        status="active",
    )
    db_session.add(tenant)
    await db_session.flush()
    
    user = User(
        id=uuid4(),
        primary_email="user@example.com",
        name="User",
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
    
    # Create control
    control = Control(
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-001",
        name="Test Control",
    )
    db_session.add(control)
    await db_session.flush()
    
    # Create multiple test attributes for the same control
    ta1 = TestAttribute(
        id=uuid4(),
        tenant_id=tenant.id,
        control_id=control.id,
        code="TA-001",
        name="Test Attribute 1",
    )
    ta2 = TestAttribute(
        id=uuid4(),
        tenant_id=tenant.id,
        control_id=control.id,
        code="TA-002",
        name="Test Attribute 2",
    )
    db_session.add(ta1)
    db_session.add(ta2)
    await db_session.commit()
    
    # Query test attributes by control_id
    result = await db_session.execute(
        select(TestAttribute).where(TestAttribute.control_id == control.id)
    )
    test_attributes = result.scalars().all()
    
    assert len(test_attributes) == 2
    codes = [ta.code for ta in test_attributes]
    assert "TA-001" in codes
    assert "TA-002" in codes


@pytest.mark.asyncio
async def test_test_attribute_cascade_delete_on_control(db_session: AsyncSession):
    """Test: Deleting a control cascades to delete test attributes."""
    # Create tenant and membership
    tenant = Tenant(
        id=uuid4(),
        name="Test Tenant",
        slug="test-tenant",
        status="active",
    )
    db_session.add(tenant)
    await db_session.flush()
    
    user = User(
        id=uuid4(),
        primary_email="user@example.com",
        name="User",
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
    
    # Create control
    control = Control(
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-001",
        name="Test Control",
    )
    db_session.add(control)
    await db_session.flush()
    
    # Create test attribute
    test_attribute = TestAttribute(
        id=uuid4(),
        tenant_id=tenant.id,
        control_id=control.id,
        code="TA-001",
        name="Test Attribute",
    )
    db_session.add(test_attribute)
    await db_session.commit()
    
    # Verify test attribute exists
    result = await db_session.execute(
        select(TestAttribute).where(TestAttribute.id == test_attribute.id)
    )
    assert result.scalar_one_or_none() is not None
    
    # Delete control (should cascade delete test attribute)
    await db_session.delete(control)
    await db_session.commit()
    
    # Verify test attribute is deleted
    result = await db_session.execute(
        select(TestAttribute).where(TestAttribute.id == test_attribute.id)
    )
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_test_attribute_cascade_delete_on_tenant(db_session: AsyncSession):
    """Test: Deleting a tenant cascades to delete test attributes."""
    # Create tenant and membership
    tenant = Tenant(
        id=uuid4(),
        name="Test Tenant",
        slug="test-tenant",
        status="active",
    )
    db_session.add(tenant)
    await db_session.flush()
    
    user = User(
        id=uuid4(),
        primary_email="user@example.com",
        name="User",
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
    
    # Create control
    control = Control(
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-001",
        name="Test Control",
    )
    db_session.add(control)
    await db_session.flush()
    
    # Create test attribute
    test_attribute = TestAttribute(
        id=uuid4(),
        tenant_id=tenant.id,
        control_id=control.id,
        code="TA-001",
        name="Test Attribute",
    )
    db_session.add(test_attribute)
    await db_session.commit()
    
    # Verify test attribute exists
    result = await db_session.execute(
        select(TestAttribute).where(TestAttribute.id == test_attribute.id)
    )
    assert result.scalar_one_or_none() is not None
    
    # Delete tenant (should cascade delete test attribute)
    await db_session.delete(tenant)
    await db_session.commit()
    
    # Verify test attribute is deleted
    result = await db_session.execute(
        select(TestAttribute).where(TestAttribute.id == test_attribute.id)
    )
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_test_attribute_tenant_isolation(db_session: AsyncSession):
    """Test: Test attributes are isolated by tenant."""
    # Create two tenants
    tenant_a = Tenant(
        id=uuid4(),
        name="Tenant A",
        slug="tenant-a",
        status="active",
    )
    tenant_b = Tenant(
        id=uuid4(),
        name="Tenant B",
        slug="tenant-b",
        status="active",
    )
    db_session.add(tenant_a)
    db_session.add(tenant_b)
    await db_session.flush()
    
    # Create users and memberships
    user_a = User(
        id=uuid4(),
        primary_email="user_a@example.com",
        name="User A",
        is_platform_admin=False,
        is_active=True,
    )
    user_b = User(
        id=uuid4(),
        primary_email="user_b@example.com",
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
    
    # Create controls in each tenant
    control_a = Control(
        id=uuid4(),
        tenant_id=tenant_a.id,
        created_by_membership_id=membership_a.id,
        control_code="AC-001",
        name="Control A",
    )
    control_b = Control(
        id=uuid4(),
        tenant_id=tenant_b.id,
        created_by_membership_id=membership_b.id,
        control_code="AC-001",
        name="Control B",
    )
    db_session.add(control_a)
    db_session.add(control_b)
    await db_session.flush()
    
    # Create test attributes in each tenant
    ta_a = TestAttribute(
        id=uuid4(),
        tenant_id=tenant_a.id,
        control_id=control_a.id,
        code="TA-001",
        name="Test Attribute A",
    )
    ta_b = TestAttribute(
        id=uuid4(),
        tenant_id=tenant_b.id,
        control_id=control_b.id,
        code="TA-001",
        name="Test Attribute B",
    )
    db_session.add(ta_a)
    db_session.add(ta_b)
    await db_session.commit()
    
    # Query test attributes for tenant_a - should only see tenant_a's
    result = await db_session.execute(
        select(TestAttribute).where(TestAttribute.tenant_id == tenant_a.id)
    )
    test_attributes_a = result.scalars().all()
    
    assert len(test_attributes_a) == 1
    assert test_attributes_a[0].id == ta_a.id
    assert test_attributes_a[0].tenant_id == tenant_a.id
    
    # Query test attributes for tenant_b - should only see tenant_b's
    result = await db_session.execute(
        select(TestAttribute).where(TestAttribute.tenant_id == tenant_b.id)
    )
    test_attributes_b = result.scalars().all()
    
    assert len(test_attributes_b) == 1
    assert test_attributes_b[0].id == ta_b.id
    assert test_attributes_b[0].tenant_id == tenant_b.id
