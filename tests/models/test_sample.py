"""
Tests for Sample model.

Tests basic CRUD operations, relationships, cascade deletes, and tenant isolation.
"""

import pytest
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.tenant import Tenant
from models.user import User
from models.user_tenant import UserTenant
from models.project import Project
from models.application import Application
from models.control import Control
from models.pbc_request import PbcRequest
from models.sample import Sample


@pytest.mark.asyncio
async def test_create_sample_minimal(db_session: AsyncSession):
    """Test creating a sample with minimal required fields"""
    # Setup tenant, user, membership
    tenant = Tenant(id=uuid4(), name="Test Tenant", slug="test-tenant", status="active")
    db_session.add(tenant)
    await db_session.flush()

    user = User(
        id=uuid4(),
        primary_email="test@example.com",
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
        role="auditor",
        is_default=True,
    )
    db_session.add(membership)
    await db_session.flush()

    # Setup project, application, control
    project = Project(
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        name="Test Project",
        status="active",
    )
    db_session.add(project)
    await db_session.flush()

    application = Application(
        id=uuid4(),
        tenant_id=tenant.id,
        name="Test App",
        category="Web Application",
    )
    db_session.add(application)
    await db_session.flush()

    control = Control(
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-001",
        name="Access Control",
        is_key=True,
        is_automated=False,
    )
    db_session.add(control)
    await db_session.flush()

    # Setup PBC request
    pbc_request = PbcRequest(
        id=uuid4(),
        tenant_id=tenant.id,
        project_id=project.id,
        application_id=application.id,
        control_id=control.id,
        owner_membership_id=membership.id,
        title="Request Access Logs",
        status="pending",
    )
    db_session.add(pbc_request)
    await db_session.flush()

    # Create sample
    sample = Sample(
        id=uuid4(),
        tenant_id=tenant.id,
        pbc_request_id=pbc_request.id,
        sample_number=1,
        identifier="TXN-2025-001",
    )
    db_session.add(sample)
    await db_session.commit()
    await db_session.refresh(sample)

    # Assertions
    assert sample.id is not None
    assert sample.tenant_id == tenant.id
    assert sample.pbc_request_id == pbc_request.id
    assert sample.sample_number == 1
    assert sample.identifier == "TXN-2025-001"
    assert sample.status == "pending"  # default value
    assert sample.description is None
    assert sample.test_notes is None
    assert sample.tested_at is None
    assert sample.tested_by_membership_id is None
    assert sample.created_at is not None


@pytest.mark.asyncio
async def test_create_sample_full_fields(db_session: AsyncSession):
    """Test creating a sample with all fields populated"""
    # Setup tenant, user, membership
    tenant = Tenant(id=uuid4(), name="Test Tenant", slug="test-tenant", status="active")
    db_session.add(tenant)
    await db_session.flush()

    user = User(
        id=uuid4(),
        primary_email="test@example.com",
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
        role="auditor",
        is_default=True,
    )
    db_session.add(membership)
    await db_session.flush()

    # Setup project, application, control
    project = Project(
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        name="Test Project",
        status="active",
    )
    db_session.add(project)
    await db_session.flush()

    application = Application(
        id=uuid4(),
        tenant_id=tenant.id,
        name="Test App",
        category="Web Application",
    )
    db_session.add(application)
    await db_session.flush()

    control = Control(
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-001",
        name="Access Control",
        is_key=True,
        is_automated=False,
    )
    db_session.add(control)
    await db_session.flush()

    # Setup PBC request
    pbc_request = PbcRequest(
        id=uuid4(),
        tenant_id=tenant.id,
        project_id=project.id,
        application_id=application.id,
        control_id=control.id,
        owner_membership_id=membership.id,
        title="Request Access Logs",
        status="pending",
    )
    db_session.add(pbc_request)
    await db_session.flush()

    # Create sample with all fields
    from datetime import timezone
    tested_at = datetime.now(timezone.utc)
    sample = Sample(
        id=uuid4(),
        tenant_id=tenant.id,
        pbc_request_id=pbc_request.id,
        sample_number=5,
        identifier="TXN-2025-042",
        description="User login transaction for John Doe",
        status="tested",
        test_notes="Verified access controls are working correctly. No exceptions found.",
        tested_at=tested_at,
        tested_by_membership_id=membership.id,
    )
    db_session.add(sample)
    await db_session.commit()
    await db_session.refresh(sample)

    # Assertions
    assert sample.id is not None
    assert sample.sample_number == 5
    assert sample.identifier == "TXN-2025-042"
    assert sample.description == "User login transaction for John Doe"
    assert sample.status == "tested"
    assert sample.test_notes == "Verified access controls are working correctly. No exceptions found."
    assert sample.tested_at == tested_at
    assert sample.tested_by_membership_id == membership.id


@pytest.mark.asyncio
async def test_query_samples_by_pbc_request(db_session: AsyncSession):
    """Test querying samples by PBC request"""
    # Setup tenant, user, membership
    tenant = Tenant(id=uuid4(), name="Test Tenant", slug="test-tenant", status="active")
    db_session.add(tenant)
    await db_session.flush()

    user = User(
        id=uuid4(),
        primary_email="test@example.com",
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
        role="auditor",
        is_default=True,
    )
    db_session.add(membership)
    await db_session.flush()

    # Setup project, application, control
    project = Project(
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        name="Test Project",
        status="active",
    )
    db_session.add(project)
    await db_session.flush()

    application = Application(
        id=uuid4(),
        tenant_id=tenant.id,
        name="Test App",
        category="Web Application",
    )
    db_session.add(application)
    await db_session.flush()

    control = Control(
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-001",
        name="Access Control",
        is_key=True,
        is_automated=False,
    )
    db_session.add(control)
    await db_session.flush()

    # Setup PBC request
    pbc_request = PbcRequest(
        id=uuid4(),
        tenant_id=tenant.id,
        project_id=project.id,
        application_id=application.id,
        control_id=control.id,
        owner_membership_id=membership.id,
        title="Request Access Logs",
        status="pending",
    )
    db_session.add(pbc_request)
    await db_session.flush()

    # Create multiple samples
    sample1 = Sample(
        id=uuid4(),
        tenant_id=tenant.id,
        pbc_request_id=pbc_request.id,
        sample_number=1,
        identifier="TXN-001",
    )
    sample2 = Sample(
        id=uuid4(),
        tenant_id=tenant.id,
        pbc_request_id=pbc_request.id,
        sample_number=2,
        identifier="TXN-002",
    )
    db_session.add_all([sample1, sample2])
    await db_session.commit()

    # Query samples by PBC request
    result = await db_session.execute(
        select(Sample).where(Sample.pbc_request_id == pbc_request.id)
    )
    samples = result.scalars().all()

    # Assertions
    assert len(samples) == 2
    assert samples[0].pbc_request_id == pbc_request.id
    assert samples[1].pbc_request_id == pbc_request.id


@pytest.mark.asyncio
async def test_sample_cascade_delete_on_pbc_request(db_session: AsyncSession):
    """Test that samples are deleted when PBC request is deleted"""
    # Setup tenant, user, membership
    tenant = Tenant(id=uuid4(), name="Test Tenant", slug="test-tenant", status="active")
    db_session.add(tenant)
    await db_session.flush()

    user = User(
        id=uuid4(),
        primary_email="test@example.com",
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
        role="auditor",
        is_default=True,
    )
    db_session.add(membership)
    await db_session.flush()

    # Setup project, application, control
    project = Project(
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        name="Test Project",
        status="active",
    )
    db_session.add(project)
    await db_session.flush()

    application = Application(
        id=uuid4(),
        tenant_id=tenant.id,
        name="Test App",
        category="Web Application",
    )
    db_session.add(application)
    await db_session.flush()

    control = Control(
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-001",
        name="Access Control",
        is_key=True,
        is_automated=False,
    )
    db_session.add(control)
    await db_session.flush()

    # Setup PBC request
    pbc_request = PbcRequest(
        id=uuid4(),
        tenant_id=tenant.id,
        project_id=project.id,
        application_id=application.id,
        control_id=control.id,
        owner_membership_id=membership.id,
        title="Request Access Logs",
        status="pending",
    )
    db_session.add(pbc_request)
    await db_session.flush()

    # Create sample
    sample = Sample(
        id=uuid4(),
        tenant_id=tenant.id,
        pbc_request_id=pbc_request.id,
        sample_number=1,
        identifier="TXN-001",
    )
    db_session.add(sample)
    await db_session.flush()
    sample_id = sample.id

    # Delete PBC request
    await db_session.delete(pbc_request)
    await db_session.commit()

    # Verify sample was deleted (cascade)
    result = await db_session.execute(select(Sample).where(Sample.id == sample_id))
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_sample_cascade_delete_on_tenant(db_session: AsyncSession):
    """Test that samples are deleted when tenant is deleted"""
    # Setup tenant, user, membership
    tenant = Tenant(id=uuid4(), name="Test Tenant", slug="test-tenant", status="active")
    db_session.add(tenant)
    await db_session.flush()

    user = User(
        id=uuid4(),
        primary_email="test@example.com",
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
        role="auditor",
        is_default=True,
    )
    db_session.add(membership)
    await db_session.flush()

    # Setup project, application, control
    project = Project(
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        name="Test Project",
        status="active",
    )
    db_session.add(project)
    await db_session.flush()

    application = Application(
        id=uuid4(),
        tenant_id=tenant.id,
        name="Test App",
        category="Web Application",
    )
    db_session.add(application)
    await db_session.flush()

    control = Control(
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-001",
        name="Access Control",
        is_key=True,
        is_automated=False,
    )
    db_session.add(control)
    await db_session.flush()

    # Setup PBC request
    pbc_request = PbcRequest(
        id=uuid4(),
        tenant_id=tenant.id,
        project_id=project.id,
        application_id=application.id,
        control_id=control.id,
        owner_membership_id=membership.id,
        title="Request Access Logs",
        status="pending",
    )
    db_session.add(pbc_request)
    await db_session.flush()

    # Create sample
    sample = Sample(
        id=uuid4(),
        tenant_id=tenant.id,
        pbc_request_id=pbc_request.id,
        sample_number=1,
        identifier="TXN-001",
    )
    db_session.add(sample)
    await db_session.flush()
    sample_id = sample.id

    # Delete tenant
    await db_session.delete(tenant)
    await db_session.commit()

    # Verify sample was deleted (cascade)
    result = await db_session.execute(select(Sample).where(Sample.id == sample_id))
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_sample_tested_by_nullified_on_membership_delete(db_session: AsyncSession):
    """Test that tested_by_membership_id is set to NULL when membership is deleted"""
    # Setup tenant, user, membership
    tenant = Tenant(id=uuid4(), name="Test Tenant", slug="test-tenant", status="active")
    db_session.add(tenant)
    await db_session.flush()

    user1 = User(
        id=uuid4(),
        primary_email="test1@example.com",
        name="Test User 1",
        is_platform_admin=False,
        is_active=True,
    )
    user2 = User(
        id=uuid4(),
        primary_email="test2@example.com",
        name="Test User 2",
        is_platform_admin=False,
        is_active=True,
    )
    db_session.add_all([user1, user2])
    await db_session.flush()

    membership1 = UserTenant(
        id=uuid4(),
        user_id=user1.id,
        tenant_id=tenant.id,
        role="auditor",
        is_default=True,
    )
    membership2 = UserTenant(
        id=uuid4(),
        user_id=user2.id,
        tenant_id=tenant.id,
        role="auditor",
        is_default=True,
    )
    db_session.add_all([membership1, membership2])
    await db_session.flush()

    # Setup project, application, control
    project = Project(
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership1.id,
        name="Test Project",
        status="active",
    )
    db_session.add(project)
    await db_session.flush()

    application = Application(
        id=uuid4(),
        tenant_id=tenant.id,
        name="Test App",
        category="Web Application",
    )
    db_session.add(application)
    await db_session.flush()

    control = Control(
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership1.id,
        control_code="AC-001",
        name="Access Control",
        is_key=True,
        is_automated=False,
    )
    db_session.add(control)
    await db_session.flush()

    # Setup PBC request
    pbc_request = PbcRequest(
        id=uuid4(),
        tenant_id=tenant.id,
        project_id=project.id,
        application_id=application.id,
        control_id=control.id,
        owner_membership_id=membership1.id,
        title="Request Access Logs",
        status="pending",
    )
    db_session.add(pbc_request)
    await db_session.flush()

    # Create sample tested by membership2
    sample = Sample(
        id=uuid4(),
        tenant_id=tenant.id,
        pbc_request_id=pbc_request.id,
        sample_number=1,
        identifier="TXN-001",
        tested_by_membership_id=membership2.id,
    )
    db_session.add(sample)
    await db_session.flush()
    sample_id = sample.id

    # Delete membership2
    await db_session.delete(membership2)
    await db_session.commit()

    # Expire all objects to ensure we get fresh data from DB
    db_session.expire_all()

    # Verify sample still exists but tested_by_membership_id is NULL
    result = await db_session.execute(select(Sample).where(Sample.id == sample_id))
    updated_sample = result.scalar_one_or_none()
    assert updated_sample is not None
    assert updated_sample.tested_by_membership_id is None


@pytest.mark.asyncio
async def test_tenant_isolation(db_session: AsyncSession):
    """Test that samples are isolated by tenant"""
    # Setup tenant A
    tenant_a = Tenant(id=uuid4(), name="Tenant A", slug="tenant-a", status="active")
    db_session.add(tenant_a)
    await db_session.flush()

    user_a = User(
        id=uuid4(),
        primary_email="usera@example.com",
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
        role="auditor",
        is_default=True,
    )
    db_session.add(membership_a)
    await db_session.flush()

    project_a = Project(
        id=uuid4(),
        tenant_id=tenant_a.id,
        created_by_membership_id=membership_a.id,
        name="Project A",
        status="active",
    )
    db_session.add(project_a)
    await db_session.flush()

    application_a = Application(
        id=uuid4(),
        tenant_id=tenant_a.id,
        name="App A",
        category="Web Application",
    )
    db_session.add(application_a)
    await db_session.flush()

    control_a = Control(
        id=uuid4(),
        tenant_id=tenant_a.id,
        created_by_membership_id=membership_a.id,
        control_code="AC-001",
        name="Control A",
        is_key=True,
        is_automated=False,
    )
    db_session.add(control_a)
    await db_session.flush()

    pbc_request_a = PbcRequest(
        id=uuid4(),
        tenant_id=tenant_a.id,
        project_id=project_a.id,
        application_id=application_a.id,
        control_id=control_a.id,
        owner_membership_id=membership_a.id,
        title="Request A",
        status="pending",
    )
    db_session.add(pbc_request_a)
    await db_session.flush()

    # Setup tenant B
    tenant_b = Tenant(id=uuid4(), name="Tenant B", slug="tenant-b", status="active")
    db_session.add(tenant_b)
    await db_session.flush()

    user_b = User(
        id=uuid4(),
        primary_email="userb@example.com",
        name="User B",
        is_platform_admin=False,
        is_active=True,
    )
    db_session.add(user_b)
    await db_session.flush()

    membership_b = UserTenant(
        id=uuid4(),
        user_id=user_b.id,
        tenant_id=tenant_b.id,
        role="auditor",
        is_default=True,
    )
    db_session.add(membership_b)
    await db_session.flush()

    project_b = Project(
        id=uuid4(),
        tenant_id=tenant_b.id,
        created_by_membership_id=membership_b.id,
        name="Project B",
        status="active",
    )
    db_session.add(project_b)
    await db_session.flush()

    application_b = Application(
        id=uuid4(),
        tenant_id=tenant_b.id,
        name="App B",
        category="Web Application",
    )
    db_session.add(application_b)
    await db_session.flush()

    control_b = Control(
        id=uuid4(),
        tenant_id=tenant_b.id,
        created_by_membership_id=membership_b.id,
        control_code="AC-001",
        name="Control B",
        is_key=True,
        is_automated=False,
    )
    db_session.add(control_b)
    await db_session.flush()

    pbc_request_b = PbcRequest(
        id=uuid4(),
        tenant_id=tenant_b.id,
        project_id=project_b.id,
        application_id=application_b.id,
        control_id=control_b.id,
        owner_membership_id=membership_b.id,
        title="Request B",
        status="pending",
    )
    db_session.add(pbc_request_b)
    await db_session.flush()

    # Create samples for each tenant
    sample_a = Sample(
        id=uuid4(),
        tenant_id=tenant_a.id,
        pbc_request_id=pbc_request_a.id,
        sample_number=1,
        identifier="TXN-A-001",
    )
    sample_b = Sample(
        id=uuid4(),
        tenant_id=tenant_b.id,
        pbc_request_id=pbc_request_b.id,
        sample_number=1,
        identifier="TXN-B-001",
    )
    db_session.add_all([sample_a, sample_b])
    await db_session.commit()

    # Query samples for tenant A
    result_a = await db_session.execute(
        select(Sample).where(Sample.tenant_id == tenant_a.id)
    )
    samples_a = result_a.scalars().all()

    # Query samples for tenant B
    result_b = await db_session.execute(
        select(Sample).where(Sample.tenant_id == tenant_b.id)
    )
    samples_b = result_b.scalars().all()

    # Assertions
    assert len(samples_a) == 1
    assert samples_a[0].identifier == "TXN-A-001"
    assert len(samples_b) == 1
    assert samples_b[0].identifier == "TXN-B-001"
