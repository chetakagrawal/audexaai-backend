"""Comprehensive tests for project test attribute overrides.

Test hierarchy:
1. Model and repo layer (basic DB operations)
2. Service layer (business logic and validations)
3. Integration tests (precedence, version freezing, etc.)
"""

from datetime import datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.tenancy import TenancyContext
from models.tenant import Tenant
from models.user import User
from models.user_tenant import UserTenant
from models.control import Control
from models.test_attribute import TestAttribute
from models.project import Project
from models.project_control import ProjectControl
from models.application import Application
from models.project_control_application import ProjectControlApplication
from models.project_test_attribute_override import (
    ProjectTestAttributeOverride,
    ProjectTestAttributeOverrideUpsert,
)
from repos import project_test_attribute_overrides_repo
from services import project_test_attribute_overrides_service


# ========================================================
# FIXTURES
# ========================================================

@pytest.mark.asyncio
async def test_create_global_override(db_session: AsyncSession):
    """Test: Creating a global override (application_id=NULL) freezes test_attribute version."""
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
        control_code="AC-001",
        name="Test Control",
        row_version=1,
    )
    db_session.add(control)
    await db_session.flush()
    
    # Create test attribute
    test_attr = TestAttribute(
        tenant_id=tenant.id,
        control_id=control.id,
        code="TA-001",
        name="Test Attribute",
        frequency="Monthly",
        test_procedure="Original procedure",
        expected_evidence="Original evidence",
        created_by_membership_id=membership.id,
        row_version=3,  # Simulate this is version 3
    )
    db_session.add(test_attr)
    await db_session.flush()
    
    # Create project
    project = Project(
        tenant_id=tenant.id,
        name="Test Project",
        status="active",
        created_by_membership_id=membership.id,
        row_version=1,
    )
    db_session.add(project)
    await db_session.flush()
    
    # Create project_control
    project_control = ProjectControl(
        tenant_id=tenant.id,
        project_id=project.id,
        control_id=control.id,
        control_version_num=control.row_version,
        added_at=datetime.utcnow(),
        added_by_membership_id=membership.id,
    )
    db_session.add(project_control)
    await db_session.commit()
    
    membership_ctx = TenancyContext(
        membership_id=membership.id,
        tenant_id=tenant.id,
        role="admin",
    )
    
    # Create global override
    payload = ProjectTestAttributeOverrideUpsert(
        application_id=None,
        procedure_override="Customized procedure for project",
        notes="Project-specific customization",
    )
    
    override = await project_test_attribute_overrides_service.upsert_override(
        db_session,
        membership_ctx=membership_ctx,
        project_control_id=project_control.id,
        test_attribute_id=test_attr.id,
        payload=payload,
    )
    
    # Assertions
    assert override.tenant_id == tenant.id
    assert override.project_control_id == project_control.id
    assert override.test_attribute_id == test_attr.id
    assert override.application_id is None  # Global override
    assert override.base_test_attribute_version_num == 3  # Frozen at creation
    assert override.procedure_override == "Customized procedure for project"
    assert override.notes == "Project-specific customization"
    assert override.row_version == 1
    assert override.created_by_membership_id == membership.id


@pytest.mark.asyncio
async def test_create_app_specific_override(db_session: AsyncSession):
    """Test: Creating an app-specific override requires app to be active in project_control_applications."""
    # Setup (reusing logic from previous test)
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
    
    control = Control(
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-002",
        name="Test Control",
        row_version=1,
    )
    db_session.add(control)
    await db_session.flush()
    
    test_attr = TestAttribute(
        tenant_id=tenant.id,
        control_id=control.id,
        code="TA-002",
        name="Test Attribute",
        created_by_membership_id=membership.id,
        row_version=2,
    )
    db_session.add(test_attr)
    await db_session.flush()
    
    project = Project(
        tenant_id=tenant.id,
        name="Test Project",
        status="active",
        created_by_membership_id=membership.id,
        row_version=1,
    )
    db_session.add(project)
    await db_session.flush()
    
    project_control = ProjectControl(
        tenant_id=tenant.id,
        project_id=project.id,
        control_id=control.id,
        control_version_num=control.row_version,
        added_at=datetime.utcnow(),
        added_by_membership_id=membership.id,
    )
    db_session.add(project_control)
    await db_session.flush()
    
    # Create application
    app = Application(
        tenant_id=tenant.id,
        name="Test App",
        row_version=1,
    )
    db_session.add(app)
    await db_session.flush()
    
    # Add app to project_control
    pca = ProjectControlApplication(
        tenant_id=tenant.id,
        project_control_id=project_control.id,
        application_id=app.id,
        application_version_num=app.row_version,
        source="manual",
        added_at=datetime.utcnow(),
        added_by_membership_id=membership.id,
    )
    db_session.add(pca)
    await db_session.commit()
    
    membership_ctx = TenancyContext(
        membership_id=membership.id,
        tenant_id=tenant.id,
        role="admin",
    )
    
    # Create app-specific override
    payload = ProjectTestAttributeOverrideUpsert(
        application_id=app.id,
        name_override="App-Specific Name",
        procedure_override="App-specific procedure",
    )
    
    override = await project_test_attribute_overrides_service.upsert_override(
        db_session,
        membership_ctx=membership_ctx,
        project_control_id=project_control.id,
        test_attribute_id=test_attr.id,
        payload=payload,
    )
    
    # Assertions
    assert override.application_id == app.id
    assert override.name_override == "App-Specific Name"
    assert override.base_test_attribute_version_num == 2


@pytest.mark.asyncio
async def test_unique_constraint_global_override(db_session: AsyncSession):
    """Test: Cannot create duplicate active global override."""
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
    
    control = Control(
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-003",
        name="Test Control",
        row_version=1,
    )
    db_session.add(control)
    await db_session.flush()
    
    test_attr = TestAttribute(
        tenant_id=tenant.id,
        control_id=control.id,
        code="TA-003",
        name="Test Attribute",
        created_by_membership_id=membership.id,
        row_version=1,
    )
    db_session.add(test_attr)
    await db_session.flush()
    
    project = Project(
        tenant_id=tenant.id,
        name="Test Project",
        status="active",
        created_by_membership_id=membership.id,
        row_version=1,
    )
    db_session.add(project)
    await db_session.flush()
    
    project_control = ProjectControl(
        tenant_id=tenant.id,
        project_id=project.id,
        control_id=control.id,
        control_version_num=control.row_version,
        added_at=datetime.utcnow(),
        added_by_membership_id=membership.id,
    )
    db_session.add(project_control)
    await db_session.flush()
    
    # Create first override manually via repo
    override1 = ProjectTestAttributeOverride(
        tenant_id=tenant.id,
        project_control_id=project_control.id,
        test_attribute_id=test_attr.id,
        application_id=None,
        base_test_attribute_version_num=test_attr.row_version,
        procedure_override="First override",
        created_by_membership_id=membership.id,
        row_version=1,
    )
    db_session.add(override1)
    await db_session.flush()
    
    # Try to create second override (should be prevented by upsert logic - it updates instead)
    membership_ctx = TenancyContext(
        membership_id=membership.id,
        tenant_id=tenant.id,
        role="admin",
    )
    
    payload = ProjectTestAttributeOverrideUpsert(
        application_id=None,
        procedure_override="Second override",
    )
    
    # Service should update the existing one, not create a new one
    result = await project_test_attribute_overrides_service.upsert_override(
        db_session,
        membership_ctx=membership_ctx,
        project_control_id=project_control.id,
        test_attribute_id=test_attr.id,
        payload=payload,
    )
    
    # Should be the same override, updated
    assert result.id == override1.id
    assert result.procedure_override == "Second override"
    assert result.row_version == 2  # Incremented


@pytest.mark.asyncio
async def test_precedence_resolution(db_session: AsyncSession):
    """Test: Precedence resolution - app-specific > global > base."""
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
    
    control = Control(
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-004",
        name="Test Control",
        row_version=1,
    )
    db_session.add(control)
    await db_session.flush()
    
    test_attr = TestAttribute(
        tenant_id=tenant.id,
        control_id=control.id,
        code="TA-004",
        name="Base Name",
        frequency="Monthly",
        test_procedure="Base procedure",
        expected_evidence="Base evidence",
        created_by_membership_id=membership.id,
        row_version=1,
    )
    db_session.add(test_attr)
    await db_session.flush()
    
    project = Project(
        tenant_id=tenant.id,
        name="Test Project",
        status="active",
        created_by_membership_id=membership.id,
        row_version=1,
    )
    db_session.add(project)
    await db_session.flush()
    
    project_control = ProjectControl(
        tenant_id=tenant.id,
        project_id=project.id,
        control_id=control.id,
        control_version_num=control.row_version,
        added_at=datetime.utcnow(),
        added_by_membership_id=membership.id,
    )
    db_session.add(project_control)
    await db_session.flush()
    
    app = Application(
        tenant_id=tenant.id,
        name="Test App",
        row_version=1,
    )
    db_session.add(app)
    await db_session.flush()
    
    pca = ProjectControlApplication(
        tenant_id=tenant.id,
        project_control_id=project_control.id,
        application_id=app.id,
        application_version_num=app.row_version,
        source="manual",
        added_at=datetime.utcnow(),
        added_by_membership_id=membership.id,
    )
    db_session.add(pca)
    await db_session.flush()
    
    # Create global override
    global_override = ProjectTestAttributeOverride(
        tenant_id=tenant.id,
        project_control_id=project_control.id,
        test_attribute_id=test_attr.id,
        application_id=None,
        base_test_attribute_version_num=test_attr.row_version,
        procedure_override="Global override procedure",
        created_by_membership_id=membership.id,
        row_version=1,
    )
    db_session.add(global_override)
    await db_session.flush()
    
    # Create app-specific override
    app_override = ProjectTestAttributeOverride(
        tenant_id=tenant.id,
        project_control_id=project_control.id,
        test_attribute_id=test_attr.id,
        application_id=app.id,
        base_test_attribute_version_num=test_attr.row_version,
        name_override="App Override Name",
        procedure_override="App override procedure",
        created_by_membership_id=membership.id,
        row_version=1,
    )
    db_session.add(app_override)
    await db_session.commit()
    
    membership_ctx = TenancyContext(
        membership_id=membership.id,
        tenant_id=tenant.id,
        role="admin",
    )
    
    # Test 1: Resolve with application_id -> should get app override
    result_app = await project_test_attribute_overrides_service.resolve_effective_test_attribute(
        db_session,
        membership_ctx=membership_ctx,
        project_control_id=project_control.id,
        test_attribute_id=test_attr.id,
        application_id=app.id,
    )
    
    assert result_app["source"] == "project_app_override"
    assert result_app["name"] == "App Override Name"
    assert result_app["test_procedure"] == "App override procedure"
    assert result_app["override_id"] == app_override.id
    
    # Test 2: Resolve without application_id -> should get global override
    result_global = await project_test_attribute_overrides_service.resolve_effective_test_attribute(
        db_session,
        membership_ctx=membership_ctx,
        project_control_id=project_control.id,
        test_attribute_id=test_attr.id,
        application_id=None,
    )
    
    assert result_global["source"] == "project_global_override"
    assert result_global["name"] == "Base Name"  # Not overridden in global
    assert result_global["test_procedure"] == "Global override procedure"
    assert result_global["override_id"] == global_override.id
    
    # Test 3: Delete both overrides and resolve -> should get base
    await project_test_attribute_overrides_service.delete_override(
        db_session,
        membership_ctx=membership_ctx,
        override_id=global_override.id,
    )
    await project_test_attribute_overrides_service.delete_override(
        db_session,
        membership_ctx=membership_ctx,
        override_id=app_override.id,
    )
    
    result_base = await project_test_attribute_overrides_service.resolve_effective_test_attribute(
        db_session,
        membership_ctx=membership_ctx,
        project_control_id=project_control.id,
        test_attribute_id=test_attr.id,
        application_id=None,
    )
    
    assert result_base["source"] == "base"
    assert result_base["name"] == "Base Name"
    assert result_base["test_procedure"] == "Base procedure"
    assert result_base["override_id"] is None


@pytest.mark.asyncio
async def test_validation_test_attribute_wrong_control(db_session: AsyncSession):
    """Test: Cannot create override if test_attribute.control_id != project_control.control_id."""
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
    
    # Create two different controls
    control1 = Control(
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-005",
        name="Control 1",
        row_version=1,
    )
    control2 = Control(
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-006",
        name="Control 2",
        row_version=1,
    )
    db_session.add(control1)
    db_session.add(control2)
    await db_session.flush()
    
    # Test attribute belongs to control2
    test_attr = TestAttribute(
        tenant_id=tenant.id,
        control_id=control2.id,  # Different control
        code="TA-005",
        name="Test Attribute",
        created_by_membership_id=membership.id,
        row_version=1,
    )
    db_session.add(test_attr)
    await db_session.flush()
    
    project = Project(
        tenant_id=tenant.id,
        name="Test Project",
        status="active",
        created_by_membership_id=membership.id,
        row_version=1,
    )
    db_session.add(project)
    await db_session.flush()
    
    # Project control is for control1
    project_control = ProjectControl(
        tenant_id=tenant.id,
        project_id=project.id,
        control_id=control1.id,  # Different control
        control_version_num=control1.row_version,
        added_at=datetime.utcnow(),
        added_by_membership_id=membership.id,
    )
    db_session.add(project_control)
    await db_session.commit()
    
    membership_ctx = TenancyContext(
        membership_id=membership.id,
        tenant_id=tenant.id,
        role="admin",
    )
    
    # Try to create override -> should fail
    payload = ProjectTestAttributeOverrideUpsert(
        application_id=None,
        procedure_override="Should fail",
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await project_test_attribute_overrides_service.upsert_override(
            db_session,
            membership_ctx=membership_ctx,
            project_control_id=project_control.id,
            test_attribute_id=test_attr.id,
            payload=payload,
        )
    
    assert exc_info.value.status_code == 400
    assert "does not belong to the same control" in exc_info.value.detail


@pytest.mark.asyncio
async def test_validation_app_not_in_scope(db_session: AsyncSession):
    """Test: Cannot create app override if app not in project_control_applications."""
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
    
    control = Control(
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-007",
        name="Test Control",
        row_version=1,
    )
    db_session.add(control)
    await db_session.flush()
    
    test_attr = TestAttribute(
        tenant_id=tenant.id,
        control_id=control.id,
        code="TA-007",
        name="Test Attribute",
        created_by_membership_id=membership.id,
        row_version=1,
    )
    db_session.add(test_attr)
    await db_session.flush()
    
    project = Project(
        tenant_id=tenant.id,
        name="Test Project",
        status="active",
        created_by_membership_id=membership.id,
        row_version=1,
    )
    db_session.add(project)
    await db_session.flush()
    
    project_control = ProjectControl(
        tenant_id=tenant.id,
        project_id=project.id,
        control_id=control.id,
        control_version_num=control.row_version,
        added_at=datetime.utcnow(),
        added_by_membership_id=membership.id,
    )
    db_session.add(project_control)
    await db_session.flush()
    
    # Create app but DON'T add to project_control_applications
    app = Application(
        tenant_id=tenant.id,
        name="Out of Scope App",
        row_version=1,
    )
    db_session.add(app)
    await db_session.commit()
    
    membership_ctx = TenancyContext(
        membership_id=membership.id,
        tenant_id=tenant.id,
        role="admin",
    )
    
    # Try to create app override -> should fail
    payload = ProjectTestAttributeOverrideUpsert(
        application_id=app.id,
        procedure_override="Should fail",
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await project_test_attribute_overrides_service.upsert_override(
            db_session,
            membership_ctx=membership_ctx,
            project_control_id=project_control.id,
            test_attribute_id=test_attr.id,
            payload=payload,
        )
    
    assert exc_info.value.status_code == 400
    assert "not active for this project control" in exc_info.value.detail


@pytest.mark.asyncio
async def test_version_ready_behavior(db_session: AsyncSession):
    """Test: Updating override increments row_version and sets updated metadata."""
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
    
    control = Control(
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-008",
        name="Test Control",
        row_version=1,
    )
    db_session.add(control)
    await db_session.flush()
    
    test_attr = TestAttribute(
        tenant_id=tenant.id,
        control_id=control.id,
        code="TA-008",
        name="Test Attribute",
        created_by_membership_id=membership.id,
        row_version=1,
    )
    db_session.add(test_attr)
    await db_session.flush()
    
    project = Project(
        tenant_id=tenant.id,
        name="Test Project",
        status="active",
        created_by_membership_id=membership.id,
        row_version=1,
    )
    db_session.add(project)
    await db_session.flush()
    
    project_control = ProjectControl(
        tenant_id=tenant.id,
        project_id=project.id,
        control_id=control.id,
        control_version_num=control.row_version,
        added_at=datetime.utcnow(),
        added_by_membership_id=membership.id,
    )
    db_session.add(project_control)
    await db_session.commit()
    
    membership_ctx = TenancyContext(
        membership_id=membership.id,
        tenant_id=tenant.id,
        role="admin",
    )
    
    # Create override
    payload1 = ProjectTestAttributeOverrideUpsert(
        application_id=None,
        procedure_override="Version 1",
    )
    
    override1 = await project_test_attribute_overrides_service.upsert_override(
        db_session,
        membership_ctx=membership_ctx,
        project_control_id=project_control.id,
        test_attribute_id=test_attr.id,
        payload=payload1,
    )
    
    assert override1.row_version == 1
    assert override1.created_by_membership_id == membership.id
    assert override1.updated_at is None  # Not set on creation
    
    # Update override
    payload2 = ProjectTestAttributeOverrideUpsert(
        application_id=None,
        procedure_override="Version 2",
    )
    
    override2 = await project_test_attribute_overrides_service.upsert_override(
        db_session,
        membership_ctx=membership_ctx,
        project_control_id=project_control.id,
        test_attribute_id=test_attr.id,
        payload=payload2,
    )
    
    assert override2.id == override1.id  # Same override
    assert override2.row_version == 2  # Incremented
    assert override2.updated_at is not None  # Set on update
    assert override2.updated_by_membership_id == membership.id
    assert override2.procedure_override == "Version 2"
    
    # Soft delete
    await project_test_attribute_overrides_service.delete_override(
        db_session,
        membership_ctx=membership_ctx,
        override_id=override2.id,
    )
    
    # Refresh to see changes
    await db_session.refresh(override2)
    
    assert override2.deleted_at is not None
    assert override2.deleted_by_membership_id == membership.id
    assert override2.row_version == 3  # Incremented on delete


@pytest.mark.asyncio
async def test_tenant_isolation(db_session: AsyncSession):
    """Test: Tenant isolation is enforced."""
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
    control_b = Control(
        tenant_id=tenant_b.id,
        created_by_membership_id=membership_b.id,
        control_code="AC-009",
        name="Control B",
        row_version=1,
    )
    db_session.add(control_b)
    await db_session.flush()
    
    test_attr_b = TestAttribute(
        tenant_id=tenant_b.id,
        control_id=control_b.id,
        code="TA-009",
        name="Test Attribute B",
        created_by_membership_id=membership_b.id,
        row_version=1,
    )
    db_session.add(test_attr_b)
    await db_session.flush()
    
    project_b = Project(
        tenant_id=tenant_b.id,
        name="Project B",
        status="active",
        created_by_membership_id=membership_b.id,
        row_version=1,
    )
    db_session.add(project_b)
    await db_session.flush()
    
    project_control_b = ProjectControl(
        tenant_id=tenant_b.id,
        project_id=project_b.id,
        control_id=control_b.id,
        control_version_num=control_b.row_version,
        added_at=datetime.utcnow(),
        added_by_membership_id=membership_b.id,
    )
    db_session.add(project_control_b)
    await db_session.commit()
    
    # User A tries to access tenant B's project_control -> should fail
    membership_ctx_a = TenancyContext(
        membership_id=membership_a.id,
        tenant_id=tenant_a.id,
        role="admin",
    )
    
    payload = ProjectTestAttributeOverrideUpsert(
        application_id=None,
        procedure_override="Cross-tenant attempt",
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await project_test_attribute_overrides_service.upsert_override(
            db_session,
            membership_ctx=membership_ctx_a,
            project_control_id=project_control_b.id,
            test_attribute_id=test_attr_b.id,
            payload=payload,
        )
    
    assert exc_info.value.status_code == 404  # Not found due to tenant isolation

