"""Unit tests for test_attributes repository layer.

These tests verify database operations in isolation.
"""

from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from models.test_attribute import TestAttribute
from models.control import Control
from models.tenant import Tenant
from models.user import User
from models.user_tenant import UserTenant
from repos import test_attributes_repo


@pytest.mark.asyncio
async def test_repo_create_test_attribute(db_session: AsyncSession):
    """Test: Repository can create a test attribute."""
    # Setup: Create tenant, user, membership, and control
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
    await db_session.flush()
    
    # Create test attribute
    test_attribute = TestAttribute(
        tenant_id=tenant.id,
        control_id=control.id,
        code="TA-001",
        name="Test Attribute",
        frequency="Monthly",
    )
    
    created = await test_attributes_repo.create(db_session, test_attribute)
    await db_session.commit()
    
    assert created.id is not None
    assert created.code == "TA-001"
    assert created.name == "Test Attribute"
    assert created.tenant_id == tenant.id
    assert created.control_id == control.id


@pytest.mark.asyncio
async def test_repo_get_by_id_found(db_session: AsyncSession):
    """Test: Repository can retrieve a test attribute by ID."""
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
        control_code="AC-002",
        name="Test Control",
        row_version=1,
    )
    db_session.add(control)
    await db_session.flush()
    
    test_attribute = TestAttribute(
        tenant_id=tenant.id,
        control_id=control.id,
        code="TA-002",
        name="Test Attribute",
    )
    db_session.add(test_attribute)
    await db_session.commit()
    
    # Retrieve
    found = await test_attributes_repo.get_by_id(
        db_session,
        tenant_id=tenant.id,
        test_attribute_id=test_attribute.id,
        include_deleted=False,
    )
    
    assert found is not None
    assert found.id == test_attribute.id
    assert found.code == "TA-002"


@pytest.mark.asyncio
async def test_repo_get_by_id_not_found(db_session: AsyncSession):
    """Test: Repository returns None for non-existent test attribute."""
    tenant = Tenant(id=uuid4(), name="Test Tenant", slug="test-tenant", status="active")
    db_session.add(tenant)
    await db_session.commit()
    
    fake_id = uuid4()
    found = await test_attributes_repo.get_by_id(
        db_session,
        tenant_id=tenant.id,
        test_attribute_id=fake_id,
        include_deleted=False,
    )
    
    assert found is None


@pytest.mark.asyncio
async def test_repo_list_by_control(db_session: AsyncSession):
    """Test: Repository can list test attributes for a control."""
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
    
    control1 = Control(
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-003",
        name="Control 1",
        row_version=1,
    )
    control2 = Control(
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-004",
        name="Control 2",
        row_version=1,
    )
    db_session.add(control1)
    db_session.add(control2)
    await db_session.flush()
    
    # Create test attributes for control1
    ta1 = TestAttribute(
        tenant_id=tenant.id,
        control_id=control1.id,
        code="TA-003-1",
        name="Test Attribute 1",
    )
    ta2 = TestAttribute(
        tenant_id=tenant.id,
        control_id=control1.id,
        code="TA-003-2",
        name="Test Attribute 2",
    )
    # Create test attribute for control2
    ta3 = TestAttribute(
        tenant_id=tenant.id,
        control_id=control2.id,
        code="TA-004-1",
        name="Test Attribute 3",
    )
    db_session.add(ta1)
    db_session.add(ta2)
    db_session.add(ta3)
    await db_session.commit()
    
    # List test attributes for control1
    test_attributes = await test_attributes_repo.list_by_control(
        db_session,
        tenant_id=tenant.id,
        control_id=control1.id,
        include_deleted=False,
    )
    
    assert len(test_attributes) == 2
    ta_ids = {ta.id for ta in test_attributes}
    assert ta1.id in ta_ids
    assert ta2.id in ta_ids
    assert ta3.id not in ta_ids

