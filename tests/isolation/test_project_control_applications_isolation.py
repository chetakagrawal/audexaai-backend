"""Comprehensive tenant isolation tests for Project Control Applications endpoints."""

import pytest
from fastapi import status
from uuid import uuid4

from auth.jwt import create_dev_token


class TestProjectControlApplicationsListIsolation:
    """Test GET /api/v1/project-controls/{project_control_id}/applications isolation."""
    
    @pytest.mark.asyncio
    async def test_missing_membership_header_returns_403(
        self, client, tenant_a, user_tenant_a, db_session
    ):
        """Missing X-Membership-Id header returns 403."""
        user_a, membership_a = user_tenant_a
        
        # Create project, control, project_control, and application
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
        
        # Attach control to project
        mapping_data = {"control_id": control_id}
        pc_response = client.post(f"/api/v1/projects/{project_id}/controls", json=mapping_data, headers=headers_with_membership)
        project_control = pc_response.json()
        project_control_id = project_control["id"]
        
        application_data = {"name": "Test Application"}
        app_response = client.post("/api/v1/applications", json=application_data, headers=headers_with_membership)
        application = app_response.json()
        application_id = application["id"]
        
        # Attach application to project control
        pca_data = {"application_id": application_id}
        client.post(f"/api/v1/project-controls/{project_control_id}/applications", json=pca_data, headers=headers_with_membership)
        
        # Try to list applications without membership header
        headers_no_membership = {"Authorization": f"Bearer {token}"}
        response = client.get(f"/api/v1/project-controls/{project_control_id}/applications", headers=headers_no_membership)
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.asyncio
    async def test_cross_tenant_read_blocked(
        self, client, tenant_a, tenant_b, user_tenant_a, user_tenant_b, db_session
    ):
        """User in Tenant A cannot see Tenant B's project control applications."""
        user_a, membership_a = user_tenant_a
        user_b, membership_b = user_tenant_b
        
        # User B creates project, control, project_control, and application in Tenant B
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
        pc_response = client.post(f"/api/v1/projects/{project_b_id}/controls", json=mapping_data, headers=headers_b)
        project_control_b = pc_response.json()
        project_control_b_id = project_control_b["id"]
        
        application_data = {"name": "Tenant B Application"}
        app_response = client.post("/api/v1/applications", json=application_data, headers=headers_b)
        application_b = app_response.json()
        application_b_id = application_b["id"]
        
        # Attach application to project control
        pca_data = {"application_id": application_b_id}
        client.post(f"/api/v1/project-controls/{project_control_b_id}/applications", json=pca_data, headers=headers_b)
        
        # User A tries to list Tenant B's project control applications
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
        
        response = client.get(f"/api/v1/project-controls/{project_control_b_id}/applications", headers=headers_a)
        # Should return 404 (project control not found in Tenant A)
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestProjectControlApplicationsCreateIsolation:
    """Test POST /api/v1/project-controls/{project_control_id}/applications isolation."""
    
    @pytest.mark.asyncio
    async def test_missing_membership_header_returns_403(
        self, client, tenant_a, user_tenant_a, db_session
    ):
        """Missing X-Membership-Id header returns 403."""
        user_a, membership_a = user_tenant_a
        
        # Create project, control, project_control, and application
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
        
        # Attach control to project
        mapping_data = {"control_id": control_id}
        pc_response = client.post(f"/api/v1/projects/{project_id}/controls", json=mapping_data, headers=headers_with_membership)
        project_control = pc_response.json()
        project_control_id = project_control["id"]
        
        application_data = {"name": "Test Application"}
        app_response = client.post("/api/v1/applications", json=application_data, headers=headers_with_membership)
        application = app_response.json()
        application_id = application["id"]
        
        # Try to attach application without membership header
        headers_no_membership = {"Authorization": f"Bearer {token}"}
        pca_data = {"application_id": application_id}
        response = client.post(
            f"/api/v1/project-controls/{project_control_id}/applications",
            json=pca_data,
            headers=headers_no_membership,
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.asyncio
    async def test_cross_tenant_attach_application_blocked(
        self, client, tenant_a, tenant_b, user_tenant_a, user_tenant_b, db_session
    ):
        """Cannot attach application from different tenant to project control."""
        user_a, membership_a = user_tenant_a
        user_b, membership_b = user_tenant_b
        
        # User A creates project, control, and project_control in Tenant A
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
        
        control_data = {
            "control_code": "AC-001",
            "name": "Tenant A Control",
            "is_key": False,
            "is_automated": False,
        }
        control_response = client.post("/api/v1/controls", json=control_data, headers=headers_a)
        control = control_response.json()
        control_id = control["id"]
        
        # Attach control to project
        mapping_data = {"control_id": control_id}
        pc_response = client.post(f"/api/v1/projects/{project_id}/controls", json=mapping_data, headers=headers_a)
        project_control = pc_response.json()
        project_control_id = project_control["id"]
        
        # User B creates application in Tenant B
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
        
        application_data = {"name": "Tenant B Application"}
        app_response = client.post("/api/v1/applications", json=application_data, headers=headers_b)
        application_b = app_response.json()
        application_b_id = application_b["id"]
        
        # User A tries to attach Tenant B's application to Tenant A's project control
        pca_data = {"application_id": application_b_id}
        response = client.post(
            f"/api/v1/project-controls/{project_control_id}/applications",
            json=pca_data,
            headers=headers_a,
        )
        # Should fail with 400 or 404
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND,
        ]
    
    @pytest.mark.asyncio
    async def test_cross_tenant_project_control_access_blocked(
        self, client, tenant_a, tenant_b, user_tenant_a, user_tenant_b, db_session
    ):
        """Cannot attach application to project control from different tenant."""
        user_a, membership_a = user_tenant_a
        user_b, membership_b = user_tenant_b
        
        # User B creates project, control, and project_control in Tenant B
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
        pc_response = client.post(f"/api/v1/projects/{project_b_id}/controls", json=mapping_data, headers=headers_b)
        project_control_b = pc_response.json()
        project_control_b_id = project_control_b["id"]
        
        # User A creates application in Tenant A
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
        
        application_data = {"name": "Tenant A Application"}
        app_response = client.post("/api/v1/applications", json=application_data, headers=headers_a)
        application_a = app_response.json()
        application_a_id = application_a["id"]
        
        # User A tries to attach Tenant A's application to Tenant B's project control
        pca_data = {"application_id": application_a_id}
        response = client.post(
            f"/api/v1/project-controls/{project_control_b_id}/applications",
            json=pca_data,
            headers=headers_a,
        )
        # Should fail with 404 (project control not found in Tenant A)
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestProjectControlApplicationsDeleteIsolation:
    """Test DELETE /api/v1/project-control-applications/{pca_id} isolation."""
    
    @pytest.mark.asyncio
    async def test_cross_tenant_delete_blocked(
        self, client, tenant_a, tenant_b, user_tenant_a, user_tenant_b, db_session
    ):
        """User in Tenant A cannot delete Tenant B's project control application."""
        user_a, membership_a = user_tenant_a
        user_b, membership_b = user_tenant_b
        
        # User B creates project, control, project_control, application, and mapping in Tenant B
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
        pc_response = client.post(f"/api/v1/projects/{project_b_id}/controls", json=mapping_data, headers=headers_b)
        project_control_b = pc_response.json()
        project_control_b_id = project_control_b["id"]
        
        application_data = {"name": "Tenant B Application"}
        app_response = client.post("/api/v1/applications", json=application_data, headers=headers_b)
        application_b = app_response.json()
        application_b_id = application_b["id"]
        
        # Attach application to project control
        pca_data = {"application_id": application_b_id}
        pca_response = client.post(f"/api/v1/project-controls/{project_control_b_id}/applications", json=pca_data, headers=headers_b)
        pca_b = pca_response.json()
        pca_b_id = pca_b["id"]
        
        # User A tries to delete Tenant B's mapping
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
        
        response = client.delete(f"/api/v1/project-control-applications/{pca_b_id}", headers=headers_a)
        # Should fail with 404 (mapping not found in Tenant A)
        assert response.status_code == status.HTTP_404_NOT_FOUND

