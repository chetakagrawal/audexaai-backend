"""DB-backed tests for PbcRequest model.

These tests verify model behavior, database constraints, and query patterns
for the PbcRequest model. All tests use a real database session.
"""

from datetime import date, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.application import Application
from models.control import Control
from models.pbc_request import PbcRequest
from models.project import Project
from models.tenant import Tenant
from models.user import User
from models.user_tenant import UserTenant


@pytest.mark.asyncio
async def test_create_pbc_request_minimal(db_session: AsyncSession):
    """Test: Can create a PBC request with minimal required fields."""
    # Create tenant
    tenant = Tenant(
        id=uuid4(),
        name="Test Tenant",
        slug="test-tenant",
        status="active",
    )
    db_session.add(tenant)
    await db_session.flush()
    
    # Create user and membership
    user = User(
        id=uuid4(),
        primary_email="user@example.com",
        name="User",
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
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        name="Test Project",
        status="active",
    )
    db_session.add(project)
    await db_session.flush()
    
    # Create application
    application = Application(
        id=uuid4(),
        tenant_id=tenant.id,
        name="Test Application",
    )
    db_session.add(application)
    await db_session.flush()
    
    # Create control
    control = Control(
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-001",
        name="Test Control",
    )
    db_session.add(control)
    await db_session.flush()
    
    # Create PBC request (minimal - only required fields)
    pbc_request = PbcRequest(
        id=uuid4(),
        tenant_id=tenant.id,
        project_id=project.id,
        application_id=application.id,
        control_id=control.id,
        owner_membership_id=membership.id,
        title="Request Access Logs",
    )
    db_session.add(pbc_request)
    await db_session.commit()
    await db_session.refresh(pbc_request)
    
    assert pbc_request.id is not None
    assert pbc_request.tenant_id == tenant.id
    assert pbc_request.project_id == project.id
    assert pbc_request.application_id == application.id
    assert pbc_request.control_id == control.id
    assert pbc_request.owner_membership_id == membership.id
    assert pbc_request.title == "Request Access Logs"
    assert pbc_request.samples_requested is None
    assert pbc_request.due_date is None
    assert pbc_request.status == "pending"
    assert pbc_request.created_at is not None
    assert isinstance(pbc_request.created_at, datetime)


@pytest.mark.asyncio
async def test_create_pbc_request_with_all_fields(db_session: AsyncSession):
    """Test: Can create a PBC request with all fields populated."""
    # Create tenant
    tenant = Tenant(
        id=uuid4(),
        name="Test Tenant",
        slug="test-tenant-full",
        status="active",
    )
    db_session.add(tenant)
    await db_session.flush()
    
    # Create user and membership
    user = User(
        id=uuid4(),
        primary_email="user@example.com",
        name="User",
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
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        name="Test Project",
        status="active",
    )
    db_session.add(project)
    await db_session.flush()
    
    # Create application
    application = Application(
        id=uuid4(),
        tenant_id=tenant.id,
        name="Test Application",
    )
    db_session.add(application)
    await db_session.flush()
    
    # Create control
    control = Control(
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-002",
        name="Test Control",
    )
    db_session.add(control)
    await db_session.flush()
    
    # Create PBC request with all fields
    due = date(2025, 3, 15)
    pbc_request = PbcRequest(
        id=uuid4(),
        tenant_id=tenant.id,
        project_id=project.id,
        application_id=application.id,
        control_id=control.id,
        owner_membership_id=membership.id,
        title="Request User Access Reviews",
        samples_requested=25,
        due_date=due,
        status="in_progress",
    )
    db_session.add(pbc_request)
    await db_session.commit()
    await db_session.refresh(pbc_request)
    
    assert pbc_request.title == "Request User Access Reviews"
    assert pbc_request.samples_requested == 25
    assert pbc_request.due_date == due
    assert pbc_request.status == "in_progress"


@pytest.mark.asyncio
async def test_pbc_request_query_by_project(db_session: AsyncSession):
    """Test: Can query PBC requests by project_id."""
    # Create tenant
    tenant = Tenant(
        id=uuid4(),
        name="Test Tenant",
        slug="test-tenant-query",
        status="active",
    )
    db_session.add(tenant)
    await db_session.flush()
    
    # Create user and membership
    user = User(
        id=uuid4(),
        primary_email="user@example.com",
        name="User",
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
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        name="Test Project",
        status="active",
    )
    db_session.add(project)
    await db_session.flush()
    
    # Create application and control
    application = Application(
        id=uuid4(),
        tenant_id=tenant.id,
        name="Test Application",
    )
    db_session.add(application)
    
    control = Control(
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-003",
        name="Test Control",
    )
    db_session.add(control)
    await db_session.flush()
    
    # Create multiple PBC requests for the project
    pbc1 = PbcRequest(
        id=uuid4(),
        tenant_id=tenant.id,
        project_id=project.id,
        application_id=application.id,
        control_id=control.id,
        owner_membership_id=membership.id,
        title="PBC Request 1",
    )
    pbc2 = PbcRequest(
        id=uuid4(),
        tenant_id=tenant.id,
        project_id=project.id,
        application_id=application.id,
        control_id=control.id,
        owner_membership_id=membership.id,
        title="PBC Request 2",
    )
    db_session.add(pbc1)
    db_session.add(pbc2)
    await db_session.commit()
    
    # Query by project_id
    result = await db_session.execute(
        select(PbcRequest).where(PbcRequest.project_id == project.id)
    )
    pbc_requests = result.scalars().all()
    
    assert len(pbc_requests) == 2
    titles = [pbc.title for pbc in pbc_requests]
    assert "PBC Request 1" in titles
    assert "PBC Request 2" in titles


@pytest.mark.asyncio
async def test_pbc_request_cascade_delete_on_project(db_session: AsyncSession):
    """Test: Deleting a project cascades to delete PBC requests."""
    # Create tenant
    tenant = Tenant(
        id=uuid4(),
        name="Test Tenant",
        slug="test-tenant-cascade",
        status="active",
    )
    db_session.add(tenant)
    await db_session.flush()
    
    # Create user and membership
    user = User(
        id=uuid4(),
        primary_email="user@example.com",
        name="User",
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
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        name="Test Project",
        status="active",
    )
    db_session.add(project)
    await db_session.flush()
    
    # Create application and control
    application = Application(
        id=uuid4(),
        tenant_id=tenant.id,
        name="Test Application",
    )
    db_session.add(application)
    
    control = Control(
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-004",
        name="Test Control",
    )
    db_session.add(control)
    await db_session.flush()
    
    # Create PBC request
    pbc_request = PbcRequest(
        id=uuid4(),
        tenant_id=tenant.id,
        project_id=project.id,
        application_id=application.id,
        control_id=control.id,
        owner_membership_id=membership.id,
        title="Test PBC Request",
    )
    db_session.add(pbc_request)
    await db_session.commit()
    
    pbc_request_id = pbc_request.id
    
    # Verify PBC request exists
    result = await db_session.execute(
        select(PbcRequest).where(PbcRequest.id == pbc_request_id)
    )
    assert result.scalar_one_or_none() is not None
    
    # Delete project (should cascade)
    await db_session.delete(project)
    await db_session.commit()
    
    # Verify PBC request is deleted
    result = await db_session.execute(
        select(PbcRequest).where(PbcRequest.id == pbc_request_id)
    )
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_pbc_request_cascade_delete_on_control(db_session: AsyncSession):
    """Test: Deleting a control cascades to delete PBC requests."""
    # Create tenant
    tenant = Tenant(
        id=uuid4(),
        name="Test Tenant",
        slug="test-tenant-ctrl-cascade",
        status="active",
    )
    db_session.add(tenant)
    await db_session.flush()
    
    # Create user and membership
    user = User(
        id=uuid4(),
        primary_email="user@example.com",
        name="User",
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
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        name="Test Project",
        status="active",
    )
    db_session.add(project)
    await db_session.flush()
    
    # Create application
    application = Application(
        id=uuid4(),
        tenant_id=tenant.id,
        name="Test Application",
    )
    db_session.add(application)
    await db_session.flush()
    
    # Create control
    control = Control(
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-005",
        name="Test Control",
    )
    db_session.add(control)
    await db_session.flush()
    
    # Create PBC request
    pbc_request = PbcRequest(
        id=uuid4(),
        tenant_id=tenant.id,
        project_id=project.id,
        application_id=application.id,
        control_id=control.id,
        owner_membership_id=membership.id,
        title="Test PBC Request",
    )
    db_session.add(pbc_request)
    await db_session.commit()
    
    pbc_request_id = pbc_request.id
    
    # Delete control (should cascade)
    await db_session.delete(control)
    await db_session.commit()
    
    # Verify PBC request is deleted
    result = await db_session.execute(
        select(PbcRequest).where(PbcRequest.id == pbc_request_id)
    )
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_pbc_request_cascade_delete_on_tenant(db_session: AsyncSession):
    """Test: Deleting a tenant cascades to delete PBC requests."""
    # Create tenant
    tenant = Tenant(
        id=uuid4(),
        name="Test Tenant",
        slug="test-tenant-tenant-cascade",
        status="active",
    )
    db_session.add(tenant)
    await db_session.flush()
    
    # Create user and membership
    user = User(
        id=uuid4(),
        primary_email="user@example.com",
        name="User",
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
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        name="Test Project",
        status="active",
    )
    db_session.add(project)
    await db_session.flush()
    
    # Create application and control
    application = Application(
        id=uuid4(),
        tenant_id=tenant.id,
        name="Test Application",
    )
    db_session.add(application)
    
    control = Control(
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-006",
        name="Test Control",
    )
    db_session.add(control)
    await db_session.flush()
    
    # Create PBC request
    pbc_request = PbcRequest(
        id=uuid4(),
        tenant_id=tenant.id,
        project_id=project.id,
        application_id=application.id,
        control_id=control.id,
        owner_membership_id=membership.id,
        title="Test PBC Request",
    )
    db_session.add(pbc_request)
    await db_session.commit()
    
    pbc_request_id = pbc_request.id
    
    # Delete tenant (should cascade)
    await db_session.delete(tenant)
    await db_session.commit()
    
    # Verify PBC request is deleted
    result = await db_session.execute(
        select(PbcRequest).where(PbcRequest.id == pbc_request_id)
    )
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_pbc_request_tenant_isolation(db_session: AsyncSession):
    """Test: PBC requests are isolated by tenant."""
    # Create two tenants
    tenant_a = Tenant(
        id=uuid4(),
        name="Tenant A",
        slug="tenant-a",
        status="active",
    )
    tenant_b = Tenant(
        id=uuid4(),
        name="Tenant B",
        slug="tenant-b",
        status="active",
    )
    db_session.add(tenant_a)
    db_session.add(tenant_b)
    await db_session.flush()
    
    # Create users and memberships for both tenants
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
    await db_session.flush()
    
    # Create projects in each tenant
    project_a = Project(
        id=uuid4(),
        tenant_id=tenant_a.id,
        created_by_membership_id=membership_a.id,
        name="Project A",
        status="active",
    )
    project_b = Project(
        id=uuid4(),
        tenant_id=tenant_b.id,
        created_by_membership_id=membership_b.id,
        name="Project B",
        status="active",
    )
    db_session.add(project_a)
    db_session.add(project_b)
    await db_session.flush()
    
    # Create applications and controls
    app_a = Application(id=uuid4(), tenant_id=tenant_a.id, name="App A")
    app_b = Application(id=uuid4(), tenant_id=tenant_b.id, name="App B")
    db_session.add(app_a)
    db_session.add(app_b)
    
    control_a = Control(
        id=uuid4(),
        tenant_id=tenant_a.id,
        created_by_membership_id=membership_a.id,
        control_code="AC-001",
        name="Control A",
    )
    control_b = Control(
        id=uuid4(),
        tenant_id=tenant_b.id,
        created_by_membership_id=membership_b.id,
        control_code="AC-001",
        name="Control B",
    )
    db_session.add(control_a)
    db_session.add(control_b)
    await db_session.flush()
    
    # Create PBC requests in each tenant
    pbc_a = PbcRequest(
        id=uuid4(),
        tenant_id=tenant_a.id,
        project_id=project_a.id,
        application_id=app_a.id,
        control_id=control_a.id,
        owner_membership_id=membership_a.id,
        title="PBC Request A",
    )
    pbc_b = PbcRequest(
        id=uuid4(),
        tenant_id=tenant_b.id,
        project_id=project_b.id,
        application_id=app_b.id,
        control_id=control_b.id,
        owner_membership_id=membership_b.id,
        title="PBC Request B",
    )
    db_session.add(pbc_a)
    db_session.add(pbc_b)
    await db_session.commit()
    
    # Query PBC requests for tenant_a - should only see tenant_a's
    result = await db_session.execute(
        select(PbcRequest).where(PbcRequest.tenant_id == tenant_a.id)
    )
    pbc_requests_a = result.scalars().all()
    
    assert len(pbc_requests_a) == 1
    assert pbc_requests_a[0].id == pbc_a.id
    assert pbc_requests_a[0].tenant_id == tenant_a.id
    
    # Query PBC requests for tenant_b - should only see tenant_b's
    result = await db_session.execute(
        select(PbcRequest).where(PbcRequest.tenant_id == tenant_b.id)
    )
    pbc_requests_b = result.scalars().all()
    
    assert len(pbc_requests_b) == 1
    assert pbc_requests_b[0].id == pbc_b.id
    assert pbc_requests_b[0].tenant_id == tenant_b.id


@pytest.mark.asyncio
async def test_pbc_request_query_by_status(db_session: AsyncSession):
    """Test: Can query PBC requests by status."""
    # Create tenant
    tenant = Tenant(
        id=uuid4(),
        name="Test Tenant",
        slug="test-tenant-status",
        status="active",
    )
    db_session.add(tenant)
    await db_session.flush()
    
    # Create user and membership
    user = User(
        id=uuid4(),
        primary_email="user@example.com",
        name="User",
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
    
    # Create project, application, control
    project = Project(
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        name="Test Project",
        status="active",
    )
    db_session.add(project)
    
    application = Application(id=uuid4(), tenant_id=tenant.id, name="Test App")
    db_session.add(application)
    
    control = Control(
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-007",
        name="Test Control",
    )
    db_session.add(control)
    await db_session.flush()
    
    # Create PBC requests with different statuses
    pbc_pending = PbcRequest(
        id=uuid4(),
        tenant_id=tenant.id,
        project_id=project.id,
        application_id=application.id,
        control_id=control.id,
        owner_membership_id=membership.id,
        title="Pending Request",
        status="pending",
    )
    pbc_complete = PbcRequest(
        id=uuid4(),
        tenant_id=tenant.id,
        project_id=project.id,
        application_id=application.id,
        control_id=control.id,
        owner_membership_id=membership.id,
        title="Completed Request",
        status="completed",
    )
    db_session.add(pbc_pending)
    db_session.add(pbc_complete)
    await db_session.commit()
    
    # Query by status
    result = await db_session.execute(
        select(PbcRequest).where(
            PbcRequest.tenant_id == tenant.id,
            PbcRequest.status == "pending",
        )
    )
    pending_requests = result.scalars().all()
    
    assert len(pending_requests) == 1
    assert pending_requests[0].title == "Pending Request"
    
    result = await db_session.execute(
        select(PbcRequest).where(
            PbcRequest.tenant_id == tenant.id,
            PbcRequest.status == "completed",
        )
    )
    completed_requests = result.scalars().all()
    
    assert len(completed_requests) == 1
    assert completed_requests[0].title == "Completed Request"
