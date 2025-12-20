"""Unit tests for project_controls service layer (TDD - write failing tests first)."""

import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from models.project import Project
from models.control import Control
from models.project_control import ProjectControl
from services import project_controls_service


class MockMembershipContext:
    """Mock membership context for testing."""
    def __init__(self, tenant_id, membership_id):
        self.tenant_id = tenant_id
        self.membership_id = membership_id


@pytest.mark.asyncio
async def test_add_control_freezes_version(db_session: AsyncSession):
    """
    Test: add_control_to_project freezes control_version_num from controls.row_version.
    
    This is the KEY version-freezing test.
    """
    tenant_id = uuid4()
    membership_id = uuid4()
    ctx = MockMembershipContext(tenant_id, membership_id)
    
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
    
    # Create control with row_version=3
    control = Control(
        id=uuid4(),
        tenant_id=tenant_id,
        created_by_membership_id=membership_id,
        control_code="AC-001",
        name="Test Control",
        is_key=True,
        is_automated=False,
        created_at=datetime.utcnow(),
        row_version=3,  # Current version is 3
    )
    db_session.add(control)
    await db_session.commit()
    await db_session.refresh(project)
    await db_session.refresh(control)
    
    # Add control to project
    result = await project_controls_service.add_control_to_project(
        db_session,
        membership_ctx=ctx,
        project_id=project.id,
        control_id=control.id,
        is_key_override=None,
        frequency_override=None,
        notes=None,
    )
    
    # Verify version was frozen
    assert result.control_version_num == 3
    assert result.control_id == control.id
    assert result.project_id == project.id
    assert result.added_by_membership_id == membership_id
    assert result.added_at is not None
    assert result.removed_at is None


@pytest.mark.asyncio
async def test_add_control_version_remains_frozen_after_control_update(db_session: AsyncSession):
    """
    Test: After adding control to project, updating the control in library
    does NOT change the frozen control_version_num in project_control.
    
    This is the KEY test for version immutability.
    """
    tenant_id = uuid4()
    membership_id = uuid4()
    ctx = MockMembershipContext(tenant_id, membership_id)
    
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
    
    # Create control with row_version=1
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
    await db_session.commit()
    await db_session.refresh(project)
    await db_session.refresh(control)
    
    # Add control to project (freezes at version 1)
    pc = await project_controls_service.add_control_to_project(
        db_session,
        membership_ctx=ctx,
        project_id=project.id,
        control_id=control.id,
    )
    assert pc.control_version_num == 1
    
    # Simulate control update (row_version increments)
    control.name = "Updated Control Name"
    control.row_version = 2  # Version incremented
    await db_session.commit()
    await db_session.refresh(pc)
    
    # Verify project_control still has frozen version
    assert pc.control_version_num == 1  # MUST remain 1
    assert control.row_version == 2  # Control is now at version 2


@pytest.mark.asyncio
async def test_add_control_idempotent_returns_existing(db_session: AsyncSession):
    """Test: Adding the same control twice returns the existing mapping (idempotent)."""
    tenant_id = uuid4()
    membership_id = uuid4()
    ctx = MockMembershipContext(tenant_id, membership_id)
    
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
    db_session.add_all([project, control])
    await db_session.commit()
    await db_session.refresh(project)
    await db_session.refresh(control)
    
    # Add first time
    pc1 = await project_controls_service.add_control_to_project(
        db_session,
        membership_ctx=ctx,
        project_id=project.id,
        control_id=control.id,
    )
    
    # Add second time - should return same mapping
    pc2 = await project_controls_service.add_control_to_project(
        db_session,
        membership_ctx=ctx,
        project_id=project.id,
        control_id=control.id,
    )
    
    assert pc1.id == pc2.id  # Same instance returned


@pytest.mark.asyncio
async def test_add_control_fails_if_project_not_found(db_session: AsyncSession):
    """Test: add_control_to_project raises 404 if project doesn't exist."""
    tenant_id = uuid4()
    membership_id = uuid4()
    ctx = MockMembershipContext(tenant_id, membership_id)
    
    nonexistent_project_id = uuid4()
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
    await db_session.commit()
    await db_session.refresh(control)
    
    with pytest.raises(HTTPException) as exc_info:
        await project_controls_service.add_control_to_project(
            db_session,
            membership_ctx=ctx,
            project_id=nonexistent_project_id,
            control_id=control.id,
        )
    
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_add_control_fails_if_control_not_found(db_session: AsyncSession):
    """Test: add_control_to_project raises 404 if control doesn't exist."""
    tenant_id = uuid4()
    membership_id = uuid4()
    ctx = MockMembershipContext(tenant_id, membership_id)
    
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
    await db_session.commit()
    await db_session.refresh(project)
    
    nonexistent_control_id = uuid4()
    
    with pytest.raises(HTTPException) as exc_info:
        await project_controls_service.add_control_to_project(
            db_session,
            membership_ctx=ctx,
            project_id=project.id,
            control_id=nonexistent_control_id,
        )
    
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_add_control_fails_if_control_is_deleted(db_session: AsyncSession):
    """Test: add_control_to_project raises error if control is soft-deleted."""
    tenant_id = uuid4()
    membership_id = uuid4()
    ctx = MockMembershipContext(tenant_id, membership_id)
    
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
        name="Deleted Control",
        is_key=False,
        is_automated=False,
        created_at=datetime.utcnow(),
        row_version=1,
        deleted_at=datetime.utcnow(),  # Soft deleted
        deleted_by_membership_id=membership_id,
    )
    db_session.add_all([project, control])
    await db_session.commit()
    await db_session.refresh(project)
    await db_session.refresh(control)
    
    with pytest.raises(HTTPException) as exc_info:
        await project_controls_service.add_control_to_project(
            db_session,
            membership_ctx=ctx,
            project_id=project.id,
            control_id=control.id,
        )
    
    assert exc_info.value.status_code in [404, 400]


@pytest.mark.asyncio
async def test_add_control_enforces_tenant_isolation(db_session: AsyncSession):
    """Test: Cannot add control from different tenant."""
    tenant_a = uuid4()
    tenant_b = uuid4()
    membership_a = uuid4()
    membership_b = uuid4()
    ctx_a = MockMembershipContext(tenant_a, membership_a)
    
    # Project in tenant A
    project = Project(
        id=uuid4(),
        tenant_id=tenant_a,
        created_by_membership_id=membership_a,
        name="Tenant A Project",
        status="draft",
        created_at=datetime.utcnow(),
        row_version=1,
    )
    # Control in tenant B
    control = Control(
        id=uuid4(),
        tenant_id=tenant_b,
        created_by_membership_id=membership_b,
        control_code="AC-001",
        name="Tenant B Control",
        is_key=False,
        is_automated=False,
        created_at=datetime.utcnow(),
        row_version=1,
    )
    db_session.add_all([project, control])
    await db_session.commit()
    await db_session.refresh(project)
    await db_session.refresh(control)
    
    # Try to add tenant B control to tenant A project
    with pytest.raises(HTTPException) as exc_info:
        await project_controls_service.add_control_to_project(
            db_session,
            membership_ctx=ctx_a,
            project_id=project.id,
            control_id=control.id,
        )
    
    # Should fail with 404 (control not found in tenant A) or 400 (tenant mismatch)
    assert exc_info.value.status_code in [404, 400]


@pytest.mark.asyncio
async def test_remove_control_soft_deletes(db_session: AsyncSession):
    """Test: remove_control_from_project sets removed_at and removed_by."""
    tenant_id = uuid4()
    membership_id = uuid4()
    ctx = MockMembershipContext(tenant_id, membership_id)
    
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
    db_session.add_all([project, control])
    await db_session.commit()
    await db_session.refresh(project)
    await db_session.refresh(control)
    
    # Add control
    pc = await project_controls_service.add_control_to_project(
        db_session,
        membership_ctx=ctx,
        project_id=project.id,
        control_id=control.id,
    )
    assert pc.removed_at is None
    
    # Remove control
    await project_controls_service.remove_control_from_project(
        db_session,
        membership_ctx=ctx,
        project_control_id=pc.id,
    )
    
    await db_session.refresh(pc)
    assert pc.removed_at is not None
    assert pc.removed_by_membership_id == membership_id


@pytest.mark.asyncio
async def test_remove_control_idempotent(db_session: AsyncSession):
    """Test: Removing a control twice is idempotent (no error)."""
    tenant_id = uuid4()
    membership_id = uuid4()
    ctx = MockMembershipContext(tenant_id, membership_id)
    
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
    db_session.add_all([project, control])
    await db_session.commit()
    await db_session.refresh(project)
    await db_session.refresh(control)
    
    pc = await project_controls_service.add_control_to_project(
        db_session,
        membership_ctx=ctx,
        project_id=project.id,
        control_id=control.id,
    )
    
    # Remove once
    await project_controls_service.remove_control_from_project(
        db_session,
        membership_ctx=ctx,
        project_control_id=pc.id,
    )
    
    # Remove again - should be idempotent (no error)
    await project_controls_service.remove_control_from_project(
        db_session,
        membership_ctx=ctx,
        project_control_id=pc.id,
    )
    
    await db_session.refresh(pc)
    assert pc.removed_at is not None


@pytest.mark.asyncio
async def test_readd_control_creates_new_mapping_with_current_version(db_session: AsyncSession):
    """
    Test: After removing a control, re-adding it creates a NEW mapping
    and freezes the CURRENT control version (not the old frozen version).
    """
    tenant_id = uuid4()
    membership_id = uuid4()
    ctx = MockMembershipContext(tenant_id, membership_id)
    
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
        row_version=1,  # Version 1
    )
    db_session.add_all([project, control])
    await db_session.commit()
    await db_session.refresh(project)
    await db_session.refresh(control)
    
    # Add control (freezes at version 1)
    pc1 = await project_controls_service.add_control_to_project(
        db_session,
        membership_ctx=ctx,
        project_id=project.id,
        control_id=control.id,
    )
    assert pc1.control_version_num == 1
    pc1_id = pc1.id
    
    # Remove control
    await project_controls_service.remove_control_from_project(
        db_session,
        membership_ctx=ctx,
        project_control_id=pc1.id,
    )
    
    # Update control in library (version increments to 5)
    control.name = "Updated Control"
    control.row_version = 5
    await db_session.commit()
    await db_session.refresh(control)
    
    # Re-add control
    pc2 = await project_controls_service.add_control_to_project(
        db_session,
        membership_ctx=ctx,
        project_id=project.id,
        control_id=control.id,
    )
    
    # Should be a NEW mapping with CURRENT version (5)
    assert pc2.id != pc1_id  # Different mapping
    assert pc2.control_version_num == 5  # Freezes at current version
    assert pc2.removed_at is None  # Active


@pytest.mark.asyncio
async def test_update_overrides_does_not_change_version(db_session: AsyncSession):
    """Test: update_project_control_overrides updates only override fields, not version."""
    tenant_id = uuid4()
    membership_id = uuid4()
    ctx = MockMembershipContext(tenant_id, membership_id)
    
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
        row_version=3,
    )
    db_session.add_all([project, control])
    await db_session.commit()
    await db_session.refresh(project)
    await db_session.refresh(control)
    
    # Add control
    pc = await project_controls_service.add_control_to_project(
        db_session,
        membership_ctx=ctx,
        project_id=project.id,
        control_id=control.id,
        is_key_override=False,
    )
    assert pc.control_version_num == 3
    assert pc.is_key_override is False
    
    # Update overrides
    updated = await project_controls_service.update_project_control_overrides(
        db_session,
        membership_ctx=ctx,
        project_control_id=pc.id,
        is_key_override=True,
        frequency_override="quarterly",
        notes="Updated notes",
    )
    
    assert updated.is_key_override is True
    assert updated.frequency_override == "quarterly"
    assert updated.notes == "Updated notes"
    assert updated.control_version_num == 3  # MUST NOT change
    assert updated.control_id == control.id  # MUST NOT change


@pytest.mark.asyncio
async def test_list_project_controls_returns_active_only(db_session: AsyncSession):
    """Test: list_project_controls returns only active mappings."""
    tenant_id = uuid4()
    membership_id = uuid4()
    ctx = MockMembershipContext(tenant_id, membership_id)
    
    project = Project(
        id=uuid4(),
        tenant_id=tenant_id,
        created_by_membership_id=membership_id,
        name="Test Project",
        status="draft",
        created_at=datetime.utcnow(),
        row_version=1,
    )
    control1 = Control(
        id=uuid4(),
        tenant_id=tenant_id,
        created_by_membership_id=membership_id,
        control_code="AC-001",
        name="Control 1",
        is_key=False,
        is_automated=False,
        created_at=datetime.utcnow(),
        row_version=1,
    )
    control2 = Control(
        id=uuid4(),
        tenant_id=tenant_id,
        created_by_membership_id=membership_id,
        control_code="AC-002",
        name="Control 2",
        is_key=False,
        is_automated=False,
        created_at=datetime.utcnow(),
        row_version=1,
    )
    db_session.add_all([project, control1, control2])
    await db_session.commit()
    await db_session.refresh(project)
    await db_session.refresh(control1)
    await db_session.refresh(control2)
    
    # Add both controls
    pc1 = await project_controls_service.add_control_to_project(
        db_session,
        membership_ctx=ctx,
        project_id=project.id,
        control_id=control1.id,
    )
    pc2 = await project_controls_service.add_control_to_project(
        db_session,
        membership_ctx=ctx,
        project_id=project.id,
        control_id=control2.id,
    )
    
    # Remove one
    await project_controls_service.remove_control_from_project(
        db_session,
        membership_ctx=ctx,
        project_control_id=pc2.id,
    )
    
    # List should return only active (pc1)
    result = await project_controls_service.list_project_controls(
        db_session,
        membership_ctx=ctx,
        project_id=project.id,
    )
    
    assert len(result) == 1
    assert result[0].id == pc1.id

