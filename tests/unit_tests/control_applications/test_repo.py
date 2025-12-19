"""Unit tests for control_applications repository layer.

These tests verify database operations in isolation.
"""

from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from models.application import Application
from models.control import Control
from models.control_application import ControlApplication
from models.tenant import Tenant
from models.user import User
from models.user_tenant import UserTenant
from repos import control_applications_repo


@pytest.mark.asyncio
async def test_repo_create_mapping(db_session: AsyncSession):
    """Test: Repository can create a control-application mapping."""
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
        updated_at=datetime.utcnow(),
    )
    db_session.add(control)
    await db_session.flush()
    
    application = Application(
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        name="Test Application",
        row_version=1,
        updated_at=datetime.utcnow(),
    )
    db_session.add(application)
    await db_session.flush()
    
    # Create mapping
    mapping = ControlApplication(
        tenant_id=tenant.id,
        control_id=control.id,
        application_id=application.id,
        added_at=datetime.utcnow(),
        added_by_membership_id=membership.id,
    )
    
    created = await control_applications_repo.create(db_session, mapping)
    await db_session.commit()
    
    assert created.id is not None
    assert created.control_id == control.id
    assert created.application_id == application.id
    assert created.tenant_id == tenant.id
    assert created.added_by_membership_id == membership.id
    assert created.removed_at is None


@pytest.mark.asyncio
async def test_repo_list_active_by_control(db_session: AsyncSession):
    """Test: Repository can list active mappings for a control."""
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
        updated_at=datetime.utcnow(),
    )
    db_session.add(control)
    await db_session.flush()
    
    app1 = Application(
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        name="App 1",
        row_version=1,
        updated_at=datetime.utcnow(),
    )
    app2 = Application(
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        name="App 2",
        row_version=1,
        updated_at=datetime.utcnow(),
    )
    db_session.add(app1)
    db_session.add(app2)
    await db_session.flush()
    
    # Create active and removed mappings
    mapping_active = ControlApplication(
        tenant_id=tenant.id,
        control_id=control.id,
        application_id=app1.id,
        added_at=datetime.utcnow(),
        added_by_membership_id=membership.id,
    )
    mapping_removed = ControlApplication(
        tenant_id=tenant.id,
        control_id=control.id,
        application_id=app2.id,
        added_at=datetime.utcnow(),
        added_by_membership_id=membership.id,
        removed_at=datetime.utcnow(),
        removed_by_membership_id=membership.id,
    )
    db_session.add(mapping_active)
    db_session.add(mapping_removed)
    await db_session.commit()
    
    # List active mappings
    active = await control_applications_repo.list_active_by_control(
        db_session,
        tenant_id=tenant.id,
        control_id=control.id,
    )
    
    assert len(active) == 1
    assert active[0].id == mapping_active.id
    assert active[0].application_id == app1.id


@pytest.mark.asyncio
async def test_repo_get_active_found(db_session: AsyncSession):
    """Test: Repository can retrieve an active mapping."""
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
        updated_at=datetime.utcnow(),
    )
    db_session.add(control)
    await db_session.flush()
    
    application = Application(
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        name="Test Application",
        row_version=1,
        updated_at=datetime.utcnow(),
    )
    db_session.add(application)
    await db_session.flush()
    
    mapping = ControlApplication(
        tenant_id=tenant.id,
        control_id=control.id,
        application_id=application.id,
        added_at=datetime.utcnow(),
        added_by_membership_id=membership.id,
    )
    db_session.add(mapping)
    await db_session.commit()
    
    # Retrieve
    found = await control_applications_repo.get_active(
        db_session,
        tenant_id=tenant.id,
        control_id=control.id,
        application_id=application.id,
    )
    
    assert found is not None
    assert found.id == mapping.id
    assert found.removed_at is None


@pytest.mark.asyncio
async def test_repo_get_active_not_found(db_session: AsyncSession):
    """Test: Repository returns None for non-existent active mapping."""
    tenant = Tenant(id=uuid4(), name="Test Tenant", slug="test-tenant", status="active")
    db_session.add(tenant)
    await db_session.commit()
    
    fake_control_id = uuid4()
    fake_app_id = uuid4()
    
    found = await control_applications_repo.get_active(
        db_session,
        tenant_id=tenant.id,
        control_id=fake_control_id,
        application_id=fake_app_id,
    )
    
    assert found is None


@pytest.mark.asyncio
async def test_repo_get_active_excludes_removed(db_session: AsyncSession):
    """Test: Repository excludes removed mappings."""
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
        updated_at=datetime.utcnow(),
    )
    db_session.add(control)
    await db_session.flush()
    
    application = Application(
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        name="Test Application",
        row_version=1,
        updated_at=datetime.utcnow(),
    )
    db_session.add(application)
    await db_session.flush()
    
    # Create removed mapping
    mapping = ControlApplication(
        tenant_id=tenant.id,
        control_id=control.id,
        application_id=application.id,
        added_at=datetime.utcnow(),
        added_by_membership_id=membership.id,
        removed_at=datetime.utcnow(),
        removed_by_membership_id=membership.id,
    )
    db_session.add(mapping)
    await db_session.commit()
    
    # Should not find removed mapping
    found = await control_applications_repo.get_active(
        db_session,
        tenant_id=tenant.id,
        control_id=control.id,
        application_id=application.id,
    )
    
    assert found is None


@pytest.mark.asyncio
async def test_repo_soft_remove(db_session: AsyncSession):
    """Test: Repository can soft remove a mapping."""
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
        updated_at=datetime.utcnow(),
    )
    db_session.add(control)
    await db_session.flush()
    
    application = Application(
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        name="Test Application",
        row_version=1,
        updated_at=datetime.utcnow(),
    )
    db_session.add(application)
    await db_session.flush()
    
    mapping = ControlApplication(
        tenant_id=tenant.id,
        control_id=control.id,
        application_id=application.id,
        added_at=datetime.utcnow(),
        added_by_membership_id=membership.id,
    )
    db_session.add(mapping)
    await db_session.commit()
    
    # Soft remove
    removed_at = datetime.utcnow()
    updated = await control_applications_repo.soft_remove(
        db_session,
        mapping,
        removed_at=removed_at,
        removed_by_membership_id=membership.id,
    )
    await db_session.commit()
    
    assert updated.removed_at is not None
    assert updated.removed_by_membership_id == membership.id
    # Row still exists
    assert updated.id == mapping.id

