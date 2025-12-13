"""Tests for multi-membership switching behavior."""

import pytest
from fastapi import status
from uuid import uuid4

from auth.jwt import create_dev_token


class TestMultiMembershipSwitching:
    """Test that users with multiple memberships can switch context correctly."""
    
    @pytest.mark.asyncio
    async def test_comprehensive_multi_membership_isolation(
        self, client, tenant_a, tenant_b, user_tenant_a, db_session
    ):
        """Comprehensive test: user with two memberships sees isolated data per tenant."""
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
        
        headers_a = {
            "Authorization": f"Bearer {token}",
            "X-Membership-Id": str(membership_a.id),
        }
        headers_b = {
            "Authorization": f"Bearer {token}",
            "X-Membership-Id": str(membership_b.id),
        }
        
        # Create resources in Tenant A
        project_data_a = {"name": "Tenant A Project", "status": "draft"}
        project_response_a = client.post("/api/v1/projects", json=project_data_a, headers=headers_a)
        project_a = project_response_a.json()
        project_a_id = project_a["id"]
        
        control_data_a = {
            "control_code": "AC-001",
            "name": "Tenant A Control",
            "is_key": False,
            "is_automated": False,
        }
        control_response_a = client.post("/api/v1/controls", json=control_data_a, headers=headers_a)
        control_a = control_response_a.json()
        control_a_id = control_a["id"]
        
        # Create resources in Tenant B
        project_data_b = {"name": "Tenant B Project", "status": "draft"}
        project_response_b = client.post("/api/v1/projects", json=project_data_b, headers=headers_b)
        project_b = project_response_b.json()
        project_b_id = project_b["id"]
        
        control_data_b = {
            "control_code": "AC-001",
            "name": "Tenant B Control",
            "is_key": False,
            "is_automated": False,
        }
        control_response_b = client.post("/api/v1/controls", json=control_data_b, headers=headers_b)
        control_b = control_response_b.json()
        control_b_id = control_b["id"]
        
        # Attach controls to projects
        mapping_a = {"control_id": control_a_id}
        client.post(f"/api/v1/projects/{project_a_id}/controls", json=mapping_a, headers=headers_a)
        
        mapping_b = {"control_id": control_b_id}
        client.post(f"/api/v1/projects/{project_b_id}/controls", json=mapping_b, headers=headers_b)
        
        # Verify Tenant A context - should only see Tenant A resources
        projects_a = client.get("/api/v1/projects", headers=headers_a).json()
        controls_a = client.get("/api/v1/controls", headers=headers_a).json()
        project_controls_a = client.get(f"/api/v1/projects/{project_a_id}/controls", headers=headers_a).json()
        
        assert len(projects_a) == 1
        assert projects_a[0]["id"] == project_a_id
        assert project_b_id not in [p["id"] for p in projects_a]
        
        assert len(controls_a) == 1
        assert controls_a[0]["id"] == control_a_id
        assert control_b_id not in [c["id"] for c in controls_a]
        
        assert len(project_controls_a) == 1
        assert project_controls_a[0]["control_id"] == control_a_id
        
        # Verify Tenant B context - should only see Tenant B resources
        projects_b = client.get("/api/v1/projects", headers=headers_b).json()
        controls_b = client.get("/api/v1/controls", headers=headers_b).json()
        project_controls_b = client.get(f"/api/v1/projects/{project_b_id}/controls", headers=headers_b).json()
        
        assert len(projects_b) == 1
        assert projects_b[0]["id"] == project_b_id
        assert project_a_id not in [p["id"] for p in projects_b]
        
        assert len(controls_b) == 1
        assert controls_b[0]["id"] == control_b_id
        assert control_a_id not in [c["id"] for c in controls_b]
        
        assert len(project_controls_b) == 1
        assert project_controls_b[0]["control_id"] == control_b_id
        
        # Verify cross-tenant access is blocked
        response = client.get(f"/api/v1/projects/{project_b_id}", headers=headers_a)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        response = client.get(f"/api/v1/controls/{control_b_id}", headers=headers_a)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        response = client.get(f"/api/v1/projects/{project_a_id}", headers=headers_b)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        response = client.get(f"/api/v1/controls/{control_a_id}", headers=headers_b)
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_switching_membership_immediately_changes_context(
        self, client, tenant_a, tenant_b, user_tenant_a, db_session
    ):
        """Switching X-Membership-Id header immediately changes data visibility."""
        user_a, membership_a = user_tenant_a
        
        # Create second membership
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
        project_data = {"name": "Test Project", "status": "draft"}
        response = client.post("/api/v1/projects", json=project_data, headers=headers_a)
        project = response.json()
        project_id = project["id"]
        
        # Verify visible with Tenant A membership
        response = client.get("/api/v1/projects", headers=headers_a)
        assert response.status_code == status.HTTP_200_OK
        projects = response.json()
        assert len(projects) == 1
        assert projects[0]["id"] == project_id
        
        # Switch to Tenant B membership
        headers_b = {
            "Authorization": f"Bearer {token}",
            "X-Membership-Id": str(membership_b.id),
        }
        
        # Project should not be visible
        response = client.get("/api/v1/projects", headers=headers_b)
        assert response.status_code == status.HTTP_200_OK
        projects = response.json()
        assert len(projects) == 0
        
        # Direct access should return 404
        response = client.get(f"/api/v1/projects/{project_id}", headers=headers_b)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        # Switch back to Tenant A - project should be visible again
        response = client.get("/api/v1/projects", headers=headers_a)
        assert response.status_code == status.HTTP_200_OK
        projects = response.json()
        assert len(projects) == 1
        assert projects[0]["id"] == project_id

