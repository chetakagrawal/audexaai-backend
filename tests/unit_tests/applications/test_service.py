"""Unit tests for applications service layer.

These tests verify business logic, tenant scoping, and validation.
"""

from uuid import uuid4

import pytest
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.tenancy import TenancyContext
from models.application import Application, ApplicationCreate, ApplicationUpdate
from models.tenant import Tenant
from models.user import User
from models.user_tenant import UserTenant
from services.applications_service import (
    create_application,
    delete_application,
    get_application,
    list_applications,
    update_application,
)


@pytest.mark.asyncio
async def test_service_create_application_success(db_session: AsyncSession):
    """Test: Creating an application succeeds with valid data."""
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
    
    # Create application
    payload = ApplicationCreate(
        name="Test Application",
        category="Financial",
        scope_rationale="Test scope",
        business_owner_membership_id=membership.id,
        it_owner_membership_id=membership.id,
    )
    
    application = await create_application(
        db_session,
        membership_ctx=membership_ctx,
        payload=payload,
    )
    
    assert application.name == "Test Application"
    assert application.category == "Financial"
    assert application.tenant_id == tenant.id
    assert application.business_owner_membership_id == membership.id
    assert application.it_owner_membership_id == membership.id


@pytest.mark.asyncio
async def test_service_create_application_invalid_business_owner(db_session: AsyncSession):
    """Test: Creating application with business owner from different tenant fails."""
    # Setup two tenants
    tenant_a = Tenant(id=uuid4(), name="Tenant A", slug="tenant-a", status="active")
    tenant_b = Tenant(id=uuid4(), name="Tenant B", slug="tenant-b", status="active")
    db_session.add(tenant_a)
    db_session.add(tenant_b)
    await db_session.flush()
    
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
    await db_session.commit()
    
    membership_ctx = TenancyContext(
        membership_id=membership_a.id,
        tenant_id=tenant_a.id,
        role="admin",
    )
    
    # Try to create with business owner from Tenant B
    payload = ApplicationCreate(
        name="Test Application",
        business_owner_membership_id=membership_b.id,  # From Tenant B
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await create_application(
            db_session,
            membership_ctx=membership_ctx,
            payload=payload,
        )
    
    assert exc_info.value.status_code in [
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_404_NOT_FOUND,
    ]


@pytest.mark.asyncio
async def test_service_create_application_invalid_it_owner(db_session: AsyncSession):
    """Test: Creating application with IT owner from different tenant fails."""
    # Setup two tenants
    tenant_a = Tenant(id=uuid4(), name="Tenant A", slug="tenant-a", status="active")
    tenant_b = Tenant(id=uuid4(), name="Tenant B", slug="tenant-b", status="active")
    db_session.add(tenant_a)
    db_session.add(tenant_b)
    await db_session.flush()
    
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
    await db_session.commit()
    
    membership_ctx = TenancyContext(
        membership_id=membership_a.id,
        tenant_id=tenant_a.id,
        role="admin",
    )
    
    # Try to create with IT owner from Tenant B
    payload = ApplicationCreate(
        name="Test Application",
        it_owner_membership_id=membership_b.id,  # From Tenant B
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await create_application(
            db_session,
            membership_ctx=membership_ctx,
            payload=payload,
        )
    
    assert exc_info.value.status_code in [
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_404_NOT_FOUND,
    ]


@pytest.mark.asyncio
async def test_service_get_application_success(db_session: AsyncSession):
    """Test: Getting an application succeeds when it exists."""
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
    
    # Create application
    application = Application(
        tenant_id=tenant.id,
        name="Test Application",
        category="Financial",
    )
    db_session.add(application)
    await db_session.commit()
    await db_session.refresh(application)
    
    membership_ctx = TenancyContext(
        membership_id=membership.id,
        tenant_id=tenant.id,
        role="admin",
    )
    
    # Get application
    found = await get_application(
        db_session,
        membership_ctx=membership_ctx,
        application_id=application.id,
    )
    
    assert found.id == application.id
    assert found.name == "Test Application"


@pytest.mark.asyncio
async def test_service_get_application_not_found(db_session: AsyncSession):
    """Test: Getting non-existent application raises 404."""
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
    
    fake_id = uuid4()
    
    with pytest.raises(HTTPException) as exc_info:
        await get_application(
            db_session,
            membership_ctx=membership_ctx,
            application_id=fake_id,
        )
    
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_service_get_application_tenant_isolation(db_session: AsyncSession):
    """Test: Cannot get application from different tenant."""
    # Setup two tenants
    tenant_a = Tenant(id=uuid4(), name="Tenant A", slug="tenant-a", status="active")
    tenant_b = Tenant(id=uuid4(), name="Tenant B", slug="tenant-b", status="active")
    db_session.add(tenant_a)
    db_session.add(tenant_b)
    await db_session.flush()
    
    user_a = User(
        id=uuid4(),
        primary_email="user_a@example.com",
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
    await db_session.flush()
    
    # Create application in Tenant B
    app_b = Application(
        tenant_id=tenant_b.id,
        name="Tenant B App",
    )
    db_session.add(app_b)
    await db_session.commit()
    await db_session.refresh(app_b)
    
    membership_ctx = TenancyContext(
        membership_id=membership_a.id,
        tenant_id=tenant_a.id,
        role="admin",
    )
    
    # Try to get from Tenant A (should fail)
    with pytest.raises(HTTPException) as exc_info:
        await get_application(
            db_session,
            membership_ctx=membership_ctx,
            application_id=app_b.id,
        )
    
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_service_list_applications(db_session: AsyncSession):
    """Test: Listing applications returns tenant's applications."""
    # Setup
    tenant_a = Tenant(id=uuid4(), name="Tenant A", slug="tenant-a", status="active")
    tenant_b = Tenant(id=uuid4(), name="Tenant B", slug="tenant-b", status="active")
    db_session.add(tenant_a)
    db_session.add(tenant_b)
    await db_session.flush()
    
    user_a = User(
        id=uuid4(),
        primary_email="user_a@example.com",
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
    await db_session.flush()
    
    # Create applications
    app_a1 = Application(tenant_id=tenant_a.id, name="App A1")
    app_a2 = Application(tenant_id=tenant_a.id, name="App A2")
    app_b1 = Application(tenant_id=tenant_b.id, name="App B1")
    
    db_session.add(app_a1)
    db_session.add(app_a2)
    db_session.add(app_b1)
    await db_session.commit()
    
    membership_ctx = TenancyContext(
        membership_id=membership_a.id,
        tenant_id=tenant_a.id,
        role="admin",
    )
    
    # List applications
    apps = await list_applications(
        db_session,
        membership_ctx=membership_ctx,
    )
    
    assert len(apps) == 2
    names = {app.name for app in apps}
    assert "App A1" in names
    assert "App A2" in names
    assert "App B1" not in names


@pytest.mark.asyncio
async def test_service_update_application_success(db_session: AsyncSession):
    """Test: Updating an application succeeds."""
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
    
    # Create application
    application = Application(
        tenant_id=tenant.id,
        name="Original Name",
        category="Original Category",
    )
    db_session.add(application)
    await db_session.commit()
    await db_session.refresh(application)
    
    membership_ctx = TenancyContext(
        membership_id=membership.id,
        tenant_id=tenant.id,
        role="admin",
    )
    
    # Update application
    payload = ApplicationUpdate(
        name="Updated Name",
        category="Updated Category",
    )
    
    updated = await update_application(
        db_session,
        membership_ctx=membership_ctx,
        application_id=application.id,
        payload=payload,
    )
    
    assert updated.name == "Updated Name"
    assert updated.category == "Updated Category"


@pytest.mark.asyncio
async def test_service_update_application_not_found(db_session: AsyncSession):
    """Test: Updating non-existent application raises 404."""
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
    
    fake_id = uuid4()
    payload = ApplicationUpdate(name="Updated Name")
    
    with pytest.raises(HTTPException) as exc_info:
        await update_application(
            db_session,
            membership_ctx=membership_ctx,
            application_id=fake_id,
            payload=payload,
        )
    
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_service_delete_application_success(db_session: AsyncSession):
    """Test: Deleting an application succeeds (hard delete in Sub-stage A)."""
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
    
    # Create application
    application = Application(
        tenant_id=tenant.id,
        name="Test Application",
    )
    db_session.add(application)
    await db_session.commit()
    await db_session.refresh(application)
    
    membership_ctx = TenancyContext(
        membership_id=membership.id,
        tenant_id=tenant.id,
        role="admin",
    )
    
    # Delete application
    await delete_application(
        db_session,
        membership_ctx=membership_ctx,
        application_id=application.id,
    )
    
    # Verify it's soft deleted (soft delete with audit metadata)
    from repos import applications_repo
    found = await applications_repo.get_by_id(
        db_session,
        tenant_id=tenant.id,
        application_id=application.id,
        include_deleted=True,
    )
    
    assert found is not None  # Soft delete keeps the record
    assert found.deleted_at is not None  # But marks it as deleted
    assert found.deleted_by_membership_id == membership.id


@pytest.mark.asyncio
async def test_service_delete_application_not_found(db_session: AsyncSession):
    """Test: Deleting non-existent application raises 404."""
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
    
    fake_id = uuid4()
    
    with pytest.raises(HTTPException) as exc_info:
        await delete_application(
            db_session,
            membership_ctx=membership_ctx,
            application_id=fake_id,
        )
    
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


# SUB-STAGE B tests: Metadata columns and soft delete
@pytest.mark.asyncio
async def test_service_create_application_sets_audit_metadata(db_session: AsyncSession):
    """Test: Creating an application sets row_version=1, updated_at, created_by, updated_by=creator."""
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
    
    # Create application
    payload = ApplicationCreate(
        name="Test Application",
        category="Financial",
    )
    
    application = await create_application(
        db_session,
        membership_ctx=membership_ctx,
        payload=payload,
    )
    
    assert application.row_version == 1
    assert application.updated_at is not None
    assert application.created_by_membership_id == membership.id
    assert application.updated_by_membership_id == membership.id  # Set to creator for consistency
    assert application.deleted_at is None
    assert application.deleted_by_membership_id is None


@pytest.mark.asyncio
async def test_service_update_application_increments_row_version(db_session: AsyncSession):
    """Test: Updating an application increments row_version and sets updated_by/updated_at."""
    from datetime import datetime
    
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
    
    # Create application
    application = Application(
        tenant_id=tenant.id,
        name="Original Name",
        created_by_membership_id=membership.id,
        updated_by_membership_id=membership.id,
        row_version=1,
        updated_at=datetime.utcnow(),
    )
    db_session.add(application)
    await db_session.commit()
    await db_session.refresh(application)
    
    initial_row_version = application.row_version
    initial_updated_at = application.updated_at
    
    membership_ctx = TenancyContext(
        membership_id=membership.id,
        tenant_id=tenant.id,
        role="admin",
    )
    
    # Update application
    payload = ApplicationUpdate(
        name="Updated Name",
    )
    
    updated = await update_application(
        db_session,
        membership_ctx=membership_ctx,
        application_id=application.id,
        payload=payload,
    )
    
    assert updated.row_version == initial_row_version + 1
    assert updated.updated_by_membership_id == membership.id
    assert updated.updated_at is not None
    assert updated.updated_at > initial_updated_at


@pytest.mark.asyncio
async def test_service_delete_application_soft_delete(db_session: AsyncSession):
    """Test: Deleting an application performs soft delete with metadata."""
    from datetime import datetime
    
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
    
    # Create application
    application = Application(
        tenant_id=tenant.id,
        name="Test Application",
        created_by_membership_id=membership.id,
        updated_by_membership_id=membership.id,
        row_version=1,
        updated_at=datetime.utcnow(),
    )
    db_session.add(application)
    await db_session.commit()
    await db_session.refresh(application)
    
    initial_row_version = application.row_version
    
    membership_ctx = TenancyContext(
        membership_id=membership.id,
        tenant_id=tenant.id,
        role="admin",
    )
    
    # Delete application (soft delete)
    await delete_application(
        db_session,
        membership_ctx=membership_ctx,
        application_id=application.id,
    )
    
    # Refresh to get updated state
    await db_session.refresh(application)
    
    assert application.deleted_at is not None
    assert application.deleted_by_membership_id == membership.id
    assert application.row_version == initial_row_version + 1
    assert application.updated_at is not None
    assert application.updated_by_membership_id == membership.id


@pytest.mark.asyncio
async def test_service_get_application_excludes_deleted(db_session: AsyncSession):
    """Test: Get application excludes soft-deleted applications."""
    from datetime import datetime
    
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
    
    # Create and soft-delete application
    application = Application(
        tenant_id=tenant.id,
        name="Test Application",
        created_by_membership_id=membership.id,
        updated_by_membership_id=membership.id,
        row_version=1,
        updated_at=datetime.utcnow(),
        deleted_at=datetime.utcnow(),
        deleted_by_membership_id=membership.id,
    )
    db_session.add(application)
    await db_session.commit()
    await db_session.refresh(application)
    
    membership_ctx = TenancyContext(
        membership_id=membership.id,
        tenant_id=tenant.id,
        role="admin",
    )
    
    # Should raise 404 for deleted application
    with pytest.raises(HTTPException) as exc_info:
        await get_application(
            db_session,
            membership_ctx=membership_ctx,
            application_id=application.id,
        )
    
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_service_list_applications_excludes_deleted(db_session: AsyncSession):
    """Test: List applications excludes soft-deleted applications."""
    from datetime import datetime
    
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
    app_active = Application(
        tenant_id=tenant.id,
        name="Active App",
        created_by_membership_id=membership.id,
        updated_by_membership_id=membership.id,
        row_version=1,
        updated_at=datetime.utcnow(),
    )
    app_deleted = Application(
        tenant_id=tenant.id,
        name="Deleted App",
        created_by_membership_id=membership.id,
        updated_by_membership_id=membership.id,
        row_version=1,
        updated_at=datetime.utcnow(),
        deleted_at=datetime.utcnow(),
        deleted_by_membership_id=membership.id,
    )
    
    db_session.add(app_active)
    db_session.add(app_deleted)
    await db_session.commit()
    
    membership_ctx = TenancyContext(
        membership_id=membership.id,
        tenant_id=tenant.id,
        role="admin",
    )
    
    # List applications (should exclude deleted)
    apps = await list_applications(
        db_session,
        membership_ctx=membership_ctx,
    )
    
    assert len(apps) == 1
    assert apps[0].name == "Active App"
    assert apps[0].id == app_active.id


@pytest.mark.asyncio
async def test_service_create_application_uniqueness_violation(db_session: AsyncSession):
    """Test: Cannot create two active applications with same (tenant_id, name)."""
    from sqlalchemy.exc import IntegrityError
    
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
    
    # Create first application
    payload1 = ApplicationCreate(name="Unique App")
    app1 = await create_application(
        db_session,
        membership_ctx=membership_ctx,
        payload=payload1,
    )
    
    # Try to create second application with same name (should fail)
    payload2 = ApplicationCreate(name="Unique App")
    
    with pytest.raises((HTTPException, IntegrityError)) as exc_info:
        await create_application(
            db_session,
            membership_ctx=membership_ctx,
            payload=payload2,
        )
    
    # Should raise either IntegrityError (from DB) or HTTPException (from service handling)
    assert exc_info.value is not None


@pytest.mark.asyncio
async def test_service_create_application_same_name_different_tenants(db_session: AsyncSession):
    """Test: Can create same name across different tenants."""
    # Setup two tenants
    tenant_a = Tenant(id=uuid4(), name="Tenant A", slug="tenant-a", status="active")
    tenant_b = Tenant(id=uuid4(), name="Tenant B", slug="tenant-b", status="active")
    db_session.add(tenant_a)
    db_session.add(tenant_b)
    await db_session.flush()
    
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
    await db_session.commit()
    
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
    
    # Create applications with same name in different tenants
    payload = ApplicationCreate(name="Same Name App")
    
    app_a = await create_application(
        db_session,
        membership_ctx=membership_ctx_a,
        payload=payload,
    )
    
    app_b = await create_application(
        db_session,
        membership_ctx=membership_ctx_b,
        payload=payload,
    )
    
    assert app_a.name == "Same Name App"
    assert app_b.name == "Same Name App"
    assert app_a.tenant_id != app_b.tenant_id


@pytest.mark.asyncio
async def test_service_recreate_application_after_soft_delete(db_session: AsyncSession):
    """Test: Can recreate same name in same tenant after soft delete."""
    from datetime import datetime
    
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
    
    membership_ctx = TenancyContext(
        membership_id=membership.id,
        tenant_id=tenant.id,
        role="admin",
    )
    
    # Create and soft-delete application
    payload1 = ApplicationCreate(name="Reusable Name")
    app1 = await create_application(
        db_session,
        membership_ctx=membership_ctx,
        payload=payload1,
    )
    
    await delete_application(
        db_session,
        membership_ctx=membership_ctx,
        application_id=app1.id,
    )
    
    # Can recreate with same name
    payload2 = ApplicationCreate(name="Reusable Name")
    app2 = await create_application(
        db_session,
        membership_ctx=membership_ctx,
        payload=payload2,
    )
    
    assert app2.name == "Reusable Name"
    assert app2.id != app1.id
    assert app2.deleted_at is None

