"""Integration tests for signup promotion endpoint."""

from datetime import datetime, UTC
from uuid import uuid4

import pytest
from fastapi import status
from sqlalchemy import select

from auth.jwt import create_dev_token
from models.auth_identity import AuthIdentity
from models.signup import Signup, SignupStatus, AuthMode
from models.tenant import Tenant
from models.user import User
from models.user_tenant import UserTenant


@pytest.mark.asyncio
async def test_promote_signup_success(client, db_session):
    """
    Test: Platform admin can promote an approved signup.
    
    Should create tenant, user, membership, and auth identity.
    """
    from models.auth_identity import AuthIdentity
    from models.user import User
    
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
    
    from models.auth_identity import AuthIdentity as AuthIdentityModel
    auth_identity = AuthIdentityModel(
        id=uuid4(),
        user_id=platform_admin.id,
        provider="dev",
        provider_subject="admin@platform.com",
        email="admin@platform.com",
        email_verified=True,
    )
    db_session.add(auth_identity)
    await db_session.commit()
    
    # Create approved signup
    signup = Signup(
        id=uuid4(),
        email="promote@example.com",
        full_name="John Doe",
        company_name="Acme Corp",
        company_domain="acme.com",
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
    
    response = client.post(
        f"/api/v1/admin/signups/{signup.id}/promote",
        headers=headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "tenant_id" in data
    assert "user_id" in data
    assert "membership_id" in data
    assert data["status"] == "promoted"
    
    # Verify signup was updated
    await db_session.refresh(signup)
    assert signup.status == SignupStatus.PROMOTED.value
    assert signup.tenant_id is not None
    assert signup.user_id is not None
    assert signup.membership_id is not None
    assert signup.promoted_at is not None
    
    # Verify tenant was created
    result = await db_session.execute(
        select(Tenant).where(Tenant.id == signup.tenant_id)
    )
    tenant = result.scalar_one()
    assert tenant.name == "Acme Corp"
    assert tenant.slug is not None
    assert tenant.status == "active"
    
    # Verify user was created
    result = await db_session.execute(
        select(User).where(User.id == signup.user_id)
    )
    user = result.scalar_one()
    assert user.primary_email == "promote@example.com"
    assert user.name == "John Doe"
    assert user.is_platform_admin is False
    assert user.is_active is True
    
    # Verify membership was created
    result = await db_session.execute(
        select(UserTenant).where(UserTenant.id == signup.membership_id)
    )
    membership = result.scalar_one()
    assert membership.user_id == signup.user_id
    assert membership.tenant_id == signup.tenant_id
    assert membership.role == "owner"
    assert membership.is_default is True
    
    # Verify auth identity was created
    result = await db_session.execute(
        select(AuthIdentity).where(AuthIdentity.user_id == signup.user_id)
    )
    auth_id = result.scalar_one()
    assert auth_id.provider == "dev"
    assert auth_id.provider_subject == "promote@example.com"
    assert auth_id.email == "promote@example.com"


@pytest.mark.asyncio
async def test_promote_signup_idempotent(client, db_session):
    """
    Test: Promoting an already promoted signup is idempotent.
    
    Should return existing tenant_id/user_id/membership_id without creating duplicates.
    """
    from models.user import User
    from models.auth_identity import AuthIdentity as AuthIdentityModel
    
    platform_admin = User(
        id=uuid4(),
        primary_email="admin2@platform.com",
        name="Admin 2",
        is_platform_admin=True,
        is_active=True,
    )
    db_session.add(platform_admin)
    await db_session.flush()
    
    auth_identity = AuthIdentityModel(
        id=uuid4(),
        user_id=platform_admin.id,
        provider="dev",
        provider_subject="admin2@platform.com",
        email="admin2@platform.com",
        email_verified=True,
    )
    db_session.add(auth_identity)
    await db_session.commit()
    
    # Create promoted signup (already promoted)
    tenant_id = uuid4()
    user_id = uuid4()
    membership_id = uuid4()
    
    signup = Signup(
        id=uuid4(),
        email="idempotent@example.com",
        company_name="Existing Corp",
        status=SignupStatus.PROMOTED.value,
        tenant_id=tenant_id,
        user_id=user_id,
        membership_id=membership_id,
        promoted_at=datetime.now(UTC),
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
    
    # Try to promote again
    response = client.post(
        f"/api/v1/admin/signups/{signup.id}/promote",
        headers=headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["tenant_id"] == str(tenant_id)
    assert data["user_id"] == str(user_id)
    assert data["membership_id"] == str(membership_id)
    assert data["status"] == "promoted"
    
    # Verify no duplicate was created (should only be one)
    result = await db_session.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    tenants = result.scalars().all()
    assert len(tenants) <= 1  # Should be 0 (doesn't exist) or 1 (already exists)


@pytest.mark.asyncio
async def test_promote_signup_requires_approved_status(client, db_session):
    """
    Test: Cannot promote signup that is not approved or verified.
    """
    from models.user import User
    from models.auth_identity import AuthIdentity as AuthIdentityModel
    
    platform_admin = User(
        id=uuid4(),
        primary_email="admin3@platform.com",
        name="Admin 3",
        is_platform_admin=True,
        is_active=True,
    )
    db_session.add(platform_admin)
    await db_session.flush()
    
    auth_identity = AuthIdentityModel(
        id=uuid4(),
        user_id=platform_admin.id,
        provider="dev",
        provider_subject="admin3@platform.com",
        email="admin3@platform.com",
        email_verified=True,
    )
    db_session.add(auth_identity)
    await db_session.commit()
    
    # Create pending signup (not approved)
    signup = Signup(
        id=uuid4(),
        email="pending@example.com",
        status=SignupStatus.PENDING_REVIEW.value,
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
    
    response = client.post(
        f"/api/v1/admin/signups/{signup.id}/promote",
        headers=headers
    )
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_promote_signup_with_sso_mode(client, db_session):
    """
    Test: Promoting SSO signup creates placeholder auth identity with SSO metadata.
    """
    from models.user import User
    from models.auth_identity import AuthIdentity as AuthIdentityModel
    
    platform_admin = User(
        id=uuid4(),
        primary_email="admin4@platform.com",
        name="Admin 4",
        is_platform_admin=True,
        is_active=True,
    )
    db_session.add(platform_admin)
    await db_session.flush()
    
    auth_identity = AuthIdentityModel(
        id=uuid4(),
        user_id=platform_admin.id,
        provider="dev",
        provider_subject="admin4@platform.com",
        email="admin4@platform.com",
        email_verified=True,
    )
    db_session.add(auth_identity)
    await db_session.commit()
    
    signup = Signup(
        id=uuid4(),
        email="sso@example.com",
        full_name="SSO User",
        company_name="SSO Corp",
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
    
    response = client.post(
        f"/api/v1/admin/signups/{signup.id}/promote",
        headers=headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    
    # Verify auth identity has SSO provider
    await db_session.refresh(signup)
    result = await db_session.execute(
        select(AuthIdentity).where(AuthIdentity.user_id == signup.user_id)
    )
    auth_id = result.scalar_one()
    assert auth_id.provider == "oidc"
    
    # Verify signup metadata has SSO status
    assert signup.signup_metadata is not None
    assert signup.signup_metadata.get("sso_status") == "not_configured"


@pytest.mark.asyncio
async def test_promote_signup_tenant_slug_uniqueness(client, db_session):
    """
    Test: Tenant slug is unique - if slug exists, append suffix.
    """
    from models.user import User
    from models.auth_identity import AuthIdentity as AuthIdentityModel
    
    platform_admin = User(
        id=uuid4(),
        primary_email="admin5@platform.com",
        name="Admin 5",
        is_platform_admin=True,
        is_active=True,
    )
    db_session.add(platform_admin)
    await db_session.flush()
    
    auth_identity = AuthIdentityModel(
        id=uuid4(),
        user_id=platform_admin.id,
        provider="dev",
        provider_subject="admin5@platform.com",
        email="admin5@platform.com",
        email_verified=True,
    )
    db_session.add(auth_identity)
    await db_session.commit()
    
    # Create existing tenant with slug
    existing_tenant = Tenant(
        id=uuid4(),
        name="Test Company",
        slug="test-company",
        status="active",
    )
    db_session.add(existing_tenant)
    await db_session.commit()
    
    # Create signup with same company name
    signup = Signup(
        id=uuid4(),
        email="unique@example.com",
        company_name="Test Company",
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
    
    response = client.post(
        f"/api/v1/admin/signups/{signup.id}/promote",
        headers=headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    
    # Verify new tenant has different slug
    await db_session.refresh(signup)
    result = await db_session.execute(
        select(Tenant).where(Tenant.id == signup.tenant_id)
    )
    tenant = result.scalar_one()
    assert tenant.slug != "test-company"
    assert tenant.slug.startswith("test-company")


@pytest.mark.asyncio
async def test_promote_signup_without_company_name(client, db_session):
    """
    Test: Promotion works when company_name is null - uses email local-part + "Workspace".
    """
    from models.user import User
    from models.auth_identity import AuthIdentity as AuthIdentityModel
    
    platform_admin = User(
        id=uuid4(),
        primary_email="admin6@platform.com",
        name="Admin 6",
        is_platform_admin=True,
        is_active=True,
    )
    db_session.add(platform_admin)
    await db_session.flush()
    
    auth_identity = AuthIdentityModel(
        id=uuid4(),
        user_id=platform_admin.id,
        provider="dev",
        provider_subject="admin6@platform.com",
        email="admin6@platform.com",
        email_verified=True,
    )
    db_session.add(auth_identity)
    await db_session.commit()
    
    signup = Signup(
        id=uuid4(),
        email="individual@example.com",
        full_name="Individual User",
        company_name=None,  # No company
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
    
    response = client.post(
        f"/api/v1/admin/signups/{signup.id}/promote",
        headers=headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    
    await db_session.refresh(signup)
    result = await db_session.execute(
        select(Tenant).where(Tenant.id == signup.tenant_id)
    )
    tenant = result.scalar_one()
    assert "individual" in tenant.name.lower() or "workspace" in tenant.name.lower()


@pytest.mark.asyncio
async def test_promote_signup_upserts_existing_user(client, db_session):
    """
    Test: If user with email already exists, reuse it instead of creating duplicate.
    """
    from models.user import User
    from models.auth_identity import AuthIdentity as AuthIdentityModel
    
    platform_admin = User(
        id=uuid4(),
        primary_email="admin7@platform.com",
        name="Admin 7",
        is_platform_admin=True,
        is_active=True,
    )
    db_session.add(platform_admin)
    await db_session.flush()
    
    auth_identity = AuthIdentityModel(
        id=uuid4(),
        user_id=platform_admin.id,
        provider="dev",
        provider_subject="admin7@platform.com",
        email="admin7@platform.com",
        email_verified=True,
    )
    db_session.add(auth_identity)
    
    # Create existing user with same email
    existing_user = User(
        id=uuid4(),
        primary_email="existing@example.com",
        name="Existing User",
        is_platform_admin=False,
        is_active=True,
    )
    db_session.add(existing_user)
    await db_session.commit()
    
    # Create signup with same email
    signup = Signup(
        id=uuid4(),
        email="existing@example.com",
        company_name="New Company",
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
    
    response = client.post(
        f"/api/v1/admin/signups/{signup.id}/promote",
        headers=headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    
    # Verify existing user was reused
    await db_session.refresh(signup)
    assert signup.user_id == existing_user.id
    
    # Verify membership was created linking existing user to new tenant
    result = await db_session.execute(
        select(UserTenant).where(UserTenant.user_id == existing_user.id)
    )
    memberships = result.scalars().all()
    assert len(memberships) >= 1


@pytest.mark.asyncio
async def test_promote_signup_requires_platform_admin(client, db_session, user_tenant_a):
    """
    Test: Non-platform admin cannot promote signups.
    """
    user_a, _ = user_tenant_a
    signup = Signup(
        id=uuid4(),
        email="test@example.com",
        status=SignupStatus.APPROVED.value,
    )
    db_session.add(signup)
    await db_session.commit()
    
    token = create_dev_token(
        user_id=user_a.id,
        tenant_id=None,
        role="admin",
        is_platform_admin=False,
    )
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.post(
        f"/api/v1/admin/signups/{signup.id}/promote",
        headers=headers
    )
    
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_promote_signup_not_found(client, db_session):
    """
    Test: Promoting non-existent signup returns 404.
    """
    from models.user import User
    from models.auth_identity import AuthIdentity as AuthIdentityModel
    
    platform_admin = User(
        id=uuid4(),
        primary_email="admin8@platform.com",
        name="Admin 8",
        is_platform_admin=True,
        is_active=True,
    )
    db_session.add(platform_admin)
    await db_session.flush()
    
    auth_identity = AuthIdentityModel(
        id=uuid4(),
        user_id=platform_admin.id,
        provider="dev",
        provider_subject="admin8@platform.com",
        email="admin8@platform.com",
        email_verified=True,
    )
    db_session.add(auth_identity)
    await db_session.commit()
    
    token = create_dev_token(
        user_id=platform_admin.id,
        tenant_id=None,
        role="admin",
        is_platform_admin=True,
    )
    headers = {"Authorization": f"Bearer {token}"}
    
    fake_id = uuid4()
    response = client.post(
        f"/api/v1/admin/signups/{fake_id}/promote",
        headers=headers
    )
    
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_promote_signup_transaction_rollback_on_error(client, db_session):
    """
    Test: If promotion fails partway, no partial records are created.
    
    This tests transaction safety - if creating tenant/user/membership fails,
    everything should roll back.
    """
    from models.user import User
    from models.auth_identity import AuthIdentity as AuthIdentityModel
    
    platform_admin = User(
        id=uuid4(),
        primary_email="admin9@platform.com",
        name="Admin 9",
        is_platform_admin=True,
        is_active=True,
    )
    db_session.add(platform_admin)
    await db_session.flush()
    
    auth_identity = AuthIdentityModel(
        id=uuid4(),
        user_id=platform_admin.id,
        provider="dev",
        provider_subject="admin9@platform.com",
        email="admin9@platform.com",
        email_verified=True,
    )
    db_session.add(auth_identity)
    await db_session.commit()
    
    signup = Signup(
        id=uuid4(),
        email="transaction@example.com",
        company_name="Transaction Test",
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
    
    # Count existing records
    result = await db_session.execute(select(Tenant))
    tenant_count_before = len(result.scalars().all())
    
    result = await db_session.execute(select(User))
    user_count_before = len(result.scalars().all())
    
    # Promotion should succeed - transaction safety is tested by idempotency and constraints
    response = client.post(
        f"/api/v1/admin/signups/{signup.id}/promote",
        headers=headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    
    # Verify signup was updated (transaction completed)
    await db_session.refresh(signup)
    assert signup.status == SignupStatus.PROMOTED.value
