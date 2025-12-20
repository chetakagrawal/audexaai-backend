"""Unit tests for project_control_applications repository layer (TDD - write failing tests first)."""

import pytest
from datetime import datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from models.project_control_application import ProjectControlApplication
from models.project_control import ProjectControl
from models.project import Project
from models.control import Control
from models.application import Application
from models.tenant import Tenant
from models.user import User
from models.user_tenant import UserTenant
from repos import project_control_applications_repo


async def create_minimal_project_control_and_application(db_session: AsyncSession, tenant_id, membership_id):
    """Helper to create minimal ProjectControl and Application for repo tests."""
    # Create project
    project = Project(
        id=uuid4(),
        tenant_id=tenant_id,
        created_by_membership_id=membership_id,
        name="Test Project",
        status="draft",
        created_at=datetime.utcnow(),
        row_version=1,
    )
    db_session.add(project)
    await db_session.flush()
    
    # Create control
    control = Control(
        id=uuid4(),
        tenant_id=tenant_id,
        created_by_membership_id=membership_id,
        control_code="AC-001",
        name="Test Control",
        is_key=False,
        is_automated=False,
        created_at=datetime.utcnow(),
        row_version=1,
    )
    db_session.add(control)
    await db_session.flush()
    
    # Create project_control
    project_control = ProjectControl(
        id=uuid4(),
        tenant_id=tenant_id,
        project_id=project.id,
        control_id=control.id,
        control_version_num=1,
        added_at=datetime.utcnow(),
        added_by_membership_id=membership_id,
        created_at=datetime.utcnow(),
    )
    db_session.add(project_control)
    await db_session.flush()
    
    # Create application
    application = Application(
        id=uuid4(),
        tenant_id=tenant_id,
        created_by_membership_id=membership_id,
        name="Test Application",
        created_at=datetime.utcnow(),
        row_version=1,
    )
    db_session.add(application)
    await db_session.flush()
    
    return project_control, application


@pytest.mark.asyncio
async def test_get_active_returns_active_mapping(db_session: AsyncSession, tenant_a, user_tenant_a):
    """Test: get_active returns an active project-control-application mapping."""
    user_a, membership_a = user_tenant_a
    tenant_id = tenant_a.id
    membership_id = membership_a.id
    
    # Create project_control and application
    project_control, application = await create_minimal_project_control_and_application(
        db_session, tenant_id, membership_id
    )
    project_control_id = project_control.id
    application_id = application.id
    
    # Create an active mapping
    pca = ProjectControlApplication(
        tenant_id=tenant_id,
        project_control_id=project_control_id,
        application_id=application_id,
        application_version_num=1,
        source="manual",
        added_at=datetime.utcnow(),
        added_by_membership_id=membership_id,
        removed_at=None,
    )
    db_session.add(pca)
    await db_session.commit()
    await db_session.refresh(pca)
    
    # Test get_active
    result = await project_control_applications_repo.get_active(
        db_session,
        tenant_id=tenant_id,
        project_control_id=project_control_id,
        application_id=application_id,
    )
    
    assert result is not None
    assert result.id == pca.id
    assert result.application_version_num == 1
    assert result.removed_at is None


@pytest.mark.asyncio
async def test_get_active_returns_none_for_removed(db_session: AsyncSession):
    """Test: get_active returns None for a removed (soft-deleted) mapping."""
    tenant = Tenant(id=uuid4(), name="Test Tenant", slug="test-tenant", status="active")
    db_session.add(tenant)
    await db_session.flush()
    user = User(id=uuid4(), primary_email="user@example.com", name="Test User", is_platform_admin=False, is_active=True)
    db_session.add(user)
    await db_session.flush()
    membership = UserTenant(id=uuid4(), user_id=user.id, tenant_id=tenant.id, role="admin", is_default=True)
    db_session.add(membership)
    await db_session.flush()
    
    tenant_id = tenant.id
    membership_id = membership.id
    
    # Create project_control and application
    project_control, application = await create_minimal_project_control_and_application(
        db_session, tenant_id, membership_id
    )
    project_control_id = project_control.id
    application_id = application.id
    
    # Create a removed mapping
    pca = ProjectControlApplication(
        tenant_id=tenant_id,
        project_control_id=project_control_id,
        application_id=application_id,
        application_version_num=1,
        source="manual",
        added_at=datetime.utcnow(),
        added_by_membership_id=membership_id,
        removed_at=datetime.utcnow(),
        removed_by_membership_id=membership_id,
    )
    db_session.add(pca)
    await db_session.commit()
    
    # Test get_active - should return None because removed_at is set
    result = await project_control_applications_repo.get_active(
        db_session,
        tenant_id=tenant_id,
        project_control_id=project_control_id,
        application_id=application_id,
    )
    
    assert result is None


@pytest.mark.asyncio
async def test_get_by_id_returns_mapping(db_session: AsyncSession):
    """Test: get_by_id returns a project-control-application mapping by ID."""
    tenant = Tenant(id=uuid4(), name="Test Tenant", slug="test-tenant", status="active")
    db_session.add(tenant)
    await db_session.flush()
    user = User(id=uuid4(), primary_email="user@example.com", name="Test User", is_platform_admin=False, is_active=True)
    db_session.add(user)
    await db_session.flush()
    membership = UserTenant(id=uuid4(), user_id=user.id, tenant_id=tenant.id, role="admin", is_default=True)
    db_session.add(membership)
    await db_session.flush()
    
    tenant_id = tenant.id
    membership_id = membership.id
    
    # Create project_control and application
    project_control, application = await create_minimal_project_control_and_application(
        db_session, tenant_id, membership_id
    )
    project_control_id = project_control.id
    application_id = application.id
    
    pca = ProjectControlApplication(
        tenant_id=tenant_id,
        project_control_id=project_control_id,
        application_id=application_id,
        application_version_num=2,
        source="manual",
        added_at=datetime.utcnow(),
        added_by_membership_id=membership_id,
    )
    db_session.add(pca)
    await db_session.commit()
    await db_session.refresh(pca)
    
    # Test get_by_id
    result = await project_control_applications_repo.get_by_id(
        db_session,
        tenant_id=tenant_id,
        pca_id=pca.id,
    )
    
    assert result is not None
    assert result.id == pca.id
    assert result.application_version_num == 2


@pytest.mark.asyncio
async def test_get_by_id_excludes_removed_by_default(db_session: AsyncSession):
    """Test: get_by_id excludes removed mappings by default."""
    tenant = Tenant(id=uuid4(), name="Test Tenant", slug="test-tenant", status="active")
    db_session.add(tenant)
    await db_session.flush()
    user = User(id=uuid4(), primary_email="user@example.com", name="Test User", is_platform_admin=False, is_active=True)
    db_session.add(user)
    await db_session.flush()
    membership = UserTenant(id=uuid4(), user_id=user.id, tenant_id=tenant.id, role="admin", is_default=True)
    db_session.add(membership)
    await db_session.flush()
    
    tenant_id = tenant.id
    membership_id = membership.id
    
    # Create project_control and application
    project_control, application = await create_minimal_project_control_and_application(
        db_session, tenant_id, membership_id
    )
    project_control_id = project_control.id
    application_id = application.id
    
    pca = ProjectControlApplication(
        tenant_id=tenant_id,
        project_control_id=project_control_id,
        application_id=application_id,
        application_version_num=1,
        source="manual",
        added_at=datetime.utcnow(),
        added_by_membership_id=membership_id,
        removed_at=datetime.utcnow(),
        removed_by_membership_id=membership_id,
    )
    db_session.add(pca)
    await db_session.commit()
    await db_session.refresh(pca)
    
    # Should return None without include_removed
    result = await project_control_applications_repo.get_by_id(
        db_session,
        tenant_id=tenant_id,
        pca_id=pca.id,
    )
    assert result is None
    
    # Should return the mapping with include_removed=True
    result_with_removed = await project_control_applications_repo.get_by_id(
        db_session,
        tenant_id=tenant_id,
        pca_id=pca.id,
        include_removed=True,
    )
    assert result_with_removed is not None
    assert result_with_removed.id == pca.id


@pytest.mark.asyncio
async def test_list_by_project_control_returns_active_only(db_session: AsyncSession):
    """Test: list_by_project_control returns only active mappings by default."""
    tenant = Tenant(id=uuid4(), name="Test Tenant", slug="test-tenant", status="active")
    db_session.add(tenant)
    await db_session.flush()
    user = User(id=uuid4(), primary_email="user@example.com", name="Test User", is_platform_admin=False, is_active=True)
    db_session.add(user)
    await db_session.flush()
    membership = UserTenant(id=uuid4(), user_id=user.id, tenant_id=tenant.id, role="admin", is_default=True)
    db_session.add(membership)
    await db_session.flush()
    
    tenant_id = tenant.id
    membership_id = membership.id
    
    # Create project_control and applications
    project_control, application1 = await create_minimal_project_control_and_application(
        db_session, tenant_id, membership_id
    )
    application2 = Application(
        id=uuid4(),
        tenant_id=tenant_id,
        created_by_membership_id=membership_id,
        name="Test Application 2",
        created_at=datetime.utcnow(),
        row_version=1,
    )
    application3 = Application(
        id=uuid4(),
        tenant_id=tenant_id,
        created_by_membership_id=membership_id,
        name="Test Application 3",
        created_at=datetime.utcnow(),
        row_version=1,
    )
    db_session.add_all([application2, application3])
    await db_session.flush()
    
    project_control_id = project_control.id
    
    # Create 2 active and 1 removed mapping
    pca1 = ProjectControlApplication(
        tenant_id=tenant_id,
        project_control_id=project_control_id,
        application_id=application1.id,
        application_version_num=1,
        source="manual",
        added_at=datetime.utcnow(),
        added_by_membership_id=membership_id,
    )
    pca2 = ProjectControlApplication(
        tenant_id=tenant_id,
        project_control_id=project_control_id,
        application_id=application2.id,
        application_version_num=2,
        source="manual",
        added_at=datetime.utcnow(),
        added_by_membership_id=membership_id,
    )
    pca3_removed = ProjectControlApplication(
        tenant_id=tenant_id,
        project_control_id=project_control_id,
        application_id=application3.id,
        application_version_num=3,
        source="manual",
        added_at=datetime.utcnow(),
        added_by_membership_id=membership_id,
        removed_at=datetime.utcnow(),
        removed_by_membership_id=membership_id,
    )
    db_session.add_all([pca1, pca2, pca3_removed])
    await db_session.commit()
    
    # List active only
    result = await project_control_applications_repo.list_by_project_control(
        db_session,
        tenant_id=tenant_id,
        project_control_id=project_control_id,
    )
    
    assert len(result) == 2
    application_ids = {pca.application_id for pca in result}
    assert pca1.application_id in application_ids
    assert pca2.application_id in application_ids
    assert pca3_removed.application_id not in application_ids


@pytest.mark.asyncio
async def test_list_by_project_control_includes_removed_when_requested(db_session: AsyncSession):
    """Test: list_by_project_control includes removed mappings when include_removed=True."""
    tenant = Tenant(id=uuid4(), name="Test Tenant", slug="test-tenant", status="active")
    db_session.add(tenant)
    await db_session.flush()
    user = User(id=uuid4(), primary_email="user@example.com", name="Test User", is_platform_admin=False, is_active=True)
    db_session.add(user)
    await db_session.flush()
    membership = UserTenant(id=uuid4(), user_id=user.id, tenant_id=tenant.id, role="admin", is_default=True)
    db_session.add(membership)
    await db_session.flush()
    
    tenant_id = tenant.id
    membership_id = membership.id
    
    # Create project_control and applications
    project_control, application1 = await create_minimal_project_control_and_application(
        db_session, tenant_id, membership_id
    )
    application2 = Application(
        id=uuid4(),
        tenant_id=tenant_id,
        created_by_membership_id=membership_id,
        name="Test Application 2",
        created_at=datetime.utcnow(),
        row_version=1,
    )
    db_session.add(application2)
    await db_session.flush()
    
    project_control_id = project_control.id
    
    pca1 = ProjectControlApplication(
        tenant_id=tenant_id,
        project_control_id=project_control_id,
        application_id=application1.id,
        application_version_num=1,
        source="manual",
        added_at=datetime.utcnow(),
        added_by_membership_id=membership_id,
    )
    pca2_removed = ProjectControlApplication(
        tenant_id=tenant_id,
        project_control_id=project_control_id,
        application_id=application2.id,
        application_version_num=2,
        source="manual",
        added_at=datetime.utcnow(),
        added_by_membership_id=membership_id,
        removed_at=datetime.utcnow(),
        removed_by_membership_id=membership_id,
    )
    db_session.add_all([pca1, pca2_removed])
    await db_session.commit()
    
    # List with include_removed
    result = await project_control_applications_repo.list_by_project_control(
        db_session,
        tenant_id=tenant_id,
        project_control_id=project_control_id,
        include_removed=True,
    )
    
    assert len(result) == 2


@pytest.mark.asyncio
async def test_create_saves_project_control_application(db_session: AsyncSession):
    """Test: create saves a new project-control-application mapping."""
    tenant = Tenant(id=uuid4(), name="Test Tenant", slug="test-tenant", status="active")
    db_session.add(tenant)
    await db_session.flush()
    user = User(id=uuid4(), primary_email="user@example.com", name="Test User", is_platform_admin=False, is_active=True)
    db_session.add(user)
    await db_session.flush()
    membership = UserTenant(id=uuid4(), user_id=user.id, tenant_id=tenant.id, role="admin", is_default=True)
    db_session.add(membership)
    await db_session.flush()
    
    tenant_id = tenant.id
    membership_id = membership.id
    
    # Create project_control and application
    project_control, application = await create_minimal_project_control_and_application(
        db_session, tenant_id, membership_id
    )
    project_control_id = project_control.id
    application_id = application.id
    
    pca = ProjectControlApplication(
        tenant_id=tenant_id,
        project_control_id=project_control_id,
        application_id=application_id,
        application_version_num=5,
        source="manual",
        added_at=datetime.utcnow(),
        added_by_membership_id=membership_id,
    )
    
    result = await project_control_applications_repo.create(db_session, pca)
    
    assert result.id is not None
    assert result.application_version_num == 5
    assert result.removed_at is None


@pytest.mark.asyncio
async def test_save_updates_project_control_application(db_session: AsyncSession):
    """Test: save updates an existing project-control-application mapping."""
    tenant = Tenant(id=uuid4(), name="Test Tenant", slug="test-tenant", status="active")
    db_session.add(tenant)
    await db_session.flush()
    user = User(id=uuid4(), primary_email="user@example.com", name="Test User", is_platform_admin=False, is_active=True)
    db_session.add(user)
    await db_session.flush()
    membership = UserTenant(id=uuid4(), user_id=user.id, tenant_id=tenant.id, role="admin", is_default=True)
    db_session.add(membership)
    await db_session.flush()
    
    tenant_id = tenant.id
    membership_id = membership.id
    
    # Create project_control and application
    project_control, application = await create_minimal_project_control_and_application(
        db_session, tenant_id, membership_id
    )
    project_control_id = project_control.id
    application_id = application.id
    
    pca = ProjectControlApplication(
        tenant_id=tenant_id,
        project_control_id=project_control_id,
        application_id=application_id,
        application_version_num=1,
        source="manual",
        added_at=datetime.utcnow(),
        added_by_membership_id=membership_id,
    )
    db_session.add(pca)
    await db_session.commit()
    await db_session.refresh(pca)
    
    # Update removed_at
    pca.removed_at = datetime.utcnow()
    pca.removed_by_membership_id = membership_id
    result = await project_control_applications_repo.save(db_session, pca)
    
    assert result.removed_at is not None
    assert result.removed_by_membership_id == membership_id
    assert result.application_version_num == 1  # Version should not change


@pytest.mark.asyncio
async def test_tenant_isolation_in_get_active(db_session: AsyncSession):
    """Test: get_active enforces tenant isolation."""
    tenant_a_obj = Tenant(id=uuid4(), name="Tenant A", slug="tenant-a", status="active")
    db_session.add(tenant_a_obj)
    await db_session.flush()
    user_a = User(id=uuid4(), primary_email="user-a@example.com", name="User A", is_platform_admin=False, is_active=True)
    db_session.add(user_a)
    await db_session.flush()
    membership_a_obj = UserTenant(id=uuid4(), user_id=user_a.id, tenant_id=tenant_a_obj.id, role="admin", is_default=True)
    db_session.add(membership_a_obj)
    await db_session.flush()
    
    tenant_a = tenant_a_obj.id
    tenant_b = uuid4()
    membership_id = membership_a_obj.id
    
    # Create project_control and application in tenant A
    project_control, application = await create_minimal_project_control_and_application(
        db_session, tenant_a, membership_id
    )
    project_control_id = project_control.id
    application_id = application.id
    
    # Create mapping in tenant A
    pca_a = ProjectControlApplication(
        tenant_id=tenant_a,
        project_control_id=project_control_id,
        application_id=application_id,
        application_version_num=1,
        source="manual",
        added_at=datetime.utcnow(),
        added_by_membership_id=membership_id,
    )
    db_session.add(pca_a)
    await db_session.commit()
    
    # Query with tenant B should return None
    result = await project_control_applications_repo.get_active(
        db_session,
        tenant_id=tenant_b,
        project_control_id=project_control_id,
        application_id=application_id,
    )
    
    assert result is None


@pytest.mark.asyncio
async def test_tenant_isolation_in_list_by_project_control(db_session: AsyncSession):
    """Test: list_by_project_control enforces tenant isolation."""
    tenant_a_obj = Tenant(id=uuid4(), name="Tenant A", slug="tenant-a", status="active")
    db_session.add(tenant_a_obj)
    await db_session.flush()
    user_a = User(id=uuid4(), primary_email="user-a@example.com", name="User A", is_platform_admin=False, is_active=True)
    db_session.add(user_a)
    await db_session.flush()
    membership_a_obj = UserTenant(id=uuid4(), user_id=user_a.id, tenant_id=tenant_a_obj.id, role="admin", is_default=True)
    db_session.add(membership_a_obj)
    await db_session.flush()
    
    tenant_b_obj = Tenant(id=uuid4(), name="Tenant B", slug="tenant-b", status="active")
    db_session.add(tenant_b_obj)
    await db_session.flush()
    user_b = User(id=uuid4(), primary_email="user-b@example.com", name="User B", is_platform_admin=False, is_active=True)
    db_session.add(user_b)
    await db_session.flush()
    membership_b_obj = UserTenant(id=uuid4(), user_id=user_b.id, tenant_id=tenant_b_obj.id, role="admin", is_default=True)
    db_session.add(membership_b_obj)
    await db_session.flush()
    
    tenant_a = tenant_a_obj.id
    tenant_b = tenant_b_obj.id
    membership_id = membership_a_obj.id
    membership_b_id = membership_b_obj.id
    
    # Create project_control and applications in tenant A
    project_control_a, application_a1 = await create_minimal_project_control_and_application(
        db_session, tenant_a, membership_id
    )
    application_a2 = Application(
        id=uuid4(),
        tenant_id=tenant_a,
        created_by_membership_id=membership_id,
        name="Test Application A2",
        created_at=datetime.utcnow(),
        row_version=1,
    )
    db_session.add(application_a2)
    await db_session.flush()
    
    # Create project_control and application in tenant B
    project_control_b, application_b = await create_minimal_project_control_and_application(
        db_session, tenant_b, membership_b_id
    )
    
    project_control_id = project_control_a.id
    
    # Create mappings in tenant A
    pca_a1 = ProjectControlApplication(
        tenant_id=tenant_a,
        project_control_id=project_control_id,
        application_id=application_a1.id,
        application_version_num=1,
        source="manual",
        added_at=datetime.utcnow(),
        added_by_membership_id=membership_id,
    )
    pca_a2 = ProjectControlApplication(
        tenant_id=tenant_a,
        project_control_id=project_control_id,
        application_id=application_a2.id,
        application_version_num=2,
        source="manual",
        added_at=datetime.utcnow(),
        added_by_membership_id=membership_id,
    )
    # Create mapping in tenant B
    pca_b = ProjectControlApplication(
        tenant_id=tenant_b,
        project_control_id=project_control_b.id,
        application_id=application_b.id,
        application_version_num=1,
        source="manual",
        added_at=datetime.utcnow(),
        added_by_membership_id=membership_id,
    )
    db_session.add_all([pca_a1, pca_a2, pca_b])
    await db_session.commit()
    
    # List for tenant A should only return tenant A mappings
    result_a = await project_control_applications_repo.list_by_project_control(
        db_session,
        tenant_id=tenant_a,
        project_control_id=project_control_id,
    )
    
    assert len(result_a) == 2
    assert all(pca.tenant_id == tenant_a for pca in result_a)
    
    # List for tenant B should only return tenant B mappings
    result_b = await project_control_applications_repo.list_by_project_control(
        db_session,
        tenant_id=tenant_b,
        project_control_id=project_control_b.id,
    )
    
    assert len(result_b) == 1
    assert all(pca.tenant_id == tenant_b for pca in result_b)

