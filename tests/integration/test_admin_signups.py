"""Integration tests for admin signup endpoints."""

from datetime import datetime, UTC
from uuid import uuid4

import pytest
from fastapi import status

from auth.jwt import create_dev_token
from models.signup import Signup, SignupStatus


@pytest.mark.asyncio
async def test_list_signups_requires_platform_admin(client, db_session, user_tenant_a):
    """
    Test: Non-platform admin cannot access admin endpoints.
    """
    user_a, _ = user_tenant_a
    token = create_dev_token(
        user_id=user_a.id,
        tenant_id=None,
        role="admin",
        is_platform_admin=False,
    )
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.get("/api/v1/admin/signups", headers=headers)
    
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_list_signups_platform_admin(client, db_session):
    """
    Test: Platform admin can list signups.
    """
    from models.user import User
    from models.auth_identity import AuthIdentity
    
    # Create platform admin user
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
    
    # Create test signups
    signup1 = Signup(
        id=uuid4(),
        email="test1@example.com",
        status=SignupStatus.PENDING_REVIEW.value,
    )
    signup2 = Signup(
        id=uuid4(),
        email="test2@example.com",
        status=SignupStatus.APPROVED.value,
    )
    signup3 = Signup(
        id=uuid4(),
        email="test3@example.com",
        status=SignupStatus.PENDING_REVIEW.value,
    )
    db_session.add_all([signup1, signup2, signup3])
    await db_session.commit()
    
    token = create_dev_token(
        user_id=platform_admin.id,
        tenant_id=None,
        role="admin",
        is_platform_admin=True,
    )
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.get("/api/v1/admin/signups", headers=headers)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 3  # At least our 3 signups


@pytest.mark.asyncio
async def test_list_signups_filter_by_status(client, db_session):
    """
    Test: Can filter signups by status.
    """
    from models.user import User
    from models.auth_identity import AuthIdentity
    
    # Create platform admin
    platform_admin = User(
        id=uuid4(),
        primary_email="admin2@platform.com",
        name="Admin 2",
        is_platform_admin=True,
        is_active=True,
    )
    db_session.add(platform_admin)
    await db_session.flush()
    
    auth_identity = AuthIdentity(
        id=uuid4(),
        user_id=platform_admin.id,
        provider="dev",
        provider_subject="admin2@platform.com",
        email="admin2@platform.com",
        email_verified=True,
    )
    db_session.add(auth_identity)
    await db_session.commit()
    
    # Create signups with different statuses
    pending1 = Signup(
        id=uuid4(),
        email="pending1@example.com",
        status=SignupStatus.PENDING_REVIEW.value,
    )
    pending2 = Signup(
        id=uuid4(),
        email="pending2@example.com",
        status=SignupStatus.PENDING_REVIEW.value,
    )
    approved = Signup(
        id=uuid4(),
        email="approved@example.com",
        status=SignupStatus.APPROVED.value,
    )
    db_session.add_all([pending1, pending2, approved])
    await db_session.commit()
    
    token = create_dev_token(
        user_id=platform_admin.id,
        tenant_id=None,
        role="admin",
        is_platform_admin=True,
    )
    headers = {"Authorization": f"Bearer {token}"}
    
    # Filter by pending_review
    response = client.get(
        "/api/v1/admin/signups?status=pending_review",
        headers=headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) >= 2  # At least our 2 pending signups
    assert all(s["status"] == "pending_review" for s in data)


@pytest.mark.asyncio
async def test_list_signups_pagination(client, db_session):
    """
    Test: Pagination with limit and offset works.
    """
    from models.user import User
    from models.auth_identity import AuthIdentity
    
    # Create platform admin
    platform_admin = User(
        id=uuid4(),
        primary_email="admin3@platform.com",
        name="Admin 3",
        is_platform_admin=True,
        is_active=True,
    )
    db_session.add(platform_admin)
    await db_session.flush()
    
    auth_identity = AuthIdentity(
        id=uuid4(),
        user_id=platform_admin.id,
        provider="dev",
        provider_subject="admin3@platform.com",
        email="admin3@platform.com",
        email_verified=True,
    )
    db_session.add(auth_identity)
    await db_session.commit()
    
    # Create multiple signups
    signups = [
        Signup(
            id=uuid4(),
            email=f"pagination{i}@example.com",
            status=SignupStatus.PENDING_REVIEW.value,
        )
        for i in range(5)
    ]
    db_session.add_all(signups)
    await db_session.commit()
    
    token = create_dev_token(
        user_id=platform_admin.id,
        tenant_id=None,
        role="admin",
        is_platform_admin=True,
    )
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get first page
    response = client.get("/api/v1/admin/signups?limit=2&offset=0", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 2
    
    # Get second page
    response2 = client.get("/api/v1/admin/signups?limit=2&offset=2", headers=headers)
    assert response2.status_code == status.HTTP_200_OK
    data2 = response2.json()
    assert len(data2) >= 2


@pytest.mark.asyncio
async def test_approve_signup_success(client, db_session):
    """
    Test: Platform admin can approve a signup.
    """
    from models.user import User
    from models.auth_identity import AuthIdentity
    
    # Create platform admin
    platform_admin = User(
        id=uuid4(),
        primary_email="admin4@platform.com",
        name="Admin 4",
        is_platform_admin=True,
        is_active=True,
    )
    db_session.add(platform_admin)
    await db_session.flush()
    
    auth_identity = AuthIdentity(
        id=uuid4(),
        user_id=platform_admin.id,
        provider="dev",
        provider_subject="admin4@platform.com",
        email="admin4@platform.com",
        email_verified=True,
    )
    db_session.add(auth_identity)
    await db_session.commit()
    
    # Create pending signup
    signup = Signup(
        id=uuid4(),
        email="approve@example.com",
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
        f"/api/v1/admin/signups/{signup.id}/approve",
        headers=headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "approved"
    assert "approved_at" in data
    
    # Verify in database
    await db_session.refresh(signup)
    assert signup.status == SignupStatus.APPROVED.value
    assert signup.approved_at is not None


@pytest.mark.asyncio
async def test_approve_signup_not_found(client, db_session):
    """
    Test: Approving non-existent signup returns 404.
    """
    from models.user import User
    from models.auth_identity import AuthIdentity
    
    platform_admin = User(
        id=uuid4(),
        primary_email="admin5@platform.com",
        name="Admin 5",
        is_platform_admin=True,
        is_active=True,
    )
    db_session.add(platform_admin)
    await db_session.flush()
    
    auth_identity = AuthIdentity(
        id=uuid4(),
        user_id=platform_admin.id,
        provider="dev",
        provider_subject="admin5@platform.com",
        email="admin5@platform.com",
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
        f"/api/v1/admin/signups/{fake_id}/approve",
        headers=headers
    )
    
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_approve_rejected_signup_returns_409(client, db_session):
    """
    Test: Cannot approve a rejected signup (409 Conflict).
    """
    from models.user import User
    from models.auth_identity import AuthIdentity
    
    platform_admin = User(
        id=uuid4(),
        primary_email="admin6@platform.com",
        name="Admin 6",
        is_platform_admin=True,
        is_active=True,
    )
    db_session.add(platform_admin)
    await db_session.flush()
    
    auth_identity = AuthIdentity(
        id=uuid4(),
        user_id=platform_admin.id,
        provider="dev",
        provider_subject="admin6@platform.com",
        email="admin6@platform.com",
        email_verified=True,
    )
    db_session.add(auth_identity)
    await db_session.commit()
    
    # Create rejected signup
    signup = Signup(
        id=uuid4(),
        email="rejected@example.com",
        status=SignupStatus.REJECTED.value,
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
        f"/api/v1/admin/signups/{signup.id}/approve",
        headers=headers
    )
    
    assert response.status_code == status.HTTP_409_CONFLICT


@pytest.mark.asyncio
async def test_reject_signup_success(client, db_session):
    """
    Test: Platform admin can reject a signup with optional reason.
    """
    from models.user import User
    from models.auth_identity import AuthIdentity
    
    platform_admin = User(
        id=uuid4(),
        primary_email="admin7@platform.com",
        name="Admin 7",
        is_platform_admin=True,
        is_active=True,
    )
    db_session.add(platform_admin)
    await db_session.flush()
    
    auth_identity = AuthIdentity(
        id=uuid4(),
        user_id=platform_admin.id,
        provider="dev",
        provider_subject="admin7@platform.com",
        email="admin7@platform.com",
        email_verified=True,
    )
    db_session.add(auth_identity)
    await db_session.commit()
    
    # Create pending signup
    signup = Signup(
        id=uuid4(),
        email="reject@example.com",
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
    
    reject_data = {"reason": "Does not meet requirements"}
    response = client.post(
        f"/api/v1/admin/signups/{signup.id}/reject",
        json=reject_data,
        headers=headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "rejected"
    
    # Verify in database
    await db_session.refresh(signup)
    assert signup.status == SignupStatus.REJECTED.value
    assert signup.signup_metadata is not None
    assert signup.signup_metadata.get("rejection_reason") == "Does not meet requirements"


@pytest.mark.asyncio
async def test_reject_signup_without_reason(client, db_session):
    """
    Test: Can reject signup without providing a reason.
    """
    from models.user import User
    from models.auth_identity import AuthIdentity
    
    platform_admin = User(
        id=uuid4(),
        primary_email="admin8@platform.com",
        name="Admin 8",
        is_platform_admin=True,
        is_active=True,
    )
    db_session.add(platform_admin)
    await db_session.flush()
    
    auth_identity = AuthIdentity(
        id=uuid4(),
        user_id=platform_admin.id,
        provider="dev",
        provider_subject="admin8@platform.com",
        email="admin8@platform.com",
        email_verified=True,
    )
    db_session.add(auth_identity)
    await db_session.commit()
    
    signup = Signup(
        id=uuid4(),
        email="reject2@example.com",
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
        f"/api/v1/admin/signups/{signup.id}/reject",
        json={},
        headers=headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    await db_session.refresh(signup)
    assert signup.status == SignupStatus.REJECTED.value


@pytest.mark.asyncio
async def test_reject_rejected_signup_returns_409(client, db_session):
    """
    Test: Cannot reject an already rejected signup (409 Conflict).
    """
    from models.user import User
    from models.auth_identity import AuthIdentity
    
    platform_admin = User(
        id=uuid4(),
        primary_email="admin9@platform.com",
        name="Admin 9",
        is_platform_admin=True,
        is_active=True,
    )
    db_session.add(platform_admin)
    await db_session.flush()
    
    auth_identity = AuthIdentity(
        id=uuid4(),
        user_id=platform_admin.id,
        provider="dev",
        provider_subject="admin9@platform.com",
        email="admin9@platform.com",
        email_verified=True,
    )
    db_session.add(auth_identity)
    await db_session.commit()
    
    # Create rejected signup
    signup = Signup(
        id=uuid4(),
        email="already-rejected@example.com",
        status=SignupStatus.REJECTED.value,
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
        f"/api/v1/admin/signups/{signup.id}/reject",
        json={"reason": "Another reason"},
        headers=headers
    )
    
    assert response.status_code == status.HTTP_409_CONFLICT


@pytest.mark.asyncio
async def test_approve_requires_platform_admin(client, db_session, user_tenant_a):
    """
    Test: Non-platform admin cannot approve signups.
    """
    user_a, _ = user_tenant_a
    signup = Signup(
        id=uuid4(),
        email="test@example.com",
        status=SignupStatus.PENDING_REVIEW.value,
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
        f"/api/v1/admin/signups/{signup.id}/approve",
        headers=headers
    )
    
    assert response.status_code == status.HTTP_403_FORBIDDEN
