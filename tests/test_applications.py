"""Integration tests for applications endpoints."""

import pytest
from fastapi import status

from auth.jwt import create_dev_token


@pytest.mark.asyncio
async def test_create_application_success(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Creating an application succeeds."""
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
    
    application_data = {
        "name": "ERP System",
        "category": "Financial",
        "scope_rationale": "Core financial system",
        "business_owner_membership_id": str(membership_a.id),
        "it_owner_membership_id": str(membership_a.id),
    }
    
    response = client.post("/api/v1/applications", json=application_data, headers=headers)
    
    assert response.status_code == status.HTTP_201_CREATED
    
    application = response.json()
    assert application["name"] == "ERP System"
    assert application["category"] == "Financial"
    assert application["scope_rationale"] == "Core financial system"
    assert application["business_owner_membership_id"] == str(membership_a.id)
    assert application["it_owner_membership_id"] == str(membership_a.id)
    assert "tenant_id" in application
    assert application["tenant_id"] == str(tenant_a.id)
    assert "id" in application
    assert "created_at" in application


@pytest.mark.asyncio
async def test_list_applications_success(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Listing applications returns all applications in tenant."""
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
    
    # Create first application
    app1_data = {
        "name": "ERP System",
        "category": "Financial",
        "business_owner_membership_id": str(membership_a.id),
        "it_owner_membership_id": str(membership_a.id),
    }
    client.post("/api/v1/applications", json=app1_data, headers=headers)
    
    # Create second application
    app2_data = {
        "name": "CRM System",
        "category": "Sales",
        "business_owner_membership_id": str(membership_a.id),
        "it_owner_membership_id": str(membership_a.id),
    }
    client.post("/api/v1/applications", json=app2_data, headers=headers)
    
    # List applications
    response = client.get("/api/v1/applications", headers=headers)
    
    assert response.status_code == status.HTTP_200_OK
    
    applications = response.json()
    assert len(applications) == 2
    names = [app["name"] for app in applications]
    assert "ERP System" in names
    assert "CRM System" in names


@pytest.mark.asyncio
async def test_get_application_success(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Getting a specific application by ID succeeds."""
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
    
    # Create application
    application_data = {
        "name": "ERP System",
        "category": "Financial",
        "business_owner_membership_id": str(membership_a.id),
        "it_owner_membership_id": str(membership_a.id),
    }
    create_response = client.post("/api/v1/applications", json=application_data, headers=headers)
    application_id = create_response.json()["id"]
    
    # Get application
    response = client.get(f"/api/v1/applications/{application_id}", headers=headers)
    
    assert response.status_code == status.HTTP_200_OK
    
    application = response.json()
    assert application["id"] == application_id
    assert application["name"] == "ERP System"


@pytest.mark.asyncio
async def test_create_application_invalid_business_owner(
    client, tenant_a, tenant_b, user_tenant_a, user_tenant_b, db_session
):
    """Test: Creating application with business owner from different tenant fails."""
    user_a, membership_a = user_tenant_a
    user_b, membership_b = user_tenant_b
    
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
    
    # Try to create application with business owner from Tenant B
    application_data = {
        "name": "ERP System",
        "business_owner_membership_id": str(membership_b.id),  # From Tenant B
        "it_owner_membership_id": str(membership_a.id),
    }
    
    response = client.post("/api/v1/applications", json=application_data, headers=headers)
    
    assert response.status_code in [
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_404_NOT_FOUND,
    ]


@pytest.mark.asyncio
async def test_create_application_invalid_it_owner(
    client, tenant_a, tenant_b, user_tenant_a, user_tenant_b, db_session
):
    """Test: Creating application with IT owner from different tenant fails."""
    user_a, membership_a = user_tenant_a
    user_b, membership_b = user_tenant_b
    
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
    
    # Try to create application with IT owner from Tenant B
    application_data = {
        "name": "ERP System",
        "business_owner_membership_id": str(membership_a.id),
        "it_owner_membership_id": str(membership_b.id),  # From Tenant B
    }
    
    response = client.post("/api/v1/applications", json=application_data, headers=headers)
    
    assert response.status_code in [
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_404_NOT_FOUND,
    ]


@pytest.mark.asyncio
async def test_tenant_isolation_applications(
    client, tenant_a, tenant_b, user_tenant_a, user_tenant_b, db_session
):
    """Test: Tenant A cannot access Tenant B's applications."""
    user_a, membership_a = user_tenant_a
    user_b, membership_b = user_tenant_b
    
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
    
    app_data = {
        "name": "Tenant B Application",
        "business_owner_membership_id": str(membership_b.id),
        "it_owner_membership_id": str(membership_b.id),
    }
    create_response = client.post("/api/v1/applications", json=app_data, headers=headers_b)
    app_b_id = create_response.json()["id"]
    
    # User A tries to access Tenant B's application
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
    
    response = client.get(f"/api/v1/applications/{app_b_id}", headers=headers_a)
    
    # Should return 404 (application not found in Tenant A)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    
    # List should not show Tenant B's application
    list_response = client.get("/api/v1/applications", headers=headers_a)
    assert list_response.status_code == status.HTTP_200_OK
    applications = list_response.json()
    assert len(applications) == 0  # Should be empty for Tenant A
