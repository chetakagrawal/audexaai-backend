"""Integration tests for signup promotion with setup token generation."""

from datetime import datetime, timedelta, UTC
from uuid import UUID, uuid4

import pytest
from fastapi import status
from sqlalchemy import select

from auth.jwt import create_dev_token
from models.signup import Signup, SignupStatus, AuthMode
from models.setup_token import SetupToken
from models.user import User
from models.auth_identity import AuthIdentity


@pytest.mark.asyncio
async def test_promote_sso_signup_creates_setup_token(client, db_session):
    """
    Test: Promoting an SSO signup creates a setup token.
    """
    # Create platform admin
    platform_admin = User(
        id=uuid4(),
        primary_email="admin@platform.com",
        name="Platform Admin",
        is_platform_admin=True,
        is_active=True,
    )
    db_session.add(platform_admin)
    await db_session.flush()
    
    auth_identity = AuthIdentity(
        id=uuid4(),
        user_id=platform_admin.id,
        provider="dev",
        provider_subject="admin@platform.com",
        email="admin@platform.com",
        email_verified=True,
    )
    db_session.add(auth_identity)
    await db_session.commit()
    
    # Create SSO signup
    signup = Signup(
        id=uuid4(),
        email="sso-user@example.com",
        full_name="SSO User",
        company_name="SSO Corp",
        company_domain="ssocorp.com",
        requested_auth_mode=AuthMode.SSO.value,
        status=SignupStatus.APPROVED.value,
    )
    db_session.add(signup)
    await db_session.commit()
    
    token = create_dev_token(
        user_id=platform_admin.id,
        tenant_id=None,
        role="admin",
        is_platform_admin=True,
    )
    headers = {"Authorization": f"Bearer {token}"}
    
    # Promote signup
    response = client.post(
        f"/api/v1/admin/signups/{signup.id}/promote",
        headers=headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "tenant_id" in data
    assert "user_id" in data
    
    # Verify setup token was created
    result = await db_session.execute(
        select(SetupToken).where(SetupToken.signup_id == signup.id)
    )
    setup_token = result.scalar_one_or_none()
    
    assert setup_token is not None
    assert setup_token.user_id == UUID(data["user_id"])  # Check from response
    assert setup_token.expires_at > datetime.now(UTC)
    assert setup_token.used_at is None


@pytest.mark.asyncio
async def test_promote_direct_signup_no_setup_token(client, db_session):
    """
    Test: Promoting a direct auth signup does NOT create a setup token.
    """
    # Create platform admin
    platform_admin = User(
        id=uuid4(),
        primary_email="admin@platform.com",
        name="Platform Admin",
        is_platform_admin=True,
        is_active=True,
    )
    db_session.add(platform_admin)
    await db_session.flush()
    
    auth_identity = AuthIdentity(
        id=uuid4(),
        user_id=platform_admin.id,
        provider="dev",
        provider_subject="admin@platform.com",
        email="admin@platform.com",
        email_verified=True,
    )
    db_session.add(auth_identity)
    await db_session.commit()
    
    # Create direct auth signup
    signup = Signup(
        id=uuid4(),
        email="direct-user@example.com",
        full_name="Direct User",
        company_name="Direct Corp",
        company_domain="directcorp.com",
        requested_auth_mode=AuthMode.DIRECT.value,
        status=SignupStatus.APPROVED.value,
    )
    db_session.add(signup)
    await db_session.commit()
    
    token = create_dev_token(
        user_id=platform_admin.id,
        tenant_id=None,
        role="admin",
        is_platform_admin=True,
    )
    headers = {"Authorization": f"Bearer {token}"}
    
    # Promote signup
    response = client.post(
        f"/api/v1/admin/signups/{signup.id}/promote",
        headers=headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    
    # Verify NO setup token was created
    result = await db_session.execute(
        select(SetupToken).where(SetupToken.signup_id == signup.id)
    )
    setup_token = result.scalar_one_or_none()
    
    assert setup_token is None
