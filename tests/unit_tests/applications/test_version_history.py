"""Unit tests for application version history.

These tests verify that version snapshots are captured on UPDATE and DELETE operations.
"""

from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.tenancy import TenancyContext
from models.application import Application
from models.tenant import Tenant
from models.user import User
from models.user_tenant import UserTenant
from services.applications_service import create_application, delete_application, update_application


@pytest.mark.asyncio
async def test_update_application_captures_snapshot(db_session: AsyncSession):
    """Test: Updating an application captures a snapshot in entity_versions."""
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
    
    # Create application (row_version=1)
    from models.application import ApplicationCreate
    payload = ApplicationCreate(
        name="Original Name",
        category="ERP",
    )
    application = await create_application(
        db_session,
        membership_ctx=membership_ctx,
        payload=payload,
    )
    await db_session.refresh(application)
    
    original_name = application.name
    original_category = application.category
    original_row_version = application.row_version
    
    # Update application (should trigger snapshot)
    from models.application import ApplicationUpdate
    update_payload = ApplicationUpdate(
        name="Updated Name",
        category="CRM",  # Changed
    )
    updated = await update_application(
        db_session,
        membership_ctx=membership_ctx,
        application_id=application.id,
        payload=update_payload,
    )
    await db_session.commit()
    
    # Verify snapshot was created
    result = await db_session.execute(
        text("""
            SELECT entity_type, entity_id, operation, version_num, 
                   changed_by_membership_id, data
            FROM entity_versions
            WHERE tenant_id = :tenant_id
              AND entity_type = 'applications'
              AND entity_id = :entity_id
            ORDER BY version_num DESC
        """),
        {"tenant_id": str(tenant.id), "entity_id": str(application.id)},
    )
    versions = result.fetchall()
    
    assert len(versions) == 1, "Should have one snapshot"
    version = versions[0]
    assert version.entity_type == "applications"
    assert version.entity_id == application.id
    assert version.operation == "UPDATE"
    assert version.version_num == original_row_version  # Should be 1 (OLD row_version)
    assert version.changed_by_membership_id == membership.id
    
    # Verify snapshot data contains OLD values
    import json
    data = json.loads(version.data) if isinstance(version.data, str) else version.data
    assert data["name"] == original_name, "Snapshot should contain OLD name"
    assert data["category"] == original_category, "Snapshot should contain OLD category"
    assert data["row_version"] == original_row_version, "Snapshot should contain OLD row_version"
    
    # Verify current application has new values
    assert updated.name == "Updated Name"
    assert updated.category == "CRM"
    assert updated.row_version == original_row_version + 1


@pytest.mark.asyncio
async def test_soft_delete_captures_delete_snapshot(db_session: AsyncSession):
    """Test: Soft deleting an application captures a DELETE snapshot."""
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
    
    # Create application
    from models.application import ApplicationCreate
    payload = ApplicationCreate(
        name="Application to Delete",
    )
    application = await create_application(
        db_session,
        membership_ctx=membership_ctx,
        payload=payload,
    )
    await db_session.refresh(application)
    
    # Update it once to get row_version=2
    from models.application import ApplicationUpdate
    await update_application(
        db_session,
        membership_ctx=membership_ctx,
        application_id=application.id,
        payload=ApplicationUpdate(
            name="Updated Before Delete",
        ),
    )
    await db_session.commit()
    await db_session.refresh(application)
    
    pre_delete_row_version = application.row_version  # Should be 2
    
    # Soft delete the application
    await delete_application(
        db_session,
        membership_ctx=membership_ctx,
        application_id=application.id,
    )
    await db_session.commit()
    
    # Verify DELETE snapshot was created
    result = await db_session.execute(
        text("""
            SELECT entity_type, entity_id, operation, version_num,
                   changed_by_membership_id, data
            FROM entity_versions
            WHERE tenant_id = :tenant_id
              AND entity_type = 'applications'
              AND entity_id = :entity_id
              AND operation = 'DELETE'
            ORDER BY version_num DESC
        """),
        {"tenant_id": str(tenant.id), "entity_id": str(application.id)},
    )
    delete_versions = result.fetchall()
    
    assert len(delete_versions) == 1, "Should have one DELETE snapshot"
    delete_version = delete_versions[0]
    assert delete_version.operation == "DELETE"
    assert delete_version.version_num == pre_delete_row_version, "Should capture OLD row_version before delete"
    assert delete_version.changed_by_membership_id == membership.id
    
    # Verify snapshot data contains the state before deletion
    import json
    data = json.loads(delete_version.data) if isinstance(delete_version.data, str) else delete_version.data
    assert data["row_version"] == pre_delete_row_version
    assert data["deleted_at"] is None, "Snapshot should have deleted_at=NULL (before delete)"


@pytest.mark.asyncio
async def test_multi_update_ordering(db_session: AsyncSession):
    """Test: Multiple updates create multiple snapshots in correct order."""
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
    
    # Create application
    from models.application import ApplicationCreate, ApplicationUpdate
    application = await create_application(
        db_session,
        membership_ctx=membership_ctx,
        payload=ApplicationCreate(
            name="Version 1",
        ),
    )
    await db_session.commit()
    
    # Update twice
    await update_application(
        db_session,
        membership_ctx=membership_ctx,
        application_id=application.id,
        payload=ApplicationUpdate(
            name="Version 2",
        ),
    )
    await db_session.commit()
    
    await update_application(
        db_session,
        membership_ctx=membership_ctx,
        application_id=application.id,
        payload=ApplicationUpdate(
            name="Version 3",
        ),
    )
    await db_session.commit()
    
    # Verify we have 2 snapshots (for row_version 1 and 2)
    result = await db_session.execute(
        text("""
            SELECT version_num, data
            FROM entity_versions
            WHERE tenant_id = :tenant_id
              AND entity_type = 'applications'
              AND entity_id = :entity_id
            ORDER BY version_num DESC
        """),
        {"tenant_id": str(tenant.id), "entity_id": str(application.id)},
    )
    versions = result.fetchall()
    
    assert len(versions) == 2, "Should have 2 snapshots"
    
    # Verify ordering (desc by version_num)
    assert versions[0].version_num == 2, "First should be version 2"
    assert versions[1].version_num == 1, "Second should be version 1"
    
    # Verify snapshot data
    import json
    data_v2 = json.loads(versions[0].data) if isinstance(versions[0].data, str) else versions[0].data
    data_v1 = json.loads(versions[1].data) if isinstance(versions[1].data, str) else versions[1].data
    
    assert data_v2["name"] == "Version 2", "Snapshot v2 should have old name 'Version 2'"
    assert data_v1["name"] == "Version 1", "Snapshot v1 should have old name 'Version 1'"


@pytest.mark.asyncio
async def test_version_history_tenant_isolation(db_session: AsyncSession):
    """Test: Version history queries are tenant-scoped."""
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
    await db_session.commit()
    
    membership_ctx_a = TenancyContext(
        membership_id=membership_a.id,
        tenant_id=tenant_a.id,
        role="admin",
    )
    membership_ctx_b = TenancyContext(
        membership_id=membership_b.id,
        tenant_id=tenant_b.id,
        role="admin",
    )
    
    # Create applications in both tenants
    from models.application import ApplicationCreate, ApplicationUpdate
    application_a = await create_application(
        db_session,
        membership_ctx=membership_ctx_a,
        payload=ApplicationCreate(
            name="Application A",
        ),
    )
    application_b = await create_application(
        db_session,
        membership_ctx=membership_ctx_b,
        payload=ApplicationCreate(
            name="Application B",
        ),
    )
    await db_session.commit()
    
    # Update both applications to create snapshots
    await update_application(
        db_session,
        membership_ctx=membership_ctx_a,
        application_id=application_a.id,
        payload=ApplicationUpdate(
            name="Application A Updated",
        ),
    )
    await update_application(
        db_session,
        membership_ctx=membership_ctx_b,
        application_id=application_b.id,
        payload=ApplicationUpdate(
            name="Application B Updated",
        ),
    )
    await db_session.commit()
    
    # Query versions for tenant_a - should only see application_a's versions
    result_a = await db_session.execute(
        text("""
            SELECT entity_id, version_num
            FROM entity_versions
            WHERE tenant_id = :tenant_id
              AND entity_type = 'applications'
            ORDER BY entity_id, version_num DESC
        """),
        {"tenant_id": str(tenant_a.id)},
    )
    versions_a = result_a.fetchall()
    
    assert len(versions_a) == 1, "Tenant A should only see its own versions"
    assert versions_a[0].entity_id == application_a.id
    
    # Query versions for tenant_b - should only see application_b's versions
    result_b = await db_session.execute(
        text("""
            SELECT entity_id, version_num
            FROM entity_versions
            WHERE tenant_id = :tenant_id
              AND entity_type = 'applications'
            ORDER BY entity_id, version_num DESC
        """),
        {"tenant_id": str(tenant_b.id)},
    )
    versions_b = result_b.fetchall()
    
    assert len(versions_b) == 1, "Tenant B should only see its own versions"
    assert versions_b[0].entity_id == application_b.id

