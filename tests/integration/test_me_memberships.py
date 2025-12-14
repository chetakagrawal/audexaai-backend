"""Integration tests for /me/memberships endpoint."""

from uuid import uuid4

import pytest
from fastapi import status

from auth.jwt import create_dev_token
from models.auth_identity import AuthIdentity
from models.tenant import Tenant
from models.user import User
from models.user_tenant import UserTenant


@pytest.mark.asyncio
async def test_get_me_memberships_success(client, db_session):
    """
    Test: Get memberships for authenticated user succeeds.
    
    Happy path: User with multiple memberships can retrieve all memberships
    with tenant details and default_membership_id.
    """
    # Create user
    user = User(
        id=uuid4(),
        primary_email="test@example.com",
        name="Test User",
        is_platform_admin=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    
    # Create auth identity
    auth_identity = AuthIdentity(
        id=uuid4(),
        user_id=user.id,
        provider="dev",
        provider_subject="test@example.com",
        email="test@example.com",
        email_verified=True,
    )
    db_session.add(auth_identity)
    
    # Create two tenants
    tenant1 = Tenant(
        id=uuid4(),
        name="Tenant One",
        slug="tenant-one",
        status="active",
    )
    tenant2 = Tenant(
        id=uuid4(),
        name="Tenant Two",
        slug="tenant-two",
        status="active",
    )
    db_session.add_all([tenant1, tenant2])
    await db_session.flush()
    
    # Create memberships - first one is default
    membership1 = UserTenant(
        id=uuid4(),
        user_id=user.id,
        tenant_id=tenant1.id,
        role="admin",
        is_default=True,
    )
    membership2 = UserTenant(
        id=uuid4(),
        user_id=user.id,
        tenant_id=tenant2.id,
        role="user",
        is_default=False,
    )
    db_session.add_all([membership1, membership2])
    await db_session.commit()
    
    # Create JWT token (no X-Membership-Id required for this endpoint)
    token = create_dev_token(
        user_id=user.id,
        tenant_id=tenant1.id,
        role="admin",
        is_platform_admin=False,
    )
    headers = {"Authorization": f"Bearer {token}"}
    
    # Call endpoint
    response = client.get("/api/v1/me/memberships", headers=headers)
    
    # Verify response
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    assert "default_membership_id" in data
    assert "memberships" in data
    assert data["default_membership_id"] == str(membership1.id)
    assert len(data["memberships"]) == 2
    
    # Verify membership details (order by created_at desc, so membership2 comes first)
    memberships = data["memberships"]
    # Find memberships by ID (order may vary, but most recent is first)
    membership_dict = {m["membership_id"]: m for m in memberships}
    
    # Verify membership1 details
    m1_data = membership_dict[str(membership1.id)]
    assert m1_data["tenant_id"] == str(tenant1.id)
    assert m1_data["tenant_name"] == "Tenant One"
    assert m1_data["tenant_slug"] == "tenant-one"
    assert m1_data["role"] == "admin"
    assert m1_data["is_default"] is True
    
    # Verify membership2 details
    m2_data = membership_dict[str(membership2.id)]
    assert m2_data["tenant_id"] == str(tenant2.id)
    assert m2_data["tenant_name"] == "Tenant Two"
    assert m2_data["tenant_slug"] == "tenant-two"
    assert m2_data["role"] == "user"
    assert m2_data["is_default"] is False


@pytest.mark.asyncio
async def test_get_me_memberships_no_default(client, db_session):
    """
    Test: User with memberships but no default returns null for default_membership_id.
    """
    # Create user
    user = User(
        id=uuid4(),
        primary_email="test2@example.com",
        name="Test User 2",
        is_platform_admin=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    
    # Create auth identity
    auth_identity = AuthIdentity(
        id=uuid4(),
        user_id=user.id,
        provider="dev",
        provider_subject="test2@example.com",
        email="test2@example.com",
        email_verified=True,
    )
    db_session.add(auth_identity)
    
    # Create tenant
    tenant = Tenant(
        id=uuid4(),
        name="Tenant No Default",
        slug="tenant-no-default",
        status="active",
    )
    db_session.add(tenant)
    await db_session.flush()
    
    # Create membership without default flag
    membership = UserTenant(
        id=uuid4(),
        user_id=user.id,
        tenant_id=tenant.id,
        role="admin",
        is_default=False,
    )
    db_session.add(membership)
    await db_session.commit()
    
    # Create JWT token
    token = create_dev_token(
        user_id=user.id,
        tenant_id=tenant.id,
        role="admin",
        is_platform_admin=False,
    )
    headers = {"Authorization": f"Bearer {token}"}
    
    # Call endpoint
    response = client.get("/api/v1/me/memberships", headers=headers)
    
    # Verify response
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    assert data["default_membership_id"] is None
    assert len(data["memberships"]) == 1


@pytest.mark.asyncio
async def test_get_me_memberships_no_memberships(client, db_session):
    """
    Test: Platform admin with no memberships returns empty list and null default.
    
    Note: Non-platform admin users need at least one membership for get_current_user
    to validate the token, so we test with a platform admin who has no tenant memberships.
    """
    # Create platform admin user
    user = User(
        id=uuid4(),
        primary_email="test3@example.com",
        name="Test User 3",
        is_platform_admin=True,  # Platform admin doesn't require tenant membership
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    
    # Create auth identity
    auth_identity = AuthIdentity(
        id=uuid4(),
        user_id=user.id,
        provider="dev",
        provider_subject="test3@example.com",
        email="test3@example.com",
        email_verified=True,
    )
    db_session.add(auth_identity)
    await db_session.commit()
    
    # Create JWT token for platform admin (tenant_id can be None)
    token = create_dev_token(
        user_id=user.id,
        tenant_id=None,
        role="admin",
        is_platform_admin=True,
    )
    headers = {"Authorization": f"Bearer {token}"}
    
    # Call endpoint
    response = client.get("/api/v1/me/memberships", headers=headers)
    
    # Verify response
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    assert data["default_membership_id"] is None
    assert data["memberships"] == []


@pytest.mark.asyncio
async def test_get_me_memberships_requires_auth(client):
    """
    Test: Endpoint requires authentication.
    """
    response = client.get("/api/v1/me/memberships")
    
    assert response.status_code == status.HTTP_403_FORBIDDEN
