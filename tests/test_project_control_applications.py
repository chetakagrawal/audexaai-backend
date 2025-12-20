"""Integration tests for project control applications endpoints."""

import pytest
from fastapi import status

from auth.jwt import create_dev_token


@pytest.mark.asyncio
async def test_attach_application_to_project_control_success(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Attaching an application to a project control succeeds."""
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
    project_data = {"name": "Test Project", "status": "draft"}
    project_response = client.post("/api/v1/projects", json=project_data, headers=headers)
    project = project_response.json()
    project_id = project["id"]
    
    # Create control
    control_data = {
        "control_code": "AC-001",
        "name": "Test Control",
        "is_key": False,
        "is_automated": False,
    }
    control_response = client.post("/api/v1/controls", json=control_data, headers=headers)
    control = control_response.json()
    control_id = control["id"]
    
    # Create project-control mapping
    project_control_data = {"control_id": control_id}
    project_control_response = client.post(
        f"/api/v1/projects/{project_id}/controls",
        json=project_control_data,
        headers=headers,
    )
    project_control = project_control_response.json()
    project_control_id = project_control["id"]
    
    # Create application
    application_data = {
        "name": "ERP System",
        "business_owner_membership_id": str(membership_a.id),
        "it_owner_membership_id": str(membership_a.id),
    }
    application_response = client.post("/api/v1/applications", json=application_data, headers=headers)
    application = application_response.json()
    application_id = application["id"]
    
    # Attach application to project control
    mapping_data = {"application_id": application_id}
    
    response = client.post(
        f"/api/v1/project-controls/{project_control_id}/applications",
        json=mapping_data,
        headers=headers,
    )
    
    assert response.status_code == status.HTTP_201_CREATED
    
    mapping = response.json()
    assert mapping["project_control_id"] == project_control_id
    assert mapping["application_id"] == application_id
    assert "tenant_id" in mapping
    assert mapping["tenant_id"] == str(tenant_a.id)
    assert "id" in mapping
    assert "application_version_num" in mapping
    assert mapping["application_version_num"] == application["row_version"]
    assert "added_at" in mapping
    assert "added_by_membership_id" in mapping
    assert mapping["added_by_membership_id"] == str(membership_a.id)


@pytest.mark.asyncio
async def test_list_project_control_applications_success(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Listing project control applications returns all mappings for the project control."""
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
    project_data = {"name": "Test Project", "status": "draft"}
    project_response = client.post("/api/v1/projects", json=project_data, headers=headers)
    project = project_response.json()
    project_id = project["id"]
    
    # Create control
    control_data = {
        "control_code": "AC-001",
        "name": "Test Control",
        "is_key": False,
        "is_automated": False,
    }
    control_response = client.post("/api/v1/controls", json=control_data, headers=headers)
    control = control_response.json()
    control_id = control["id"]
    
    # Create project-control mapping
    project_control_data = {"control_id": control_id}
    project_control_response = client.post(
        f"/api/v1/projects/{project_id}/controls",
        json=project_control_data,
        headers=headers,
    )
    project_control = project_control_response.json()
    project_control_id = project_control["id"]
    
    # Create applications
    app1_data = {
        "name": "ERP System",
        "business_owner_membership_id": str(membership_a.id),
        "it_owner_membership_id": str(membership_a.id),
    }
    app1_response = client.post("/api/v1/applications", json=app1_data, headers=headers)
    app1_id = app1_response.json()["id"]
    
    app2_data = {
        "name": "CRM System",
        "business_owner_membership_id": str(membership_a.id),
        "it_owner_membership_id": str(membership_a.id),
    }
    app2_response = client.post("/api/v1/applications", json=app2_data, headers=headers)
    app2_id = app2_response.json()["id"]
    
    # Attach applications to project control
    client.post(
        f"/api/v1/project-controls/{project_control_id}/applications",
        json={"application_id": app1_id},
        headers=headers,
    )
    client.post(
        f"/api/v1/project-controls/{project_control_id}/applications",
        json={"application_id": app2_id},
        headers=headers,
    )
    
    # List mappings
    response = client.get(
        f"/api/v1/project-controls/{project_control_id}/applications",
        headers=headers,
    )
    
    assert response.status_code == status.HTTP_200_OK
    
    applications = response.json()
    assert len(applications) == 2
    application_ids = [app["id"] for app in applications]
    assert app1_id in application_ids
    assert app2_id in application_ids


@pytest.mark.asyncio
async def test_project_control_application_idempotency(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Re-attaching the same application to a project control is idempotent."""
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
    
    # Create project and control
    project_data = {"name": "Test Project", "status": "draft"}
    project_response = client.post("/api/v1/projects", json=project_data, headers=headers)
    project = project_response.json()
    project_id = project["id"]
    
    control_data = {
        "control_code": "AC-001",
        "name": "Test Control",
        "is_key": False,
        "is_automated": False,
    }
    control_response = client.post("/api/v1/controls", json=control_data, headers=headers)
    control = control_response.json()
    control_id = control["id"]
    
    # Create project-control mapping
    project_control_data = {"control_id": control_id}
    project_control_response = client.post(
        f"/api/v1/projects/{project_id}/controls",
        json=project_control_data,
        headers=headers,
    )
    project_control = project_control_response.json()
    project_control_id = project_control["id"]
    
    # Create application
    application_data = {
        "name": "ERP System",
        "business_owner_membership_id": str(membership_a.id),
        "it_owner_membership_id": str(membership_a.id),
    }
    application_response = client.post("/api/v1/applications", json=application_data, headers=headers)
    application = application_response.json()
    application_id = application["id"]
    
    # Attach application to project control first time
    mapping_data = {"application_id": application_id}
    response1 = client.post(
        f"/api/v1/project-controls/{project_control_id}/applications",
        json=mapping_data,
        headers=headers,
    )
    assert response1.status_code == status.HTTP_201_CREATED
    
    # Try to attach same application again
    response2 = client.post(
        f"/api/v1/project-controls/{project_control_id}/applications",
        json=mapping_data,
        headers=headers,
    )
    
    # Should return 201 (idempotent - same mapping returned)
    assert response2.status_code == status.HTTP_201_CREATED
    
    # Verify it's the same mapping (idempotent)
    mapping1 = response1.json()
    mapping2 = response2.json()
    assert mapping1["id"] == mapping2["id"]  # Same mapping returned


@pytest.mark.asyncio
async def test_remove_application_from_project_control_success(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Removing an application from a project control succeeds."""
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
    
    # Create project and control
    project_data = {"name": "Test Project", "status": "draft"}
    project_response = client.post("/api/v1/projects", json=project_data, headers=headers)
    project = project_response.json()
    project_id = project["id"]
    
    control_data = {
        "control_code": "AC-001",
        "name": "Test Control",
        "is_key": False,
        "is_automated": False,
    }
    control_response = client.post("/api/v1/controls", json=control_data, headers=headers)
    control = control_response.json()
    control_id = control["id"]
    
    # Create project-control mapping
    project_control_data = {"control_id": control_id}
    project_control_response = client.post(
        f"/api/v1/projects/{project_id}/controls",
        json=project_control_data,
        headers=headers,
    )
    project_control = project_control_response.json()
    project_control_id = project_control["id"]
    
    # Create application
    application_data = {
        "name": "ERP System",
        "business_owner_membership_id": str(membership_a.id),
        "it_owner_membership_id": str(membership_a.id),
    }
    application_response = client.post("/api/v1/applications", json=application_data, headers=headers)
    application = application_response.json()
    application_id = application["id"]
    
    # Attach application to project control
    mapping_data = {"application_id": application_id}
    attach_response = client.post(
        f"/api/v1/project-controls/{project_control_id}/applications",
        json=mapping_data,
        headers=headers,
    )
    mapping = attach_response.json()
    pca_id = mapping["id"]
    
    # Remove application from project control
    response = client.delete(
        f"/api/v1/project-control-applications/{pca_id}",
        headers=headers,
    )
    
    assert response.status_code == status.HTTP_204_NO_CONTENT
    
    # Verify application is no longer in the list
    list_response = client.get(
        f"/api/v1/project-controls/{project_control_id}/applications",
        headers=headers,
    )
    applications = list_response.json()
    application_ids = [app["id"] for app in applications]
    assert application_id not in application_ids


@pytest.mark.asyncio
async def test_tenant_isolation_project_control_applications(
    client, tenant_a, tenant_b, user_tenant_a, user_tenant_b, db_session
):
    """Test: Tenant A cannot access Tenant B's project control applications."""
    user_a, membership_a = user_tenant_a
    user_b, membership_b = user_tenant_b
    
    # User A creates project, control, project-control, and application in Tenant A
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
    project_a = project_response.json()
    project_a_id = project_a["id"]
    
    control_data = {
        "control_code": "AC-001",
        "name": "Tenant A Control",
        "is_key": False,
        "is_automated": False,
    }
    control_response = client.post("/api/v1/controls", json=control_data, headers=headers_a)
    control_a = control_response.json()
    control_a_id = control_a["id"]
    
    # Create project-control mapping
    project_control_data = {"control_id": control_a_id}
    project_control_response = client.post(
        f"/api/v1/projects/{project_a_id}/controls",
        json=project_control_data,
        headers=headers_a,
    )
    project_control_a = project_control_response.json()
    project_control_a_id = project_control_a["id"]
    
    application_data = {
        "name": "Tenant A Application",
        "business_owner_membership_id": str(membership_a.id),
        "it_owner_membership_id": str(membership_a.id),
    }
    application_response = client.post("/api/v1/applications", json=application_data, headers=headers_a)
    application_a = application_response.json()
    application_a_id = application_a["id"]
    
    # Attach application to project control
    mapping_data = {"application_id": application_a_id}
    attach_response = client.post(
        f"/api/v1/project-controls/{project_control_a_id}/applications",
        json=mapping_data,
        headers=headers_a,
    )
    pca_a = attach_response.json()
    pca_a_id = pca_a["id"]
    
    # User B tries to access Tenant A's project control applications
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
    
    # Should return 404 (project control not found in Tenant B)
    response = client.get(
        f"/api/v1/project-controls/{project_control_a_id}/applications",
        headers=headers_b,
    )
    
    assert response.status_code == status.HTTP_404_NOT_FOUND
    
    # Try to delete Tenant A's mapping from Tenant B
    delete_response = client.delete(
        f"/api/v1/project-control-applications/{pca_a_id}",
        headers=headers_b,
    )
    
    assert delete_response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_cannot_attach_application_from_different_tenant(
    client, tenant_a, tenant_b, user_tenant_a, user_tenant_b, db_session
):
    """Test: Cannot attach an application from another tenant to a project control."""
    user_a, membership_a = user_tenant_a
    user_b, membership_b = user_tenant_b
    
    # User A creates project, control, and project-control in Tenant A
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
        "name": "Test Control",
        "is_key": False,
        "is_automated": False,
    }
    control_response = client.post("/api/v1/controls", json=control_data, headers=headers_a)
    control = control_response.json()
    control_id = control["id"]
    
    # Create project-control mapping
    project_control_data = {"control_id": control_id}
    project_control_response = client.post(
        f"/api/v1/projects/{project_id}/controls",
        json=project_control_data,
        headers=headers_a,
    )
    project_control = project_control_response.json()
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
    
    application_data = {
        "name": "Tenant B Application",
        "business_owner_membership_id": str(membership_b.id),
        "it_owner_membership_id": str(membership_b.id),
    }
    application_response = client.post("/api/v1/applications", json=application_data, headers=headers_b)
    application_b = application_response.json()
    application_b_id = application_b["id"]
    
    # User A tries to attach Tenant B's application to Tenant A's project control
    # Should fail with 404 (application not found in Tenant A)
    mapping_data = {"application_id": application_b_id}
    response = client.post(
        f"/api/v1/project-controls/{project_control_id}/applications",
        json=mapping_data,
        headers=headers_a,
    )
    
    assert response.status_code in [
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_404_NOT_FOUND,
        status.HTTP_403_FORBIDDEN,
    ]


@pytest.mark.asyncio
async def test_version_freezing_on_attach(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Application version is frozen when attached to project control."""
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
    
    # Create project and control
    project_data = {"name": "Test Project", "status": "draft"}
    project_response = client.post("/api/v1/projects", json=project_data, headers=headers)
    project = project_response.json()
    project_id = project["id"]
    
    control_data = {
        "control_code": "AC-001",
        "name": "Test Control",
        "is_key": False,
        "is_automated": False,
    }
    control_response = client.post("/api/v1/controls", json=control_data, headers=headers)
    control = control_response.json()
    control_id = control["id"]
    
    # Create project-control mapping
    project_control_data = {"control_id": control_id}
    project_control_response = client.post(
        f"/api/v1/projects/{project_id}/controls",
        json=project_control_data,
        headers=headers,
    )
    project_control = project_control_response.json()
    project_control_id = project_control["id"]
    
    # Create application
    application_data = {
        "name": "ERP System",
        "business_owner_membership_id": str(membership_a.id),
        "it_owner_membership_id": str(membership_a.id),
    }
    application_response = client.post("/api/v1/applications", json=application_data, headers=headers)
    application = application_response.json()
    application_id = application["id"]
    initial_version = application["row_version"]
    
    # Attach application to project control
    mapping_data = {"application_id": application_id}
    attach_response = client.post(
        f"/api/v1/project-controls/{project_control_id}/applications",
        json=mapping_data,
        headers=headers,
    )
    mapping = attach_response.json()
    
    # Verify version was frozen
    assert mapping["application_version_num"] == initial_version
    
    # Update application (version should increment)
    # Note: We can't easily test version increment in integration test without updating the application
    # The unit tests already verify version freezing works correctly
    # This test just verifies the attach operation succeeds and freezes the version
    # The frozen version is verified in unit tests (test_add_application_version_remains_frozen_after_application_update)


@pytest.mark.asyncio
async def test_cannot_attach_to_removed_project_control(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Cannot attach application to a removed project control."""
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
    
    # Create project and control
    project_data = {"name": "Test Project", "status": "draft"}
    project_response = client.post("/api/v1/projects", json=project_data, headers=headers)
    project = project_response.json()
    project_id = project["id"]
    
    control_data = {
        "control_code": "AC-001",
        "name": "Test Control",
        "is_key": False,
        "is_automated": False,
    }
    control_response = client.post("/api/v1/controls", json=control_data, headers=headers)
    control = control_response.json()
    control_id = control["id"]
    
    # Create project-control mapping
    project_control_data = {"control_id": control_id}
    project_control_response = client.post(
        f"/api/v1/projects/{project_id}/controls",
        json=project_control_data,
        headers=headers,
    )
    project_control = project_control_response.json()
    project_control_id = project_control["id"]
    
    # Remove project control
    client.delete(
        f"/api/v1/project-controls/{project_control_id}",
        headers=headers,
    )
    
    # Create application
    application_data = {
        "name": "ERP System",
        "business_owner_membership_id": str(membership_a.id),
        "it_owner_membership_id": str(membership_a.id),
    }
    application_response = client.post("/api/v1/applications", json=application_data, headers=headers)
    application = application_response.json()
    application_id = application["id"]
    
    # Try to attach application to removed project control
    mapping_data = {"application_id": application_id}
    response = client.post(
        f"/api/v1/project-controls/{project_control_id}/applications",
        json=mapping_data,
        headers=headers,
    )
    
    # Should fail with 400 or 404
    assert response.status_code in [
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_404_NOT_FOUND,
    ]

