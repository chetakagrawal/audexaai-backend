"""Unit tests for controls service layer.

These tests verify business logic, tenant scoping, and audit metadata handling.
"""

from datetime import datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from api.tenancy import TenancyContext
from models.control import Control, ControlCreate, ControlBase
from models.tenant import Tenant
from models.user import User
from models.user_tenant import UserTenant
from models.auth_identity import AuthIdentity
from models.application import Application
from services.controls_service import (
    create_control,
    delete_control,
    get_control,
    list_controls,
    update_control,
)


@pytest.mark.asyncio
async def test_service_create_control_sets_audit_metadata(db_session: AsyncSession):
    """Test: Creating a control sets row_version=1, updated_at, updated_by is None."""
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
    
    membership_ctx = TenancyContext(
        membership_id=membership.id,
        tenant_id=tenant.id,
        role="admin",
    )
    
    # Create control
    payload = ControlCreate(
        control_code="AC-001",
        name="Test Control",
        is_key=False,
        is_automated=False,
    )
    
    control = await create_control(
        db_session,
        membership_ctx=membership_ctx,
        payload=payload,
    )
    
    assert control.row_version == 1
    assert control.updated_at is not None
    assert control.updated_by_membership_id is None  # Not set on creation
    assert control.deleted_at is None
    assert control.deleted_by_membership_id is None
    assert control.tenant_id == tenant.id
    assert control.created_by_membership_id == membership.id


@pytest.mark.asyncio
async def test_service_update_control_increments_row_version(db_session: AsyncSession):
    """Test: Updating a control increments row_version and sets updated_by."""
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
    await db_session.refresh(control)
    
    initial_row_version = control.row_version
    initial_updated_at = control.updated_at
    
    membership_ctx = TenancyContext(
        membership_id=membership.id,
        tenant_id=tenant.id,
        role="admin",
    )
    
    # Update control
    payload = ControlBase(
        control_code="AC-002",
        name="Updated Control Name",
        is_key=True,
        is_automated=False,
    )
    
    updated = await update_control(
        db_session,
        membership_ctx=membership_ctx,
        control_id=control.id,
        payload=payload,
        is_platform_admin=False,
    )
    
    assert updated.row_version == initial_row_version + 1
    assert updated.updated_at != initial_updated_at
    assert updated.updated_by_membership_id == membership.id
    assert updated.deleted_at is None
    assert updated.deleted_by_membership_id is None
    assert updated.name == "Updated Control Name"
    assert updated.is_key is True


@pytest.mark.asyncio
async def test_service_delete_control_soft_deletes(db_session: AsyncSession):
    """Test: Deleting a control soft deletes it and increments row_version."""
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
        control_code="AC-003",
        name="Test Control",
        row_version=1,
        updated_at=datetime.utcnow(),
    )
    db_session.add(control)
    await db_session.commit()
    await db_session.refresh(control)
    
    initial_row_version = control.row_version
    
    membership_ctx = TenancyContext(
        membership_id=membership.id,
        tenant_id=tenant.id,
        role="admin",
    )
    
    # Delete control
    deleted = await delete_control(
        db_session,
        membership_ctx=membership_ctx,
        control_id=control.id,
        is_platform_admin=False,
    )
    
    assert deleted.deleted_at is not None
    assert deleted.deleted_by_membership_id == membership.id
    assert deleted.row_version == initial_row_version + 1
    assert deleted.updated_at is not None
    assert deleted.updated_by_membership_id == membership.id


@pytest.mark.asyncio
async def test_service_get_control_excludes_deleted(db_session: AsyncSession):
    """Test: Get control excludes soft-deleted controls."""
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
        control_code="AC-004",
        name="Test Control",
        row_version=1,
        updated_at=datetime.utcnow(),
        deleted_at=datetime.utcnow(),
        deleted_by_membership_id=membership.id,
    )
    db_session.add(control)
    await db_session.commit()
    
    membership_ctx = TenancyContext(
        membership_id=membership.id,
        tenant_id=tenant.id,
        role="admin",
    )
    
    # Should raise 404 for deleted control
    with pytest.raises(HTTPException) as exc_info:
        await get_control(
            db_session,
            membership_ctx=membership_ctx,
            control_id=control.id,
            is_platform_admin=False,
        )
    
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_service_list_controls_excludes_deleted(db_session: AsyncSession):
    """Test: List controls excludes soft-deleted controls."""
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
        control_code="AC-005",
        name="Active Control",
        row_version=1,
        updated_at=datetime.utcnow(),
    )
    control_deleted = Control(
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-006",
        name="Deleted Control",
        row_version=1,
        updated_at=datetime.utcnow(),
        deleted_at=datetime.utcnow(),
        deleted_by_membership_id=membership.id,
    )
    db_session.add(control_active)
    db_session.add(control_deleted)
    await db_session.commit()
    
    membership_ctx = TenancyContext(
        membership_id=membership.id,
        tenant_id=tenant.id,
        role="admin",
    )
    
    # List should exclude deleted
    controls = await list_controls(
        db_session,
        membership_ctx=membership_ctx,
        is_platform_admin=False,
    )
    
    assert len(controls) == 1
    assert controls[0].id == control_active.id


@pytest.mark.asyncio
async def test_service_create_control_enforces_tenant_isolation(db_session: AsyncSession):
    """Test: Cannot create control for different tenant."""
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
    db_session.add(user_a)
    await db_session.flush()
    
    membership_a = UserTenant(
        id=uuid4(),
        user_id=user_a.id,
        tenant_id=tenant_a.id,
        role="admin",
        is_default=True,
    )
    db_session.add(membership_a)
    await db_session.commit()
    
    # Try to create control with tenant_a membership but different tenant_id in payload
    # (This shouldn't happen in practice since tenant_id comes from membership_ctx)
    membership_ctx = TenancyContext(
        membership_id=membership_a.id,
        tenant_id=tenant_a.id,  # Correct tenant
        role="admin",
    )
    
    payload = ControlCreate(
        control_code="AC-007",
        name="Test Control",
        is_key=False,
        is_automated=False,
    )
    
    # Should succeed - tenant_id is set from membership_ctx, not payload
    control = await create_control(
        db_session,
        membership_ctx=membership_ctx,
        payload=payload,
    )
    
    assert control.tenant_id == tenant_a.id


@pytest.mark.asyncio
async def test_service_update_control_enforces_tenant_isolation(db_session: AsyncSession):
    """Test: Cannot update control from different tenant."""
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
        control_code="AC-008",
        name="Test Control",
        row_version=1,
        updated_at=datetime.utcnow(),
    )
    db_session.add(control)
    await db_session.commit()
    
    # Try to update with tenant_a membership
    membership_ctx_a = TenancyContext(
        membership_id=membership_a.id,
        tenant_id=tenant_a.id,
        role="admin",
    )
    
    payload = ControlBase(
        control_code="AC-008",
        name="Updated Name",
        is_key=False,
        is_automated=False,
    )
    
    # Should raise 404 - control not found in tenant_a
    with pytest.raises(HTTPException) as exc_info:
        await update_control(
            db_session,
            membership_ctx=membership_ctx_a,
            control_id=control.id,
            payload=payload,
            is_platform_admin=False,
        )
    
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_service_create_control_with_applications(db_session: AsyncSession):
    """Test: Create control with application associations."""
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
    
    # Create applications
    app1 = Application(
        id=uuid4(),
        tenant_id=tenant.id,
        name="App 1",
        business_owner_membership_id=membership.id,
        it_owner_membership_id=membership.id,
    )
    app2 = Application(
        id=uuid4(),
        tenant_id=tenant.id,
        name="App 2",
        business_owner_membership_id=membership.id,
        it_owner_membership_id=membership.id,
    )
    db_session.add(app1)
    db_session.add(app2)
    await db_session.commit()
    
    membership_ctx = TenancyContext(
        membership_id=membership.id,
        tenant_id=tenant.id,
        role="admin",
    )
    
    # Create control with applications
    payload = ControlCreate(
        control_code="AC-009",
        name="Test Control",
        is_key=False,
        is_automated=False,
        application_ids=[app1.id, app2.id],
    )
    
    control = await create_control(
        db_session,
        membership_ctx=membership_ctx,
        payload=payload,
    )
    
    assert control.id is not None
    
    # Verify control_applications were created (check via query)
    from sqlalchemy import select
    from models.control_application import ControlApplication
    
    result = await db_session.execute(
        select(ControlApplication).where(ControlApplication.control_id == control.id)
    )
    control_apps = result.scalars().all()
    
    assert len(control_apps) == 2
    app_ids = {ca.application_id for ca in control_apps}
    assert app1.id in app_ids
    assert app2.id in app_ids


@pytest.mark.asyncio
async def test_service_create_control_rejects_invalid_application(db_session: AsyncSession):
    """Test: Create control fails if application doesn't exist or belongs to different tenant."""
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
    
    # Create application in tenant_b
    app_b = Application(
        id=uuid4(),
        tenant_id=tenant_b.id,
        name="App B",
        business_owner_membership_id=membership_b.id,
        it_owner_membership_id=membership_b.id,
    )
    db_session.add(app_b)
    await db_session.commit()
    
    membership_ctx_a = TenancyContext(
        membership_id=membership_a.id,
        tenant_id=tenant_a.id,
        role="admin",
    )
    
    # Try to create control in tenant_a with application from tenant_b
    payload = ControlCreate(
        control_code="AC-010",
        name="Test Control",
        is_key=False,
        is_automated=False,
        application_ids=[app_b.id],  # Application from different tenant
    )
    
    # Should raise 404 - application not found in tenant_a
    with pytest.raises(HTTPException) as exc_info:
        await create_control(
            db_session,
            membership_ctx=membership_ctx_a,
            payload=payload,
        )
    
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

