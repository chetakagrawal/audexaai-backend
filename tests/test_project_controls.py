"""Integration tests for project controls endpoints (TDD - failing tests first)."""

import pytest
from fastapi import status

from auth.jwt import create_dev_token


@pytest.mark.asyncio
async def test_create_project_control_success(
    client, tenant_a, user_tenant_a, db_session
):
    """
    Test: Creating a project-control mapping succeeds.
    
    This test will FAIL until we add the POST endpoint.
    """
    user_a, membership_a = user_tenant_a
    
    # Create a project first
    token = create_dev_token(
        user_id=user_a.id,
        tenant_id=tenant_a.id,
        role=membership_a.role,
        is_platform_admin=False,
    )
    headers = {"Authorization": f"Bearer {token}"}
    
    project_data = {"name": "Test Project", "status": "draft"}
    project_response = client.post("/api/v1/projects", json=project_data, headers=headers)
    assert project_response.status_code == status.HTTP_200_OK
    project = project_response.json()
    project_id = project["id"]
    
    # Create a control first
    control_data = {
        "control_code": "AC-001",
        "name": "Test Control",
        "is_key": False,
        "is_automated": False,
    }
    control_response = client.post("/api/v1/controls", json=control_data, headers=headers)
    assert control_response.status_code == status.HTTP_200_OK
    control = control_response.json()
    control_id = control["id"]
    
    # Now create project-control mapping
    mapping_data = {
        "control_id": control_id,
        "is_key_override": True,
        "frequency_override": "monthly",
        "notes": "Override for this project",
    }
    
    response = client.post(
        f"/api/v1/projects/{project_id}/controls",
        json=mapping_data,
        headers=headers,
    )
    
    # This will fail until endpoint is created
    assert response.status_code == status.HTTP_200_OK or response.status_code == status.HTTP_201_CREATED
    
    mapping = response.json()
    assert mapping["project_id"] == project_id
    assert mapping["control_id"] == control_id
    assert mapping["is_key_override"] is True
    assert mapping["frequency_override"] == "monthly"
    assert mapping["notes"] == "Override for this project"
    assert "tenant_id" in mapping
    assert mapping["tenant_id"] == str(tenant_a.id)


@pytest.mark.asyncio
async def test_list_project_controls_success(
    client, tenant_a, user_tenant_a, db_session
):
    """
    Test: Listing project controls returns all mappings for the project.
    
    This test will FAIL until we add the GET endpoint.
    """
    user_a, membership_a = user_tenant_a
    
    token = create_dev_token(
        user_id=user_a.id,
        tenant_id=tenant_a.id,
        role=membership_a.role,
        is_platform_admin=False,
    )
    headers = {"Authorization": f"Bearer {token}"}
    
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
    
    # Create mapping
    mapping_data = {"control_id": control_id}
    client.post(
        f"/api/v1/projects/{project_id}/controls",
        json=mapping_data,
        headers=headers,
    )
    
    # List mappings
    response = client.get(
        f"/api/v1/projects/{project_id}/controls",
        headers=headers,
    )
    
    # This will fail until endpoint is created
    assert response.status_code == status.HTTP_200_OK
    
    mappings = response.json()
    assert len(mappings) == 1
    assert mappings[0]["project_id"] == project_id
    assert mappings[0]["control_id"] == control_id


@pytest.mark.asyncio
async def test_tenant_isolation_project_controls(
    client, tenant_a, tenant_b, user_tenant_a, user_tenant_b, db_session
):
    """
    Test: Tenant A cannot access Tenant B's project-control mappings.
    
    This test verifies tenant isolation.
    """
    user_a, membership_a = user_tenant_a
    user_b, membership_b = user_tenant_b
    
    # User A creates project and control in Tenant A
    token_a = create_dev_token(
        user_id=user_a.id,
        tenant_id=tenant_a.id,
        role=membership_a.role,
        is_platform_admin=False,
    )
    headers_a = {"Authorization": f"Bearer {token_a}"}
    
    project_data_a = {"name": "Tenant A Project", "status": "draft"}
    project_response = client.post("/api/v1/projects", json=project_data_a, headers=headers_a)
    project_a = project_response.json()
    project_a_id = project_a["id"]
    
    control_data_a = {
        "control_code": "AC-001",
        "name": "Tenant A Control",
        "is_key": False,
        "is_automated": False,
    }
    control_response = client.post("/api/v1/controls", json=control_data_a, headers=headers_a)
    control_a = control_response.json()
    control_a_id = control_a["id"]
    
    # Create mapping in Tenant A
    mapping_data = {"control_id": control_a_id}
    client.post(
        f"/api/v1/projects/{project_a_id}/controls",
        json=mapping_data,
        headers=headers_a,
    )
    
    # User B tries to access Tenant A's project controls
    token_b = create_dev_token(
        user_id=user_b.id,
        tenant_id=tenant_b.id,
        role=membership_b.role,
        is_platform_admin=False,
    )
    headers_b = {"Authorization": f"Bearer {token_b}"}
    
    # Should return 404 (project not found in Tenant B) or empty list
    response = client.get(
        f"/api/v1/projects/{project_a_id}/controls",
        headers=headers_b,
    )
    
    # Should not see Tenant A's mappings
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
    if response.status_code == status.HTTP_200_OK:
        mappings = response.json()
        assert len(mappings) == 0  # Should be empty for Tenant B


@pytest.mark.asyncio
async def test_cannot_attach_control_from_different_tenant(
    client, tenant_a, tenant_b, user_tenant_a, user_tenant_b, db_session
):
    """
    Test: Cannot attach a control from another tenant to a project.
    
    This test verifies that controls must belong to the same tenant as the project.
    """
    user_a, membership_a = user_tenant_a
    user_b, membership_b = user_tenant_b
    
    # User A creates project in Tenant A
    token_a = create_dev_token(
        user_id=user_a.id,
        tenant_id=tenant_a.id,
        role=membership_a.role,
        is_platform_admin=False,
    )
    headers_a = {"Authorization": f"Bearer {token_a}"}
    
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
    headers_b = {"Authorization": f"Bearer {token_b}"}
    
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
    # Should fail with 400 or 404
    mapping_data = {"control_id": control_b_id}
    response = client.post(
        f"/api/v1/projects/{project_id}/controls",
        json=mapping_data,
        headers=headers_a,
    )
    
    assert response.status_code in [
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_404_NOT_FOUND,
        status.HTTP_403_FORBIDDEN,
    ]


@pytest.mark.asyncio
async def test_project_control_idempotency(
    client, tenant_a, user_tenant_a, db_session
):
    """
    Test: Re-attaching the same control to a project is idempotent.
    
    This test verifies that duplicate mappings are handled correctly (409 or no-op).
    """
    user_a, membership_a = user_tenant_a
    
    token = create_dev_token(
        user_id=user_a.id,
        tenant_id=tenant_a.id,
        role=membership_a.role,
        is_platform_admin=False,
    )
    headers = {"Authorization": f"Bearer {token}"}
    
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
    
    # Create mapping first time
    mapping_data = {"control_id": control_id}
    response1 = client.post(
        f"/api/v1/projects/{project_id}/controls",
        json=mapping_data,
        headers=headers,
    )
    assert response1.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]
    
    # Try to create same mapping again
    response2 = client.post(
        f"/api/v1/projects/{project_id}/controls",
        json=mapping_data,
        headers=headers,
    )
    
    # Should return 409 Conflict or 200 OK (no-op)
    assert response2.status_code in [
        status.HTTP_409_CONFLICT,
        status.HTTP_200_OK,
        status.HTTP_201_CREATED,
    ]
    
    # If 200/201, verify it's the same mapping (idempotent)
    if response2.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]:
        mapping1 = response1.json()
        mapping2 = response2.json()
        assert mapping1["id"] == mapping2["id"]  # Same mapping returned

