"""Integration tests for active membership contract (TDD - failing tests first)."""

import pytest
from fastapi import status

from auth.jwt import create_dev_token


@pytest.mark.asyncio
async def test_login_response_includes_memberships_list(
    client, tenant_a, tenant_b, user_tenant_a, db_session
):
    """
    Test: Login response includes list of all user memberships.
    
    This test will FAIL until we update the login response.
    """
    user_a, membership_a = user_tenant_a
    
    # Create a second membership for the same user in tenant_b
    from models.user_tenant import UserTenant
    from uuid import uuid4
    
    membership_b = UserTenant(
        id=uuid4(),
        user_id=user_a.id,
        tenant_id=tenant_b.id,
        role="viewer",
        is_default=False,
    )
    db_session.add(membership_b)
    await db_session.commit()
    
    # Login
    login_data = {
        "email": user_a.primary_email,
        "tenant_slug": tenant_a.slug,
    }
    response = client.post("/api/v1/auth/dev-login", json=login_data)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    # This will fail until we add memberships to response
    assert "memberships" in data
    memberships = data["memberships"]
    assert isinstance(memberships, list)
    assert len(memberships) == 2
    
    # Verify membership structure
    membership_ids = [m["membership_id"] for m in memberships]
    assert str(membership_a.id) in membership_ids
    assert str(membership_b.id) in membership_ids
    
    # Verify each membership has required fields
    for membership in memberships:
        assert "membership_id" in membership
        assert "tenant_id" in membership
        assert "tenant_name" in membership
        assert "role" in membership


@pytest.mark.asyncio
async def test_missing_membership_header_returns_403(
    client, tenant_a, user_tenant_a, db_session
):
    """
    Test: Missing X-Membership-Id header on tenant-scoped endpoint returns 403.
    
    This test will FAIL until we enforce the header requirement.
    """
    user_a, membership_a = user_tenant_a
    
    token = create_dev_token(
        user_id=user_a.id,
        tenant_id=tenant_a.id,
        role=membership_a.role,
        is_platform_admin=False,
    )
    headers = {"Authorization": f"Bearer {token}"}
    # Note: NO X-Membership-Id header
    
    # Try to access tenant-scoped endpoint
    response = client.get("/api/v1/projects", headers=headers)
    
    # This will fail until we enforce header requirement
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_invalid_membership_header_returns_403(
    client, tenant_a, user_tenant_a, db_session
):
    """
    Test: X-Membership-Id that belongs to a different user returns 403.
    
    This test will FAIL until we validate membership ownership.
    """
    user_a, membership_a = user_tenant_a
    
    # Create another user with a membership
    from models.user import User
    from models.user_tenant import UserTenant
    from uuid import uuid4
    
    other_user = User(
        id=uuid4(),
        primary_email="other@example.com",
        name="Other User",
        is_platform_admin=False,
        is_active=True,
    )
    db_session.add(other_user)
    await db_session.flush()
    
    other_membership = UserTenant(
        id=uuid4(),
        user_id=other_user.id,
        tenant_id=tenant_a.id,
        role="admin",
        is_default=True,
    )
    db_session.add(other_membership)
    await db_session.commit()
    
    # User A tries to use Other User's membership
    token = create_dev_token(
        user_id=user_a.id,
        tenant_id=tenant_a.id,
        role=membership_a.role,
        is_platform_admin=False,
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Membership-Id": str(other_membership.id),  # Wrong user's membership
    }
    
    # Try to access tenant-scoped endpoint
    response = client.get("/api/v1/projects", headers=headers)
    
    # This will fail until we validate membership ownership
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_switching_membership_shows_different_tenant_data(
    client, tenant_a, tenant_b, user_tenant_a, db_session
):
    """
    Test: User with two memberships sees different data when switching X-Membership-Id.
    
    This test verifies that changing the header changes data visibility.
    """
    user_a, membership_a = user_tenant_a
    
    # Create second membership for user_a in tenant_b
    from models.user_tenant import UserTenant
    from uuid import uuid4
    
    membership_b = UserTenant(
        id=uuid4(),
        user_id=user_a.id,
        tenant_id=tenant_b.id,
        role="admin",
        is_default=False,
    )
    db_session.add(membership_b)
    await db_session.commit()
    
    # Create project in tenant_a
    token = create_dev_token(
        user_id=user_a.id,
        tenant_id=tenant_a.id,
        role=membership_a.role,
        is_platform_admin=False,
    )
    headers_a = {
        "Authorization": f"Bearer {token}",
        "X-Membership-Id": str(membership_a.id),
    }
    
    project_data_a = {"name": "Tenant A Project", "status": "draft"}
    response_a = client.post("/api/v1/projects", json=project_data_a, headers=headers_a)
    assert response_a.status_code == status.HTTP_200_OK
    project_a = response_a.json()
    project_a_id = project_a["id"]
    
    # Create project in tenant_b
    headers_b = {
        "Authorization": f"Bearer {token}",
        "X-Membership-Id": str(membership_b.id),
    }
    
    project_data_b = {"name": "Tenant B Project", "status": "draft"}
    response_b = client.post("/api/v1/projects", json=project_data_b, headers=headers_b)
    assert response_b.status_code == status.HTTP_200_OK
    project_b = response_b.json()
    project_b_id = project_b["id"]
    
    # List projects with membership_a - should only see tenant_a project
    list_response_a = client.get("/api/v1/projects", headers=headers_a)
    assert list_response_a.status_code == status.HTTP_200_OK
    projects_a = list_response_a.json()
    project_ids_a = [p["id"] for p in projects_a]
    assert project_a_id in project_ids_a
    assert project_b_id not in project_ids_a  # Should not see tenant_b project
    
    # List projects with membership_b - should only see tenant_b project
    list_response_b = client.get("/api/v1/projects", headers=headers_b)
    assert list_response_b.status_code == status.HTTP_200_OK
    projects_b = list_response_b.json()
    project_ids_b = [p["id"] for p in projects_b]
    assert project_b_id in project_ids_b
    assert project_a_id not in project_ids_b  # Should not see tenant_a project


@pytest.mark.asyncio
async def test_tenant_id_ignored_from_request_payload(
    client, tenant_a, tenant_b, user_tenant_a, user_tenant_b, db_session
):
    """
    Test: Server ignores tenant_id from request payload and uses membership context.
    
    This test verifies that tenant_id in request body is not used for authorization.
    """
    user_a, membership_a = user_tenant_a
    user_b, membership_b = user_tenant_b
    
    # User A tries to create a project with tenant_id set to Tenant B
    token = create_dev_token(
        user_id=user_a.id,
        tenant_id=tenant_a.id,
        role=membership_a.role,
        is_platform_admin=False,
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Membership-Id": str(membership_a.id),
    }
    
    # Attempt to create project with tenant_id pointing to tenant_b
    project_data = {
        "name": "Hacked Project",
        "status": "draft",
        "tenant_id": str(tenant_b.id),  # Should be ignored
    }
    
    response = client.post("/api/v1/projects", json=project_data, headers=headers)
    
    # Should succeed (if tenant_id is ignored) or fail with 400 (if rejected)
    # Either way, the project should be created in tenant_a, not tenant_b
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]
    
    if response.status_code == status.HTTP_200_OK:
        project = response.json()
        # Project should belong to tenant_a (from membership), not tenant_b
        assert project["tenant_id"] == str(tenant_a.id)
        assert project["tenant_id"] != str(tenant_b.id)
    
    # Verify user_b cannot see this project (it's in tenant_a)
    token_b = create_dev_token(
        user_id=user_b.id,
        tenant_id=tenant_b.id,
        role=membership_b.role,
        is_platform_admin=False,
    )
    headers_b = {
        "Authorization": f"Bearer {token_b}",
        "X-Membership-Id": str(membership_b.id),
    }
    
    list_response = client.get("/api/v1/projects", headers=headers_b)
    assert list_response.status_code == status.HTTP_200_OK
    projects = list_response.json()
    project_ids = [p["id"] for p in projects]
    
    if response.status_code == status.HTTP_200_OK:
        assert project["id"] not in project_ids  # User B should not see tenant A's project

