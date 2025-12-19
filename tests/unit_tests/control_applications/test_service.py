"""Unit tests for control_applications service layer.

These tests verify business logic, tenant scoping, and validation.
"""

from datetime import datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.tenancy import TenancyContext
from models.application import Application
from models.control import Control
from models.control_application import ControlApplication
from models.tenant import Tenant
from models.user import User
from models.user_tenant import UserTenant
from services import control_applications_service


@pytest.mark.asyncio
async def test_service_add_application_to_control_success(db_session: AsyncSession):
    """Test: Adding an application to a control succeeds with valid data."""
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
    await db_session.commit()
    
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
    await db_session.commit()
    
    membership_ctx = TenancyContext(
        membership_id=membership.id,
        tenant_id=tenant.id,
        role="admin",
    )
    
    # Add application to control
    mapping = await control_applications_service.add_application_to_control(
        db_session,
        membership_ctx=membership_ctx,
        control_id=control.id,
        application_id=application.id,
    )
    
    assert mapping.control_id == control.id
    assert mapping.application_id == application.id
    assert mapping.tenant_id == tenant.id
    assert mapping.added_by_membership_id == membership.id
    assert mapping.removed_at is None


@pytest.mark.asyncio
async def test_service_add_application_to_control_idempotent(db_session: AsyncSession):
    """Test: Adding the same application twice is idempotent."""
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
    await db_session.commit()
    
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
    await db_session.commit()
    
    membership_ctx = TenancyContext(
        membership_id=membership.id,
        tenant_id=tenant.id,
        role="admin",
    )
    
    # Add first time
    mapping1 = await control_applications_service.add_application_to_control(
        db_session,
        membership_ctx=membership_ctx,
        control_id=control.id,
        application_id=application.id,
    )
    
    # Add second time (should be idempotent)
    mapping2 = await control_applications_service.add_application_to_control(
        db_session,
        membership_ctx=membership_ctx,
        control_id=control.id,
        application_id=application.id,
    )
    
    # Should return the same mapping
    assert mapping1.id == mapping2.id


@pytest.mark.asyncio
async def test_service_add_application_to_control_control_not_found(db_session: AsyncSession):
    """Test: Adding application fails if control not found."""
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
    await db_session.commit()
    
    membership_ctx = TenancyContext(
        membership_id=membership.id,
        tenant_id=tenant.id,
        role="admin",
    )
    
    fake_control_id = uuid4()
    fake_app_id = uuid4()
    
    with pytest.raises(HTTPException) as exc_info:
        await control_applications_service.add_application_to_control(
            db_session,
            membership_ctx=membership_ctx,
            control_id=fake_control_id,
            application_id=fake_app_id,
        )
    
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "Control not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_service_add_application_to_control_application_not_found(db_session: AsyncSession):
    """Test: Adding application fails if application not found."""
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
    await db_session.commit()
    
    control = Control(
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-001",
        name="Test Control",
        row_version=1,
        updated_at=datetime.utcnow(),
    )
    db_session.add(control)
    await db_session.commit()
    
    membership_ctx = TenancyContext(
        membership_id=membership.id,
        tenant_id=tenant.id,
        role="admin",
    )
    
    fake_app_id = uuid4()
    
    with pytest.raises(HTTPException) as exc_info:
        await control_applications_service.add_application_to_control(
            db_session,
            membership_ctx=membership_ctx,
            control_id=control.id,
            application_id=fake_app_id,
        )
    
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "Application not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_service_remove_application_from_control_success(db_session: AsyncSession):
    """Test: Removing an application from a control succeeds."""
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
    await db_session.commit()
    
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
    await db_session.commit()
    
    # Create mapping
    mapping = ControlApplication(
        tenant_id=tenant.id,
        control_id=control.id,
        application_id=application.id,
        added_at=datetime.utcnow(),
        added_by_membership_id=membership.id,
    )
    db_session.add(mapping)
    await db_session.commit()
    
    membership_ctx = TenancyContext(
        membership_id=membership.id,
        tenant_id=tenant.id,
        role="admin",
    )
    
    # Remove application from control
    await control_applications_service.remove_application_from_control(
        db_session,
        membership_ctx=membership_ctx,
        control_id=control.id,
        application_id=application.id,
    )
    
    # Verify mapping is soft removed
    await db_session.refresh(mapping)
    assert mapping.removed_at is not None
    assert mapping.removed_by_membership_id == membership.id
    # Row still exists
    assert mapping.id is not None


@pytest.mark.asyncio
async def test_service_remove_application_from_control_idempotent(db_session: AsyncSession):
    """Test: Removing a non-existent mapping is idempotent."""
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
    await db_session.commit()
    
    control = Control(
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-001",
        name="Test Control",
        row_version=1,
        updated_at=datetime.utcnow(),
    )
    db_session.add(control)
    await db_session.commit()
    
    membership_ctx = TenancyContext(
        membership_id=membership.id,
        tenant_id=tenant.id,
        role="admin",
    )
    
    fake_app_id = uuid4()
    
    # Should not raise (idempotent)
    await control_applications_service.remove_application_from_control(
        db_session,
        membership_ctx=membership_ctx,
        control_id=control.id,
        application_id=fake_app_id,
    )


@pytest.mark.asyncio
async def test_service_list_control_applications_success(db_session: AsyncSession):
    """Test: Listing control applications returns active applications."""
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
    await db_session.commit()
    
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
    
    membership_ctx = TenancyContext(
        membership_id=membership.id,
        tenant_id=tenant.id,
        role="admin",
    )
    
    # List applications
    applications = await control_applications_service.list_control_applications(
        db_session,
        membership_ctx=membership_ctx,
        control_id=control.id,
    )
    
    # Should only return active application
    assert len(applications) == 1
    assert applications[0].id == app1.id
    assert applications[0].name == "App 1"


@pytest.mark.asyncio
async def test_service_add_remove_add_creates_new_row(db_session: AsyncSession):
    """Test: Add -> remove -> add again creates a NEW mapping row (history preserved)."""
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
    await db_session.commit()
    
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
    await db_session.commit()
    
    membership_ctx = TenancyContext(
        membership_id=membership.id,
        tenant_id=tenant.id,
        role="admin",
    )
    
    # Add
    mapping1 = await control_applications_service.add_application_to_control(
        db_session,
        membership_ctx=membership_ctx,
        control_id=control.id,
        application_id=application.id,
    )
    mapping1_id = mapping1.id
    
    # Remove
    await control_applications_service.remove_application_from_control(
        db_session,
        membership_ctx=membership_ctx,
        control_id=control.id,
        application_id=application.id,
    )
    
    # Verify old mapping is removed
    await db_session.refresh(mapping1)
    assert mapping1.removed_at is not None
    
    # Add again
    mapping2 = await control_applications_service.add_application_to_control(
        db_session,
        membership_ctx=membership_ctx,
        control_id=control.id,
        application_id=application.id,
    )
    
    # Should be a NEW row with different ID
    assert mapping2.id != mapping1_id
    assert mapping2.removed_at is None  # New mapping is active
    # Old mapping still exists with removed_at set
    await db_session.refresh(mapping1)
    assert mapping1.removed_at is not None

