"""Integration tests for controls API endpoints.

These tests verify end-to-end API behavior including authentication, 
tenant isolation, audit metadata, and soft delete functionality.
"""

import pytest
from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.jwt import create_dev_token
from models.control import Control


@pytest.mark.asyncio
async def test_create_control_sets_audit_metadata(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Creating a control via API sets row_version=1, updated_at, updated_by is None."""
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
    
    control_data = {
        "control_code": "AC-001",
        "name": "Test Control",
        "is_key": False,
        "is_automated": False,
    }
    response = client.post("/api/v1/controls", json=control_data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    
    control = response.json()
    assert control["row_version"] == 1
    assert control["updated_at"] is not None
    assert control["updated_by_membership_id"] is None  # Not set on creation
    assert control["deleted_at"] is None
    assert control["deleted_by_membership_id"] is None
    
    # Verify in database
    result = await db_session.execute(
        select(Control).where(Control.id == control["id"])
    )
    db_control = result.scalar_one_or_none()
    assert db_control is not None
    assert db_control.row_version == 1
    assert db_control.updated_at is not None
    assert db_control.updated_by_membership_id is None
    assert db_control.deleted_at is None
    assert db_control.deleted_by_membership_id is None


@pytest.mark.asyncio
async def test_update_control_increments_row_version(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Updating a control via API increments row_version and sets updated_by."""
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
        "control_code": "AC-002",
        "name": "Test Control",
        "is_key": False,
        "is_automated": False,
    }
    create_response = client.post("/api/v1/controls", json=control_data, headers=headers)
    assert create_response.status_code == status.HTTP_200_OK
    control = create_response.json()
    control_id = control["id"]
    initial_row_version = control["row_version"]
    initial_updated_at = control["updated_at"]
    
    # Update control
    update_data = {
        "control_code": "AC-002",
        "name": "Updated Control Name",
        "is_key": True,
        "is_automated": False,
    }
    update_response = client.put(
        f"/api/v1/controls/{control_id}", json=update_data, headers=headers
    )
    assert update_response.status_code == status.HTTP_200_OK
    
    updated_control = update_response.json()
    assert updated_control["row_version"] == initial_row_version + 1
    assert updated_control["updated_at"] != initial_updated_at
    assert updated_control["updated_by_membership_id"] == str(membership_a.id)
    assert updated_control["deleted_at"] is None
    assert updated_control["deleted_by_membership_id"] is None


@pytest.mark.asyncio
async def test_delete_control_soft_deletes(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Deleting a control via API soft deletes it and increments row_version."""
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
    create_response = client.post("/api/v1/controls", json=control_data, headers=headers)
    assert create_response.status_code == status.HTTP_200_OK
    control = create_response.json()
    control_id = control["id"]
    initial_row_version = control["row_version"]
    
    # Delete control
    delete_response = client.delete(f"/api/v1/controls/{control_id}", headers=headers)
    assert delete_response.status_code == status.HTTP_200_OK
    
    deleted_control = delete_response.json()
    assert deleted_control["deleted_at"] is not None
    assert deleted_control["deleted_by_membership_id"] == str(membership_a.id)
    assert deleted_control["row_version"] == initial_row_version + 1
    assert deleted_control["updated_at"] is not None
    assert deleted_control["updated_by_membership_id"] == str(membership_a.id)
    
    # Verify deleted control is not returned by list
    list_response = client.get("/api/v1/controls", headers=headers)
    assert list_response.status_code == status.HTTP_200_OK
    controls = list_response.json()
    control_ids = [c["id"] for c in controls]
    assert control_id not in control_ids
    
    # Verify deleted control returns 404 on get
    get_response = client.get(f"/api/v1/controls/{control_id}", headers=headers)
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_cannot_create_duplicate_active_control_code(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Cannot create two active controls with same (tenant_id, control_code)."""
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
    
    control_data = {
        "control_code": "AC-004",
        "name": "Test Control",
        "is_key": False,
        "is_automated": False,
    }
    
    # Create first control
    response1 = client.post("/api/v1/controls", json=control_data, headers=headers)
    assert response1.status_code == status.HTTP_200_OK
    
    # Try to create duplicate - should fail
    response2 = client.post("/api/v1/controls", json=control_data, headers=headers)
    assert response2.status_code in (
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_409_CONFLICT,
    )


@pytest.mark.asyncio
async def test_can_reuse_control_code_after_soft_delete(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Can create a new active control with same control_code after soft delete."""
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
    
    control_data = {
        "control_code": "AC-005",
        "name": "Test Control",
        "is_key": False,
        "is_automated": False,
    }
    
    # Create control
    create_response = client.post("/api/v1/controls", json=control_data, headers=headers)
    assert create_response.status_code == status.HTTP_200_OK
    control = create_response.json()
    control_id = control["id"]
    
    # Delete control
    delete_response = client.delete(f"/api/v1/controls/{control_id}", headers=headers)
    assert delete_response.status_code == status.HTTP_200_OK
    
    # Can now create new control with same control_code
    create_response2 = client.post("/api/v1/controls", json=control_data, headers=headers)
    assert create_response2.status_code == status.HTTP_200_OK
    new_control = create_response2.json()
    assert new_control["control_code"] == "AC-005"
    assert new_control["id"] != control_id  # Different control


@pytest.mark.asyncio
async def test_different_tenants_can_have_same_control_code(
    client, tenant_a, tenant_b, user_tenant_a, user_tenant_b, db_session
):
    """Test: Different tenants can have controls with the same control_code."""
    user_a, membership_a = user_tenant_a
    user_b, membership_b = user_tenant_b
    
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
        "control_code": "AC-006",  # Same code
        "name": "Test Control",
        "is_key": False,
        "is_automated": False,
    }
    
    # Create in tenant A
    response_a = client.post("/api/v1/controls", json=control_data, headers=headers_a)
    assert response_a.status_code == status.HTTP_200_OK
    
    # Create in tenant B with same code - should succeed
    response_b = client.post("/api/v1/controls", json=control_data, headers=headers_b)
    assert response_b.status_code == status.HTTP_200_OK
    
    control_a = response_a.json()
    control_b = response_b.json()
    assert control_a["control_code"] == control_b["control_code"]
    assert control_a["tenant_id"] != control_b["tenant_id"]


@pytest.mark.asyncio
async def test_list_controls_excludes_deleted(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: List controls endpoint excludes soft-deleted controls."""
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
    
    # Create two controls
    control_data_1 = {
        "control_code": "AC-007",
        "name": "Active Control",
        "is_key": False,
        "is_automated": False,
    }
    control_data_2 = {
        "control_code": "AC-008",
        "name": "To Be Deleted",
        "is_key": False,
        "is_automated": False,
    }
    
    create_response_1 = client.post("/api/v1/controls", json=control_data_1, headers=headers)
    create_response_2 = client.post("/api/v1/controls", json=control_data_2, headers=headers)
    assert create_response_1.status_code == status.HTTP_200_OK
    assert create_response_2.status_code == status.HTTP_200_OK
    
    control_1 = create_response_1.json()
    control_2 = create_response_2.json()
    
    # Delete second control
    delete_response = client.delete(f"/api/v1/controls/{control_2['id']}", headers=headers)
    assert delete_response.status_code == status.HTTP_200_OK
    
    # List should only return active control
    list_response = client.get("/api/v1/controls", headers=headers)
    assert list_response.status_code == status.HTTP_200_OK
    controls = list_response.json()
    control_ids = [c["id"] for c in controls]
    assert control_1["id"] in control_ids
    assert control_2["id"] not in control_ids


@pytest.mark.asyncio
async def test_get_control_returns_404_for_deleted(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Get control endpoint returns 404 for soft-deleted controls."""
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
        "control_code": "AC-009",
        "name": "Test Control",
        "is_key": False,
        "is_automated": False,
    }
    create_response = client.post("/api/v1/controls", json=control_data, headers=headers)
    assert create_response.status_code == status.HTTP_200_OK
    control = create_response.json()
    control_id = control["id"]
    
    # Delete control
    delete_response = client.delete(f"/api/v1/controls/{control_id}", headers=headers)
    assert delete_response.status_code == status.HTTP_200_OK
    
    # Get should return 404
    get_response = client.get(f"/api/v1/controls/{control_id}", headers=headers)
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_update_control_returns_404_for_deleted(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Update control endpoint returns 404 for soft-deleted controls."""
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
    create_response = client.post("/api/v1/controls", json=control_data, headers=headers)
    assert create_response.status_code == status.HTTP_200_OK
    control = create_response.json()
    control_id = control["id"]
    
    # Delete control
    delete_response = client.delete(f"/api/v1/controls/{control_id}", headers=headers)
    assert delete_response.status_code == status.HTTP_200_OK
    
    # Update should return 404
    update_data = {
        "control_code": "AC-010",
        "name": "Updated Name",
        "is_key": False,
        "is_automated": False,
    }
    update_response = client.put(
        f"/api/v1/controls/{control_id}", json=update_data, headers=headers
    )
    assert update_response.status_code == status.HTTP_404_NOT_FOUND

