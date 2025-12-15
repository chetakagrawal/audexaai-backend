"""DB-backed tests for ProjectApplication model.

These tests verify model behavior, database constraints, and query patterns
for the ProjectApplication junction table. All tests use a real database session.
"""

from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.project_application import ProjectApplication
from models.project import Project
from models.application import Application
from models.tenant import Tenant
from models.user import User
from models.user_tenant import UserTenant


@pytest.mark.asyncio
async def test_create_project_application_minimal(db_session: AsyncSession):
    """Test: Can create a project-application mapping with minimal fields."""
    # Create tenant and membership
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
        status="draft",
    )
    db_session.add(project)
    await db_session.flush()
    
    # Create application
    application = Application(
        id=uuid4(),
        tenant_id=tenant.id,
        name="ERP System",
        business_owner_membership_id=membership.id,
        it_owner_membership_id=membership.id,
    )
    db_session.add(application)
    await db_session.flush()
    
    # Create mapping
    project_application = ProjectApplication(
        id=uuid4(),
        tenant_id=tenant.id,
        project_id=project.id,
        application_id=application.id,
    )
    db_session.add(project_application)
    await db_session.commit()
    await db_session.refresh(project_application)
    
    assert project_application.id is not None
    assert project_application.tenant_id == tenant.id
    assert project_application.project_id == project.id
    assert project_application.application_id == application.id
    assert project_application.created_at is not None
    assert isinstance(project_application.created_at, datetime)


@pytest.mark.asyncio
async def test_project_application_unique_constraint(db_session: AsyncSession):
    """
    Test: Unique constraint prevents duplicate (tenant_id, project_id, application_id) mappings.
    """
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
    
    project = Project(
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        name="Test Project",
        status="draft",
    )
    db_session.add(project)
    await db_session.flush()
    
    application = Application(
        id=uuid4(),
        tenant_id=tenant.id,
        name="ERP System",
        business_owner_membership_id=membership.id,
        it_owner_membership_id=membership.id,
    )
    db_session.add(application)
    await db_session.flush()
    
    # Create first mapping
    mapping1 = ProjectApplication(
        id=uuid4(),
        tenant_id=tenant.id,
        project_id=project.id,
        application_id=application.id,
    )
    db_session.add(mapping1)
    await db_session.commit()
    await db_session.refresh(mapping1)
    
    # Try to create duplicate mapping (should fail)
    mapping2 = ProjectApplication(
        id=uuid4(),
        tenant_id=tenant.id,
        project_id=project.id,  # Same project
        application_id=application.id,  # Same application
    )
    db_session.add(mapping2)
    
    with pytest.raises(Exception):  # Should raise IntegrityError
        await db_session.commit()


@pytest.mark.asyncio
async def test_project_application_query_by_project(db_session: AsyncSession):
    """Test: Can query project-applications by project_id."""
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
    
    # Create projects
    project1 = Project(
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        name="Project 1",
        status="draft",
    )
    project2 = Project(
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        name="Project 2",
        status="draft",
    )
    db_session.add_all([project1, project2])
    await db_session.flush()
    
    # Create applications
    app1 = Application(
        id=uuid4(),
        tenant_id=tenant.id,
        name="ERP System",
        business_owner_membership_id=membership.id,
        it_owner_membership_id=membership.id,
    )
    app2 = Application(
        id=uuid4(),
        tenant_id=tenant.id,
        name="CRM System",
        business_owner_membership_id=membership.id,
        it_owner_membership_id=membership.id,
    )
    db_session.add_all([app1, app2])
    await db_session.flush()
    
    # Create mappings
    mapping1 = ProjectApplication(
        id=uuid4(),
        tenant_id=tenant.id,
        project_id=project1.id,
        application_id=app1.id,
    )
    mapping2 = ProjectApplication(
        id=uuid4(),
        tenant_id=tenant.id,
        project_id=project1.id,
        application_id=app2.id,
    )
    mapping3 = ProjectApplication(
        id=uuid4(),
        tenant_id=tenant.id,
        project_id=project2.id,
        application_id=app1.id,
    )
    
    db_session.add_all([mapping1, mapping2, mapping3])
    await db_session.commit()
    
    # Query by project_id
    result = await db_session.execute(
        select(ProjectApplication).where(ProjectApplication.project_id == project1.id)
    )
    project1_mappings = result.scalars().all()
    
    assert len(project1_mappings) == 2
    assert {m.id for m in project1_mappings} == {mapping1.id, mapping2.id}
    assert all(m.project_id == project1.id for m in project1_mappings)


@pytest.mark.asyncio
async def test_project_application_cascade_delete(db_session: AsyncSession):
    """Test: Deleting a project cascades to delete project-applications."""
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
    
    project = Project(
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        name="Test Project",
        status="draft",
    )
    db_session.add(project)
    await db_session.flush()
    
    application = Application(
        id=uuid4(),
        tenant_id=tenant.id,
        name="ERP System",
        business_owner_membership_id=membership.id,
        it_owner_membership_id=membership.id,
    )
    db_session.add(application)
    await db_session.flush()
    
    # Create mapping
    mapping = ProjectApplication(
        id=uuid4(),
        tenant_id=tenant.id,
        project_id=project.id,
        application_id=application.id,
    )
    db_session.add(mapping)
    await db_session.commit()
    
    # Delete project (should cascade delete mapping)
    await db_session.delete(project)
    await db_session.commit()
    
    # Verify mapping is deleted
    result = await db_session.execute(
        select(ProjectApplication).where(ProjectApplication.id == mapping.id)
    )
    deleted_mapping = result.scalar_one_or_none()
    assert deleted_mapping is None
