"""Integration tests for SSO configuration endpoints."""

from datetime import datetime, timedelta, UTC
from uuid import uuid4

import pytest
from fastapi import status
from sqlalchemy import select

from models.signup import Signup, SignupStatus, AuthMode
from models.setup_token import SetupToken
from models.tenant_sso_config import TenantSSOConfig
from models.user import User
from models.user_tenant import UserTenant
from models.tenant import Tenant


async def create_setup_token_context(db_session, user, tenant, signup):
    """Helper to create setup token context."""
    membership = UserTenant(
        id=uuid4(),
        user_id=user.id,
        tenant_id=tenant.id,
        role="admin",
        is_default=True,
    )
    db_session.add(membership)
    await db_session.flush()
    
    token = SetupToken(
        id=uuid4(),
        token=str(uuid4()),
        user_id=user.id,
        signup_id=signup.id,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    db_session.add(token)
    await db_session.flush()
    
    return membership, token


@pytest.mark.asyncio
async def test_configure_sso_invalid_token(client, db_session):
    """
    Test: Configuring SSO with invalid token returns 401.
    """
    response = client.post(
        "/api/v1/setup/sso/configure",
        params={"token": "invalid-token"},
        json={
            "provider_type": "oidc",
            "oidc_config": {
                "client_id": "test-client",
                "client_secret": "test-secret",
                "discovery_url": "https://example.com/.well-known/openid-configuration",
            }
        }
    )
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_configure_sso_oidc_success(client, db_session):
    """
    Test: Successfully configure OIDC SSO.
    """
    # Create user, tenant, signup
    user = User(
        id=uuid4(),
        primary_email="user@example.com",
        name="Test User",
        is_platform_admin=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    
    tenant = Tenant(
        id=uuid4(),
        name="Test Tenant",
        slug="test-tenant",
        status="active",
    )
    db_session.add(tenant)
    await db_session.flush()
    
    signup = Signup(
        id=uuid4(),
        email="user@example.com",
        status=SignupStatus.PROMOTED.value,
        requested_auth_mode=AuthMode.SSO.value,
    )
    db_session.add(signup)
    await db_session.flush()
    
    # Create setup token
    _, token = await create_setup_token_context(db_session, user, tenant, signup)
    await db_session.commit()
    
    # Configure OIDC
    response = client.post(
        "/api/v1/setup/sso/configure",
        params={"token": token.token},
        json={
            "provider_type": "oidc",
            "oidc_config": {
                "client_id": "test-client-id",
                "client_secret": "test-client-secret",
                "discovery_url": "https://oidc.example.com/.well-known/openid-configuration",
                "redirect_uri": "https://app.audexaai.com/auth/oidc/callback",
            }
        }
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["provider_type"] == "oidc"
    assert data["tenant_id"] == str(tenant.id)
    assert data["is_configured"] is False  # Not configured until complete
    
    # Verify in database
    result = await db_session.execute(
        select(TenantSSOConfig).where(TenantSSOConfig.tenant_id == tenant.id)
    )
    sso_config = result.scalar_one_or_none()
    assert sso_config is not None
    assert sso_config.provider_type == "oidc"
    assert sso_config.oidc_client_id == "test-client-id"
    assert sso_config.oidc_client_secret == "test-client-secret"
    assert sso_config.oidc_discovery_url == "https://oidc.example.com/.well-known/openid-configuration"


@pytest.mark.asyncio
async def test_configure_sso_saml_success(client, db_session):
    """
    Test: Successfully configure SAML SSO.
    """
    # Create user, tenant, signup
    user = User(
        id=uuid4(),
        primary_email="user@example.com",
        name="Test User",
        is_platform_admin=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    
    tenant = Tenant(
        id=uuid4(),
        name="Test Tenant",
        slug="test-tenant",
        status="active",
    )
    db_session.add(tenant)
    await db_session.flush()
    
    signup = Signup(
        id=uuid4(),
        email="user@example.com",
        status=SignupStatus.PROMOTED.value,
        requested_auth_mode=AuthMode.SSO.value,
    )
    db_session.add(signup)
    await db_session.flush()
    
    # Create setup token
    _, token = await create_setup_token_context(db_session, user, tenant, signup)
    await db_session.commit()
    
    # Configure SAML
    response = client.post(
        "/api/v1/setup/sso/configure",
        params={"token": token.token},
        json={
            "provider_type": "saml",
            "saml_config": {
                "metadata_url": "https://saml.example.com/metadata",
                "entity_id": "https://saml.example.com/entity",
                "sso_url": "https://saml.example.com/sso",
                "x509_certificate": "-----BEGIN CERTIFICATE-----\nTEST\n-----END CERTIFICATE-----",
            }
        }
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["provider_type"] == "saml"
    assert data["tenant_id"] == str(tenant.id)
    
    # Verify in database
    result = await db_session.execute(
        select(TenantSSOConfig).where(TenantSSOConfig.tenant_id == tenant.id)
    )
    sso_config = result.scalar_one_or_none()
    assert sso_config is not None
    assert sso_config.provider_type == "saml"
    assert sso_config.metadata_url == "https://saml.example.com/metadata"
    assert sso_config.entity_id == "https://saml.example.com/entity"


@pytest.mark.asyncio
async def test_configure_sso_invalid_provider_type(client, db_session):
    """
    Test: Configuring SSO with invalid provider type returns 400.
    """
    user = User(
        id=uuid4(),
        primary_email="user@example.com",
        name="Test User",
        is_platform_admin=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    
    tenant = Tenant(
        id=uuid4(),
        name="Test Tenant",
        slug="test-tenant",
        status="active",
    )
    db_session.add(tenant)
    await db_session.flush()
    
    signup = Signup(
        id=uuid4(),
        email="user@example.com",
        status=SignupStatus.PROMOTED.value,
    )
    db_session.add(signup)
    await db_session.flush()
    
    _, token = await create_setup_token_context(db_session, user, tenant, signup)
    await db_session.commit()
    
    response = client.post(
        "/api/v1/setup/sso/configure",
        params={"token": token.token},
        json={
            "provider_type": "invalid",
            "oidc_config": {
                "client_id": "test",
                "client_secret": "test",
                "discovery_url": "https://example.com",
            }
        }
    )
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_test_sso_connection_success(client, db_session):
    """
    Test: Testing SSO connection with valid config.
    """
    user = User(
        id=uuid4(),
        primary_email="user@example.com",
        name="Test User",
        is_platform_admin=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    
    tenant = Tenant(
        id=uuid4(),
        name="Test Tenant",
        slug="test-tenant",
        status="active",
    )
    db_session.add(tenant)
    await db_session.flush()
    
    signup = Signup(
        id=uuid4(),
        email="user@example.com",
        status=SignupStatus.PROMOTED.value,
    )
    db_session.add(signup)
    await db_session.flush()
    
    _, token = await create_setup_token_context(db_session, user, tenant, signup)
    
    # Create SSO config first
    sso_config = TenantSSOConfig(
        id=uuid4(),
        tenant_id=tenant.id,
        provider_type="oidc",
        oidc_client_id="test-client",
        oidc_client_secret="test-secret",
        oidc_discovery_url="https://example.com/.well-known/openid-configuration",
        is_configured=False,
    )
    db_session.add(sso_config)
    await db_session.commit()
    
    # Test connection
    response = client.post(
        "/api/v1/setup/sso/test",
        params={"token": token.token},
        json={
            "provider_type": "oidc",
            "oidc_config": {
                "client_id": "test-client",
                "client_secret": "test-secret",
                "discovery_url": "https://example.com/.well-known/openid-configuration",
            }
        }
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["success"] is True
    assert "config_id" in data


@pytest.mark.asyncio
async def test_test_sso_connection_no_config(client, db_session):
    """
    Test: Testing SSO connection without config returns 400.
    """
    user = User(
        id=uuid4(),
        primary_email="user@example.com",
        name="Test User",
        is_platform_admin=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    
    tenant = Tenant(
        id=uuid4(),
        name="Test Tenant",
        slug="test-tenant",
        status="active",
    )
    db_session.add(tenant)
    await db_session.flush()
    
    signup = Signup(
        id=uuid4(),
        email="user@example.com",
        status=SignupStatus.PROMOTED.value,
    )
    db_session.add(signup)
    await db_session.flush()
    
    _, token = await create_setup_token_context(db_session, user, tenant, signup)
    await db_session.commit()
    
    # Test connection without config
    response = client.post(
        "/api/v1/setup/sso/test",
        params={"token": token.token},
        json={
            "provider_type": "oidc",
            "oidc_config": {
                "client_id": "test",
                "client_secret": "test",
                "discovery_url": "https://example.com",
            }
        }
    )
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_complete_sso_setup_success(client, db_session):
    """
    Test: Successfully complete SSO setup.
    """
    from models.auth_identity import AuthIdentity
    
    user = User(
        id=uuid4(),
        primary_email="user@example.com",
        name="Test User",
        is_platform_admin=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    
    tenant = Tenant(
        id=uuid4(),
        name="Test Tenant",
        slug="test-tenant",
        status="active",
    )
    db_session.add(tenant)
    await db_session.flush()
    
    signup = Signup(
        id=uuid4(),
        email="user@example.com",
        status=SignupStatus.PROMOTED.value,
        requested_auth_mode=AuthMode.SSO.value,
    )
    db_session.add(signup)
    await db_session.flush()
    
    _, token = await create_setup_token_context(db_session, user, tenant, signup)
    
    # Create SSO config
    sso_config = TenantSSOConfig(
        id=uuid4(),
        tenant_id=tenant.id,
        provider_type="oidc",
        oidc_client_id="test-client",
        oidc_client_secret="test-secret",
        oidc_discovery_url="https://example.com/.well-known/openid-configuration",
        is_configured=False,
    )
    db_session.add(sso_config)
    
    # Create OIDC auth identity
    auth_identity = AuthIdentity(
        id=uuid4(),
        user_id=user.id,
        provider="oidc",
        provider_subject="user@example.com",
        email="user@example.com",
        email_verified=False,
    )
    db_session.add(auth_identity)
    await db_session.commit()
    
    # Complete setup
    response = client.post(
        "/api/v1/setup/sso/complete",
        params={"token": token.token}
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["success"] is True
    
    # Verify changes
    await db_session.refresh(sso_config)
    assert sso_config.is_configured is True
    
    await db_session.refresh(signup)
    assert signup.signup_metadata is not None
    assert signup.signup_metadata.get("sso_status") == "configured"
    
    await db_session.refresh(token)
    assert token.used_at is not None
    
    await db_session.refresh(auth_identity)
    assert auth_identity.email_verified is True


@pytest.mark.asyncio
async def test_complete_sso_setup_no_config(client, db_session):
    """
    Test: Completing SSO setup without config returns 400.
    """
    user = User(
        id=uuid4(),
        primary_email="user@example.com",
        name="Test User",
        is_platform_admin=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    
    tenant = Tenant(
        id=uuid4(),
        name="Test Tenant",
        slug="test-tenant",
        status="active",
    )
    db_session.add(tenant)
    await db_session.flush()
    
    signup = Signup(
        id=uuid4(),
        email="user@example.com",
        status=SignupStatus.PROMOTED.value,
    )
    db_session.add(signup)
    await db_session.flush()
    
    _, token = await create_setup_token_context(db_session, user, tenant, signup)
    await db_session.commit()
    
    # Complete without config
    response = client.post(
        "/api/v1/setup/sso/complete",
        params={"token": token.token}
    )
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "not found" in response.json()["detail"].lower()
