"""Unit tests for project_controls repository layer (TDD - write failing tests first)."""

import pytest
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from models.project_control import ProjectControl
from repos import project_controls_repo


@pytest.mark.asyncio
async def test_get_active_returns_active_mapping(db_session: AsyncSession, tenant_a, user_tenant_a):
    """Test: get_active returns an active project-control mapping."""
    user_a, membership_a = user_tenant_a
    tenant_id = tenant_a.id
    from uuid import uuid4
    project_id = uuid4()
    control_id = uuid4()
    membership_id = membership_a.id
    
    # Create an active mapping
    pc = ProjectControl(
        tenant_id=tenant_id,
        project_id=project_id,
        control_id=control_id,
        control_version_num=1,
        added_at=datetime.utcnow(),
        added_by_membership_id=membership_id,
        removed_at=None,
    )
    db_session.add(pc)
    await db_session.commit()
    await db_session.refresh(pc)
    
    # Test get_active
    result = await project_controls_repo.get_active(
        db_session,
        tenant_id=tenant_id,
        project_id=project_id,
        control_id=control_id,
    )
    
    assert result is not None
    assert result.id == pc.id
    assert result.control_version_num == 1
    assert result.removed_at is None


@pytest.mark.asyncio
async def test_get_active_returns_none_for_removed(db_session: AsyncSession):
    """Test: get_active returns None for a removed (soft-deleted) mapping."""
    tenant_id = uuid4()
    project_id = uuid4()
    control_id = uuid4()
    membership_id = uuid4()
    
    # Create a removed mapping
    pc = ProjectControl(
        tenant_id=tenant_id,
        project_id=project_id,
        control_id=control_id,
        control_version_num=1,
        added_at=datetime.utcnow(),
        added_by_membership_id=membership_id,
        removed_at=datetime.utcnow(),
        removed_by_membership_id=membership_id,
    )
    db_session.add(pc)
    await db_session.commit()
    
    # Test get_active - should return None because removed_at is set
    result = await project_controls_repo.get_active(
        db_session,
        tenant_id=tenant_id,
        project_id=project_id,
        control_id=control_id,
    )
    
    assert result is None


@pytest.mark.asyncio
async def test_get_by_id_returns_mapping(db_session: AsyncSession):
    """Test: get_by_id returns a project-control mapping by ID."""
    tenant_id = uuid4()
    project_id = uuid4()
    control_id = uuid4()
    membership_id = uuid4()
    
    pc = ProjectControl(
        tenant_id=tenant_id,
        project_id=project_id,
        control_id=control_id,
        control_version_num=2,
        added_at=datetime.utcnow(),
        added_by_membership_id=membership_id,
    )
    db_session.add(pc)
    await db_session.commit()
    await db_session.refresh(pc)
    
    # Test get_by_id
    result = await project_controls_repo.get_by_id(
        db_session,
        tenant_id=tenant_id,
        project_control_id=pc.id,
    )
    
    assert result is not None
    assert result.id == pc.id
    assert result.control_version_num == 2


@pytest.mark.asyncio
async def test_get_by_id_excludes_removed_by_default(db_session: AsyncSession):
    """Test: get_by_id excludes removed mappings by default."""
    tenant_id = uuid4()
    project_id = uuid4()
    control_id = uuid4()
    membership_id = uuid4()
    
    pc = ProjectControl(
        tenant_id=tenant_id,
        project_id=project_id,
        control_id=control_id,
        control_version_num=1,
        added_at=datetime.utcnow(),
        added_by_membership_id=membership_id,
        removed_at=datetime.utcnow(),
        removed_by_membership_id=membership_id,
    )
    db_session.add(pc)
    await db_session.commit()
    await db_session.refresh(pc)
    
    # Should return None without include_removed
    result = await project_controls_repo.get_by_id(
        db_session,
        tenant_id=tenant_id,
        project_control_id=pc.id,
    )
    assert result is None
    
    # Should return the mapping with include_removed=True
    result_with_removed = await project_controls_repo.get_by_id(
        db_session,
        tenant_id=tenant_id,
        project_control_id=pc.id,
        include_removed=True,
    )
    assert result_with_removed is not None
    assert result_with_removed.id == pc.id


@pytest.mark.asyncio
async def test_list_by_project_returns_active_only(db_session: AsyncSession):
    """Test: list_by_project returns only active mappings by default."""
    tenant_id = uuid4()
    project_id = uuid4()
    membership_id = uuid4()
    
    # Create 2 active and 1 removed mapping
    pc1 = ProjectControl(
        tenant_id=tenant_id,
        project_id=project_id,
        control_id=uuid4(),
        control_version_num=1,
        added_at=datetime.utcnow(),
        added_by_membership_id=membership_id,
    )
    pc2 = ProjectControl(
        tenant_id=tenant_id,
        project_id=project_id,
        control_id=uuid4(),
        control_version_num=2,
        added_at=datetime.utcnow(),
        added_by_membership_id=membership_id,
    )
    pc3_removed = ProjectControl(
        tenant_id=tenant_id,
        project_id=project_id,
        control_id=uuid4(),
        control_version_num=3,
        added_at=datetime.utcnow(),
        added_by_membership_id=membership_id,
        removed_at=datetime.utcnow(),
        removed_by_membership_id=membership_id,
    )
    db_session.add_all([pc1, pc2, pc3_removed])
    await db_session.commit()
    
    # List active only
    result = await project_controls_repo.list_by_project(
        db_session,
        tenant_id=tenant_id,
        project_id=project_id,
    )
    
    assert len(result) == 2
    control_ids = {pc.control_id for pc in result}
    assert pc1.control_id in control_ids
    assert pc2.control_id in control_ids
    assert pc3_removed.control_id not in control_ids


@pytest.mark.asyncio
async def test_list_by_project_includes_removed_when_requested(db_session: AsyncSession):
    """Test: list_by_project includes removed mappings when include_removed=True."""
    tenant_id = uuid4()
    project_id = uuid4()
    membership_id = uuid4()
    
    pc1 = ProjectControl(
        tenant_id=tenant_id,
        project_id=project_id,
        control_id=uuid4(),
        control_version_num=1,
        added_at=datetime.utcnow(),
        added_by_membership_id=membership_id,
    )
    pc2_removed = ProjectControl(
        tenant_id=tenant_id,
        project_id=project_id,
        control_id=uuid4(),
        control_version_num=2,
        added_at=datetime.utcnow(),
        added_by_membership_id=membership_id,
        removed_at=datetime.utcnow(),
        removed_by_membership_id=membership_id,
    )
    db_session.add_all([pc1, pc2_removed])
    await db_session.commit()
    
    # List with include_removed
    result = await project_controls_repo.list_by_project(
        db_session,
        tenant_id=tenant_id,
        project_id=project_id,
        include_removed=True,
    )
    
    assert len(result) == 2


@pytest.mark.asyncio
async def test_create_saves_project_control(db_session: AsyncSession):
    """Test: create saves a new project-control mapping."""
    tenant_id = uuid4()
    project_id = uuid4()
    control_id = uuid4()
    membership_id = uuid4()
    
    pc = ProjectControl(
        tenant_id=tenant_id,
        project_id=project_id,
        control_id=control_id,
        control_version_num=5,
        added_at=datetime.utcnow(),
        added_by_membership_id=membership_id,
    )
    
    result = await project_controls_repo.create(db_session, pc)
    
    assert result.id is not None
    assert result.control_version_num == 5
    assert result.removed_at is None


@pytest.mark.asyncio
async def test_save_updates_project_control(db_session: AsyncSession):
    """Test: save updates an existing project-control mapping."""
    tenant_id = uuid4()
    project_id = uuid4()
    control_id = uuid4()
    membership_id = uuid4()
    
    pc = ProjectControl(
        tenant_id=tenant_id,
        project_id=project_id,
        control_id=control_id,
        control_version_num=1,
        added_at=datetime.utcnow(),
        added_by_membership_id=membership_id,
        is_key_override=False,
    )
    db_session.add(pc)
    await db_session.commit()
    await db_session.refresh(pc)
    
    # Update override
    pc.is_key_override = True
    result = await project_controls_repo.save(db_session, pc)
    
    assert result.is_key_override is True
    assert result.control_version_num == 1  # Version should not change


@pytest.mark.asyncio
async def test_tenant_isolation_in_get_active(db_session: AsyncSession):
    """Test: get_active enforces tenant isolation."""
    tenant_a = uuid4()
    tenant_b = uuid4()
    project_id = uuid4()
    control_id = uuid4()
    membership_id = uuid4()
    
    # Create mapping in tenant A
    pc_a = ProjectControl(
        tenant_id=tenant_a,
        project_id=project_id,
        control_id=control_id,
        control_version_num=1,
        added_at=datetime.utcnow(),
        added_by_membership_id=membership_id,
    )
    db_session.add(pc_a)
    await db_session.commit()
    
    # Query with tenant B should return None
    result = await project_controls_repo.get_active(
        db_session,
        tenant_id=tenant_b,
        project_id=project_id,
        control_id=control_id,
    )
    
    assert result is None

