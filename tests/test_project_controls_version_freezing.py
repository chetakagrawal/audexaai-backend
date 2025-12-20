"""Integration tests for project controls version freezing feature."""

import pytest
from fastapi import status

from auth.jwt import create_dev_token


@pytest.mark.asyncio
async def test_version_freezing_on_add(client, tenant_a, user_tenant_a, db_session):
    """
    Test: When adding a control to a project, the control version is frozen.
    Later updates to the control in the library do NOT affect the frozen version.
    """
    user_a, membership_a = user_tenant_a
    
    # Create a project
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
    
    project_data = {"name": "Test Project", "status": "draft"}
    project_response = client.post("/api/v1/projects", json=project_data, headers=headers)
    assert project_response.status_code == status.HTTP_200_OK
    project = project_response.json()
    project_id = project["id"]
    
    # Create a control
    control_data = {
        "control_code": "AC-001",
        "name": "Test Control V1",
        "is_key": False,
        "is_automated": False,
    }
    control_response = client.post("/api/v1/controls", json=control_data, headers=headers)
    assert control_response.status_code == status.HTTP_200_OK
    control = control_response.json()
    control_id = control["id"]
    initial_row_version = control["row_version"]  # Should be 1
    assert initial_row_version == 1
    
    # Add control to project (this should freeze the version)
    mapping_data = {"control_id": control_id}
    pc_response = client.post(
        f"/api/v1/projects/{project_id}/controls",
        json=mapping_data,
        headers=headers,
    )
    assert pc_response.status_code == status.HTTP_201_CREATED
    project_control = pc_response.json()
    assert project_control["control_version_num"] == 1  # Frozen at version 1
    assert project_control["control_id"] == control_id
    project_control_id = project_control["id"]
    
    # Update the control in the library (this should increment row_version)
    update_data = {
        "control_code": "AC-001",  # Required field
        "name": "Test Control V2 (Updated)",
        "is_key": False,
        "is_automated": False,
    }
    update_response = client.put(
        f"/api/v1/controls/{control_id}",
        json=update_data,
        headers=headers,
    )
    assert update_response.status_code == status.HTTP_200_OK
    updated_control = update_response.json()
    assert updated_control["row_version"] == 2  # Version incremented to 2
    assert updated_control["name"] == "Test Control V2 (Updated)"
    
    # Verify that project_control still has frozen version 1
    pc_get_response = client.get(
        f"/api/v1/project-controls/{project_control_id}",
        headers=headers,
    )
    assert pc_get_response.status_code == status.HTTP_200_OK
    pc_after_update = pc_get_response.json()
    assert pc_after_update["control_version_num"] == 1  # MUST still be 1 (frozen)
    assert pc_after_update["control_id"] == control_id
    
    # Update the control again to version 3
    update_data2 = {
        "control_code": "AC-001",  # Required field
        "name": "Test Control V3 (Updated Again)",
        "is_key": False,
        "is_automated": False,
    }
    update_response2 = client.put(
        f"/api/v1/controls/{control_id}",
        json=update_data2,
        headers=headers,
    )
    assert update_response2.status_code == status.HTTP_200_OK
    updated_control2 = update_response2.json()
    assert updated_control2["row_version"] == 3  # Version incremented to 3
    
    # Verify that project_control STILL has frozen version 1
    pc_get_response2 = client.get(
        f"/api/v1/project-controls/{project_control_id}",
        headers=headers,
    )
    assert pc_get_response2.status_code == status.HTTP_200_OK
    pc_after_update2 = pc_get_response2.json()
    assert pc_after_update2["control_version_num"] == 1  # MUST STILL be 1 (frozen)


@pytest.mark.asyncio
async def test_readd_control_freezes_new_version(client, tenant_a, user_tenant_a, db_session):
    """
    Test: After removing a control from a project, re-adding it creates a NEW
    mapping with the CURRENT control version (not the old frozen version).
    """
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
        "control_code": "AC-002",
        "name": "Test Control Original",
        "is_key": False,
        "is_automated": False,
    }
    control_response = client.post("/api/v1/controls", json=control_data, headers=headers)
    control = control_response.json()
    control_id = control["id"]
    assert control["row_version"] == 1
    
    # Add control to project (freezes at version 1)
    mapping_data = {"control_id": control_id}
    pc_response = client.post(
        f"/api/v1/projects/{project_id}/controls",
        json=mapping_data,
        headers=headers,
    )
    assert pc_response.status_code == status.HTTP_201_CREATED
    pc1 = pc_response.json()
    pc1_id = pc1["id"]
    assert pc1["control_version_num"] == 1  # Frozen at version 1
    
    # Remove the control from the project
    remove_response = client.delete(
        f"/api/v1/project-controls/{pc1_id}",
        headers=headers,
    )
    assert remove_response.status_code == status.HTTP_204_NO_CONTENT
    
    # Update control multiple times (increment version to 5)
    for i in range(2, 6):
        update_data = {
            "control_code": "AC-002",  # Required field
            "name": f"Test Control Version {i}",
            "is_key": False,
            "is_automated": False,
        }
        update_response = client.put(
            f"/api/v1/controls/{control_id}",
            json=update_data,
            headers=headers,
        )
        assert update_response.status_code == status.HTTP_200_OK
        updated = update_response.json()
        assert updated["row_version"] == i
    
    # Re-add the control to the project (should freeze at CURRENT version 5)
    pc_response2 = client.post(
        f"/api/v1/projects/{project_id}/controls",
        json=mapping_data,
        headers=headers,
    )
    assert pc_response2.status_code == status.HTTP_201_CREATED
    pc2 = pc_response2.json()
    pc2_id = pc2["id"]
    
    # Verify it's a NEW mapping with NEW frozen version
    assert pc2_id != pc1_id  # Different mapping ID
    assert pc2["control_version_num"] == 5  # Frozen at current version (5)
    assert pc2["removed_at"] is None  # Active
    
    # Verify that listing project controls shows only the new active mapping
    list_response = client.get(
        f"/api/v1/projects/{project_id}/controls",
        headers=headers,
    )
    assert list_response.status_code == status.HTTP_200_OK
    mappings = list_response.json()
    assert len(mappings) == 1
    assert mappings[0]["id"] == pc2_id
    assert mappings[0]["control_version_num"] == 5


@pytest.mark.asyncio
async def test_update_overrides_does_not_change_version(client, tenant_a, user_tenant_a, db_session):
    """
    Test: Updating override fields (PATCH) does NOT change the frozen control_version_num.
    """
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
        "control_code": "AC-003",
        "name": "Test Control",
        "is_key": False,
        "is_automated": False,
    }
    control_response = client.post("/api/v1/controls", json=control_data, headers=headers)
    control = control_response.json()
    control_id = control["id"]
    
    # Add control to project with initial overrides
    mapping_data = {
        "control_id": control_id,
        "is_key_override": False,
        "frequency_override": "monthly",
        "notes": "Initial notes",
    }
    pc_response = client.post(
        f"/api/v1/projects/{project_id}/controls",
        json=mapping_data,
        headers=headers,
    )
    assert pc_response.status_code == status.HTTP_201_CREATED
    pc = pc_response.json()
    pc_id = pc["id"]
    assert pc["control_version_num"] == 1
    assert pc["is_key_override"] is False
    assert pc["frequency_override"] == "monthly"
    
    # Update overrides using PATCH
    update_overrides = {
        "is_key_override": True,
        "frequency_override": "quarterly",
        "notes": "Updated notes",
    }
    patch_response = client.patch(
        f"/api/v1/project-controls/{pc_id}",
        json=update_overrides,
        headers=headers,
    )
    assert patch_response.status_code == status.HTTP_200_OK
    updated_pc = patch_response.json()
    
    # Verify overrides were updated but version is UNCHANGED
    assert updated_pc["is_key_override"] is True
    assert updated_pc["frequency_override"] == "quarterly"
    assert updated_pc["notes"] == "Updated notes"
    assert updated_pc["control_version_num"] == 1  # MUST NOT change
    assert updated_pc["control_id"] == control_id  # MUST NOT change

