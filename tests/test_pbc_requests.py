"""Integration tests for PBC requests endpoints."""

from datetime import date
from uuid import uuid4

import pytest
from fastapi import status

from auth.jwt import create_dev_token
from models.application import Application
from models.control import Control
from models.project import Project


@pytest.mark.asyncio
async def test_create_pbc_request_success(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Creating a PBC request succeeds."""
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
    
    # Create project
    project_data = {"name": "Test Project", "status": "active"}
    project_response = client.post("/api/v1/projects", json=project_data, headers=headers)
    assert project_response.status_code == status.HTTP_200_OK
    project = project_response.json()
    project_id = project["id"]
    
    # Create application
    app_data = {"name": "Test Application"}
    app_response = client.post("/api/v1/applications", json=app_data, headers=headers)
    assert app_response.status_code == status.HTTP_201_CREATED
    application = app_response.json()
    application_id = application["id"]
    
    # Create control
    control_data = {
        "control_code": "PBC-001",
        "name": "Test Control",
        "is_key": False,
        "is_automated": False,
    }
    control_response = client.post("/api/v1/controls", json=control_data, headers=headers)
    assert control_response.status_code == status.HTTP_200_OK
    control = control_response.json()
    control_id = control["id"]
    
    # Create PBC request
    pbc_data = {
        "project_id": project_id,
        "application_id": application_id,
        "control_id": control_id,
        "owner_membership_id": str(membership_a.id),
        "title": "Request Access Logs",
        "samples_requested": 25,
        "due_date": "2025-03-15",
        "status": "pending",
    }
    
    response = client.post("/api/v1/pbc-requests", json=pbc_data, headers=headers)
    
    assert response.status_code == status.HTTP_201_CREATED
    
    pbc_request = response.json()
    assert pbc_request["title"] == "Request Access Logs"
    assert pbc_request["samples_requested"] == 25
    assert pbc_request["due_date"] == "2025-03-15"
    assert pbc_request["status"] == "pending"
    assert pbc_request["project_id"] == project_id
    assert pbc_request["application_id"] == application_id
    assert pbc_request["control_id"] == control_id
    assert pbc_request["owner_membership_id"] == str(membership_a.id)
    assert pbc_request["tenant_id"] == str(tenant_a.id)
    assert "id" in pbc_request
    assert "created_at" in pbc_request


@pytest.mark.asyncio
async def test_create_pbc_request_minimal_fields(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Creating a PBC request with minimal required fields succeeds."""
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
    
    # Create project, application, control
    project_response = client.post(
        "/api/v1/projects",
        json={"name": "Test Project 2", "status": "active"},
        headers=headers,
    )
    project_id = project_response.json()["id"]
    
    app_response = client.post(
        "/api/v1/applications",
        json={"name": "Test Application 2"},
        headers=headers,
    )
    application_id = app_response.json()["id"]
    
    control_response = client.post(
        "/api/v1/controls",
        json={"control_code": "PBC-002", "name": "Test Control 2", "is_key": False, "is_automated": False},
        headers=headers,
    )
    control_id = control_response.json()["id"]
    
    # Create PBC request with only required fields
    pbc_data = {
        "project_id": project_id,
        "application_id": application_id,
        "control_id": control_id,
        "owner_membership_id": str(membership_a.id),
        "title": "Minimal PBC Request",
    }
    
    response = client.post("/api/v1/pbc-requests", json=pbc_data, headers=headers)
    
    assert response.status_code == status.HTTP_201_CREATED
    
    pbc_request = response.json()
    assert pbc_request["title"] == "Minimal PBC Request"
    assert pbc_request["samples_requested"] is None
    assert pbc_request["due_date"] is None
    assert pbc_request["status"] == "pending"


@pytest.mark.asyncio
async def test_list_pbc_requests_success(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Listing PBC requests returns all PBC requests for the tenant."""
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
    
    # Create project, application, control
    project_response = client.post(
        "/api/v1/projects",
        json={"name": "Test Project List", "status": "active"},
        headers=headers,
    )
    project_id = project_response.json()["id"]
    
    app_response = client.post(
        "/api/v1/applications",
        json={"name": "Test Application List"},
        headers=headers,
    )
    application_id = app_response.json()["id"]
    
    control_response = client.post(
        "/api/v1/controls",
        json={"control_code": "PBC-003", "name": "Test Control List", "is_key": False, "is_automated": False},
        headers=headers,
    )
    control_id = control_response.json()["id"]
    
    # Create multiple PBC requests
    for i in range(3):
        pbc_data = {
            "project_id": project_id,
            "application_id": application_id,
            "control_id": control_id,
            "owner_membership_id": str(membership_a.id),
            "title": f"PBC Request {i+1}",
        }
        client.post("/api/v1/pbc-requests", json=pbc_data, headers=headers)
    
    # List PBC requests
    response = client.get("/api/v1/pbc-requests", headers=headers)
    
    assert response.status_code == status.HTTP_200_OK
    pbc_requests = response.json()
    assert len(pbc_requests) >= 3


@pytest.mark.asyncio
async def test_list_project_pbc_requests_success(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Listing PBC requests for a project returns only that project's requests."""
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
    
    # Create two projects
    project1_response = client.post(
        "/api/v1/projects",
        json={"name": "Project 1", "status": "active"},
        headers=headers,
    )
    project1_id = project1_response.json()["id"]
    
    project2_response = client.post(
        "/api/v1/projects",
        json={"name": "Project 2", "status": "active"},
        headers=headers,
    )
    project2_id = project2_response.json()["id"]
    
    # Create shared application and control
    app_response = client.post(
        "/api/v1/applications",
        json={"name": "Shared App"},
        headers=headers,
    )
    application_id = app_response.json()["id"]
    
    control_response = client.post(
        "/api/v1/controls",
        json={"control_code": "PBC-004", "name": "Shared Control", "is_key": False, "is_automated": False},
        headers=headers,
    )
    control_id = control_response.json()["id"]
    
    # Create PBC request for project 1
    pbc1_data = {
        "project_id": project1_id,
        "application_id": application_id,
        "control_id": control_id,
        "owner_membership_id": str(membership_a.id),
        "title": "Project 1 PBC",
    }
    client.post("/api/v1/pbc-requests", json=pbc1_data, headers=headers)
    
    # Create PBC request for project 2
    pbc2_data = {
        "project_id": project2_id,
        "application_id": application_id,
        "control_id": control_id,
        "owner_membership_id": str(membership_a.id),
        "title": "Project 2 PBC",
    }
    client.post("/api/v1/pbc-requests", json=pbc2_data, headers=headers)
    
    # List PBC requests for project 1 only
    response = client.get(f"/api/v1/projects/{project1_id}/pbc-requests", headers=headers)
    
    assert response.status_code == status.HTTP_200_OK
    pbc_requests = response.json()
    assert len(pbc_requests) == 1
    assert pbc_requests[0]["title"] == "Project 1 PBC"
    assert pbc_requests[0]["project_id"] == project1_id


@pytest.mark.asyncio
async def test_get_pbc_request_success(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Getting a specific PBC request succeeds."""
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
    
    # Create project, application, control
    project_response = client.post(
        "/api/v1/projects",
        json={"name": "Test Project Get", "status": "active"},
        headers=headers,
    )
    project_id = project_response.json()["id"]
    
    app_response = client.post(
        "/api/v1/applications",
        json={"name": "Test Application Get"},
        headers=headers,
    )
    application_id = app_response.json()["id"]
    
    control_response = client.post(
        "/api/v1/controls",
        json={"control_code": "PBC-005", "name": "Test Control Get", "is_key": False, "is_automated": False},
        headers=headers,
    )
    control_id = control_response.json()["id"]
    
    # Create PBC request
    pbc_data = {
        "project_id": project_id,
        "application_id": application_id,
        "control_id": control_id,
        "owner_membership_id": str(membership_a.id),
        "title": "Get Test PBC",
    }
    create_response = client.post("/api/v1/pbc-requests", json=pbc_data, headers=headers)
    pbc_request_id = create_response.json()["id"]
    
    # Get PBC request
    response = client.get(f"/api/v1/pbc-requests/{pbc_request_id}", headers=headers)
    
    assert response.status_code == status.HTTP_200_OK
    pbc_request = response.json()
    assert pbc_request["id"] == pbc_request_id
    assert pbc_request["title"] == "Get Test PBC"


@pytest.mark.asyncio
async def test_update_pbc_request_success(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Updating a PBC request succeeds."""
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
    
    # Create project, application, control
    project_response = client.post(
        "/api/v1/projects",
        json={"name": "Test Project Update", "status": "active"},
        headers=headers,
    )
    project_id = project_response.json()["id"]
    
    app_response = client.post(
        "/api/v1/applications",
        json={"name": "Test Application Update"},
        headers=headers,
    )
    application_id = app_response.json()["id"]
    
    control_response = client.post(
        "/api/v1/controls",
        json={"control_code": "PBC-006", "name": "Test Control Update", "is_key": False, "is_automated": False},
        headers=headers,
    )
    control_id = control_response.json()["id"]
    
    # Create PBC request
    pbc_data = {
        "project_id": project_id,
        "application_id": application_id,
        "control_id": control_id,
        "owner_membership_id": str(membership_a.id),
        "title": "Original Title",
        "status": "pending",
    }
    create_response = client.post("/api/v1/pbc-requests", json=pbc_data, headers=headers)
    pbc_request_id = create_response.json()["id"]
    
    # Update PBC request
    update_data = {
        "title": "Updated Title",
        "samples_requested": 50,
        "due_date": "2025-06-30",
        "status": "in_progress",
    }
    
    response = client.put(f"/api/v1/pbc-requests/{pbc_request_id}", json=update_data, headers=headers)
    
    assert response.status_code == status.HTTP_200_OK
    updated = response.json()
    assert updated["title"] == "Updated Title"
    assert updated["samples_requested"] == 50
    assert updated["due_date"] == "2025-06-30"
    assert updated["status"] == "in_progress"
    # IDs should not change
    assert updated["project_id"] == project_id
    assert updated["control_id"] == control_id


@pytest.mark.asyncio
async def test_delete_pbc_request_success(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Deleting a PBC request succeeds."""
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
    
    # Create project, application, control
    project_response = client.post(
        "/api/v1/projects",
        json={"name": "Test Project Delete", "status": "active"},
        headers=headers,
    )
    project_id = project_response.json()["id"]
    
    app_response = client.post(
        "/api/v1/applications",
        json={"name": "Test Application Delete"},
        headers=headers,
    )
    application_id = app_response.json()["id"]
    
    control_response = client.post(
        "/api/v1/controls",
        json={"control_code": "PBC-007", "name": "Test Control Delete", "is_key": False, "is_automated": False},
        headers=headers,
    )
    control_id = control_response.json()["id"]
    
    # Create PBC request
    pbc_data = {
        "project_id": project_id,
        "application_id": application_id,
        "control_id": control_id,
        "owner_membership_id": str(membership_a.id),
        "title": "Delete Test PBC",
    }
    create_response = client.post("/api/v1/pbc-requests", json=pbc_data, headers=headers)
    pbc_request_id = create_response.json()["id"]
    
    # Delete PBC request
    response = client.delete(f"/api/v1/pbc-requests/{pbc_request_id}", headers=headers)
    
    assert response.status_code == status.HTTP_204_NO_CONTENT
    
    # Verify it's deleted
    get_response = client.get(f"/api/v1/pbc-requests/{pbc_request_id}", headers=headers)
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_cannot_create_pbc_request_for_nonexistent_project(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Cannot create PBC request for non-existent project."""
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
    
    # Create application and control (but not project)
    app_response = client.post(
        "/api/v1/applications",
        json={"name": "Test Application NonExist"},
        headers=headers,
    )
    application_id = app_response.json()["id"]
    
    control_response = client.post(
        "/api/v1/controls",
        json={"control_code": "PBC-008", "name": "Test Control NonExist", "is_key": False, "is_automated": False},
        headers=headers,
    )
    control_id = control_response.json()["id"]
    
    fake_project_id = str(uuid4())
    
    pbc_data = {
        "project_id": fake_project_id,
        "application_id": application_id,
        "control_id": control_id,
        "owner_membership_id": str(membership_a.id),
        "title": "Test PBC",
    }
    
    response = client.post("/api/v1/pbc-requests", json=pbc_data, headers=headers)
    
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Project not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_cannot_create_pbc_request_for_nonexistent_control(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Cannot create PBC request for non-existent control."""
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
    
    # Create project and application (but not control)
    project_response = client.post(
        "/api/v1/projects",
        json={"name": "Test Project NonExistCtrl", "status": "active"},
        headers=headers,
    )
    project_id = project_response.json()["id"]
    
    app_response = client.post(
        "/api/v1/applications",
        json={"name": "Test Application NonExistCtrl"},
        headers=headers,
    )
    application_id = app_response.json()["id"]
    
    fake_control_id = str(uuid4())
    
    pbc_data = {
        "project_id": project_id,
        "application_id": application_id,
        "control_id": fake_control_id,
        "owner_membership_id": str(membership_a.id),
        "title": "Test PBC",
    }
    
    response = client.post("/api/v1/pbc-requests", json=pbc_data, headers=headers)
    
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Control not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_tenant_isolation_pbc_requests(
    client, tenant_a, tenant_b, user_tenant_a, user_tenant_b, db_session
):
    """Test: Tenant A cannot access Tenant B's PBC requests."""
    user_a, membership_a = user_tenant_a
    user_b, membership_b = user_tenant_b
    
    # User A creates PBC request in Tenant A
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
    
    # Create project, application, control in Tenant A
    project_response = client.post(
        "/api/v1/projects",
        json={"name": "Tenant A Project", "status": "active"},
        headers=headers_a,
    )
    project_a_id = project_response.json()["id"]
    
    app_response = client.post(
        "/api/v1/applications",
        json={"name": "Tenant A App"},
        headers=headers_a,
    )
    app_a_id = app_response.json()["id"]
    
    control_response = client.post(
        "/api/v1/controls",
        json={"control_code": "PBC-009", "name": "Tenant A Control", "is_key": False, "is_automated": False},
        headers=headers_a,
    )
    control_a_id = control_response.json()["id"]
    
    pbc_data = {
        "project_id": project_a_id,
        "application_id": app_a_id,
        "control_id": control_a_id,
        "owner_membership_id": str(membership_a.id),
        "title": "Tenant A PBC",
    }
    pbc_response = client.post("/api/v1/pbc-requests", json=pbc_data, headers=headers_a)
    pbc_a_id = pbc_response.json()["id"]
    
    # User B tries to access Tenant A's PBC request
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
    
    # Should return 404 (PBC request not found in Tenant B)
    response = client.get(f"/api/v1/pbc-requests/{pbc_a_id}", headers=headers_b)
    
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_cannot_create_pbc_request_for_different_tenant_project(
    client, tenant_a, tenant_b, user_tenant_a, user_tenant_b, db_session
):
    """Test: Cannot create PBC request for project from different tenant."""
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
    
    project_response = client.post(
        "/api/v1/projects",
        json={"name": "Tenant B Project", "status": "active"},
        headers=headers_b,
    )
    project_b_id = project_response.json()["id"]
    
    # User A creates application and control in Tenant A
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
    
    app_response = client.post(
        "/api/v1/applications",
        json={"name": "Tenant A App CrossTenant"},
        headers=headers_a,
    )
    app_a_id = app_response.json()["id"]
    
    control_response = client.post(
        "/api/v1/controls",
        json={"control_code": "PBC-010", "name": "Tenant A Control CrossTenant", "is_key": False, "is_automated": False},
        headers=headers_a,
    )
    control_a_id = control_response.json()["id"]
    
    # User A tries to create PBC request for Tenant B's project
    pbc_data = {
        "project_id": project_b_id,
        "application_id": app_a_id,
        "control_id": control_a_id,
        "owner_membership_id": str(membership_a.id),
        "title": "Cross Tenant PBC",
    }
    
    response = client.post("/api/v1/pbc-requests", json=pbc_data, headers=headers_a)
    
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Project not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_nonexistent_pbc_request(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Getting a non-existent PBC request returns 404."""
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
    
    fake_id = str(uuid4())
    response = client.get(f"/api/v1/pbc-requests/{fake_id}", headers=headers)
    
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "PBC request not found" in response.json()["detail"]
