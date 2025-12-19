"""Unit tests for applications repository layer.

These tests verify database operations in isolation.
"""

from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from models.application import Application
from models.tenant import Tenant
from models.user import User
from models.user_tenant import UserTenant
from repos import applications_repo


@pytest.mark.asyncio
async def test_repo_create_application(db_session: AsyncSession):
    """Test: Repository can create an application."""
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
    
    # Create application
    application = Application(
        tenant_id=tenant.id,
        name="Test Application",
        category="Financial",
        scope_rationale="Test scope",
    )
    
    created = await applications_repo.create(db_session, application)
    await db_session.commit()
    
    assert created.id is not None
    assert created.name == "Test Application"
    assert created.category == "Financial"
    assert created.tenant_id == tenant.id


@pytest.mark.asyncio
async def test_repo_get_by_id_found(db_session: AsyncSession):
    """Test: Repository can retrieve an application by ID."""
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
    
    # Get by ID
    found = await applications_repo.get_by_id(
        db_session,
        tenant_id=tenant.id,
        application_id=application.id,
        include_deleted=False,
    )
    
    assert found is not None
    assert found.id == application.id
    assert found.name == "Test Application"
    assert found.tenant_id == tenant.id


@pytest.mark.asyncio
async def test_repo_get_by_id_not_found(db_session: AsyncSession):
    """Test: Repository returns None when application not found."""
    tenant = Tenant(id=uuid4(), name="Test Tenant", slug="test-tenant", status="active")
    db_session.add(tenant)
    await db_session.flush()
    
    fake_id = uuid4()
    
    found = await applications_repo.get_by_id(
        db_session,
        tenant_id=tenant.id,
        application_id=fake_id,
        include_deleted=False,
    )
    
    assert found is None


@pytest.mark.asyncio
async def test_repo_get_by_id_tenant_isolation(db_session: AsyncSession):
    """Test: Repository enforces tenant isolation."""
    # Setup two tenants
    tenant_a = Tenant(id=uuid4(), name="Tenant A", slug="tenant-a", status="active")
    tenant_b = Tenant(id=uuid4(), name="Tenant B", slug="tenant-b", status="active")
    db_session.add(tenant_a)
    db_session.add(tenant_b)
    await db_session.flush()
    
    # Create application in Tenant A
    app_a = Application(
        tenant_id=tenant_a.id,
        name="Tenant A App",
    )
    db_session.add(app_a)
    await db_session.commit()
    await db_session.refresh(app_a)
    
    # Try to get from Tenant B (should return None)
    found = await applications_repo.get_by_id(
        db_session,
        tenant_id=tenant_b.id,
        application_id=app_a.id,
        include_deleted=False,
    )
    
    assert found is None


@pytest.mark.asyncio
async def test_repo_list_applications(db_session: AsyncSession):
    """Test: Repository can list applications for a tenant."""
    # Setup
    tenant_a = Tenant(id=uuid4(), name="Tenant A", slug="tenant-a", status="active")
    tenant_b = Tenant(id=uuid4(), name="Tenant B", slug="tenant-b", status="active")
    db_session.add(tenant_a)
    db_session.add(tenant_b)
    await db_session.flush()
    
    # Create applications in Tenant A
    app_a1 = Application(tenant_id=tenant_a.id, name="App A1")
    app_a2 = Application(tenant_id=tenant_a.id, name="App A2")
    # Create application in Tenant B
    app_b1 = Application(tenant_id=tenant_b.id, name="App B1")
    
    db_session.add(app_a1)
    db_session.add(app_a2)
    db_session.add(app_b1)
    await db_session.commit()
    
    # List Tenant A applications
    apps = await applications_repo.list(
        db_session,
        tenant_id=tenant_a.id,
        include_deleted=False,
    )
    
    assert len(apps) == 2
    names = {app.name for app in apps}
    assert "App A1" in names
    assert "App A2" in names
    assert "App B1" not in names


@pytest.mark.asyncio
async def test_repo_list_empty(db_session: AsyncSession):
    """Test: Repository returns empty list when no applications exist."""
    tenant = Tenant(id=uuid4(), name="Test Tenant", slug="test-tenant", status="active")
    db_session.add(tenant)
    await db_session.flush()
    
    apps = await applications_repo.list(
        db_session,
        tenant_id=tenant.id,
        include_deleted=False,
    )
    
    assert apps == []


@pytest.mark.asyncio
async def test_repo_save_application(db_session: AsyncSession):
    """Test: Repository can save (update) an application."""
    # Setup
    tenant = Tenant(id=uuid4(), name="Test Tenant", slug="test-tenant", status="active")
    db_session.add(tenant)
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
    
    # Update application
    application.name = "Updated Name"
    application.category = "Updated Category"
    
    saved = await applications_repo.save(db_session, application)
    await db_session.commit()
    await db_session.refresh(saved)
    
    assert saved.name == "Updated Name"
    assert saved.category == "Updated Category"

