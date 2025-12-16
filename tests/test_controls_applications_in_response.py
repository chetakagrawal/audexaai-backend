"""Test that controls list endpoint returns applications array."""

import pytest
from fastapi import status

from auth.jwt import create_dev_token


@pytest.mark.asyncio
async def test_list_controls_includes_applications(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: GET /api/v1/controls returns controls with applications array populated."""
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
    
    # Create control
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
    
    # Create applications
    app1_data = {
        "name": "ERP System",
        "business_owner_membership_id": str(membership_a.id),
        "it_owner_membership_id": str(membership_a.id),
    }
    app1_response = client.post("/api/v1/applications", json=app1_data, headers=headers)
    assert app1_response.status_code == status.HTTP_201_CREATED
    app1 = app1_response.json()
    app1_id = app1["id"]
    
    app2_data = {
        "name": "CRM System",
        "business_owner_membership_id": str(membership_a.id),
        "it_owner_membership_id": str(membership_a.id),
    }
    app2_response = client.post("/api/v1/applications", json=app2_data, headers=headers)
    assert app2_response.status_code == status.HTTP_201_CREATED
    app2 = app2_response.json()
    app2_id = app2["id"]
    
    # Associate applications with control
    client.post(
        f"/api/v1/controls/{control_id}/applications",
        json={"application_id": app1_id},
        headers=headers,
    )
    client.post(
        f"/api/v1/controls/{control_id}/applications",
        json={"application_id": app2_id},
        headers=headers,
    )
    
    # List controls - should include applications
    list_response = client.get("/api/v1/controls", headers=headers)
    assert list_response.status_code == status.HTTP_200_OK
    
    controls = list_response.json()
    assert len(controls) == 1
    
    # Verify the control has applications array
    returned_control = controls[0]
    assert "applications" in returned_control, "Control response should include 'applications' field"
    assert isinstance(returned_control["applications"], list), "Applications should be a list"
    assert len(returned_control["applications"]) == 2, "Control should have 2 applications"
    
    # Verify application details
    app_names = [app["name"] for app in returned_control["applications"]]
    assert "ERP System" in app_names
    assert "CRM System" in app_names
    
    # Verify application structure
    for app in returned_control["applications"]:
        assert "id" in app
        assert "name" in app
        assert "tenant_id" in app
        assert app["id"] in [app1_id, app2_id]


@pytest.mark.asyncio
async def test_list_controls_with_no_applications_returns_empty_array(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: GET /api/v1/controls returns empty applications array when control has no applications."""
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
    
    # Create control without applications
    control_data = {
        "control_code": "AC-002",
        "name": "Control Without Apps",
        "is_key": False,
        "is_automated": False,
    }
    control_response = client.post("/api/v1/controls", json=control_data, headers=headers)
    assert control_response.status_code == status.HTTP_200_OK
    
    # List controls
    list_response = client.get("/api/v1/controls", headers=headers)
    assert list_response.status_code == status.HTTP_200_OK
    
    controls = list_response.json()
    assert len(controls) == 1
    
    # Verify the control has empty applications array
    returned_control = controls[0]
    assert "applications" in returned_control, "Control response should include 'applications' field"
    assert isinstance(returned_control["applications"], list), "Applications should be a list"
    assert len(returned_control["applications"]) == 0, "Control should have empty applications array"


@pytest.mark.asyncio
async def test_get_control_includes_applications(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: GET /api/v1/controls/{control_id} returns control with applications array populated."""
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
    
    # Create control
    control_data = {
        "control_code": "AC-003",
        "name": "Test Control",
        "is_key": False,
        "is_automated": False,
    }
    control_response = client.post("/api/v1/controls", json=control_data, headers=headers)
    assert control_response.status_code == status.HTTP_200_OK
    control = control_response.json()
    control_id = control["id"]
    
    # Create and associate application
    app_data = {
        "name": "Test Application",
        "business_owner_membership_id": str(membership_a.id),
        "it_owner_membership_id": str(membership_a.id),
    }
    app_response = client.post("/api/v1/applications", json=app_data, headers=headers)
    assert app_response.status_code == status.HTTP_201_CREATED
    app_id = app_response.json()["id"]
    
    client.post(
        f"/api/v1/controls/{control_id}/applications",
        json={"application_id": app_id},
        headers=headers,
    )
    
    # Get control by ID - should include applications
    get_response = client.get(f"/api/v1/controls/{control_id}", headers=headers)
    assert get_response.status_code == status.HTTP_200_OK
    
    returned_control = get_response.json()
    assert "applications" in returned_control, "Control response should include 'applications' field"
    assert isinstance(returned_control["applications"], list), "Applications should be a list"
    assert len(returned_control["applications"]) == 1, "Control should have 1 application"
    assert returned_control["applications"][0]["id"] == app_id
