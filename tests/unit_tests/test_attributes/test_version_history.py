"""Unit tests for test_attributes version history.

These tests verify that updates and deletes are captured in entity_versions.
"""

from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.test_attribute import TestAttribute
from models.control import Control
from models.entity_version import EntityVersion
from models.tenant import Tenant
from models.user import User
from models.user_tenant import UserTenant
from services.test_attributes_service import (
    create_test_attribute,
    update_test_attribute,
    delete_test_attribute,
)
from models.test_attribute import TestAttributeCreate
from api.tenancy import TenancyContext


@pytest.mark.asyncio
async def test_update_test_attribute_captures_snapshot(db_session: AsyncSession):
    """Test: Updating a test attribute captures a snapshot in entity_versions."""
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
    
    # Create test attribute
    payload = TestAttributeCreate(
        code="TA-001",
        name="Original Name",
        frequency="Monthly",
    )
    test_attribute = await create_test_attribute(
        db_session,
        membership_ctx=membership_ctx,
        control_id=control.id,
        payload=payload,
    )
    await db_session.commit()
    
    # Verify initial state
    assert test_attribute.row_version == 1
    
    # Update test attribute
    update_payload = TestAttributeCreate(
        code="TA-001-UPDATED",
        name="Updated Name",
        frequency="Quarterly",
    )
    updated = await update_test_attribute(
        db_session,
        membership_ctx=membership_ctx,
        test_attribute_id=test_attribute.id,
        payload=update_payload,
    )
    await db_session.commit()
    
    # Verify row_version incremented
    assert updated.row_version == 2
    
    # Check entity_versions for snapshot
    query = select(EntityVersion).where(
        EntityVersion.tenant_id == tenant.id,
        EntityVersion.entity_type == "test_attributes",
        EntityVersion.entity_id == test_attribute.id,
    )
    result = await db_session.execute(query)
    versions = list(result.scalars().all())
    
    assert len(versions) == 1, f"Expected 1 version snapshot, got {len(versions)}"
    version = versions[0]
    assert version.operation == "UPDATE"
    assert version.version_num == 1  # The OLD row_version
    assert version.entity_type == "test_attributes"
    assert version.entity_id == test_attribute.id
    
    # Verify snapshot data contains OLD values
    data = version.data
    assert data["code"] == "TA-001"
    assert data["name"] == "Original Name"
    assert data["frequency"] == "Monthly"
    assert data["row_version"] == 1


@pytest.mark.asyncio
async def test_soft_delete_captures_delete_snapshot(db_session: AsyncSession):
    """Test: Soft deleting a test attribute captures a DELETE snapshot."""
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
    payload = TestAttributeCreate(
        code="TA-002",
        name="Test Attribute",
    )
    test_attribute = await create_test_attribute(
        db_session,
        membership_ctx=membership_ctx,
        control_id=control.id,
        payload=payload,
    )
    await db_session.commit()
    
    # Soft delete test attribute
    await delete_test_attribute(
        db_session,
        membership_ctx=membership_ctx,
        test_attribute_id=test_attribute.id,
    )
    await db_session.commit()
    
    # Check entity_versions for DELETE snapshot
    query = select(EntityVersion).where(
        EntityVersion.tenant_id == tenant.id,
        EntityVersion.entity_type == "test_attributes",
        EntityVersion.entity_id == test_attribute.id,
    )
    result = await db_session.execute(query)
    versions = list(result.scalars().all())
    
    assert len(versions) == 1, f"Expected 1 version snapshot, got {len(versions)}"
    version = versions[0]
    assert version.operation == "DELETE"
    assert version.entity_type == "test_attributes"
    assert version.entity_id == test_attribute.id
    
    # Verify snapshot data contains the deleted row
    data = version.data
    assert data["code"] == "TA-002"
    assert data["name"] == "Test Attribute"


@pytest.mark.asyncio
async def test_multi_update_ordering(db_session: AsyncSession):
    """Test: Multiple updates create snapshots in correct order."""
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
    
    membership_ctx = TenancyContext(
        membership_id=membership.id,
        tenant_id=tenant.id,
        role="admin",
    )
    
    # Create test attribute
    payload = TestAttributeCreate(
        code="TA-003",
        name="Version 1",
    )
    test_attribute = await create_test_attribute(
        db_session,
        membership_ctx=membership_ctx,
        control_id=control.id,
        payload=payload,
    )
    await db_session.commit()
    
    # Update 1
    update1 = TestAttributeCreate(code="TA-003", name="Version 2")
    await update_test_attribute(
        db_session,
        membership_ctx=membership_ctx,
        test_attribute_id=test_attribute.id,
        payload=update1,
    )
    await db_session.commit()
    
    # Update 2
    update2 = TestAttributeCreate(code="TA-003", name="Version 3")
    await update_test_attribute(
        db_session,
        membership_ctx=membership_ctx,
        test_attribute_id=test_attribute.id,
        payload=update2,
    )
    await db_session.commit()
    
    # Check versions (ordered by version_num DESC)
    query = select(EntityVersion).where(
        EntityVersion.tenant_id == tenant.id,
        EntityVersion.entity_type == "test_attributes",
        EntityVersion.entity_id == test_attribute.id,
    ).order_by(EntityVersion.version_num.desc())
    result = await db_session.execute(query)
    versions = list(result.scalars().all())
    
    assert len(versions) == 2
    # Most recent snapshot (version_num=2) should have name="Version 2"
    assert versions[0].version_num == 2
    assert versions[0].data["name"] == "Version 2"
    # Older snapshot (version_num=1) should have name="Version 1"
    assert versions[1].version_num == 1
    assert versions[1].data["name"] == "Version 1"


@pytest.mark.asyncio
async def test_version_history_tenant_isolation(db_session: AsyncSession):
    """Test: Version history is tenant-isolated."""
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
    
    control_a = Control(
        tenant_id=tenant_a.id,
        created_by_membership_id=membership_a.id,
        control_code="AC-A",
        name="Control A",
        row_version=1,
    )
    control_b = Control(
        tenant_id=tenant_b.id,
        created_by_membership_id=membership_b.id,
        control_code="AC-B",
        name="Control B",
        row_version=1,
    )
    db_session.add(control_a)
    db_session.add(control_b)
    await db_session.flush()
    
    membership_ctx_a = TenancyContext(
        membership_id=membership_a.id,
        tenant_id=tenant_a.id,
        role="admin",
    )
    membership_ctx_b = TenancyContext(
        membership_id=membership_b.id,
        tenant_id=tenant_b.id,
        role="admin",
    )
    
    # Create test attributes in both tenants
    ta_a = await create_test_attribute(
        db_session,
        membership_ctx=membership_ctx_a,
        control_id=control_a.id,
        payload=TestAttributeCreate(code="TA-A", name="Test A"),
    )
    ta_b = await create_test_attribute(
        db_session,
        membership_ctx=membership_ctx_b,
        control_id=control_b.id,
        payload=TestAttributeCreate(code="TA-B", name="Test B"),
    )
    await db_session.commit()
    
    # Update both
    await update_test_attribute(
        db_session,
        membership_ctx=membership_ctx_a,
        test_attribute_id=ta_a.id,
        payload=TestAttributeCreate(code="TA-A", name="Updated A"),
    )
    await update_test_attribute(
        db_session,
        membership_ctx=membership_ctx_b,
        test_attribute_id=ta_b.id,
        payload=TestAttributeCreate(code="TA-B", name="Updated B"),
    )
    await db_session.commit()
    
    # Check versions for tenant_a - should only see tenant_a's versions
    query_a = select(EntityVersion).where(
        EntityVersion.tenant_id == tenant_a.id,
        EntityVersion.entity_type == "test_attributes",
    )
    result_a = await db_session.execute(query_a)
    versions_a = list(result_a.scalars().all())
    
    assert len(versions_a) == 1
    assert versions_a[0].entity_id == ta_a.id
    assert versions_a[0].data["name"] == "Test A"  # OLD value
    
    # Check versions for tenant_b - should only see tenant_b's versions
    query_b = select(EntityVersion).where(
        EntityVersion.tenant_id == tenant_b.id,
        EntityVersion.entity_type == "test_attributes",
    )
    result_b = await db_session.execute(query_b)
    versions_b = list(result_b.scalars().all())
    
    assert len(versions_b) == 1
    assert versions_b[0].entity_id == ta_b.id
    assert versions_b[0].data["name"] == "Test B"  # OLD value

