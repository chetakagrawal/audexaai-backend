"""Integration tests for SSO access control middleware."""

from uuid import uuid4

import pytest
from fastapi import status
from sqlalchemy import select

from auth.jwt import create_dev_token
from models.auth_identity import AuthIdentity
from models.signup import Signup, SignupStatus, AuthMode
from models.user import User
from models.user_tenant import UserTenant
from models.tenant import Tenant


@pytest.mark.asyncio
async def test_portal_access_blocked_for_unconfigured_sso_user(client, db_session):
    """
    Test: Portal routes are blocked for SSO users who haven't configured SSO yet.
    """
    # Create SSO user
    user = User(
        id=uuid4(),
        primary_email="sso-user@example.com",
        name="SSO User",
        is_platform_admin=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    
    # Create tenant and membership
    tenant = Tenant(
        id=uuid4(),
        name="Test Tenant",
        slug="test-tenant",
        status="active",
    )
    db_session.add(tenant)
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
    
    # Create signup with SSO requested but not configured
    signup = Signup(
        id=uuid4(),
        email=user.primary_email,
        status=SignupStatus.PROMOTED.value,
        requested_auth_mode=AuthMode.SSO.value,
        signup_metadata={"sso_status": "not_configured"},
    )
    db_session.add(signup)
    await db_session.commit()
    
    # Create auth identity (for JWT)
    auth_identity = AuthIdentity(
        id=uuid4(),
        user_id=user.id,
        provider="dev",  # This would be oidc in real scenario, but we use dev for testing
        provider_subject=user.primary_email,
        email=user.primary_email,
        email_verified=False,
    )
    db_session.add(auth_identity)
    await db_session.commit()
    
    # Create JWT token
    token = create_dev_token(
        user_id=user.id,
        tenant_id=tenant.id,
        role="admin",
        is_platform_admin=False,
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Membership-Id": str(membership.id),
    }
    
    # Try to access portal route - should be blocked
    response = client.get("/api/v1/projects", headers=headers)
    
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "SSO configuration required" in response.json()["detail"]
    assert "X-Requires-SSO-Setup" in response.headers
    assert response.headers["X-Requires-SSO-Setup"] == "true"


@pytest.mark.asyncio
async def test_portal_access_allowed_for_configured_sso_user(client, db_session):
    """
    Test: Portal routes are allowed for SSO users who have configured SSO.
    """
    # Create SSO user
    user = User(
        id=uuid4(),
        primary_email="sso-user@example.com",
        name="SSO User",
        is_platform_admin=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    
    # Create tenant and membership
    tenant = Tenant(
        id=uuid4(),
        name="Test Tenant",
        slug="test-tenant",
        status="active",
    )
    db_session.add(tenant)
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
    
    # Create signup with SSO requested and configured
    signup = Signup(
        id=uuid4(),
        email=user.primary_email,
        status=SignupStatus.PROMOTED.value,
        requested_auth_mode=AuthMode.SSO.value,
        signup_metadata={"sso_status": "configured"},
    )
    db_session.add(signup)
    await db_session.commit()
    
    # Create auth identity
    auth_identity = AuthIdentity(
        id=uuid4(),
        user_id=user.id,
        provider="dev",
        provider_subject=user.primary_email,
        email=user.primary_email,
        email_verified=True,
    )
    db_session.add(auth_identity)
    await db_session.commit()
    
    # Create JWT token
    token = create_dev_token(
        user_id=user.id,
        tenant_id=tenant.id,
        role="admin",
        is_platform_admin=False,
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Membership-Id": str(membership.id),
    }
    
    # Try to access portal route - should be allowed
    response = client.get("/api/v1/projects", headers=headers)
    
    # Should succeed (200 or empty list)
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_portal_access_allowed_for_direct_auth_user(client, db_session):
    """
    Test: Portal routes are allowed for direct auth users (non-SSO).
    """
    # Create direct auth user
    user = User(
        id=uuid4(),
        primary_email="direct-user@example.com",
        name="Direct User",
        is_platform_admin=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    
    # Create tenant and membership
    tenant = Tenant(
        id=uuid4(),
        name="Test Tenant",
        slug="test-tenant",
        status="active",
    )
    db_session.add(tenant)
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
    
    # Create signup with direct auth
    signup = Signup(
        id=uuid4(),
        email=user.primary_email,
        status=SignupStatus.PROMOTED.value,
        requested_auth_mode=AuthMode.DIRECT.value,
    )
    db_session.add(signup)
    await db_session.commit()
    
    # Create auth identity
    auth_identity = AuthIdentity(
        id=uuid4(),
        user_id=user.id,
        provider="dev",
        provider_subject=user.primary_email,
        email=user.primary_email,
        email_verified=True,
    )
    db_session.add(auth_identity)
    await db_session.commit()
    
    # Create JWT token
    token = create_dev_token(
        user_id=user.id,
        tenant_id=tenant.id,
        role="admin",
        is_platform_admin=False,
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Membership-Id": str(membership.id),
    }
    
    # Try to access portal route - should be allowed
    response = client.get("/api/v1/projects", headers=headers)
    
    # Should succeed
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_me_endpoint_accessible_for_unconfigured_sso_user(client, db_session):
    """
    Test: /me endpoint is accessible even for unconfigured SSO users (needed for onboarding).
    """
    # Create SSO user
    user = User(
        id=uuid4(),
        primary_email="sso-user@example.com",
        name="SSO User",
        is_platform_admin=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    
    # Create tenant and membership
    tenant = Tenant(
        id=uuid4(),
        name="Test Tenant",
        slug="test-tenant",
        status="active",
    )
    db_session.add(tenant)
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
    
    # Create signup with SSO requested but not configured
    signup = Signup(
        id=uuid4(),
        email=user.primary_email,
        status=SignupStatus.PROMOTED.value,
        requested_auth_mode=AuthMode.SSO.value,
        signup_metadata={"sso_status": "not_configured"},
    )
    db_session.add(signup)
    await db_session.commit()
    
    # Create auth identity
    auth_identity = AuthIdentity(
        id=uuid4(),
        user_id=user.id,
        provider="dev",
        provider_subject=user.primary_email,
        email=user.primary_email,
        email_verified=False,
    )
    db_session.add(auth_identity)
    await db_session.commit()
    
    # Create JWT token
    token = create_dev_token(
        user_id=user.id,
        tenant_id=tenant.id,
        role="admin",
        is_platform_admin=False,
    )
    headers = {"Authorization": f"Bearer {token}"}
    
    # Try to access /me endpoint - should be allowed
    response = client.get("/api/v1/me", headers=headers)
    
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["email"] == user.primary_email


@pytest.mark.asyncio
async def test_setup_endpoints_accessible_with_setup_token(client, db_session):
    """
    Test: Setup endpoints are accessible with setup token, even for unconfigured SSO users.
    """
    from models.setup_token import SetupToken
    from datetime import datetime, timedelta, UTC
    
    # Create SSO user
    user = User(
        id=uuid4(),
        primary_email="sso-user@example.com",
        name="SSO User",
        is_platform_admin=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    
    # Create tenant and membership
    tenant = Tenant(
        id=uuid4(),
        name="Test Tenant",
        slug="test-tenant",
        status="active",
    )
    db_session.add(tenant)
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
    
    # Create signup with SSO requested but not configured
    signup = Signup(
        id=uuid4(),
        email=user.primary_email,
        status=SignupStatus.PROMOTED.value,
        requested_auth_mode=AuthMode.SSO.value,
        signup_metadata={"sso_status": "not_configured"},
    )
    db_session.add(signup)
    await db_session.flush()
    
    # Create setup token
    setup_token = SetupToken(
        id=uuid4(),
        token=str(uuid4()),
        user_id=user.id,
        signup_id=signup.id,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    db_session.add(setup_token)
    await db_session.commit()
    
    # Try to access setup validation endpoint - should be allowed
    response = client.get(f"/api/v1/setup/validate?token={setup_token.token}")
    
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["valid"] is True


@pytest.mark.asyncio
async def test_dev_login_blocked_for_sso_user(client, db_session):
    """
    Test: Dev-login is blocked for SSO users (verification of existing implementation).
    """
    # Create signup with SSO requested
    signup = Signup(
        id=uuid4(),
        email="sso-user@example.com",
        status=SignupStatus.PROMOTED.value,
        requested_auth_mode=AuthMode.SSO.value,
    )
    db_session.add(signup)
    await db_session.commit()
    
    # Try to use dev-login - should be blocked
    login_data = {
        "email": "sso-user@example.com",
    }
    response = client.post("/api/v1/auth/dev-login", json=login_data)
    
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "SSO authentication" in response.json()["detail"]
    assert "Direct login is not available" in response.json()["detail"]
