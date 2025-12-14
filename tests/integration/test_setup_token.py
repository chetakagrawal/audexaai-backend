"""Integration tests for setup token endpoints."""

from datetime import datetime, timedelta, UTC
from uuid import uuid4

import pytest
from fastapi import status
from sqlalchemy import select

from models.signup import Signup, SignupStatus, AuthMode
from models.setup_token import SetupToken
from models.user import User
from models.user_tenant import UserTenant
from models.tenant import Tenant


@pytest.mark.asyncio
async def test_validate_setup_token_not_found(client, db_session):
    """
    Test: Validating non-existent token returns invalid.
    """
    response = client.get(
        "/api/v1/setup/validate",
        params={"token": str(uuid4())}
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["valid"] is False
    assert data["reason"] == "Token not found"
    assert data["user_id"] is None


@pytest.mark.asyncio
async def test_validate_setup_token_expired(client, db_session):
    """
    Test: Validating expired token returns invalid.
    """
    # Create user and tenant
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
    
    membership = UserTenant(
        id=uuid4(),
        user_id=user.id,
        tenant_id=tenant.id,
        role="admin",
        is_default=True,
    )
    db_session.add(membership)
    await db_session.flush()
    
    signup = Signup(
        id=uuid4(),
        email="user@example.com",
        status=SignupStatus.PROMOTED.value,
    )
    db_session.add(signup)
    await db_session.flush()
    
    # Create expired token
    expired_token = SetupToken(
        id=uuid4(),
        token=str(uuid4()),
        user_id=user.id,
        signup_id=signup.id,
        expires_at=datetime.now(UTC) - timedelta(days=1),
    )
    db_session.add(expired_token)
    await db_session.commit()
    
    response = client.get(
        "/api/v1/setup/validate",
        params={"token": expired_token.token}
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["valid"] is False
    assert "expired" in data["reason"].lower()


@pytest.mark.asyncio
async def test_validate_setup_token_used(client, db_session):
    """
    Test: Validating used token returns invalid.
    """
    # Create user and tenant
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
    
    membership = UserTenant(
        id=uuid4(),
        user_id=user.id,
        tenant_id=tenant.id,
        role="admin",
        is_default=True,
    )
    db_session.add(membership)
    await db_session.flush()
    
    signup = Signup(
        id=uuid4(),
        email="user@example.com",
        status=SignupStatus.PROMOTED.value,
    )
    db_session.add(signup)
    await db_session.flush()
    
    # Create used token
    used_token = SetupToken(
        id=uuid4(),
        token=str(uuid4()),
        user_id=user.id,
        signup_id=signup.id,
        expires_at=datetime.now(UTC) + timedelta(days=7),
        used_at=datetime.now(UTC),
    )
    db_session.add(used_token)
    await db_session.commit()
    
    response = client.get(
        "/api/v1/setup/validate",
        params={"token": used_token.token}
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["valid"] is False
    assert "used" in data["reason"].lower()


@pytest.mark.asyncio
async def test_validate_setup_token_success(client, db_session):
    """
    Test: Validating valid token returns user and tenant info.
    """
    # Create user and tenant
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
    
    membership = UserTenant(
        id=uuid4(),
        user_id=user.id,
        tenant_id=tenant.id,
        role="admin",
        is_default=True,
    )
    db_session.add(membership)
    await db_session.flush()
    
    signup = Signup(
        id=uuid4(),
        email="user@example.com",
        status=SignupStatus.PROMOTED.value,
    )
    db_session.add(signup)
    await db_session.flush()
    
    # Create valid token
    valid_token = SetupToken(
        id=uuid4(),
        token=str(uuid4()),
        user_id=user.id,
        signup_id=signup.id,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    db_session.add(valid_token)
    await db_session.commit()
    
    response = client.get(
        "/api/v1/setup/validate",
        params={"token": valid_token.token}
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["valid"] is True
    assert data["user_id"] == str(user.id)
    assert data["tenant_id"] == str(tenant.id)
    assert data["signup_id"] == str(signup.id)
    assert data["user_name"] == "Test User"
    assert data["user_email"] == "user@example.com"
    assert data["tenant_name"] == "Test Tenant"
    assert data["tenant_slug"] == "test-tenant"
    assert data["reason"] is None


@pytest.mark.asyncio
async def test_validate_setup_token_no_membership(client, db_session):
    """
    Test: Validating token for user without tenant membership returns invalid.
    """
    # Create user without tenant membership
    user = User(
        id=uuid4(),
        primary_email="user@example.com",
        name="Test User",
        is_platform_admin=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    
    signup = Signup(
        id=uuid4(),
        email="user@example.com",
        status=SignupStatus.PROMOTED.value,
    )
    db_session.add(signup)
    await db_session.flush()
    
    # Create valid token but user has no membership
    token = SetupToken(
        id=uuid4(),
        token=str(uuid4()),
        user_id=user.id,
        signup_id=signup.id,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    db_session.add(token)
    await db_session.commit()
    
    response = client.get(
        "/api/v1/setup/validate",
        params={"token": token.token}
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["valid"] is False
    assert "membership" in data["reason"].lower()

