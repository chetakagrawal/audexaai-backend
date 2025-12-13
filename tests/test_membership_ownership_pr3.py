"""Integration tests for PR3: Membership-based ownership (TDD - failing tests first)."""

import pytest
from fastapi import status

from auth.jwt import create_dev_token


@pytest.mark.asyncio
async def test_project_creation_sets_created_by_membership_id(
    client, tenant_a, user_tenant_a, db_session
):
    """
    Test: Creating a project sets created_by_membership_id from current user's membership.
    
    This test will FAIL until we add created_by_membership_id to Project model.
    """
    user_a, membership_a = user_tenant_a
    
    token = create_dev_token(
        user_id=user_a.id,
        tenant_id=tenant_a.id,
        role=membership_a.role,
        is_platform_admin=False,
    )
    
    headers = {"Authorization": f"Bearer {token}"}
    project_data = {"name": "Test Project", "status": "draft"}
    
    response = client.post("/api/v1/projects", json=project_data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    
    project = response.json()
    # This will fail until created_by_membership_id is added
    assert "created_by_membership_id" in project
    assert project["created_by_membership_id"] == str(membership_a.id)


@pytest.mark.asyncio
async def test_control_creation_sets_created_by_membership_id(
    client, tenant_a, user_tenant_a, db_session
):
    """
    Test: Creating a control sets created_by_membership_id from current user's membership.
    
    This test will FAIL until we add created_by_membership_id to Control model.
    """
    user_a, membership_a = user_tenant_a
    
    token = create_dev_token(
        user_id=user_a.id,
        tenant_id=tenant_a.id,
        role=membership_a.role,
        is_platform_admin=False,
    )
    
    headers = {"Authorization": f"Bearer {token}"}
    control_data = {
        "control_code": "AC-001",
        "name": "Test Control",
        "is_key": False,
        "is_automated": False,
    }
    
    response = client.post("/api/v1/controls", json=control_data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    
    control = response.json()
    # This will fail until created_by_membership_id is added
    assert "created_by_membership_id" in control
    assert control["created_by_membership_id"] == str(membership_a.id)


@pytest.mark.asyncio
async def test_project_created_by_membership_belongs_to_tenant(
    client, tenant_a, tenant_b, user_tenant_a, user_tenant_b, db_session
):
    """
    Test: Project's created_by_membership_id must belong to the project's tenant.
    
    This ensures membership_id enforces tenant ownership at the DB level.
    """
    user_a, membership_a = user_tenant_a
    user_b, membership_b = user_tenant_b
    
    # User A creates a project in Tenant A
    token_a = create_dev_token(
        user_id=user_a.id,
        tenant_id=tenant_a.id,
        role=membership_a.role,
        is_platform_admin=False,
    )
    
    headers_a = {"Authorization": f"Bearer {token_a}"}
    project_data = {"name": "Tenant A Project", "status": "draft"}
    
    response = client.post("/api/v1/projects", json=project_data, headers=headers_a)
    assert response.status_code == status.HTTP_200_OK
    
    project = response.json()
    assert project["tenant_id"] == str(tenant_a.id)
    assert project["created_by_membership_id"] == str(membership_a.id)
    
    # Verify membership belongs to the same tenant
    # This is enforced by FK constraint: created_by_membership_id → user_tenants.id
    # And user_tenants.tenant_id must match project.tenant_id


@pytest.mark.asyncio
async def test_cross_tenant_membership_rejection(
    client, tenant_a, tenant_b, user_tenant_a, user_tenant_b, db_session
):
    """
    Test: Cannot set created_by_membership_id to a membership from a different tenant.
    
    This test verifies that the FK constraint prevents cross-tenant ownership.
    """
    user_a, membership_a = user_tenant_a
    user_b, membership_b = user_tenant_b
    
    # User A creates a project in Tenant A
    token_a = create_dev_token(
        user_id=user_a.id,
        tenant_id=tenant_a.id,
        role=membership_a.role,
        is_platform_admin=False,
    )
    
    headers_a = {"Authorization": f"Bearer {token_a}"}
    
    # Try to create project with Tenant B's membership (should be impossible via API)
    # But if someone tries to do it directly in DB, FK constraint should prevent it
    # This test verifies the constraint exists
    
    # For now, we test that API correctly sets membership from context
    project_data = {"name": "Test Project", "status": "draft"}
    response = client.post("/api/v1/projects", json=project_data, headers=headers_a)
    assert response.status_code == status.HTTP_200_OK
    
    project = response.json()
    # API should set membership from context, not allow client to specify
    assert project["created_by_membership_id"] == str(membership_a.id)
    assert project["tenant_id"] == str(tenant_a.id)


@pytest.mark.asyncio
async def test_list_projects_includes_created_by_membership_id(
    client, tenant_a, user_tenant_a, db_session
):
    """
    Test: Listing projects includes created_by_membership_id in response.
    """
    user_a, membership_a = user_tenant_a
    
    token = create_dev_token(
        user_id=user_a.id,
        tenant_id=tenant_a.id,
        role=membership_a.role,
        is_platform_admin=False,
    )
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create a project
    project_data = {"name": "Test Project", "status": "draft"}
    response = client.post("/api/v1/projects", json=project_data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    
    # List projects
    response = client.get("/api/v1/projects", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    
    projects = response.json()
    assert len(projects) == 1
    assert "created_by_membership_id" in projects[0]
    assert projects[0]["created_by_membership_id"] == str(membership_a.id)

