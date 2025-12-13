"""Shared fixtures and utilities for isolation tests."""

import pytest
from uuid import uuid4

from auth.jwt import create_dev_token
from models.auth_identity import AuthIdentity
from models.tenant import Tenant
from models.user import User
from models.user_tenant import UserTenant


@pytest.fixture
def auth_token_factory():
    """Factory function to create JWT tokens for testing."""
    def _create_token(user_id, tenant_id, role="admin", is_platform_admin=False):
        return create_dev_token(
            user_id=user_id,
            tenant_id=tenant_id,
            role=role,
            is_platform_admin=is_platform_admin,
        )
    return _create_token


@pytest.fixture
def client_factory():
    """Factory function to create authenticated client headers."""
    def _create_headers(token, membership_id=None):
        """Create headers with Authorization and optional X-Membership-Id."""
        headers = {"Authorization": f"Bearer {token}"}
        if membership_id:
            headers["X-Membership-Id"] = str(membership_id)
        return headers
    return _create_headers


@pytest.fixture
async def create_tenant(db_session):
    """Helper to create a tenant."""
    async def _create_tenant(name=None, slug=None):
        tenant = Tenant(
            id=uuid4(),
            name=name or f"Test Tenant {uuid4().hex[:8]}",
            slug=slug or f"test-tenant-{uuid4().hex[:8]}",
            status="active",
        )
        db_session.add(tenant)
        await db_session.commit()
        await db_session.refresh(tenant)
        return tenant
    return _create_tenant


@pytest.fixture
async def create_user(db_session):
    """Helper to create a user."""
    async def _create_user(email=None, name=None, is_platform_admin=False):
        user = User(
            id=uuid4(),
            primary_email=email or f"user-{uuid4().hex[:8]}@example.com",
            name=name or f"User {uuid4().hex[:8]}",
            is_platform_admin=is_platform_admin,
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()
        
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
        await db_session.refresh(user)
        return user
    return _create_user


@pytest.fixture
async def create_membership(db_session):
    """Helper to create a user-tenant membership."""
    async def _create_membership(user, tenant, role="admin", is_default=True):
        membership = UserTenant(
            id=uuid4(),
            user_id=user.id,
            tenant_id=tenant.id,
            role=role,
            is_default=is_default,
        )
        db_session.add(membership)
        await db_session.commit()
        await db_session.refresh(membership)
        return membership
    return _create_membership

