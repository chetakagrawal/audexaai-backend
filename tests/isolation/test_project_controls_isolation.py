"""Comprehensive tenant isolation tests for Project Controls endpoints."""

import pytest
from fastapi import status
from uuid import uuid4

from auth.jwt import create_dev_token


class TestProjectControlsListIsolation:
    """Test GET /api/v1/projects/{project_id}/controls isolation."""
    
    @pytest.mark.asyncio
    async def test_missing_membership_header_returns_403(
        self, client, tenant_a, user_tenant_a, db_session
    ):
        """Missing X-Membership-Id header returns 403."""
        user_a, membership_a = user_tenant_a
        
        # Create project first
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
        
        # Try to list project controls without membership header
        headers_no_membership = {"Authorization": f"Bearer {token}"}
        response = client.get(f"/api/v1/projects/{project_id}/controls", headers=headers_no_membership)
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.asyncio
    async def test_cross_tenant_read_blocked(
        self, client, tenant_a, tenant_b, user_tenant_a, user_tenant_b, db_session
    ):
        """User in Tenant A cannot see Tenant B's project controls."""
        user_a, membership_a = user_tenant_a
        user_b, membership_b = user_tenant_b
        
        # User B creates project and control in Tenant B
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
        project_response = client.post("/api/v1/projects", json=project_data, headers=headers_b)
        project_b = project_response.json()
        project_b_id = project_b["id"]
        
        control_data = {
            "control_code": "AC-001",
            "name": "Tenant B Control",
            "is_key": False,
            "is_automated": False,
        }
        control_response = client.post("/api/v1/controls", json=control_data, headers=headers_b)
        control_b = control_response.json()
        control_b_id = control_b["id"]
        
        # Attach control to project
        mapping_data = {"control_id": control_b_id}
        client.post(f"/api/v1/projects/{project_b_id}/controls", json=mapping_data, headers=headers_b)
        
        # User A tries to list Tenant B's project controls
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
        
        response = client.get(f"/api/v1/projects/{project_b_id}/controls", headers=headers_a)
        # Should return 404 (project not found in Tenant A)
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestProjectControlsCreateIsolation:
    """Test POST /api/v1/projects/{project_id}/controls isolation."""
    
    @pytest.mark.asyncio
    async def test_missing_membership_header_returns_403(
        self, client, tenant_a, user_tenant_a, db_session
    ):
        """Missing X-Membership-Id header returns 403."""
        user_a, membership_a = user_tenant_a
        
        # Create project and control first
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
        project_response = client.post("/api/v1/projects", json=project_data, headers=headers_with_membership)
        project = project_response.json()
        project_id = project["id"]
        
        control_data = {
            "control_code": "AC-001",
            "name": "Test Control",
            "is_key": False,
            "is_automated": False,
        }
        control_response = client.post("/api/v1/controls", json=control_data, headers=headers_with_membership)
        control = control_response.json()
        control_id = control["id"]
        
        # Try to attach control without membership header
        headers_no_membership = {"Authorization": f"Bearer {token}"}
        mapping_data = {"control_id": control_id}
        response = client.post(
            f"/api/v1/projects/{project_id}/controls",
            json=mapping_data,
            headers=headers_no_membership,
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.asyncio
    async def test_cross_tenant_attach_blocked(
        self, client, tenant_a, tenant_b, user_tenant_a, user_tenant_b, db_session
    ):
        """Cannot attach control from different tenant to project."""
        user_a, membership_a = user_tenant_a
        user_b, membership_b = user_tenant_b
        
        # User A creates project in Tenant A
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
        
        project_data = {"name": "Tenant A Project", "status": "draft"}
        project_response = client.post("/api/v1/projects", json=project_data, headers=headers_a)
        project = project_response.json()
        project_id = project["id"]
        
        # User B creates control in Tenant B
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
        
        control_data = {
            "control_code": "AC-001",
            "name": "Tenant B Control",
            "is_key": False,
            "is_automated": False,
        }
        control_response = client.post("/api/v1/controls", json=control_data, headers=headers_b)
        control_b = control_response.json()
        control_b_id = control_b["id"]
        
        # User A tries to attach Tenant B's control to Tenant A's project
        mapping_data = {"control_id": control_b_id}
        response = client.post(
            f"/api/v1/projects/{project_id}/controls",
            json=mapping_data,
            headers=headers_a,
        )
        # Should fail with 400 or 404
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND,
        ]
    
    @pytest.mark.asyncio
    async def test_cross_tenant_project_access_blocked(
        self, client, tenant_a, tenant_b, user_tenant_a, user_tenant_b, db_session
    ):
        """Cannot attach control to project from different tenant."""
        user_a, membership_a = user_tenant_a
        user_b, membership_b = user_tenant_b
        
        # User B creates project in Tenant B
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
        project_response = client.post("/api/v1/projects", json=project_data, headers=headers_b)
        project_b = project_response.json()
        project_b_id = project_b["id"]
        
        # User A creates control in Tenant A
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
        
        control_data = {
            "control_code": "AC-001",
            "name": "Tenant A Control",
            "is_key": False,
            "is_automated": False,
        }
        control_response = client.post("/api/v1/controls", json=control_data, headers=headers_a)
        control_a = control_response.json()
        control_a_id = control_a["id"]
        
        # User A tries to attach Tenant A's control to Tenant B's project
        mapping_data = {"control_id": control_a_id}
        response = client.post(
            f"/api/v1/projects/{project_b_id}/controls",
            json=mapping_data,
            headers=headers_a,
        )
        # Should fail with 404 (project not found in Tenant A)
        assert response.status_code == status.HTTP_404_NOT_FOUND

