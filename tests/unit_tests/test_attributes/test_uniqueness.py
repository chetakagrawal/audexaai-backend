"""Unit tests for test_attributes uniqueness constraints."""

from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from models.test_attribute import TestAttribute
from models.control import Control
from models.tenant import Tenant
from models.user import User
from models.user_tenant import UserTenant
from services.test_attributes_service import (
    create_test_attribute,
    delete_test_attribute,
)
from models.test_attribute import TestAttributeCreate
from api.tenancy import TenancyContext


@pytest.mark.asyncio
async def test_cannot_create_duplicate_active_code_for_same_control(db_session: AsyncSession):
    """Test: Cannot create two active test attributes with same (tenant_id, control_id, code)."""
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
    await db_session.flush()
    
    membership_ctx = TenancyContext(
        membership_id=membership.id,
        tenant_id=tenant.id,
        role="admin",
    )
    
    # Create first test attribute
    payload1 = TestAttributeCreate(
        code="TA-001",
        name="Test Attribute 1",
    )
    ta1 = await create_test_attribute(
        db_session,
        membership_ctx=membership_ctx,
        control_id=control.id,
        payload=payload1,
    )
    await db_session.commit()
    
    # Try to create second test attribute with same code for same control
    payload2 = TestAttributeCreate(
        code="TA-001",  # Same code
        name="Test Attribute 2",
    )
    
    # Should raise IntegrityError due to unique constraint
    with pytest.raises(IntegrityError):
        await create_test_attribute(
            db_session,
            membership_ctx=membership_ctx,
            control_id=control.id,
            payload=payload2,
        )
        await db_session.commit()


@pytest.mark.asyncio
async def test_can_recreate_code_after_soft_delete(db_session: AsyncSession):
    """Test: Can recreate test attribute with same code after soft delete."""
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
    
    membership_ctx = TenancyContext(
        membership_id=membership.id,
        tenant_id=tenant.id,
        role="admin",
    )
    
    # Create test attribute
    payload1 = TestAttributeCreate(
        code="TA-002",
        name="Test Attribute",
    )
    ta1 = await create_test_attribute(
        db_session,
        membership_ctx=membership_ctx,
        control_id=control.id,
        payload=payload1,
    )
    await db_session.commit()
    
    # Soft delete it
    await delete_test_attribute(
        db_session,
        membership_ctx=membership_ctx,
        test_attribute_id=ta1.id,
    )
    await db_session.commit()
    
    # Now recreate with same code - should succeed
    payload2 = TestAttributeCreate(
        code="TA-002",  # Same code
        name="Recreated Test Attribute",
    )
    ta2 = await create_test_attribute(
        db_session,
        membership_ctx=membership_ctx,
        control_id=control.id,
        payload=payload2,
    )
    await db_session.commit()
    
    assert ta2.id != ta1.id
    assert ta2.code == "TA-002"
    assert ta2.deleted_at is None  # New one is active


@pytest.mark.asyncio
async def test_same_code_allowed_for_different_controls(db_session: AsyncSession):
    """Test: Same code is allowed for different controls."""
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
    
    membership_ctx = TenancyContext(
        membership_id=membership.id,
        tenant_id=tenant.id,
        role="admin",
    )
    
    # Create test attribute for control1
    payload1 = TestAttributeCreate(
        code="TA-003",
        name="Test Attribute 1",
    )
    ta1 = await create_test_attribute(
        db_session,
        membership_ctx=membership_ctx,
        control_id=control1.id,
        payload=payload1,
    )
    await db_session.commit()
    
    # Create test attribute with same code for control2 - should succeed
    payload2 = TestAttributeCreate(
        code="TA-003",  # Same code, different control
        name="Test Attribute 2",
    )
    ta2 = await create_test_attribute(
        db_session,
        membership_ctx=membership_ctx,
        control_id=control2.id,
        payload=payload2,
    )
    await db_session.commit()
    
    assert ta1.id != ta2.id
    assert ta1.code == ta2.code == "TA-003"
    assert ta1.control_id != ta2.control_id

