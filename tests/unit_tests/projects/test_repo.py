"""Unit tests for projects repository layer.

These tests verify database operations in isolation.
"""

from datetime import date, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from models.project import Project
from models.tenant import Tenant
from models.user import User
from models.user_tenant import UserTenant
from repos import projects_repo


@pytest.mark.asyncio
async def test_repo_create_project(db_session: AsyncSession):
    """Test: Repository can create a project."""
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
    
    # Create project
    project = Project(
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        name="Test Project",
        status="draft",
        row_version=1,
    )
    
    created = await projects_repo.create(db_session, project)
    await db_session.commit()
    
    assert created.id is not None
    assert created.name == "Test Project"
    assert created.status == "draft"
    assert created.tenant_id == tenant.id
    assert created.row_version == 1


@pytest.mark.asyncio
async def test_repo_get_by_id_found(db_session: AsyncSession):
    """Test: Repository can retrieve a project by ID."""
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
    
    # Create project
    project = Project(
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        name="Test Project",
        status="active",
        row_version=1,
    )
    db_session.add(project)
    await db_session.commit()
    
    # Retrieve
    found = await projects_repo.get_by_id(
        db_session,
        tenant_id=tenant.id,
        project_id=project.id,
        include_deleted=False,
    )
    
    assert found is not None
    assert found.id == project.id
    assert found.name == "Test Project"


@pytest.mark.asyncio
async def test_repo_get_by_id_not_found(db_session: AsyncSession):
    """Test: Repository returns None for non-existent project."""
    tenant = Tenant(id=uuid4(), name="Test Tenant", slug="test-tenant", status="active")
    db_session.add(tenant)
    await db_session.commit()
    
    fake_id = uuid4()
    found = await projects_repo.get_by_id(
        db_session,
        tenant_id=tenant.id,
        project_id=fake_id,
        include_deleted=False,
    )
    
    assert found is None


@pytest.mark.asyncio
async def test_repo_get_by_id_excludes_deleted(db_session: AsyncSession):
    """Test: Repository excludes soft-deleted projects by default."""
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
    
    # Create and soft-delete project
    project = Project(
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        name="Test Project",
        status="draft",
        row_version=1,
        deleted_at=datetime.utcnow(),
        deleted_by_membership_id=membership.id,
    )
    db_session.add(project)
    await db_session.commit()
    
    # Should not find deleted project
    found = await projects_repo.get_by_id(
        db_session,
        tenant_id=tenant.id,
        project_id=project.id,
        include_deleted=False,
    )
    
    assert found is None
    
    # Should find deleted project when include_deleted=True
    found_deleted = await projects_repo.get_by_id(
        db_session,
        tenant_id=tenant.id,
        project_id=project.id,
        include_deleted=True,
    )
    
    assert found_deleted is not None
    assert found_deleted.id == project.id


@pytest.mark.asyncio
async def test_repo_list_projects(db_session: AsyncSession):
    """Test: Repository can list projects for a tenant."""
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
    
    # Create projects in both tenants
    project_a1 = Project(
        tenant_id=tenant_a.id,
        created_by_membership_id=membership_a.id,
        name="Project A1",
        status="draft",
        row_version=1,
    )
    project_a2 = Project(
        tenant_id=tenant_a.id,
        created_by_membership_id=membership_a.id,
        name="Project A2",
        status="active",
        row_version=1,
    )
    project_b1 = Project(
        tenant_id=tenant_b.id,
        created_by_membership_id=membership_b.id,
        name="Project B1",
        status="draft",
        row_version=1,
    )
    db_session.add(project_a1)
    db_session.add(project_a2)
    db_session.add(project_b1)
    await db_session.commit()
    
    # List projects for tenant_a
    projects_a = await projects_repo.list(
        db_session,
        tenant_id=tenant_a.id,
        include_deleted=False,
    )
    
    assert len(projects_a) == 2
    project_ids = {p.id for p in projects_a}
    assert project_a1.id in project_ids
    assert project_a2.id in project_ids
    assert project_b1.id not in project_ids
    
    # List projects for tenant_b
    projects_b = await projects_repo.list(
        db_session,
        tenant_id=tenant_b.id,
        include_deleted=False,
    )
    
    assert len(projects_b) == 1
    assert projects_b[0].id == project_b1.id


@pytest.mark.asyncio
async def test_repo_list_excludes_deleted(db_session: AsyncSession):
    """Test: Repository list excludes soft-deleted projects by default."""
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
    
    # Create active and deleted projects
    project_active = Project(
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        name="Active Project",
        status="active",
        row_version=1,
    )
    project_deleted = Project(
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        name="Deleted Project",
        status="draft",
        row_version=1,
        deleted_at=datetime.utcnow(),
        deleted_by_membership_id=membership.id,
    )
    db_session.add(project_active)
    db_session.add(project_deleted)
    await db_session.commit()
    
    # List should exclude deleted
    projects = await projects_repo.list(
        db_session,
        tenant_id=tenant.id,
        include_deleted=False,
    )
    
    assert len(projects) == 1
    assert projects[0].id == project_active.id
    
    # List with include_deleted=True should include both
    projects_all = await projects_repo.list(
        db_session,
        tenant_id=tenant.id,
        include_deleted=True,
    )
    
    assert len(projects_all) == 2

