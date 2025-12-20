"""Unit tests for project version history.

These tests verify that version snapshots are captured on UPDATE and DELETE operations.
"""

from datetime import date, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from api.tenancy import TenancyContext
from models.project import Project, ProjectBase, ProjectUpdate
from models.tenant import Tenant
from models.user import User
from models.user_tenant import UserTenant
from services.projects_service import create_project, update_project


@pytest.mark.asyncio
async def test_update_project_captures_snapshot(db_session: AsyncSession):
    """Test: Updating a project captures a snapshot in entity_versions."""
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
    
    # Create project (row_version=1)
    payload = ProjectBase(
        name="Original Name",
        status="draft",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 12, 31),
    )
    project = await create_project(
        db_session,
        membership_ctx=membership_ctx,
        payload=payload,
    )
    await db_session.refresh(project)
    
    original_name = project.name
    original_status = project.status
    original_row_version = project.row_version
    
    # Update project (should trigger snapshot)
    update_payload = ProjectUpdate(
        name="Updated Name",
        status="active",  # Changed
    )
    updated = await update_project(
        db_session,
        membership_ctx=membership_ctx,
        project_id=project.id,
        payload=update_payload,
        is_platform_admin=False,
    )
    await db_session.commit()
    
    # Verify snapshot was created
    result = await db_session.execute(
        text("""
            SELECT entity_type, entity_id, operation, version_num, 
                   changed_by_membership_id, data
            FROM entity_versions
            WHERE tenant_id = :tenant_id
              AND entity_type = 'projects'
              AND entity_id = :entity_id
            ORDER BY version_num DESC
            LIMIT 1
        """),
        {"tenant_id": tenant.id, "entity_id": project.id}
    )
    row = result.fetchone()
    
    assert row is not None
    assert row[0] == "projects"  # entity_type
    assert row[1] == project.id  # entity_id
    assert row[2] == "UPDATE"  # operation
    assert row[3] == original_row_version  # version_num (captured OLD.row_version)
    assert row[4] == membership.id  # changed_by_membership_id
    
    # Verify snapshot data contains original values
    snapshot_data = row[5]  # data (JSONB)
    assert snapshot_data["name"] == original_name
    assert snapshot_data["status"] == original_status
    assert snapshot_data["row_version"] == original_row_version
    
    # Verify current project has new values
    assert updated.name == "Updated Name"
    assert updated.status == "active"
    assert updated.row_version == original_row_version + 1


@pytest.mark.asyncio
async def test_multiple_updates_create_multiple_snapshots(db_session: AsyncSession):
    """Test: Multiple updates create multiple version snapshots."""
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
        name="Project V1",
        status="draft",
    )
    project = await create_project(
        db_session,
        membership_ctx=membership_ctx,
        payload=payload,
    )
    await db_session.commit()
    await db_session.refresh(project)
    
    # First update
    update1 = ProjectUpdate(name="Project V2", status="active")
    await update_project(
        db_session,
        membership_ctx=membership_ctx,
        project_id=project.id,
        payload=update1,
        is_platform_admin=False,
    )
    await db_session.commit()
    
    # Second update
    update2 = ProjectUpdate(name="Project V3")
    await update_project(
        db_session,
        membership_ctx=membership_ctx,
        project_id=project.id,
        payload=update2,
        is_platform_admin=False,
    )
    await db_session.commit()
    
    # Check we have 2 snapshots
    result = await db_session.execute(
        text("""
            SELECT COUNT(*) 
            FROM entity_versions
            WHERE tenant_id = :tenant_id
              AND entity_type = 'projects'
              AND entity_id = :entity_id
        """),
        {"tenant_id": tenant.id, "entity_id": project.id}
    )
    count = result.scalar()
    assert count == 2
    
    # Verify snapshots have correct version numbers
    result = await db_session.execute(
        text("""
            SELECT version_num, data->>'name' as name, data->>'status' as status
            FROM entity_versions
            WHERE tenant_id = :tenant_id
              AND entity_type = 'projects'
              AND entity_id = :entity_id
            ORDER BY version_num
        """),
        {"tenant_id": tenant.id, "entity_id": project.id}
    )
    rows = result.fetchall()
    
    # First snapshot (version 1) should have original values
    assert rows[0][0] == 1  # version_num
    assert rows[0][1] == "Project V1"  # name
    assert rows[0][2] == "draft"  # status
    
    # Second snapshot (version 2) should have first update values
    assert rows[1][0] == 2  # version_num
    assert rows[1][1] == "Project V2"  # name
    assert rows[1][2] == "active"  # status

