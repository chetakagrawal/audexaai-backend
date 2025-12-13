"""Tests for membership enforcement across all tenant-scoped endpoints."""

import pytest
from fastapi import status
from uuid import uuid4

from auth.jwt import create_dev_token


class TestMembershipEnforcement:
    """Test that membership context is required and validated."""
    
    @pytest.mark.asyncio
    async def test_all_tenant_scoped_endpoints_require_membership(
        self, client, tenant_a, user_tenant_a, db_session
    ):
        """All tenant-scoped endpoints require X-Membership-Id header."""
        user_a, membership_a = user_tenant_a
        
        # Create resources first
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
        
        # Create project
        project_data = {"name": "Test Project", "status": "draft"}
        project_response = client.post("/api/v1/projects", json=project_data, headers=headers_with_membership)
        project = project_response.json()
        project_id = project["id"]
        
        # Create control
        control_data = {
            "control_code": "AC-001",
            "name": "Test Control",
            "is_key": False,
            "is_automated": False,
        }
        control_response = client.post("/api/v1/controls", json=control_data, headers=headers_with_membership)
        control = control_response.json()
        control_id = control["id"]
        
        # Test all endpoints without membership header
        headers_no_membership = {"Authorization": f"Bearer {token}"}
        
        # Projects endpoints
        response = client.get("/api/v1/projects", headers=headers_no_membership)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
        response = client.get(f"/api/v1/projects/{project_id}", headers=headers_no_membership)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
        response = client.post("/api/v1/projects", json=project_data, headers=headers_no_membership)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
        # Controls endpoints
        response = client.get("/api/v1/controls", headers=headers_no_membership)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
        response = client.get(f"/api/v1/controls/{control_id}", headers=headers_no_membership)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
        response = client.post("/api/v1/controls", json=control_data, headers=headers_no_membership)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
        # Project controls endpoints
        response = client.get(f"/api/v1/projects/{project_id}/controls", headers=headers_no_membership)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
        mapping_data = {"control_id": control_id}
        response = client.post(
            f"/api/v1/projects/{project_id}/controls",
            json=mapping_data,
            headers=headers_no_membership,
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.asyncio
    async def test_nonexistent_membership_id_returns_403(
        self, client, tenant_a, user_tenant_a
    ):
        """Non-existent membership ID returns 403."""
        user_a, membership_a = user_tenant_a
        
        token = create_dev_token(
            user_id=user_a.id,
            tenant_id=tenant_a.id,
            role=membership_a.role,
            is_platform_admin=False,
        )
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Membership-Id": str(uuid4()),  # Random UUID that doesn't exist
        }
        
        response = client.get("/api/v1/projects", headers=headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "not found" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_membership_ownership_validation(
        self, client, tenant_a, tenant_b, user_tenant_a, user_tenant_b
    ):
        """Membership must belong to the authenticated user."""
        user_a, membership_a = user_tenant_a
        user_b, membership_b = user_tenant_b
        
        # User A tries to use User B's membership
        token_a = create_dev_token(
            user_id=user_a.id,
            tenant_id=tenant_a.id,
            role=membership_a.role,
            is_platform_admin=False,
        )
        headers = {
            "Authorization": f"Bearer {token_a}",
            "X-Membership-Id": str(membership_b.id),  # User B's membership
        }
        
        # Test multiple endpoints
        response = client.get("/api/v1/projects", headers=headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "does not belong" in response.json()["detail"].lower()
        
        response = client.get("/api/v1/controls", headers=headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
        project_data = {"name": "Test", "status": "draft"}
        response = client.post("/api/v1/projects", json=project_data, headers=headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.asyncio
    async def test_tenant_id_never_derived_from_client_input(
        self, client, tenant_a, tenant_b, user_tenant_a, db_session
    ):
        """Verify tenant_id is never accepted from client input across all endpoints."""
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
        
        # Test project creation - tenant_id should be ignored
        project_data = {
            "name": "Test Project",
            "status": "draft",
            "tenant_id": str(tenant_b.id),  # Should be ignored
        }
        response = client.post("/api/v1/projects", json=project_data, headers=headers)
        assert response.status_code == status.HTTP_200_OK
        project = response.json()
        assert project["tenant_id"] == str(tenant_a.id)  # From membership, not payload
        assert project["tenant_id"] != str(tenant_b.id)
        
        # Test control creation - tenant_id should be ignored
        control_data = {
            "control_code": "AC-001",
            "name": "Test Control",
            "is_key": False,
            "is_automated": False,
            "tenant_id": str(tenant_b.id),  # Should be ignored
        }
        response = client.post("/api/v1/controls", json=control_data, headers=headers)
        assert response.status_code == status.HTTP_200_OK
        control = response.json()
        assert control["tenant_id"] == str(tenant_a.id)  # From membership, not payload
        assert control["tenant_id"] != str(tenant_b.id)

