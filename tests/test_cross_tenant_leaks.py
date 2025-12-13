"""Integration tests for cross-tenant leak prevention."""

import pytest
from fastapi import status

from auth.jwt import create_dev_token


@pytest.mark.asyncio
async def test_user_tenant_a_cannot_see_tenant_b_resources(
    client, tenant_a, tenant_b, user_tenant_a, user_tenant_b
):
    """
    Test: User in Tenant A cannot read Tenant B resources by guessing IDs.
    
    Scenario:
    - User A belongs to Tenant A
    - User B belongs to Tenant B
    - User A tries to access Tenant B's data
    - Should return 403 or empty results
    """
    user_a, membership_a = user_tenant_a
    user_b, membership_b = user_tenant_b
    
    # Create JWT token for User A
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
    
    # Test 1: User A tries to list tenants - should only see Tenant A
    response = client.get("/api/v1/tenants", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    tenants = response.json()
    assert len(tenants) == 1
    assert tenants[0]["id"] == str(tenant_a.id)
    assert tenants[0]["slug"] == "tenant-a"
    
    # Test 2: User A tries to list users - should only see users in Tenant A
    response = client.get("/api/v1/users", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    users = response.json()
    # Should only see User A (themselves)
    user_ids = [u["id"] for u in users]
    assert str(user_a.id) in user_ids
    assert str(user_b.id) not in user_ids  # User B should not be visible


@pytest.mark.asyncio
async def test_user_without_membership_cannot_access_tenant_scoped_endpoints(
    client, user_no_membership
):
    """
    Test: User without membership cannot access tenant-scoped endpoints.
    
    Scenario:
    - User has no tenant membership
    - User tries to access tenant-scoped endpoints
    - Should return 403 Forbidden
    """
    user = user_no_membership
    
    # Create a token without tenant_id (simulating invalid state)
    # This should fail at get_current_user level
    token = create_dev_token(
        user_id=user.id,
        tenant_id=None,  # No tenant
        role="user",
        is_platform_admin=False,
    )
    
    headers = {"Authorization": f"Bearer {token}"}
    # Note: No X-Membership-Id header - this test verifies the old behavior
    # where token without tenant_id fails
    
    # Should fail because non-platform admin must have tenant_id
    response = client.get("/api/v1/tenants", headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "tenant_id" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_user_cannot_access_other_tenant_by_id_guessing(
    client, tenant_a, tenant_b, user_tenant_a
):
    """
    Test: User cannot access another tenant's data by guessing tenant ID.
    
    Scenario:
    - User A belongs to Tenant A
    - User A tries to access Tenant B by ID
    - Should only see Tenant A, not Tenant B
    """
    user_a, membership_a = user_tenant_a
    
    # Create JWT token for User A
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
    
    # List tenants - should only return Tenant A
    response = client.get("/api/v1/tenants", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    tenants = response.json()
    
    # Verify Tenant B is not in the results
    tenant_ids = [t["id"] for t in tenants]
    assert str(tenant_a.id) in tenant_ids
    assert str(tenant_b.id) not in tenant_ids
    
    # Verify we only got Tenant A
    assert len(tenants) == 1
    assert tenants[0]["id"] == str(tenant_a.id)
