"""Unit tests for projects service layer.

These tests verify business logic, tenant scoping, and audit metadata handling.
"""

from datetime import date, datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.tenancy import TenancyContext
from models.project import Project, ProjectBase, ProjectUpdate
from models.tenant import Tenant
from models.user import User
from models.user_tenant import UserTenant
from services.projects_service import (
    create_project,
    get_project,
    list_projects,
    update_project,
)


@pytest.mark.asyncio
async def test_service_create_project_sets_audit_metadata(db_session: AsyncSession):
    """Test: Creating a project sets row_version=1, updated_at=None."""
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
    
    # Create project
    payload = ProjectBase(
        name="Test Project",
        status="draft",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 12, 31),
    )
    
    project = await create_project(
        db_session,
        membership_ctx=membership_ctx,
        payload=payload,
    )
    
    assert project.row_version == 1
    assert project.updated_at is None  # Should be NULL on creation
    assert project.updated_by_membership_id is None  # Not set on creation
    assert project.deleted_at is None
    assert project.deleted_by_membership_id is None
    assert project.tenant_id == tenant.id
    assert project.created_by_membership_id == membership.id


@pytest.mark.asyncio
async def test_service_update_project_updates_audit_metadata(db_session: AsyncSession):
    """Test: Updating a project updates audit metadata and increments row_version."""
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
    
    # Create project
    project = Project(
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        name="Original Name",
        status="draft",
        row_version=1,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    
    initial_row_version = project.row_version
    initial_updated_at = project.updated_at
    
    membership_ctx = TenancyContext(
        membership_id=membership.id,
        tenant_id=tenant.id,
        role="admin",
    )
    
    # Update project
    payload = ProjectUpdate(
        name="Updated Project Name",
        status="active",
    )
    
    updated = await update_project(
        db_session,
        membership_ctx=membership_ctx,
        project_id=project.id,
        payload=payload,
        is_platform_admin=False,
    )
    
    assert updated.row_version == initial_row_version + 1
    assert updated.updated_at is not None
    assert updated.updated_at != initial_updated_at
    assert updated.updated_by_membership_id == membership.id
    assert updated.deleted_at is None
    assert updated.deleted_by_membership_id is None
    assert updated.name == "Updated Project Name"
    assert updated.status == "active"


@pytest.mark.asyncio
async def test_service_get_project_excludes_deleted(db_session: AsyncSession):
    """Test: Get project excludes soft-deleted projects."""
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
    
    # Create and soft-delete project
    project = Project(
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        name="Deleted Project",
        status="draft",
        row_version=1,
        deleted_at=datetime.utcnow(),
        deleted_by_membership_id=membership.id,
    )
    db_session.add(project)
    await db_session.commit()
    
    membership_ctx = TenancyContext(
        membership_id=membership.id,
        tenant_id=tenant.id,
        role="admin",
    )
    
    # Should raise 404 for deleted project
    with pytest.raises(HTTPException) as exc_info:
        await get_project(
            db_session,
            membership_ctx=membership_ctx,
            project_id=project.id,
            is_platform_admin=False,
        )
    
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_service_list_projects_tenant_scoped(db_session: AsyncSession):
    """Test: List projects is tenant-scoped."""
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
    project_a = Project(
        tenant_id=tenant_a.id,
        created_by_membership_id=membership_a.id,
        name="Project A",
        status="draft",
        row_version=1,
    )
    project_b = Project(
        tenant_id=tenant_b.id,
        created_by_membership_id=membership_b.id,
        name="Project B",
        status="draft",
        row_version=1,
    )
    db_session.add(project_a)
    db_session.add(project_b)
    await db_session.commit()
    
    membership_ctx_a = TenancyContext(
        membership_id=membership_a.id,
        tenant_id=tenant_a.id,
        role="admin",
    )
    
    # List projects for tenant_a should only return project_a
    projects = await list_projects(
        db_session,
        membership_ctx=membership_ctx_a,
        is_platform_admin=False,
    )
    
    assert len(projects) == 1
    assert projects[0].id == project_a.id
    assert projects[0].name == "Project A"

