"""Unit tests for project_control_applications service layer (TDD - write failing tests first)."""

import pytest
from datetime import datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from api.tenancy import TenancyContext
from models.project import Project
from models.control import Control
from models.project_control import ProjectControl
from models.application import Application
from models.tenant import Tenant
from models.user import User
from models.user_tenant import UserTenant
from services import project_control_applications_service


async def setup_tenant_user_membership(db_session: AsyncSession):
    """Helper function to create tenant, user, and membership for tests."""
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
    
    ctx = TenancyContext(
        membership_id=membership.id,
        tenant_id=tenant.id,
        role="admin",
    )
    
    return tenant, user, membership, ctx


@pytest.mark.asyncio
async def test_add_application_freezes_version(db_session: AsyncSession):
    """
    Test: add_application_to_project_control freezes application_version_num from applications.row_version.
    
    This is the KEY version-freezing test.
    """
    # Setup tenant, user, and membership
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
    
    tenant_id = tenant.id
    membership_id = membership.id
    ctx = TenancyContext(
        membership_id=membership_id,
        tenant_id=tenant_id,
        role="admin",
    )
    
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
    
    # Create control
    control = Control(
        id=uuid4(),
        tenant_id=tenant_id,
        created_by_membership_id=membership_id,
        control_code="AC-001",
        name="Test Control",
        is_key=True,
        is_automated=False,
        created_at=datetime.utcnow(),
        row_version=1,
    )
    db_session.add(control)
    
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
    
    # Create application with row_version=3
    application = Application(
        id=uuid4(),
        tenant_id=tenant_id,
        created_by_membership_id=membership_id,
        name="Test Application",
        created_at=datetime.utcnow(),
        row_version=3,  # Current version is 3
    )
    db_session.add(application)
    await db_session.commit()
    await db_session.refresh(project)
    await db_session.refresh(control)
    await db_session.refresh(project_control)
    await db_session.refresh(application)
    
    # Add application to project control
    result = await project_control_applications_service.add_application_to_project_control(
        db_session,
        membership_ctx=ctx,
        project_control_id=project_control.id,
        application_id=application.id,
    )
    
    # Verify version was frozen
    assert result.application_version_num == 3
    assert result.application_id == application.id
    assert result.project_control_id == project_control.id
    assert result.added_by_membership_id == membership_id
    assert result.added_at is not None
    assert result.removed_at is None


@pytest.mark.asyncio
async def test_add_application_version_remains_frozen_after_application_update(db_session: AsyncSession):
    """
    Test: After adding application to project control, updating the application in library
    does NOT change the frozen application_version_num in project_control_application.
    
    This is the KEY test for version immutability.
    """
    tenant, user, membership, ctx = await setup_tenant_user_membership(db_session)
    tenant_id = tenant.id
    membership_id = membership.id
    
    # Create project, control, project_control
    project = Project(
        id=uuid4(),
        tenant_id=tenant_id,
        created_by_membership_id=membership_id,
        name="Test Project",
        status="draft",
        created_at=datetime.utcnow(),
        row_version=1,
    )
    control = Control(
        id=uuid4(),
        tenant_id=tenant_id,
        created_by_membership_id=membership_id,
        control_code="AC-001",
        name="Test Control",
        is_key=True,
        is_automated=False,
        created_at=datetime.utcnow(),
        row_version=1,
    )
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
    application = Application(
        id=uuid4(),
        tenant_id=tenant_id,
        created_by_membership_id=membership_id,
        name="Test Application",
        created_at=datetime.utcnow(),
        row_version=1,
    )
    db_session.add_all([project, control, project_control, application])
    await db_session.commit()
    await db_session.refresh(project_control)
    await db_session.refresh(application)
    
    # Add application to project control (freezes at version 1)
    pca = await project_control_applications_service.add_application_to_project_control(
        db_session,
        membership_ctx=ctx,
        project_control_id=project_control.id,
        application_id=application.id,
    )
    assert pca.application_version_num == 1
    
    # Simulate application update (row_version increments)
    application.name = "Updated Application Name"
    application.row_version = 2  # Version incremented
    await db_session.commit()
    await db_session.refresh(pca)
    
    # Verify project_control_application still has frozen version
    assert pca.application_version_num == 1  # MUST remain 1
    assert application.row_version == 2  # Application is now at version 2


@pytest.mark.asyncio
async def test_add_application_idempotent_returns_existing(db_session: AsyncSession):
    """Test: Adding the same application twice returns the existing mapping (idempotent)."""
    tenant, user, membership, ctx = await setup_tenant_user_membership(db_session)
    tenant_id = tenant.id
    membership_id = membership.id
    
    project = Project(
        id=uuid4(),
        tenant_id=tenant_id,
        created_by_membership_id=membership_id,
        name="Test Project",
        status="draft",
        created_at=datetime.utcnow(),
        row_version=1,
    )
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
    application = Application(
        id=uuid4(),
        tenant_id=tenant_id,
        created_by_membership_id=membership_id,
        name="Test Application",
        created_at=datetime.utcnow(),
        row_version=1,
    )
    db_session.add_all([project, control, project_control, application])
    await db_session.commit()
    await db_session.refresh(project_control)
    await db_session.refresh(application)
    
    # Add first time
    pca1 = await project_control_applications_service.add_application_to_project_control(
        db_session,
        membership_ctx=ctx,
        project_control_id=project_control.id,
        application_id=application.id,
    )
    
    # Add second time - should return same mapping
    pca2 = await project_control_applications_service.add_application_to_project_control(
        db_session,
        membership_ctx=ctx,
        project_control_id=project_control.id,
        application_id=application.id,
    )
    
    assert pca1.id == pca2.id  # Same instance returned


@pytest.mark.asyncio
async def test_add_application_fails_if_project_control_not_found(db_session: AsyncSession):
    """Test: add_application_to_project_control raises 404 if project_control doesn't exist."""
    tenant, user, membership, ctx = await setup_tenant_user_membership(db_session)
    tenant_id = tenant.id
    membership_id = membership.id
    
    nonexistent_project_control_id = uuid4()
    application = Application(
        id=uuid4(),
        tenant_id=tenant_id,
        created_by_membership_id=membership_id,
        name="Test Application",
        created_at=datetime.utcnow(),
        row_version=1,
    )
    db_session.add(application)
    await db_session.commit()
    await db_session.refresh(application)
    
    with pytest.raises(HTTPException) as exc_info:
        await project_control_applications_service.add_application_to_project_control(
            db_session,
            membership_ctx=ctx,
            project_control_id=nonexistent_project_control_id,
            application_id=application.id,
        )
    
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_add_application_fails_if_application_not_found(db_session: AsyncSession):
    """Test: add_application_to_project_control raises 404 if application doesn't exist."""
    tenant, user, membership, ctx = await setup_tenant_user_membership(db_session)
    tenant_id = tenant.id
    membership_id = membership.id
    
    project = Project(
        id=uuid4(),
        tenant_id=tenant_id,
        created_by_membership_id=membership_id,
        name="Test Project",
        status="draft",
        created_at=datetime.utcnow(),
        row_version=1,
    )
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
    db_session.add_all([project, control, project_control])
    await db_session.commit()
    await db_session.refresh(project_control)
    
    nonexistent_application_id = uuid4()
    
    with pytest.raises(HTTPException) as exc_info:
        await project_control_applications_service.add_application_to_project_control(
            db_session,
            membership_ctx=ctx,
            project_control_id=project_control.id,
            application_id=nonexistent_application_id,
        )
    
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_add_application_fails_if_application_is_deleted(db_session: AsyncSession):
    """Test: add_application_to_project_control raises error if application is soft-deleted."""
    tenant, user, membership, ctx = await setup_tenant_user_membership(db_session)
    tenant_id = tenant.id
    membership_id = membership.id
    
    project = Project(
        id=uuid4(),
        tenant_id=tenant_id,
        created_by_membership_id=membership_id,
        name="Test Project",
        status="draft",
        created_at=datetime.utcnow(),
        row_version=1,
    )
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
    application = Application(
        id=uuid4(),
        tenant_id=tenant_id,
        created_by_membership_id=membership_id,
        name="Deleted Application",
        created_at=datetime.utcnow(),
        row_version=1,
        deleted_at=datetime.utcnow(),  # Soft deleted
        deleted_by_membership_id=membership_id,
    )
    db_session.add_all([project, control, project_control, application])
    await db_session.commit()
    await db_session.refresh(project_control)
    await db_session.refresh(application)
    
    with pytest.raises(HTTPException) as exc_info:
        await project_control_applications_service.add_application_to_project_control(
            db_session,
            membership_ctx=ctx,
            project_control_id=project_control.id,
            application_id=application.id,
        )
    
    assert exc_info.value.status_code in [404, 400]


@pytest.mark.asyncio
async def test_add_application_enforces_tenant_isolation(db_session: AsyncSession):
    """Test: Cannot add application from different tenant."""
    # Setup tenant A
    tenant_a_obj = Tenant(id=uuid4(), name="Tenant A", slug="tenant-a", status="active")
    db_session.add(tenant_a_obj)
    await db_session.flush()
    user_a = User(id=uuid4(), primary_email="user-a@example.com", name="User A", is_platform_admin=False, is_active=True)
    db_session.add(user_a)
    await db_session.flush()
    membership_a_obj = UserTenant(id=uuid4(), user_id=user_a.id, tenant_id=tenant_a_obj.id, role="admin", is_default=True)
    db_session.add(membership_a_obj)
    await db_session.flush()
    
    # Setup tenant B
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
    membership_a = membership_a_obj.id
    membership_b = membership_b_obj.id
    ctx_a = TenancyContext(
        membership_id=membership_a,
        tenant_id=tenant_a,
        role="admin",
    )
    
    # Project control in tenant A
    project = Project(
        id=uuid4(),
        tenant_id=tenant_a,
        created_by_membership_id=membership_a,
        name="Tenant A Project",
        status="draft",
        created_at=datetime.utcnow(),
        row_version=1,
    )
    control = Control(
        id=uuid4(),
        tenant_id=tenant_a,
        created_by_membership_id=membership_a,
        control_code="AC-001",
        name="Test Control",
        is_key=False,
        is_automated=False,
        created_at=datetime.utcnow(),
        row_version=1,
    )
    project_control = ProjectControl(
        id=uuid4(),
        tenant_id=tenant_a,
        project_id=project.id,
        control_id=control.id,
        control_version_num=1,
        added_at=datetime.utcnow(),
        added_by_membership_id=membership_a,
        created_at=datetime.utcnow(),
    )
    # Application in tenant B
    application = Application(
        id=uuid4(),
        tenant_id=tenant_b,
        created_by_membership_id=membership_b,
        name="Tenant B Application",
        created_at=datetime.utcnow(),
        row_version=1,
    )
    db_session.add_all([project, control, project_control, application])
    await db_session.commit()
    await db_session.refresh(project_control)
    await db_session.refresh(application)
    
    # Try to add tenant B application to tenant A project control
    with pytest.raises(HTTPException) as exc_info:
        await project_control_applications_service.add_application_to_project_control(
            db_session,
            membership_ctx=ctx_a,
            project_control_id=project_control.id,
            application_id=application.id,
        )
    
    # Should fail with 404 (application not found in tenant A) or 400 (tenant mismatch)
    assert exc_info.value.status_code in [404, 400]


@pytest.mark.asyncio
async def test_remove_application_soft_deletes(db_session: AsyncSession):
    """Test: remove_application_from_project_control sets removed_at and removed_by."""
    tenant, user, membership, ctx = await setup_tenant_user_membership(db_session)
    tenant_id = tenant.id
    membership_id = membership.id
    
    project = Project(
        id=uuid4(),
        tenant_id=tenant_id,
        created_by_membership_id=membership_id,
        name="Test Project",
        status="draft",
        created_at=datetime.utcnow(),
        row_version=1,
    )
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
    application = Application(
        id=uuid4(),
        tenant_id=tenant_id,
        created_by_membership_id=membership_id,
        name="Test Application",
        created_at=datetime.utcnow(),
        row_version=1,
    )
    db_session.add_all([project, control, project_control, application])
    await db_session.commit()
    await db_session.refresh(project_control)
    await db_session.refresh(application)
    
    # Add application
    pca = await project_control_applications_service.add_application_to_project_control(
        db_session,
        membership_ctx=ctx,
        project_control_id=project_control.id,
        application_id=application.id,
    )
    assert pca.removed_at is None
    
    # Remove application
    await project_control_applications_service.remove_application_from_project_control(
        db_session,
        membership_ctx=ctx,
        pca_id=pca.id,
    )
    
    await db_session.refresh(pca)
    assert pca.removed_at is not None
    assert pca.removed_by_membership_id == membership_id


@pytest.mark.asyncio
async def test_remove_application_idempotent(db_session: AsyncSession):
    """Test: Removing an application twice is idempotent (no error)."""
    tenant, user, membership, ctx = await setup_tenant_user_membership(db_session)
    tenant_id = tenant.id
    membership_id = membership.id
    
    project = Project(
        id=uuid4(),
        tenant_id=tenant_id,
        created_by_membership_id=membership_id,
        name="Test Project",
        status="draft",
        created_at=datetime.utcnow(),
        row_version=1,
    )
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
    application = Application(
        id=uuid4(),
        tenant_id=tenant_id,
        created_by_membership_id=membership_id,
        name="Test Application",
        created_at=datetime.utcnow(),
        row_version=1,
    )
    db_session.add_all([project, control, project_control, application])
    await db_session.commit()
    await db_session.refresh(project_control)
    await db_session.refresh(application)
    
    pca = await project_control_applications_service.add_application_to_project_control(
        db_session,
        membership_ctx=ctx,
        project_control_id=project_control.id,
        application_id=application.id,
    )
    
    # Remove once
    await project_control_applications_service.remove_application_from_project_control(
        db_session,
        membership_ctx=ctx,
        pca_id=pca.id,
    )
    
    # Remove again - should be idempotent (no error)
    await project_control_applications_service.remove_application_from_project_control(
        db_session,
        membership_ctx=ctx,
        pca_id=pca.id,
    )
    
    await db_session.refresh(pca)
    assert pca.removed_at is not None


@pytest.mark.asyncio
async def test_readd_application_creates_new_mapping_with_current_version(db_session: AsyncSession):
    """
    Test: After removing an application, re-adding it creates a NEW mapping
    and freezes the CURRENT application version (not the old frozen version).
    """
    tenant, user, membership, ctx = await setup_tenant_user_membership(db_session)
    tenant_id = tenant.id
    membership_id = membership.id
    
    project = Project(
        id=uuid4(),
        tenant_id=tenant_id,
        created_by_membership_id=membership_id,
        name="Test Project",
        status="draft",
        created_at=datetime.utcnow(),
        row_version=1,
    )
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
    application = Application(
        id=uuid4(),
        tenant_id=tenant_id,
        created_by_membership_id=membership_id,
        name="Test Application",
        created_at=datetime.utcnow(),
        row_version=1,  # Version 1
    )
    db_session.add_all([project, control, project_control, application])
    await db_session.commit()
    await db_session.refresh(project_control)
    await db_session.refresh(application)
    
    # Add application (freezes at version 1)
    pca1 = await project_control_applications_service.add_application_to_project_control(
        db_session,
        membership_ctx=ctx,
        project_control_id=project_control.id,
        application_id=application.id,
    )
    assert pca1.application_version_num == 1
    pca1_id = pca1.id
    
    # Remove application
    await project_control_applications_service.remove_application_from_project_control(
        db_session,
        membership_ctx=ctx,
        pca_id=pca1.id,
    )
    
    # Update application in library (version increments to 5)
    application.name = "Updated Application"
    application.row_version = 5
    await db_session.commit()
    await db_session.refresh(application)
    
    # Re-add application
    pca2 = await project_control_applications_service.add_application_to_project_control(
        db_session,
        membership_ctx=ctx,
        project_control_id=project_control.id,
        application_id=application.id,
    )
    
    # Should be a NEW mapping with CURRENT version (5)
    assert pca2.id != pca1_id  # Different mapping
    assert pca2.application_version_num == 5  # Freezes at current version
    assert pca2.removed_at is None  # Active


@pytest.mark.asyncio
async def test_list_applications_excludes_removed_mappings(db_session: AsyncSession):
    """Test: list_applications_for_project_control returns only active mappings."""
    tenant, user, membership, ctx = await setup_tenant_user_membership(db_session)
    tenant_id = tenant.id
    membership_id = membership.id
    
    project = Project(
        id=uuid4(),
        tenant_id=tenant_id,
        created_by_membership_id=membership_id,
        name="Test Project",
        status="draft",
        created_at=datetime.utcnow(),
        row_version=1,
    )
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
    application1 = Application(
        id=uuid4(),
        tenant_id=tenant_id,
        created_by_membership_id=membership_id,
        name="Application 1",
        created_at=datetime.utcnow(),
        row_version=1,
    )
    application2 = Application(
        id=uuid4(),
        tenant_id=tenant_id,
        created_by_membership_id=membership_id,
        name="Application 2",
        created_at=datetime.utcnow(),
        row_version=1,
    )
    db_session.add_all([project, control, project_control, application1, application2])
    await db_session.commit()
    await db_session.refresh(project_control)
    await db_session.refresh(application1)
    await db_session.refresh(application2)
    
    # Add both applications
    pca1 = await project_control_applications_service.add_application_to_project_control(
        db_session,
        membership_ctx=ctx,
        project_control_id=project_control.id,
        application_id=application1.id,
    )
    pca2 = await project_control_applications_service.add_application_to_project_control(
        db_session,
        membership_ctx=ctx,
        project_control_id=project_control.id,
        application_id=application2.id,
    )
    
    # Remove one
    await project_control_applications_service.remove_application_from_project_control(
        db_session,
        membership_ctx=ctx,
        pca_id=pca2.id,
    )
    
    # List should return only active (application1)
    result = await project_control_applications_service.list_applications_for_project_control(
        db_session,
        membership_ctx=ctx,
        project_control_id=project_control.id,
    )
    
    assert len(result) == 1
    assert result[0].id == application1.id


@pytest.mark.asyncio
async def test_cannot_add_application_to_removed_project_control(db_session: AsyncSession):
    """Test: Cannot add application to a project_control that has been removed."""
    tenant, user, membership, ctx = await setup_tenant_user_membership(db_session)
    tenant_id = tenant.id
    membership_id = membership.id
    
    project = Project(
        id=uuid4(),
        tenant_id=tenant_id,
        created_by_membership_id=membership_id,
        name="Test Project",
        status="draft",
        created_at=datetime.utcnow(),
        row_version=1,
    )
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
    project_control = ProjectControl(
        id=uuid4(),
        tenant_id=tenant_id,
        project_id=project.id,
        control_id=control.id,
        control_version_num=1,
        added_at=datetime.utcnow(),
        added_by_membership_id=membership_id,
        removed_at=datetime.utcnow(),  # Removed
        removed_by_membership_id=membership_id,
        created_at=datetime.utcnow(),
    )
    application = Application(
        id=uuid4(),
        tenant_id=tenant_id,
        created_by_membership_id=membership_id,
        name="Test Application",
        created_at=datetime.utcnow(),
        row_version=1,
    )
    db_session.add_all([project, control, project_control, application])
    await db_session.commit()
    await db_session.refresh(project_control)
    await db_session.refresh(application)
    
    # Try to add application to removed project_control
    with pytest.raises(HTTPException) as exc_info:
        await project_control_applications_service.add_application_to_project_control(
            db_session,
            membership_ctx=ctx,
            project_control_id=project_control.id,
            application_id=application.id,
        )
    
    # Should fail with 400 or 409 with clear message
    assert exc_info.value.status_code in [400, 409]
    assert "removed" in exc_info.value.detail.lower() or "not active" in exc_info.value.detail.lower()

