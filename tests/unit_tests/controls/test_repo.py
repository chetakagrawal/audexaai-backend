"""Unit tests for controls repository layer.

These tests verify database operations in isolation.
"""

from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from models.control import Control
from models.tenant import Tenant
from models.user import User
from models.user_tenant import UserTenant
from models.auth_identity import AuthIdentity
from repos import controls_repo


@pytest.mark.asyncio
async def test_repo_create_control(db_session: AsyncSession):
    """Test: Repository can create a control."""
    # Setup: Create tenant and membership
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
    
    # Create control
    control = Control(
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-001",
        name="Test Control",
        row_version=1,
        updated_at=datetime.utcnow(),
    )
    
    created = await controls_repo.create(db_session, control)
    await db_session.commit()
    
    assert created.id is not None
    assert created.control_code == "AC-001"
    assert created.name == "Test Control"
    assert created.tenant_id == tenant.id
    assert created.row_version == 1


@pytest.mark.asyncio
async def test_repo_get_by_id_found(db_session: AsyncSession):
    """Test: Repository can retrieve a control by ID."""
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
    
    # Create control
    control = Control(
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-002",
        name="Test Control",
        row_version=1,
        updated_at=datetime.utcnow(),
    )
    db_session.add(control)
    await db_session.commit()
    
    # Retrieve
    found = await controls_repo.get_by_id(
        db_session,
        tenant_id=tenant.id,
        control_id=control.id,
        include_deleted=False,
    )
    
    assert found is not None
    assert found.id == control.id
    assert found.control_code == "AC-002"


@pytest.mark.asyncio
async def test_repo_get_by_id_not_found(db_session: AsyncSession):
    """Test: Repository returns None for non-existent control."""
    tenant = Tenant(id=uuid4(), name="Test Tenant", slug="test-tenant", status="active")
    db_session.add(tenant)
    await db_session.commit()
    
    fake_id = uuid4()
    found = await controls_repo.get_by_id(
        db_session,
        tenant_id=tenant.id,
        control_id=fake_id,
        include_deleted=False,
    )
    
    assert found is None


@pytest.mark.asyncio
async def test_repo_get_by_id_excludes_deleted(db_session: AsyncSession):
    """Test: Repository excludes soft-deleted controls by default."""
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
    
    # Create and soft-delete control
    control = Control(
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-003",
        name="Test Control",
        row_version=1,
        updated_at=datetime.utcnow(),
        deleted_at=datetime.utcnow(),
        deleted_by_membership_id=membership.id,
    )
    db_session.add(control)
    await db_session.commit()
    
    # Should not find deleted control
    found = await controls_repo.get_by_id(
        db_session,
        tenant_id=tenant.id,
        control_id=control.id,
        include_deleted=False,
    )
    
    assert found is None
    
    # Should find deleted control when include_deleted=True
    found_deleted = await controls_repo.get_by_id(
        db_session,
        tenant_id=tenant.id,
        control_id=control.id,
        include_deleted=True,
    )
    
    assert found_deleted is not None
    assert found_deleted.id == control.id


@pytest.mark.asyncio
async def test_repo_list_controls(db_session: AsyncSession):
    """Test: Repository can list controls for a tenant."""
    # Setup
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
    
    # Create controls in both tenants
    control_a1 = Control(
        tenant_id=tenant_a.id,
        created_by_membership_id=membership_a.id,
        control_code="AC-001",
        name="Control A1",
        row_version=1,
        updated_at=datetime.utcnow(),
    )
    control_a2 = Control(
        tenant_id=tenant_a.id,
        created_by_membership_id=membership_a.id,
        control_code="AC-002",
        name="Control A2",
        row_version=1,
        updated_at=datetime.utcnow(),
    )
    control_b1 = Control(
        tenant_id=tenant_b.id,
        created_by_membership_id=membership_b.id,
        control_code="AC-001",  # Same code, different tenant
        name="Control B1",
        row_version=1,
        updated_at=datetime.utcnow(),
    )
    db_session.add(control_a1)
    db_session.add(control_a2)
    db_session.add(control_b1)
    await db_session.commit()
    
    # List controls for tenant_a
    controls_a = await controls_repo.list(
        db_session,
        tenant_id=tenant_a.id,
        include_deleted=False,
    )
    
    assert len(controls_a) == 2
    control_ids = {c.id for c in controls_a}
    assert control_a1.id in control_ids
    assert control_a2.id in control_ids
    assert control_b1.id not in control_ids
    
    # List controls for tenant_b
    controls_b = await controls_repo.list(
        db_session,
        tenant_id=tenant_b.id,
        include_deleted=False,
    )
    
    assert len(controls_b) == 1
    assert controls_b[0].id == control_b1.id


@pytest.mark.asyncio
async def test_repo_list_excludes_deleted(db_session: AsyncSession):
    """Test: Repository list excludes soft-deleted controls by default."""
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
    
    # Create active and deleted controls
    control_active = Control(
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-001",
        name="Active Control",
        row_version=1,
        updated_at=datetime.utcnow(),
    )
    control_deleted = Control(
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-002",
        name="Deleted Control",
        row_version=1,
        updated_at=datetime.utcnow(),
        deleted_at=datetime.utcnow(),
        deleted_by_membership_id=membership.id,
    )
    db_session.add(control_active)
    db_session.add(control_deleted)
    await db_session.commit()
    
    # List should exclude deleted
    controls = await controls_repo.list(
        db_session,
        tenant_id=tenant.id,
        include_deleted=False,
    )
    
    assert len(controls) == 1
    assert controls[0].id == control_active.id
    
    # List with include_deleted=True should include both
    controls_all = await controls_repo.list(
        db_session,
        tenant_id=tenant.id,
        include_deleted=True,
    )
    
    assert len(controls_all) == 2

