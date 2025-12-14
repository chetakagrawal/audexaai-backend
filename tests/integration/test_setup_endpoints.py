"""Integration tests for SSO setup endpoints."""

from datetime import datetime, timedelta, UTC
from uuid import uuid4

import pytest
from fastapi import status
from sqlalchemy import select

from auth.jwt import create_dev_token
from models.setup_token import SetupToken
from models.signup import Signup, SignupStatus, AuthMode
from models.tenant_sso_config import TenantSSOConfig


@pytest.mark.asyncio
async def test_validate_setup_token_not_found(client, db_session):
    """
    Test: Validate endpoint returns invalid for non-existent token.
    """
    response = client.get("/api/v1/setup/validate?token=nonexistent-token")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["valid"] is False
    assert data["reason"] == "Token not found"


@pytest.mark.asyncio
async def test_validate_setup_token_expired(client, db_session, user_tenant_a):
    """
    Test: Validate endpoint returns invalid for expired token.
    """
    from models.user import User
    from models.signup import Signup
    
    user, membership = user_tenant_a
    
    # Create signup
    signup = Signup(
        id=uuid4(),
        email=user.primary_email,
        status=SignupStatus.PROMOTED.value,
        requested_auth_mode=AuthMode.SSO.value,
    )
    db_session.add(signup)
    await db_session.flush()
    
    # Create expired setup token
    expired_token = SetupToken(
        id=uuid4(),
        token=str(uuid4()),
        user_id=user.id,
        signup_id=signup.id,
        expires_at=datetime.now(UTC) - timedelta(days=1),  # Expired yesterday
    )
    db_session.add(expired_token)
    await db_session.commit()
    
    response = client.get(f"/api/v1/setup/validate?token={expired_token.token}")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["valid"] is False
    assert "expired" in data["reason"].lower()


@pytest.mark.asyncio
async def test_validate_setup_token_used(client, db_session, user_tenant_a):
    """
    Test: Validate endpoint returns invalid for already-used token.
    """
    user, membership = user_tenant_a
    
    # Create signup
    signup = Signup(
        id=uuid4(),
        email=user.primary_email,
        status=SignupStatus.PROMOTED.value,
        requested_auth_mode=AuthMode.SSO.value,
    )
    db_session.add(signup)
    await db_session.flush()
    
    # Create used setup token
    used_token = SetupToken(
        id=uuid4(),
        token=str(uuid4()),
        user_id=user.id,
        signup_id=signup.id,
        expires_at=datetime.now(UTC) + timedelta(days=7),
        used_at=datetime.now(UTC),  # Already used
    )
    db_session.add(used_token)
    await db_session.commit()
    
    response = client.get(f"/api/v1/setup/validate?token={used_token.token}")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["valid"] is False
    assert "used" in data["reason"].lower()


@pytest.mark.asyncio
async def test_validate_setup_token_valid(client, db_session, user_tenant_a):
    """
    Test: Validate endpoint returns user/tenant info for valid token.
    """
    user, membership = user_tenant_a
    
    # Create signup
    signup = Signup(
        id=uuid4(),
        email=user.primary_email,
        status=SignupStatus.PROMOTED.value,
        requested_auth_mode=AuthMode.SSO.value,
    )
    db_session.add(signup)
    await db_session.flush()
    
    # Create valid setup token
    valid_token = SetupToken(
        id=uuid4(),
        token=str(uuid4()),
        user_id=user.id,
        signup_id=signup.id,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    db_session.add(valid_token)
    await db_session.commit()
    
    response = client.get(f"/api/v1/setup/validate?token={valid_token.token}")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["valid"] is True
    assert data["user_id"] == str(user.id)
    assert data["tenant_id"] == str(membership.tenant_id)
    assert data["signup_id"] == str(signup.id)
    assert data["user_email"] == user.primary_email
    assert data["user_name"] == user.name


@pytest.mark.asyncio
async def test_configure_sso_requires_valid_token(client, db_session):
    """
    Test: Configure SSO requires valid setup token.
    """
    config_data = {
        "provider_type": "oidc",
        "oidc_config": {
            "client_id": "test-client",
            "client_secret": "test-secret",
            "discovery_url": "https://example.com/.well-known/openid-configuration",
        }
    }
    
    response = client.post(
        "/api/v1/setup/sso/configure?token=invalid-token",
        json=config_data
    )
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_configure_sso_oidc_success(client, db_session, user_tenant_a):
    """
    Test: Successfully configure OIDC SSO with valid token.
    """
    from models.user import User
    from models.tenant import Tenant
    from models.signup import Signup
    
    user, membership = user_tenant_a
    
    # Get tenant
    result = await db_session.execute(
        select(Tenant).where(Tenant.id == membership.tenant_id)
    )
    tenant = result.scalar_one()
    
    # Create signup
    signup = Signup(
        id=uuid4(),
        email=user.primary_email,
        status=SignupStatus.PROMOTED.value,
        requested_auth_mode=AuthMode.SSO.value,
    )
    db_session.add(signup)
    await db_session.flush()
    
    # Create valid setup token
    valid_token = SetupToken(
        id=uuid4(),
        token=str(uuid4()),
        user_id=user.id,
        signup_id=signup.id,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    db_session.add(valid_token)
    await db_session.commit()
    
    config_data = {
        "provider_type": "oidc",
        "oidc_config": {
            "client_id": "test-client-id",
            "client_secret": "test-secret",
            "discovery_url": "https://example.com/.well-known/openid-configuration",
        }
    }
    
    response = client.post(
        f"/api/v1/setup/sso/configure?token={valid_token.token}",
        json=config_data
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["tenant_id"] == str(tenant.id)
    assert data["provider_type"] == "oidc"
    assert data["is_configured"] is False
    
    # Verify config was saved
    result = await db_session.execute(
        select(TenantSSOConfig).where(TenantSSOConfig.tenant_id == tenant.id)
    )
    sso_config = result.scalar_one_or_none()
    assert sso_config is not None
    assert sso_config.oidc_client_id == "test-client-id"
    assert sso_config.oidc_discovery_url == "https://example.com/.well-known/openid-configuration"


@pytest.mark.asyncio
async def test_configure_sso_saml_success(client, db_session, user_tenant_a):
    """
    Test: Successfully configure SAML SSO with valid token.
    """
    from models.tenant import Tenant
    from models.signup import Signup
    
    user, membership = user_tenant_a
    
    # Get tenant
    result = await db_session.execute(
        select(Tenant).where(Tenant.id == membership.tenant_id)
    )
    tenant = result.scalar_one()
    
    # Create signup
    signup = Signup(
        id=uuid4(),
        email=user.primary_email,
        status=SignupStatus.PROMOTED.value,
        requested_auth_mode=AuthMode.SSO.value,
    )
    db_session.add(signup)
    await db_session.flush()
    
    # Create valid setup token
    valid_token = SetupToken(
        id=uuid4(),
        token=str(uuid4()),
        user_id=user.id,
        signup_id=signup.id,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    db_session.add(valid_token)
    await db_session.commit()
    
    config_data = {
        "provider_type": "saml",
        "saml_config": {
            "metadata_url": "https://example.com/saml/metadata",
            "entity_id": "https://example.com/entity",
            "sso_url": "https://example.com/sso",
        }
    }
    
    response = client.post(
        f"/api/v1/setup/sso/configure?token={valid_token.token}",
        json=config_data
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["provider_type"] == "saml"
    
    # Verify config was saved
    result = await db_session.execute(
        select(TenantSSOConfig).where(TenantSSOConfig.tenant_id == tenant.id)
    )
    sso_config = result.scalar_one_or_none()
    assert sso_config is not None
    assert sso_config.metadata_url == "https://example.com/saml/metadata"


@pytest.mark.asyncio
async def test_configure_sso_invalid_provider_type(client, db_session, user_tenant_a):
    """
    Test: Configure SSO rejects invalid provider type.
    """
    from models.signup import Signup
    
    user, membership = user_tenant_a
    
    # Create signup
    signup = Signup(
        id=uuid4(),
        email=user.primary_email,
        status=SignupStatus.PROMOTED.value,
        requested_auth_mode=AuthMode.SSO.value,
    )
    db_session.add(signup)
    await db_session.flush()
    
    # Create valid setup token
    valid_token = SetupToken(
        id=uuid4(),
        token=str(uuid4()),
        user_id=user.id,
        signup_id=signup.id,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    db_session.add(valid_token)
    await db_session.commit()
    
    config_data = {
        "provider_type": "invalid",
        "oidc_config": {
            "client_id": "test",
            "client_secret": "test",
            "discovery_url": "https://example.com",
        }
    }
    
    response = client.post(
        f"/api/v1/setup/sso/configure?token={valid_token.token}",
        json=config_data
    )
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_test_sso_connection_requires_config(client, db_session, user_tenant_a):
    """
    Test: Test SSO connection requires existing configuration.
    """
    from models.signup import Signup
    
    user, membership = user_tenant_a
    
    # Create signup
    signup = Signup(
        id=uuid4(),
        email=user.primary_email,
        status=SignupStatus.PROMOTED.value,
        requested_auth_mode=AuthMode.SSO.value,
    )
    db_session.add(signup)
    await db_session.flush()
    
    # Create valid setup token
    valid_token = SetupToken(
        id=uuid4(),
        token=str(uuid4()),
        user_id=user.id,
        signup_id=signup.id,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    db_session.add(valid_token)
    await db_session.commit()
    
    config_data = {
        "provider_type": "oidc",
        "oidc_config": {
            "client_id": "test-client",
            "client_secret": "test-secret",
            "discovery_url": "https://example.com/.well-known/openid-configuration",
        }
    }
    
    # Try to test without configuring first
    response = client.post(
        f"/api/v1/setup/sso/test?token={valid_token.token}",
        json=config_data
    )
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_test_sso_connection_success(client, db_session, user_tenant_a):
    """
    Test: Test SSO connection with valid configuration.
    """
    from models.tenant import Tenant
    from models.signup import Signup
    
    user, membership = user_tenant_a
    
    # Get tenant
    result = await db_session.execute(
        select(Tenant).where(Tenant.id == membership.tenant_id)
    )
    tenant = result.scalar_one()
    
    # Create signup
    signup = Signup(
        id=uuid4(),
        email=user.primary_email,
        status=SignupStatus.PROMOTED.value,
        requested_auth_mode=AuthMode.SSO.value,
    )
    db_session.add(signup)
    await db_session.flush()
    
    # Create valid setup token
    valid_token = SetupToken(
        id=uuid4(),
        token=str(uuid4()),
        user_id=user.id,
        signup_id=signup.id,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    db_session.add(valid_token)
    await db_session.flush()
    
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
    await db_session.commit()
    
    config_data = {
        "provider_type": "oidc",
        "oidc_config": {
            "client_id": "test-client",
            "client_secret": "test-secret",
            "discovery_url": "https://example.com/.well-known/openid-configuration",
        }
    }
    
    response = client.post(
        f"/api/v1/setup/sso/test?token={valid_token.token}",
        json=config_data
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_complete_sso_setup_requires_config(client, db_session, user_tenant_a):
    """
    Test: Complete SSO setup requires existing configuration.
    """
    from models.signup import Signup
    
    user, membership = user_tenant_a
    
    # Create signup
    signup = Signup(
        id=uuid4(),
        email=user.primary_email,
        status=SignupStatus.PROMOTED.value,
        requested_auth_mode=AuthMode.SSO.value,
    )
    db_session.add(signup)
    await db_session.flush()
    
    # Create valid setup token
    valid_token = SetupToken(
        id=uuid4(),
        token=str(uuid4()),
        user_id=user.id,
        signup_id=signup.id,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    db_session.add(valid_token)
    await db_session.commit()
    
    # Try to complete without configuring
    response = client.post(
        f"/api/v1/setup/sso/complete?token={valid_token.token}"
    )
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_complete_sso_setup_success(client, db_session, user_tenant_a):
    """
    Test: Successfully complete SSO setup and invalidate token.
    """
    from models.tenant import Tenant
    from models.signup import Signup
    
    user, membership = user_tenant_a
    
    # Get tenant
    result = await db_session.execute(
        select(Tenant).where(Tenant.id == membership.tenant_id)
    )
    tenant = result.scalar_one()
    
    # Create signup
    signup = Signup(
        id=uuid4(),
        email=user.primary_email,
        status=SignupStatus.PROMOTED.value,
        requested_auth_mode=AuthMode.SSO.value,
    )
    db_session.add(signup)
    await db_session.flush()
    
    # Create valid setup token
    valid_token = SetupToken(
        id=uuid4(),
        token=str(uuid4()),
        user_id=user.id,
        signup_id=signup.id,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    db_session.add(valid_token)
    await db_session.flush()
    
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
    await db_session.commit()
    
    response = client.post(
        f"/api/v1/setup/sso/complete?token={valid_token.token}"
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["success"] is True
    
    # Verify token was marked as used
    await db_session.refresh(valid_token)
    assert valid_token.used_at is not None
    
    # Verify SSO config is marked as configured
    await db_session.refresh(sso_config)
    assert sso_config.is_configured is True
    
    # Verify signup metadata was updated
    await db_session.refresh(signup)
    assert signup.signup_metadata is not None
    assert signup.signup_metadata.get("sso_status") == "configured"


@pytest.mark.asyncio
async def test_complete_sso_setup_token_cannot_be_reused(client, db_session, user_tenant_a):
    """
    Test: Once SSO setup is completed, token cannot be reused.
    """
    from models.tenant import Tenant
    from models.signup import Signup
    
    user, membership = user_tenant_a
    
    # Get tenant
    result = await db_session.execute(
        select(Tenant).where(Tenant.id == membership.tenant_id)
    )
    tenant = result.scalar_one()
    
    # Create signup
    signup = Signup(
        id=uuid4(),
        email=user.primary_email,
        status=SignupStatus.PROMOTED.value,
        requested_auth_mode=AuthMode.SSO.value,
    )
    db_session.add(signup)
    await db_session.flush()
    
    # Create valid setup token
    valid_token = SetupToken(
        id=uuid4(),
        token=str(uuid4()),
        user_id=user.id,
        signup_id=signup.id,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    db_session.add(valid_token)
    await db_session.flush()
    
    # Create SSO config
    sso_config = TenantSSOConfig(
        id=uuid4(),
        tenant_id=tenant.id,
        provider_type="oidc",
        is_configured=False,
    )
    db_session.add(sso_config)
    await db_session.commit()
    
    # Complete setup first time
    response1 = client.post(
        f"/api/v1/setup/sso/complete?token={valid_token.token}"
    )
    assert response1.status_code == status.HTTP_200_OK
    
    # Try to use token again
    response2 = client.post(
        f"/api/v1/setup/sso/complete?token={valid_token.token}"
    )
    assert response2.status_code == status.HTTP_401_UNAUTHORIZED
