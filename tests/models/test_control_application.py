"""DB-backed tests for ControlApplication model.

These tests verify model behavior, database constraints, and query patterns
for the ControlApplication junction table. All tests use a real database session.
"""

from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.control_application import ControlApplication
from models.control import Control
from models.application import Application
from models.tenant import Tenant
from models.user import User
from models.user_tenant import UserTenant


@pytest.mark.asyncio
async def test_create_control_application_minimal(db_session: AsyncSession):
    """Test: Can create a control-application mapping with minimal fields."""
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
    control_application = ControlApplication(
        id=uuid4(),
        tenant_id=tenant.id,
        control_id=control.id,
        application_id=application.id,
    )
    db_session.add(control_application)
    await db_session.commit()
    await db_session.refresh(control_application)
    
    assert control_application.id is not None
    assert control_application.tenant_id == tenant.id
    assert control_application.control_id == control.id
    assert control_application.application_id == application.id
    assert control_application.created_at is not None
    assert isinstance(control_application.created_at, datetime)


@pytest.mark.asyncio
async def test_control_application_unique_constraint(db_session: AsyncSession):
    """
    Test: Unique constraint prevents duplicate (tenant_id, control_id, application_id) mappings.
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
    
    control = Control(
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-001",
        name="Test Control",
    )
    db_session.add(control)
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
    mapping1 = ControlApplication(
        id=uuid4(),
        tenant_id=tenant.id,
        control_id=control.id,
        application_id=application.id,
    )
    db_session.add(mapping1)
    await db_session.commit()
    await db_session.refresh(mapping1)
    
    # Try to create duplicate mapping (should fail)
    mapping2 = ControlApplication(
        id=uuid4(),
        tenant_id=tenant.id,
        control_id=control.id,  # Same control
        application_id=application.id,  # Same application
    )
    db_session.add(mapping2)
    
    with pytest.raises(Exception):  # Should raise IntegrityError
        await db_session.commit()


@pytest.mark.asyncio
async def test_control_application_query_by_control(db_session: AsyncSession):
    """Test: Can query control-applications by control_id."""
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
    
    # Create controls
    control1 = Control(
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-001",
        name="Control 1",
    )
    control2 = Control(
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-002",
        name="Control 2",
    )
    db_session.add_all([control1, control2])
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
    mapping1 = ControlApplication(
        id=uuid4(),
        tenant_id=tenant.id,
        control_id=control1.id,
        application_id=app1.id,
    )
    mapping2 = ControlApplication(
        id=uuid4(),
        tenant_id=tenant.id,
        control_id=control1.id,
        application_id=app2.id,
    )
    mapping3 = ControlApplication(
        id=uuid4(),
        tenant_id=tenant.id,
        control_id=control2.id,
        application_id=app1.id,
    )
    
    db_session.add_all([mapping1, mapping2, mapping3])
    await db_session.commit()
    
    # Query by control_id
    result = await db_session.execute(
        select(ControlApplication).where(ControlApplication.control_id == control1.id)
    )
    control1_mappings = result.scalars().all()
    
    assert len(control1_mappings) == 2
    assert {m.id for m in control1_mappings} == {mapping1.id, mapping2.id}
    assert all(m.control_id == control1.id for m in control1_mappings)


@pytest.mark.asyncio
async def test_control_application_cascade_delete(db_session: AsyncSession):
    """Test: Deleting a control cascades to delete control-applications."""
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
    
    control = Control(
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-001",
        name="Test Control",
    )
    db_session.add(control)
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
    mapping = ControlApplication(
        id=uuid4(),
        tenant_id=tenant.id,
        control_id=control.id,
        application_id=application.id,
    )
    db_session.add(mapping)
    await db_session.commit()
    
    # Delete control (should cascade delete mapping)
    await db_session.delete(control)
    await db_session.commit()
    
    # Verify mapping is deleted
    result = await db_session.execute(
        select(ControlApplication).where(ControlApplication.id == mapping.id)
    )
    deleted_mapping = result.scalar_one_or_none()
    assert deleted_mapping is None
