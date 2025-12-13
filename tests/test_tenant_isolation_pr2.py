"""Integration tests for PR2 tenant isolation (Projects and Controls)."""

import pytest
from fastapi import status

from auth.jwt import create_dev_token
from models.control import Control
from models.project import Project


@pytest.mark.asyncio
async def test_user_tenant_a_cannot_access_tenant_b_project(
    client, tenant_a, tenant_b, user_tenant_a
):
    """
    Test: User in Tenant A cannot access Tenant B's project by guessing ID.
    
    Scenario:
    - User A belongs to Tenant A
    - Project exists in Tenant B
    - User A tries to access Tenant B's project by ID
    - Should return 404 (not found due to tenant filtering)
    """
    user_a, membership_a = user_tenant_a
    
    # Create a project in Tenant B (simulating another tenant's data)
    # We'll need to create this via a separate user or admin
    # For now, we'll test that User A cannot see Tenant B's projects
    
    # Create JWT token for User A
    token = create_dev_token(
        user_id=user_a.id,
        tenant_id=tenant_a.id,
        role=membership_a.role,
        is_platform_admin=False,
    )
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test 1: List projects - should only see Tenant A's projects (empty for now)
    response = client.get("/api/v1/projects", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    projects = response.json()
    # Should be empty or only contain Tenant A's projects
    for project in projects:
        assert project["tenant_id"] == str(tenant_a.id)
    
    # Test 2: Try to access a non-existent project (simulating Tenant B's project ID)
    # This should return 404, not 403, because tenant filtering makes it "not found"
    fake_project_id = "00000000-0000-0000-0000-000000000000"
    response = client.get(f"/api/v1/projects/{fake_project_id}", headers=headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_user_tenant_a_cannot_access_tenant_b_control(
    client, tenant_a, tenant_b, user_tenant_a
):
    """
    Test: User in Tenant A cannot access Tenant B's control by guessing ID.
    
    Scenario:
    - User A belongs to Tenant A
    - Control exists in Tenant B
    - User A tries to access Tenant B's control by ID
    - Should return 404 (not found due to tenant filtering)
    """
    user_a, membership_a = user_tenant_a
    
    # Create JWT token for User A
    token = create_dev_token(
        user_id=user_a.id,
        tenant_id=tenant_a.id,
        role=membership_a.role,
        is_platform_admin=False,
    )
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test 1: List controls - should only see Tenant A's controls (empty for now)
    response = client.get("/api/v1/controls", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    controls = response.json()
    # Should be empty or only contain Tenant A's controls
    for control in controls:
        assert control["tenant_id"] == str(tenant_a.id)
    
    # Test 2: Try to access a non-existent control (simulating Tenant B's control ID)
    fake_control_id = "00000000-0000-0000-0000-000000000000"
    response = client.get(f"/api/v1/controls/{fake_control_id}", headers=headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_user_can_create_project_in_own_tenant(
    client, tenant_a, user_tenant_a, db_session
):
    """
    Test: User can create project in their own tenant.
    
    Scenario:
    - User A belongs to Tenant A
    - User A creates a project
    - Project should be created with Tenant A's tenant_id (ignoring client input)
    """
    user_a, membership_a = user_tenant_a
    
    # Create JWT token for User A
    token = create_dev_token(
        user_id=user_a.id,
        tenant_id=tenant_a.id,
        role=membership_a.role,
        is_platform_admin=False,
    )
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create project (tenant_id in request should be ignored)
    project_data = {
        "tenant_id": "00000000-0000-0000-0000-000000000000",  # Wrong tenant - should be ignored
        "name": "Test Project",
        "status": "draft",
    }
    
    response = client.post("/api/v1/projects", json=project_data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    
    project = response.json()
    # Verify tenant_id was set from membership context, not client input
    assert project["tenant_id"] == str(tenant_a.id)
    assert project["name"] == "Test Project"
    
    # Verify project is accessible via list endpoint
    response = client.get("/api/v1/projects", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    projects = response.json()
    assert len(projects) == 1
    assert projects[0]["id"] == project["id"]


@pytest.mark.asyncio
async def test_user_can_create_control_in_own_tenant(
    client, tenant_a, user_tenant_a, db_session
):
    """
    Test: User can create control in their own tenant.
    
    Scenario:
    - User A belongs to Tenant A
    - User A creates a control
    - Control should be created with Tenant A's tenant_id (ignoring client input)
    """
    user_a, membership_a = user_tenant_a
    
    # Create JWT token for User A
    token = create_dev_token(
        user_id=user_a.id,
        tenant_id=tenant_a.id,
        role=membership_a.role,
        is_platform_admin=False,
    )
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create control (tenant_id in request should be ignored)
    control_data = {
        "tenant_id": "00000000-0000-0000-0000-000000000000",  # Wrong tenant - should be ignored
        "control_code": "AC-001",
        "name": "Test Control",
        "is_key": False,
        "is_automated": False,
    }
    
    response = client.post("/api/v1/controls", json=control_data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    
    control = response.json()
    # Verify tenant_id was set from membership context, not client input
    assert control["tenant_id"] == str(tenant_a.id)
    assert control["control_code"] == "AC-001"
    assert control["name"] == "Test Control"
    
    # Verify control is accessible via list endpoint
    response = client.get("/api/v1/controls", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    controls = response.json()
    assert len(controls) == 1
    assert controls[0]["id"] == control["id"]


@pytest.mark.asyncio
async def test_user_cannot_access_other_tenant_project_after_creation(
    client, tenant_a, tenant_b, user_tenant_a, user_tenant_b, db_session
):
    """
    Test: User in Tenant A cannot access Tenant B's project even if they know the ID.
    
    Scenario:
    - User A creates Project A in Tenant A
    - User B creates Project B in Tenant B
    - User A tries to access Project B by ID
    - Should return 404 (tenant filtering prevents access)
    """
    user_a, membership_a = user_tenant_a
    user_b, membership_b = user_tenant_b
    
    # Create project for Tenant B (as User B)
    token_b = create_dev_token(
        user_id=user_b.id,
        tenant_id=tenant_b.id,
        role=membership_b.role,
        is_platform_admin=False,
    )
    
    headers_b = {"Authorization": f"Bearer {token_b}"}
    project_data_b = {
        "name": "Tenant B Project",
        "status": "draft",
    }
    
    response = client.post("/api/v1/projects", json=project_data_b, headers=headers_b)
    assert response.status_code == status.HTTP_200_OK
    project_b = response.json()
    project_b_id = project_b["id"]
    
    # Now User A tries to access Tenant B's project
    token_a = create_dev_token(
        user_id=user_a.id,
        tenant_id=tenant_a.id,
        role=membership_a.role,
        is_platform_admin=False,
    )
    
    headers_a = {"Authorization": f"Bearer {token_a}"}
    
    # Should return 404, not 403 (tenant filtering makes it "not found")
    response = client.get(f"/api/v1/projects/{project_b_id}", headers=headers_a)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"].lower()

