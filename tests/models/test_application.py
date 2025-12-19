"""DB-backed tests for Application model.

These tests verify model behavior, database constraints, and query patterns
for the Application model. All tests use a real database session.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.application import Application
from models.tenant import Tenant
from models.user import User
from models.user_tenant import UserTenant
from models.auth_identity import AuthIdentity


@pytest.mark.asyncio
async def test_create_application_minimal(db_session: AsyncSession):
    """
    Test: Can create an application with minimal required fields.
    
    Required fields: name, business_owner_membership_id, it_owner_membership_id, tenant_id
    """
    # Create tenant and membership first
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
        primary_email="owner@example.com",
        name="Owner",
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
    
    # Create application
    application = Application(
        id=uuid4(),
        tenant_id=tenant.id,
        name="ERP System",
        business_owner_membership_id=membership.id,
        it_owner_membership_id=membership.id,
    )
    db_session.add(application)
    await db_session.commit()
    await db_session.refresh(application)
    
    assert application.id is not None
    assert application.name == "ERP System"
    assert application.tenant_id == tenant.id
    assert application.business_owner_membership_id == membership.id
    assert application.it_owner_membership_id == membership.id
    assert application.category is None
    assert application.scope_rationale is None
    assert application.created_at is not None
    assert isinstance(application.created_at, datetime)


@pytest.mark.asyncio
async def test_create_application_with_all_fields(db_session: AsyncSession):
    """Test: Can create an application with all fields populated."""
    # Create tenant and memberships
    tenant = Tenant(
        id=uuid4(),
        name="Test Tenant",
        slug="test-tenant",
        status="active",
    )
    db_session.add(tenant)
    await db_session.flush()
    
    # Use two different users since we can't have duplicate (user_id, tenant_id) memberships
    business_user = User(
        id=uuid4(),
        primary_email="business@example.com",
        name="Business Owner",
        is_platform_admin=False,
        is_active=True,
    )
    it_user = User(
        id=uuid4(),
        primary_email="it@example.com",
        name="IT Owner",
        is_platform_admin=False,
        is_active=True,
    )
    db_session.add_all([business_user, it_user])
    await db_session.flush()
    
    business_owner = UserTenant(
        id=uuid4(),
        user_id=business_user.id,
        tenant_id=tenant.id,
        role="admin",
        is_default=True,
    )
    it_owner = UserTenant(
        id=uuid4(),
        user_id=it_user.id,
        tenant_id=tenant.id,
        role="admin",
        is_default=False,
    )
    db_session.add_all([business_owner, it_owner])
    await db_session.flush()
    
    # Create application with all fields
    application = Application(
        id=uuid4(),
        tenant_id=tenant.id,
        name="ERP System",
        category="Financial",
        scope_rationale="Core financial system for SOX compliance",
        business_owner_membership_id=business_owner.id,
        it_owner_membership_id=it_owner.id,
    )
    db_session.add(application)
    await db_session.commit()
    await db_session.refresh(application)
    
    assert application.name == "ERP System"
    assert application.category == "Financial"
    assert application.scope_rationale == "Core financial system for SOX compliance"
    assert application.business_owner_membership_id == business_owner.id
    assert application.it_owner_membership_id == it_owner.id
    assert application.tenant_id == tenant.id


@pytest.mark.asyncio
async def test_application_allows_duplicate_names_per_tenant(db_session: AsyncSession):
    """
    Test: Multiple applications with same name are NOT allowed per tenant for active applications.
    
    Note: There's a unique constraint on (tenant_id, name) WHERE deleted_at IS NULL,
    so duplicate names are only allowed if one is soft-deleted.
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
        primary_email="owner@example.com",
        name="Owner",
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
    
    name = "ERP System"
    
    # Save IDs before any rollback
    tenant_id = tenant.id
    membership_id = membership.id
    
    # Create first application
    app1_id = uuid4()
    app1 = Application(
        id=app1_id,
        tenant_id=tenant_id,
        name=name,
        business_owner_membership_id=membership_id,
        it_owner_membership_id=membership_id,
    )
    db_session.add(app1)
    await db_session.commit()
    
    # Create second application with same name (should fail due to unique constraint)
    app2 = Application(
        id=uuid4(),
        tenant_id=tenant_id,
        name=name,  # Same name
        business_owner_membership_id=membership_id,
        it_owner_membership_id=membership_id,
    )
    db_session.add(app2)
    
    # Should raise IntegrityError due to unique constraint
    from sqlalchemy.exc import IntegrityError
    with pytest.raises(IntegrityError):
        await db_session.commit()
    
    await db_session.rollback()
    
    # Re-query app1 using the saved ID
    result = await db_session.execute(
        select(Application).where(Application.id == app1_id)
    )
    app1 = result.scalar_one()
    
    # However, if we soft-delete the first app, we can create another with the same name
    app1.deleted_at = datetime.now(timezone.utc)
    await db_session.commit()
    await db_session.refresh(app1)
    
    # Now create second application with same name (should succeed)
    app2 = Application(
        id=uuid4(),
        tenant_id=tenant_id,
        name=name,  # Same name, but first is deleted
        business_owner_membership_id=membership_id,
        it_owner_membership_id=membership_id,
    )
    db_session.add(app2)
    await db_session.commit()
    await db_session.refresh(app2)
    
    # Verify both applications exist
    assert app1.id != app2.id
    assert app1.name == app2.name
    assert app1.tenant_id == app2.tenant_id
    assert app1.deleted_at is not None
    assert app2.deleted_at is None


@pytest.mark.asyncio
async def test_application_query_by_tenant(db_session: AsyncSession):
    """Test: Can query applications by tenant_id (indexed field)."""
    # Create two tenants
    tenant_a = Tenant(
        id=uuid4(),
        name="Tenant A",
        slug="tenant-a",
        status="active",
    )
    tenant_b = Tenant(
        id=uuid4(),
        name="Tenant B",
        slug="tenant-b",
        status="active",
    )
    db_session.add_all([tenant_a, tenant_b])
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
    db_session.add_all([user_a, user_b])
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
    db_session.add_all([membership_a, membership_b])
    await db_session.flush()
    
    # Create applications in different tenants
    app_a1 = Application(
        id=uuid4(),
        tenant_id=tenant_a.id,
        name="Tenant A App 1",
        business_owner_membership_id=membership_a.id,
        it_owner_membership_id=membership_a.id,
    )
    app_a2 = Application(
        id=uuid4(),
        tenant_id=tenant_a.id,
        name="Tenant A App 2",
        business_owner_membership_id=membership_a.id,
        it_owner_membership_id=membership_a.id,
    )
    app_b = Application(
        id=uuid4(),
        tenant_id=tenant_b.id,
        name="Tenant B App",
        business_owner_membership_id=membership_b.id,
        it_owner_membership_id=membership_b.id,
    )
    
    db_session.add_all([app_a1, app_a2, app_b])
    await db_session.commit()
    
    # Query by tenant_id
    result = await db_session.execute(
        select(Application).where(Application.tenant_id == tenant_a.id)
    )
    tenant_a_apps = result.scalars().all()
    
    assert len(tenant_a_apps) == 2
    assert {app.id for app in tenant_a_apps} == {app_a1.id, app_a2.id}
    assert all(app.tenant_id == tenant_a.id for app in tenant_a_apps)


@pytest.mark.asyncio
async def test_application_query_by_category(db_session: AsyncSession):
    """Test: Can query applications by category."""
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
        primary_email="owner@example.com",
        name="Owner",
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
    
    # Create applications with different categories
    app_financial = Application(
        id=uuid4(),
        tenant_id=tenant.id,
        name="ERP System",
        category="Financial",
        business_owner_membership_id=membership.id,
        it_owner_membership_id=membership.id,
    )
    app_sales = Application(
        id=uuid4(),
        tenant_id=tenant.id,
        name="CRM System",
        category="Sales",
        business_owner_membership_id=membership.id,
        it_owner_membership_id=membership.id,
    )
    app_other = Application(
        id=uuid4(),
        tenant_id=tenant.id,
        name="Other System",
        category="Financial",  # Same category as first
        business_owner_membership_id=membership.id,
        it_owner_membership_id=membership.id,
    )
    
    db_session.add_all([app_financial, app_sales, app_other])
    await db_session.commit()
    
    # Query by category
    result = await db_session.execute(
        select(Application).where(Application.category == "Financial")
    )
    financial_apps = result.scalars().all()
    
    assert len(financial_apps) == 2
    assert {app.id for app in financial_apps} == {app_financial.id, app_other.id}
    assert all(app.category == "Financial" for app in financial_apps)


@pytest.mark.asyncio
async def test_application_foreign_key_constraints(db_session: AsyncSession):
    """Test: Foreign key constraints are enforced."""
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
        primary_email="owner@example.com",
        name="Owner",
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
    
    # Try to create application with invalid tenant_id (should fail)
    invalid_tenant_id = uuid4()
    application = Application(
        id=uuid4(),
        tenant_id=invalid_tenant_id,  # Doesn't exist
        name="Test App",
        business_owner_membership_id=membership.id,
        it_owner_membership_id=membership.id,
    )
    db_session.add(application)
    
    with pytest.raises(Exception):  # Should raise IntegrityError or similar
        await db_session.commit()
    
    await db_session.rollback()
    
    # Try to create application with invalid membership_id (should fail)
    invalid_membership_id = uuid4()
    application2 = Application(
        id=uuid4(),
        tenant_id=tenant.id,
        name="Test App",
        business_owner_membership_id=invalid_membership_id,  # Doesn't exist
        it_owner_membership_id=membership.id,
    )
    db_session.add(application2)
    
    with pytest.raises(Exception):  # Should raise IntegrityError or similar
        await db_session.commit()
