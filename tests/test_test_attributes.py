"""Integration tests for test attributes endpoints."""

import pytest
from fastapi import status

from auth.jwt import create_dev_token


@pytest.mark.asyncio
async def test_create_test_attribute_success(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Creating a test attribute succeeds."""
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
    
    # Create control first
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
    
    # Create test attribute
    test_attribute_data = {
        "code": "TA-001",
        "name": "Access Control Test",
        "frequency": "Quarterly",
        "test_procedure": "Review access logs and verify user permissions",
        "expected_evidence": "Access logs, user permission reports",
    }
    
    response = client.post(
        f"/api/v1/controls/{control_id}/test-attributes",
        json=test_attribute_data,
        headers=headers,
    )
    
    assert response.status_code == status.HTTP_201_CREATED
    
    test_attribute = response.json()
    assert test_attribute["code"] == "TA-001"
    assert test_attribute["name"] == "Access Control Test"
    assert test_attribute["frequency"] == "Quarterly"
    assert test_attribute["test_procedure"] == "Review access logs and verify user permissions"
    assert test_attribute["expected_evidence"] == "Access logs, user permission reports"
    assert test_attribute["control_id"] == control_id
    assert "tenant_id" in test_attribute
    assert test_attribute["tenant_id"] == str(tenant_a.id)
    assert "id" in test_attribute
    assert "created_at" in test_attribute


@pytest.mark.asyncio
async def test_create_test_attribute_minimal_fields(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Creating a test attribute with minimal required fields succeeds."""
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
    
    # Create control first
    control_data = {
        "control_code": "AC-002",
        "name": "Test Control",
        "is_key": False,
        "is_automated": False,
    }
    control_response = client.post("/api/v1/controls", json=control_data, headers=headers)
    control = control_response.json()
    control_id = control["id"]
    
    # Create test attribute with only required fields
    test_attribute_data = {
        "code": "TA-002",
        "name": "Minimal Test Attribute",
    }
    
    response = client.post(
        f"/api/v1/controls/{control_id}/test-attributes",
        json=test_attribute_data,
        headers=headers,
    )
    
    assert response.status_code == status.HTTP_201_CREATED
    
    test_attribute = response.json()
    assert test_attribute["code"] == "TA-002"
    assert test_attribute["name"] == "Minimal Test Attribute"
    assert test_attribute["frequency"] is None
    assert test_attribute["test_procedure"] is None
    assert test_attribute["expected_evidence"] is None


@pytest.mark.asyncio
async def test_list_control_test_attributes_success(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Listing test attributes returns all test attributes for the control."""
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
    control = control_response.json()
    control_id = control["id"]
    
    # Create multiple test attributes
    ta1_data = {
        "code": "TA-003-1",
        "name": "Test Attribute 1",
        "frequency": "Monthly",
    }
    ta2_data = {
        "code": "TA-003-2",
        "name": "Test Attribute 2",
        "frequency": "Quarterly",
    }
    
    client.post(
        f"/api/v1/controls/{control_id}/test-attributes",
        json=ta1_data,
        headers=headers,
    )
    client.post(
        f"/api/v1/controls/{control_id}/test-attributes",
        json=ta2_data,
        headers=headers,
    )
    
    # List test attributes
    response = client.get(
        f"/api/v1/controls/{control_id}/test-attributes",
        headers=headers,
    )
    
    assert response.status_code == status.HTTP_200_OK
    
    test_attributes = response.json()
    assert len(test_attributes) == 2
    codes = [ta["code"] for ta in test_attributes]
    assert "TA-003-1" in codes
    assert "TA-003-2" in codes


@pytest.mark.asyncio
async def test_get_test_attribute_success(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Getting a specific test attribute succeeds."""
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
        "control_code": "AC-004",
        "name": "Test Control",
        "is_key": False,
        "is_automated": False,
    }
    control_response = client.post("/api/v1/controls", json=control_data, headers=headers)
    control = control_response.json()
    control_id = control["id"]
    
    # Create test attribute
    test_attribute_data = {
        "code": "TA-004",
        "name": "Test Attribute",
        "frequency": "Annually",
    }
    create_response = client.post(
        f"/api/v1/controls/{control_id}/test-attributes",
        json=test_attribute_data,
        headers=headers,
    )
    created_ta = create_response.json()
    test_attribute_id = created_ta["id"]
    
    # Get test attribute
    response = client.get(
        f"/api/v1/test-attributes/{test_attribute_id}",
        headers=headers,
    )
    
    assert response.status_code == status.HTTP_200_OK
    
    test_attribute = response.json()
    assert test_attribute["id"] == test_attribute_id
    assert test_attribute["code"] == "TA-004"
    assert test_attribute["name"] == "Test Attribute"
    assert test_attribute["frequency"] == "Annually"
    assert test_attribute["control_id"] == control_id


@pytest.mark.asyncio
async def test_update_test_attribute_success(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Updating a test attribute succeeds."""
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
        "control_code": "AC-005",
        "name": "Test Control",
        "is_key": False,
        "is_automated": False,
    }
    control_response = client.post("/api/v1/controls", json=control_data, headers=headers)
    control = control_response.json()
    control_id = control["id"]
    
    # Create test attribute
    test_attribute_data = {
        "code": "TA-005",
        "name": "Original Name",
        "frequency": "Monthly",
    }
    create_response = client.post(
        f"/api/v1/controls/{control_id}/test-attributes",
        json=test_attribute_data,
        headers=headers,
    )
    created_ta = create_response.json()
    test_attribute_id = created_ta["id"]
    
    # Update test attribute
    update_data = {
        "code": "TA-005-UPDATED",
        "name": "Updated Name",
        "frequency": "Quarterly",
        "test_procedure": "Updated procedure",
        "expected_evidence": "Updated evidence",
    }
    
    response = client.put(
        f"/api/v1/test-attributes/{test_attribute_id}",
        json=update_data,
        headers=headers,
    )
    
    assert response.status_code == status.HTTP_200_OK
    
    updated_ta = response.json()
    assert updated_ta["id"] == test_attribute_id
    assert updated_ta["code"] == "TA-005-UPDATED"
    assert updated_ta["name"] == "Updated Name"
    assert updated_ta["frequency"] == "Quarterly"
    assert updated_ta["test_procedure"] == "Updated procedure"
    assert updated_ta["expected_evidence"] == "Updated evidence"
    # Control ID should not change
    assert updated_ta["control_id"] == control_id


@pytest.mark.asyncio
async def test_delete_test_attribute_success(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Deleting a test attribute succeeds."""
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
        "control_code": "AC-006",
        "name": "Test Control",
        "is_key": False,
        "is_automated": False,
    }
    control_response = client.post("/api/v1/controls", json=control_data, headers=headers)
    control = control_response.json()
    control_id = control["id"]
    
    # Create test attribute
    test_attribute_data = {
        "code": "TA-006",
        "name": "Test Attribute",
    }
    create_response = client.post(
        f"/api/v1/controls/{control_id}/test-attributes",
        json=test_attribute_data,
        headers=headers,
    )
    created_ta = create_response.json()
    test_attribute_id = created_ta["id"]
    
    # Delete test attribute
    response = client.delete(
        f"/api/v1/test-attributes/{test_attribute_id}",
        headers=headers,
    )
    
    assert response.status_code == status.HTTP_204_NO_CONTENT
    
    # Verify it's deleted
    get_response = client.get(
        f"/api/v1/test-attributes/{test_attribute_id}",
        headers=headers,
    )
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_cannot_create_test_attribute_for_nonexistent_control(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Cannot create test attribute for non-existent control."""
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
    
    from uuid import uuid4
    fake_control_id = uuid4()
    
    test_attribute_data = {
        "code": "TA-007",
        "name": "Test Attribute",
    }
    
    response = client.post(
        f"/api/v1/controls/{fake_control_id}/test-attributes",
        json=test_attribute_data,
        headers=headers,
    )
    
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Control not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_cannot_create_test_attribute_for_different_tenant_control(
    client, tenant_a, tenant_b, user_tenant_a, user_tenant_b, db_session
):
    """Test: Cannot create test attribute for control from different tenant."""
    user_a, membership_a = user_tenant_a
    user_b, membership_b = user_tenant_b
    
    # User B creates control in Tenant B
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
    
    control_data = {
        "control_code": "AC-008",
        "name": "Tenant B Control",
        "is_key": False,
        "is_automated": False,
    }
    control_response = client.post("/api/v1/controls", json=control_data, headers=headers_b)
    control_b = control_response.json()
    control_b_id = control_b["id"]
    
    # User A tries to create test attribute for Tenant B's control
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
    
    test_attribute_data = {
        "code": "TA-008",
        "name": "Test Attribute",
    }
    
    response = client.post(
        f"/api/v1/controls/{control_b_id}/test-attributes",
        json=test_attribute_data,
        headers=headers_a,
    )
    
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Control not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_tenant_isolation_test_attributes(
    client, tenant_a, tenant_b, user_tenant_a, user_tenant_b, db_session
):
    """Test: Tenant A cannot access Tenant B's test attributes."""
    user_a, membership_a = user_tenant_a
    user_b, membership_b = user_tenant_b
    
    # User A creates control and test attribute in Tenant A
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
        "control_code": "AC-009",
        "name": "Tenant A Control",
        "is_key": False,
        "is_automated": False,
    }
    control_response = client.post("/api/v1/controls", json=control_data, headers=headers_a)
    control_a = control_response.json()
    control_a_id = control_a["id"]
    
    test_attribute_data = {
        "code": "TA-009",
        "name": "Tenant A Test Attribute",
    }
    ta_response = client.post(
        f"/api/v1/controls/{control_a_id}/test-attributes",
        json=test_attribute_data,
        headers=headers_a,
    )
    ta_a = ta_response.json()
    ta_a_id = ta_a["id"]
    
    # User B tries to access Tenant A's test attribute
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
    
    # Should return 404 (test attribute not found in Tenant B)
    response = client.get(
        f"/api/v1/test-attributes/{ta_a_id}",
        headers=headers_b,
    )
    
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_list_test_attributes_empty_for_control_without_attributes(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Listing test attributes for control without attributes returns empty list."""
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
        "control_code": "AC-010",
        "name": "Test Control",
        "is_key": False,
        "is_automated": False,
    }
    control_response = client.post("/api/v1/controls", json=control_data, headers=headers)
    control = control_response.json()
    control_id = control["id"]
    
    # List test attributes (should be empty)
    response = client.get(
        f"/api/v1/controls/{control_id}/test-attributes",
        headers=headers,
    )
    
    assert response.status_code == status.HTTP_200_OK
    test_attributes = response.json()
    assert isinstance(test_attributes, list)
    assert len(test_attributes) == 0
