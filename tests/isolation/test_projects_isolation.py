"""Comprehensive tenant isolation tests for Projects endpoints."""

import pytest
from fastapi import status
from uuid import uuid4

from auth.jwt import create_dev_token


class TestProjectsListIsolation:
    """Test GET /api/v1/projects isolation."""
    
    @pytest.mark.asyncio
    async def test_missing_membership_header_returns_403(
        self, client, tenant_a, user_tenant_a
    ):
        """Missing X-Membership-Id header returns 403."""
        user_a, membership_a = user_tenant_a
        
        token = create_dev_token(
            user_id=user_a.id,
            tenant_id=tenant_a.id,
            role=membership_a.role,
            is_platform_admin=False,
        )
        headers = {"Authorization": f"Bearer {token}"}
        # Note: NO X-Membership-Id header
        
        response = client.get("/api/v1/projects", headers=headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "X-Membership-Id" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_invalid_membership_id_returns_403(
        self, client, tenant_a, user_tenant_a
    ):
        """Invalid membership ID (not a UUID) returns 400 or 403."""
        user_a, membership_a = user_tenant_a
        
        token = create_dev_token(
            user_id=user_a.id,
            tenant_id=tenant_a.id,
            role=membership_a.role,
            is_platform_admin=False,
        )
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Membership-Id": "not-a-uuid",
        }
        
        response = client.get("/api/v1/projects", headers=headers)
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
        ]
    
    @pytest.mark.asyncio
    async def test_membership_id_for_different_user_returns_403(
        self, client, tenant_a, user_tenant_a, user_tenant_b
    ):
        """Membership ID belonging to a different user returns 403."""
        user_a, membership_a = user_tenant_a
        user_b, membership_b = user_tenant_b
        
        # User A tries to use User B's membership
        token = create_dev_token(
            user_id=user_a.id,
            tenant_id=tenant_a.id,
            role=membership_a.role,
            is_platform_admin=False,
        )
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Membership-Id": str(membership_b.id),  # Wrong user's membership
        }
        
        response = client.get("/api/v1/projects", headers=headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "does not belong" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_cross_tenant_read_blocked(
        self, client, tenant_a, tenant_b, user_tenant_a, user_tenant_b, db_session
    ):
        """User in Tenant A cannot see Tenant B's projects."""
        user_a, membership_a = user_tenant_a
        user_b, membership_b = user_tenant_b
        
        # User B creates a project in Tenant B
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
        
        project_data = {"name": "Tenant B Project", "status": "draft"}
        response = client.post("/api/v1/projects", json=project_data, headers=headers_b)
        assert response.status_code == status.HTTP_200_OK
        project_b = response.json()
        project_b_id = project_b["id"]
        
        # User A tries to list projects - should not see Tenant B's project
        token_a = create_dev_token(
            user_id=user_a.id,
            tenant_id=tenant_a.id,
            role=membership_a.role,
            is_platform_admin=False,
        )
        headers_a = {
            "Authorization": f"Bearer {token_a}",
            "X-Membership-Id": str(membership_a.id),
        }
        
        response = client.get("/api/v1/projects", headers=headers_a)
        assert response.status_code == status.HTTP_200_OK
        projects = response.json()
        project_ids = [p["id"] for p in projects]
        assert project_b_id not in project_ids


class TestProjectsGetIsolation:
    """Test GET /api/v1/projects/{project_id} isolation."""
    
    @pytest.mark.asyncio
    async def test_missing_membership_header_returns_403(
        self, client, tenant_a, user_tenant_a, db_session
    ):
        """Missing X-Membership-Id header returns 403."""
        user_a, membership_a = user_tenant_a
        
        # Create a project first
        token = create_dev_token(
            user_id=user_a.id,
            tenant_id=tenant_a.id,
            role=membership_a.role,
            is_platform_admin=False,
        )
        headers_with_membership = {
            "Authorization": f"Bearer {token}",
            "X-Membership-Id": str(membership_a.id),
        }
        
        project_data = {"name": "Test Project", "status": "draft"}
        response = client.post("/api/v1/projects", json=project_data, headers=headers_with_membership)
        project = response.json()
        project_id = project["id"]
        
        # Try to get project without membership header
        headers_no_membership = {"Authorization": f"Bearer {token}"}
        response = client.get(f"/api/v1/projects/{project_id}", headers=headers_no_membership)
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.asyncio
    async def test_cross_tenant_read_by_id_blocked(
        self, client, tenant_a, tenant_b, user_tenant_a, user_tenant_b, db_session
    ):
        """User in Tenant A cannot access Tenant B's project by ID."""
        user_a, membership_a = user_tenant_a
        user_b, membership_b = user_tenant_b
        
        # User B creates a project in Tenant B
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
        
        project_data = {"name": "Tenant B Project", "status": "draft"}
        response = client.post("/api/v1/projects", json=project_data, headers=headers_b)
        project_b = response.json()
        project_b_id = project_b["id"]
        
        # User A tries to access Tenant B's project by ID
        token_a = create_dev_token(
            user_id=user_a.id,
            tenant_id=tenant_a.id,
            role=membership_a.role,
            is_platform_admin=False,
        )
        headers_a = {
            "Authorization": f"Bearer {token_a}",
            "X-Membership-Id": str(membership_a.id),
        }
        
        response = client.get(f"/api/v1/projects/{project_b_id}", headers=headers_a)
        # Should return 404 (not found due to tenant filtering)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_nonexistent_project_returns_404(
        self, client, tenant_a, user_tenant_a
    ):
        """Non-existent project ID returns 404."""
        user_a, membership_a = user_tenant_a
        
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
        
        fake_id = uuid4()
        response = client.get(f"/api/v1/projects/{fake_id}", headers=headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestProjectsCreateIsolation:
    """Test POST /api/v1/projects isolation."""
    
    @pytest.mark.asyncio
    async def test_missing_membership_header_returns_403(
        self, client, tenant_a, user_tenant_a
    ):
        """Missing X-Membership-Id header returns 403."""
        user_a, membership_a = user_tenant_a
        
        token = create_dev_token(
            user_id=user_a.id,
            tenant_id=tenant_a.id,
            role=membership_a.role,
            is_platform_admin=False,
        )
        headers = {"Authorization": f"Bearer {token}"}
        
        project_data = {"name": "Test Project", "status": "draft"}
        response = client.post("/api/v1/projects", json=project_data, headers=headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.asyncio
    async def test_tenant_id_ignored_from_payload(
        self, client, tenant_a, tenant_b, user_tenant_a, db_session
    ):
        """tenant_id in request payload is ignored; derived from membership context."""
        user_a, membership_a = user_tenant_a
        
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
        
        # Try to create project with tenant_id pointing to Tenant B (should be ignored)
        project_data = {
            "name": "Test Project",
            "status": "draft",
            "tenant_id": str(tenant_b.id),  # Should be ignored
        }
        
        response = client.post("/api/v1/projects", json=project_data, headers=headers)
        assert response.status_code == status.HTTP_200_OK
        
        project = response.json()
        # Project should belong to Tenant A (from membership), not Tenant B
        assert project["tenant_id"] == str(tenant_a.id)
        assert project["tenant_id"] != str(tenant_b.id)
    
    @pytest.mark.asyncio
    async def test_project_created_in_correct_tenant(
        self, client, tenant_a, user_tenant_a, db_session
    ):
        """Project is created in the tenant from membership context."""
        user_a, membership_a = user_tenant_a
        
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
        
        project_data = {"name": "Test Project", "status": "draft"}
        response = client.post("/api/v1/projects", json=project_data, headers=headers)
        assert response.status_code == status.HTTP_200_OK
        
        project = response.json()
        assert project["tenant_id"] == str(tenant_a.id)
        assert project["created_by_membership_id"] == str(membership_a.id)
        
        # Verify it appears in list
        list_response = client.get("/api/v1/projects", headers=headers)
        assert list_response.status_code == status.HTTP_200_OK
        projects = list_response.json()
        assert len(projects) == 1
        assert projects[0]["id"] == project["id"]


class TestProjectsMultiMembershipSwitching:
    """Test multi-membership switching for Projects."""
    
    @pytest.mark.asyncio
    async def test_switching_membership_shows_different_projects(
        self, client, tenant_a, tenant_b, user_tenant_a, db_session
    ):
        """User with two memberships sees different projects when switching."""
        user_a, membership_a = user_tenant_a
        
        # Create second membership for user_a in tenant_b
        from models.user_tenant import UserTenant
        
        membership_b = UserTenant(
            id=uuid4(),
            user_id=user_a.id,
            tenant_id=tenant_b.id,
            role="admin",
            is_default=False,
        )
        db_session.add(membership_b)
        await db_session.commit()
        
        token = create_dev_token(
            user_id=user_a.id,
            tenant_id=tenant_a.id,
            role=membership_a.role,
            is_platform_admin=False,
        )
        
        # Create project in Tenant A
        headers_a = {
            "Authorization": f"Bearer {token}",
            "X-Membership-Id": str(membership_a.id),
        }
        project_data_a = {"name": "Tenant A Project", "status": "draft"}
        response_a = client.post("/api/v1/projects", json=project_data_a, headers=headers_a)
        assert response_a.status_code == status.HTTP_200_OK
        project_a = response_a.json()
        project_a_id = project_a["id"]
        
        # Create project in Tenant B
        headers_b = {
            "Authorization": f"Bearer {token}",
            "X-Membership-Id": str(membership_b.id),
        }
        project_data_b = {"name": "Tenant B Project", "status": "draft"}
        response_b = client.post("/api/v1/projects", json=project_data_b, headers=headers_b)
        assert response_b.status_code == status.HTTP_200_OK
        project_b = response_b.json()
        project_b_id = project_b["id"]
        
        # List projects with membership_a - should only see Tenant A project
        list_response_a = client.get("/api/v1/projects", headers=headers_a)
        assert list_response_a.status_code == status.HTTP_200_OK
        projects_a = list_response_a.json()
        project_ids_a = [p["id"] for p in projects_a]
        assert project_a_id in project_ids_a
        assert project_b_id not in project_ids_a
        
        # List projects with membership_b - should only see Tenant B project
        list_response_b = client.get("/api/v1/projects", headers=headers_b)
        assert list_response_b.status_code == status.HTTP_200_OK
        projects_b = list_response_b.json()
        project_ids_b = [p["id"] for p in projects_b]
        assert project_b_id in project_ids_b
        assert project_a_id not in project_ids_b
        
        # Verify cross-tenant access is blocked
        get_response = client.get(f"/api/v1/projects/{project_b_id}", headers=headers_a)
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

