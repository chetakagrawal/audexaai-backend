"""Integration tests for control applications endpoints."""

import pytest
from fastapi import status

from auth.jwt import create_dev_token


@pytest.mark.asyncio
async def test_attach_application_to_control_success(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Attaching an application to a control succeeds."""
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
    control = control_response.json()
    control_id = control["id"]
    
    # Create application
    application_data = {
        "name": "ERP System",
        "business_owner_membership_id": str(membership_a.id),
        "it_owner_membership_id": str(membership_a.id),
    }
    application_response = client.post("/api/v1/applications", json=application_data, headers=headers)
    application = application_response.json()
    application_id = application["id"]
    
    # Attach application to control
    mapping_data = {"application_id": application_id}
    
    response = client.post(
        f"/api/v1/controls/{control_id}/applications",
        json=mapping_data,
        headers=headers,
    )
    
    assert response.status_code == status.HTTP_201_CREATED
    
    mapping = response.json()
    assert mapping["control_id"] == control_id
    assert mapping["application_id"] == application_id
    assert "tenant_id" in mapping
    assert mapping["tenant_id"] == str(tenant_a.id)
    assert "id" in mapping
    assert "added_at" in mapping
    assert "added_by_membership_id" in mapping


@pytest.mark.asyncio
async def test_list_control_applications_success(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Listing control applications returns all mappings for the control."""
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
    control = control_response.json()
    control_id = control["id"]
    
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
    
    # Attach applications to control
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
    
    # List mappings
    response = client.get(
        f"/api/v1/controls/{control_id}/applications",
        headers=headers,
    )
    
    assert response.status_code == status.HTTP_200_OK
    
    applications = response.json()
    assert len(applications) == 2
    application_ids = [app["id"] for app in applications]
    assert app1_id in application_ids
    assert app2_id in application_ids


@pytest.mark.asyncio
async def test_control_application_idempotency(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Re-attaching the same application to a control is idempotent."""
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
    
    # Create control and application
    control_data = {
        "control_code": "AC-001",
        "name": "Test Control",
        "is_key": False,
        "is_automated": False,
    }
    control_response = client.post("/api/v1/controls", json=control_data, headers=headers)
    control_id = control_response.json()["id"]
    
    application_data = {
        "name": "ERP System",
        "business_owner_membership_id": str(membership_a.id),
        "it_owner_membership_id": str(membership_a.id),
    }
    application_response = client.post("/api/v1/applications", json=application_data, headers=headers)
    application_id = application_response.json()["id"]
    
    # Create mapping first time
    mapping_data = {"application_id": application_id}
    response1 = client.post(
        f"/api/v1/controls/{control_id}/applications",
        json=mapping_data,
        headers=headers,
    )
    assert response1.status_code == status.HTTP_201_CREATED
    
    # Try to create same mapping again
    response2 = client.post(
        f"/api/v1/controls/{control_id}/applications",
        json=mapping_data,
        headers=headers,
    )
    
    # Should return 200/201 (idempotent - returns existing)
    assert response2.status_code in [
        status.HTTP_200_OK,
        status.HTTP_201_CREATED,
    ]
    
    # Verify it's the same mapping (idempotent)
    mapping1 = response1.json()
    mapping2 = response2.json()
    assert mapping1["id"] == mapping2["id"]  # Same mapping returned


@pytest.mark.asyncio
async def test_cannot_attach_application_from_different_tenant_to_control(
    client, tenant_a, tenant_b, user_tenant_a, user_tenant_b, db_session
):
    """Test: Cannot attach an application from another tenant to a control."""
    user_a, membership_a = user_tenant_a
    user_b, membership_b = user_tenant_b
    
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
    control_id = control_response.json()["id"]
    
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
    application_b_id = application_response.json()["id"]
    
    # User A tries to attach Tenant B's application to Tenant A's control
    mapping_data = {"application_id": application_b_id}
    response = client.post(
        f"/api/v1/controls/{control_id}/applications",
        json=mapping_data,
        headers=headers_a,
    )
    
    assert response.status_code in [
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_404_NOT_FOUND,
    ]


@pytest.mark.asyncio
async def test_tenant_isolation_control_applications(
    client, tenant_a, tenant_b, user_tenant_a, user_tenant_b, db_session
):
    """Test: Tenant A cannot access Tenant B's control-application mappings."""
    user_a, membership_a = user_tenant_a
    user_b, membership_b = user_tenant_b
    
    # User A creates control and application in Tenant A
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
    control_a_id = control_response.json()["id"]
    
    application_data = {
        "name": "Tenant A Application",
        "business_owner_membership_id": str(membership_a.id),
        "it_owner_membership_id": str(membership_a.id),
    }
    application_response = client.post("/api/v1/applications", json=application_data, headers=headers_a)
    application_a_id = application_response.json()["id"]
    
    # Create mapping in Tenant A
    client.post(
        f"/api/v1/controls/{control_a_id}/applications",
        json={"application_id": application_a_id},
        headers=headers_a,
    )
    
    # User B tries to access Tenant A's control applications
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
    
    # Should return 404 (control not found in Tenant B) or empty list
    response = client.get(
        f"/api/v1/controls/{control_a_id}/applications",
        headers=headers_b,
    )
    
    # Should not see Tenant A's mappings
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
    if response.status_code == status.HTTP_200_OK:
        applications = response.json()
        assert len(applications) == 0  # Should be empty for Tenant B


@pytest.mark.asyncio
async def test_remove_application_from_control_success(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Removing an application from a control succeeds (soft remove)."""
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
    control = control_response.json()
    control_id = control["id"]
    
    # Create application
    application_data = {
        "name": "ERP System",
        "business_owner_membership_id": str(membership_a.id),
        "it_owner_membership_id": str(membership_a.id),
    }
    application_response = client.post("/api/v1/applications", json=application_data, headers=headers)
    application = application_response.json()
    application_id = application["id"]
    
    # Attach application to control
    mapping_data = {"application_id": application_id}
    client.post(
        f"/api/v1/controls/{control_id}/applications",
        json=mapping_data,
        headers=headers,
    )
    
    # List applications (should have 1)
    list_response = client.get(
        f"/api/v1/controls/{control_id}/applications",
        headers=headers,
    )
    assert len(list_response.json()) == 1
    
    # Remove application from control
    delete_response = client.delete(
        f"/api/v1/controls/{control_id}/applications/{application_id}",
        headers=headers,
    )
    
    assert delete_response.status_code == status.HTTP_204_NO_CONTENT
    
    # List applications again (should be empty)
    list_response_after = client.get(
        f"/api/v1/controls/{control_id}/applications",
        headers=headers,
    )
    assert len(list_response_after.json()) == 0


@pytest.mark.asyncio
async def test_remove_add_creates_new_mapping(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Remove -> add again creates a NEW mapping row (history preserved)."""
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
    control_id = control_response.json()["id"]
    
    # Create application
    application_data = {
        "name": "ERP System",
        "business_owner_membership_id": str(membership_a.id),
        "it_owner_membership_id": str(membership_a.id),
    }
    application_response = client.post("/api/v1/applications", json=application_data, headers=headers)
    application_id = application_response.json()["id"]
    
    # Add
    add_response1 = client.post(
        f"/api/v1/controls/{control_id}/applications",
        json={"application_id": application_id},
        headers=headers,
    )
    mapping1_id = add_response1.json()["id"]
    
    # Remove
    client.delete(
        f"/api/v1/controls/{control_id}/applications/{application_id}",
        headers=headers,
    )
    
    # Add again
    add_response2 = client.post(
        f"/api/v1/controls/{control_id}/applications",
        json={"application_id": application_id},
        headers=headers,
    )
    mapping2_id = add_response2.json()["id"]
    
    # Should be a NEW row with different ID
    assert mapping1_id != mapping2_id
