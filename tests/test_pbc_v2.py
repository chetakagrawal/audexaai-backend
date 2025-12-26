"""Integration tests for PBC requests v2 endpoints."""

from datetime import date, datetime, UTC
from uuid import uuid4

import pytest
from fastapi import status

from auth.jwt import create_dev_token
from models.application import Application
from models.control import Control
from models.project import Project
from models.project_control import ProjectControl
from models.project_control_application import ProjectControlApplication
from models.test_attribute import TestAttribute
from models.project_test_attribute_override import ProjectTestAttributeOverride
from repos import (
    projects_repo,
    controls_repo,
    applications_repo,
    project_controls_repo,
    project_control_applications_repo,
    test_attributes_repo,
    project_test_attribute_overrides_repo,
    pbc_repo,
)


@pytest.mark.asyncio
async def test_generate_pbc_creates_items_for_all_line_items(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Generation creates items equal to number of resolved line items."""
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

    # Create project
    project = Project(
        tenant_id=tenant_a.id,
        name="Test Project",
        status="active",
        created_by_membership_id=membership_a.id,
    )
    project = await projects_repo.create(db_session, project)
    await db_session.commit()

    # Create control
    control = Control(
        tenant_id=tenant_a.id,
        control_code="CTL-001",
        name="Test Control",
        created_by_membership_id=membership_a.id,
    )
    control = await controls_repo.create(db_session, control)
    await db_session.commit()

    # Create application
    application = Application(
        tenant_id=tenant_a.id,
        name="Test Application",
        created_by_membership_id=membership_a.id,
    )
    application = await applications_repo.create(db_session, application)
    await db_session.commit()

    # Add control to project
    project_control = ProjectControl(
        tenant_id=tenant_a.id,
        project_id=project.id,
        control_id=control.id,
        control_version_num=control.row_version,
        added_by_membership_id=membership_a.id,
    )
    project_control = await project_controls_repo.create(db_session, project_control)
    await db_session.commit()

    # Add application to project control
    pca = ProjectControlApplication(
        tenant_id=tenant_a.id,
        project_control_id=project_control.id,
        application_id=application.id,
        application_version_num=application.row_version,
        added_by_membership_id=membership_a.id,
    )
    pca = await project_control_applications_repo.create(db_session, pca)
    await db_session.commit()

    # Create test attribute
    test_attr = TestAttribute(
        tenant_id=tenant_a.id,
        control_id=control.id,
        code="TA-001",
        name="Test Attribute",
        test_procedure="Test procedure",
        expected_evidence="Test evidence",
        created_by_membership_id=membership_a.id,
    )
    test_attr = await test_attributes_repo.create(db_session, test_attr)
    await db_session.commit()

    # Generate PBC request
    payload = {
        "mode": "new",
        "group_mode": "single_request",
        "title": "Test PBC Request",
    }
    response = client.post(
        f"/api/v1/projects/{project.id}/pbc/generate",
        json=payload,
        headers=headers,
    )
    assert response.status_code == status.HTTP_201_CREATED
    result = response.json()
    pbc_request_id = result["pbc_request_id"]
    assert result["items_created"] == 1  # 1 line item: control × app × test_attr

    # Verify items were created
    items = await pbc_repo.list_items_by_request(
        db_session,
        tenant_id=tenant_a.id,
        pbc_request_id=pbc_request_id,
        include_deleted=False,
    )
    assert len(items) == 1
    assert items[0].project_control_id == project_control.id
    assert items[0].application_id == application.id
    assert items[0].test_attribute_id == test_attr.id
    assert items[0].effective_procedure_snapshot == "Test procedure"
    assert items[0].effective_evidence_snapshot == "Test evidence"
    assert items[0].source_snapshot == "base"


@pytest.mark.asyncio
async def test_pbc_snapshot_immutability(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Snapshot fields remain unchanged after override changes."""
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

    # Create project, control, application, test attribute
    project = Project(
        tenant_id=tenant_a.id,
        name="Test Project",
        status="active",
        created_by_membership_id=membership_a.id,
    )
    project = await projects_repo.create(db_session, project)

    control = Control(
        tenant_id=tenant_a.id,
        control_code="CTL-001",
        name="Test Control",
        created_by_membership_id=membership_a.id,
    )
    control = await controls_repo.create(db_session, control)

    application = Application(
        tenant_id=tenant_a.id,
        name="Test Application",
        created_by_membership_id=membership_a.id,
    )
    application = await applications_repo.create(db_session, application)

    project_control = ProjectControl(
        tenant_id=tenant_a.id,
        project_id=project.id,
        control_id=control.id,
        control_version_num=control.row_version,
        added_by_membership_id=membership_a.id,
    )
    project_control = await project_controls_repo.create(db_session, project_control)

    pca = ProjectControlApplication(
        tenant_id=tenant_a.id,
        project_control_id=project_control.id,
        application_id=application.id,
        application_version_num=application.row_version,
        added_by_membership_id=membership_a.id,
    )
    pca = await project_control_applications_repo.create(db_session, pca)

    test_attr = TestAttribute(
        tenant_id=tenant_a.id,
        control_id=control.id,
        code="TA-001",
        name="Test Attribute",
        test_procedure="Original procedure",
        expected_evidence="Original evidence",
        created_by_membership_id=membership_a.id,
    )
    test_attr = await test_attributes_repo.create(db_session, test_attr)
    await db_session.commit()

    # Generate PBC request
    payload = {"mode": "new", "group_mode": "single_request"}
    response = client.post(
        f"/api/v1/projects/{project.id}/pbc/generate",
        json=payload,
        headers=headers,
    )
    assert response.status_code == status.HTTP_201_CREATED
    result = response.json()
    pbc_request_id = result["pbc_request_id"]

    # Get items and verify snapshot
    items = await pbc_repo.list_items_by_request(
        db_session,
        tenant_id=tenant_a.id,
        pbc_request_id=pbc_request_id,
        include_deleted=False,
    )
    assert len(items) == 1
    original_procedure = items[0].effective_procedure_snapshot
    original_evidence = items[0].effective_evidence_snapshot
    assert original_procedure == "Original procedure"
    assert original_evidence == "Original evidence"

    # Create override that changes effective values
    override = ProjectTestAttributeOverride(
        tenant_id=tenant_a.id,
        project_control_id=project_control.id,
        test_attribute_id=test_attr.id,
        application_id=application.id,
        base_test_attribute_version_num=test_attr.row_version,
        procedure_override="New procedure",
        expected_evidence_override="New evidence",
        created_by_membership_id=membership_a.id,
    )
    override = await project_test_attribute_overrides_repo.create(db_session, override)
    await db_session.commit()

    # Verify line items endpoint shows new values
    # (This would be tested via the line items endpoint if it existed)
    # For now, verify the override exists
    effective = await project_test_attribute_overrides_repo.get_active_app(
        db_session,
        tenant_id=tenant_a.id,
        project_control_id=project_control.id,
        application_id=application.id,
        test_attribute_id=test_attr.id,
    )
    assert effective is not None
    assert effective.procedure_override == "New procedure"

    # Verify PBC items still have original snapshot values
    items_after = await pbc_repo.list_items_by_request(
        db_session,
        tenant_id=tenant_a.id,
        pbc_request_id=pbc_request_id,
        include_deleted=False,
    )
    assert len(items_after) == 1
    assert items_after[0].effective_procedure_snapshot == original_procedure
    assert items_after[0].effective_evidence_snapshot == original_evidence
    assert items_after[0].effective_procedure_snapshot == "Original procedure"
    assert items_after[0].effective_evidence_snapshot == "Original evidence"


@pytest.mark.asyncio
async def test_pbc_tenant_isolation(
    client, tenant_a, tenant_b, user_tenant_a, user_tenant_b, db_session
):
    """Test: Different tenant cannot access PBC requests."""
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

    # Create project, control, application, test attribute in tenant A
    project = Project(
        tenant_id=tenant_a.id,
        name="Test Project",
        status="active",
        created_by_membership_id=membership_a.id,
    )
    project = await projects_repo.create(db_session, project)

    control = Control(
        tenant_id=tenant_a.id,
        control_code="CTL-001",
        name="Test Control",
        created_by_membership_id=membership_a.id,
    )
    control = await controls_repo.create(db_session, control)

    application = Application(
        tenant_id=tenant_a.id,
        name="Test Application",
        created_by_membership_id=membership_a.id,
    )
    application = await applications_repo.create(db_session, application)

    project_control = ProjectControl(
        tenant_id=tenant_a.id,
        project_id=project.id,
        control_id=control.id,
        control_version_num=control.row_version,
        added_by_membership_id=membership_a.id,
    )
    project_control = await project_controls_repo.create(db_session, project_control)

    pca = ProjectControlApplication(
        tenant_id=tenant_a.id,
        project_control_id=project_control.id,
        application_id=application.id,
        application_version_num=application.row_version,
        added_by_membership_id=membership_a.id,
    )
    pca = await project_control_applications_repo.create(db_session, pca)

    test_attr = TestAttribute(
        tenant_id=tenant_a.id,
        control_id=control.id,
        code="TA-001",
        name="Test Attribute",
        test_procedure="Test procedure",
        expected_evidence="Test evidence",
        created_by_membership_id=membership_a.id,
    )
    test_attr = await test_attributes_repo.create(db_session, test_attr)
    await db_session.commit()

    # Generate PBC request in tenant A
    payload = {"mode": "new", "group_mode": "single_request"}
    response = client.post(
        f"/api/v1/projects/{project.id}/pbc/generate",
        json=payload,
        headers=headers_a,
    )
    assert response.status_code == status.HTTP_201_CREATED
    result = response.json()
    pbc_request_id = result["pbc_request_id"]

    # Try to access from tenant B
    response = client.get(
        f"/api/v1/pbc/{pbc_request_id}",
        headers=headers_b,
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_replace_drafts_mode_soft_deletes_existing_drafts(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: replace_drafts mode soft-deletes prior draft requests and items."""
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

    # Create project, control, application, test attribute
    project = Project(
        tenant_id=tenant_a.id,
        name="Test Project",
        status="active",
        created_by_membership_id=membership_a.id,
    )
    project = await projects_repo.create(db_session, project)

    control = Control(
        tenant_id=tenant_a.id,
        control_code="CTL-001",
        name="Test Control",
        created_by_membership_id=membership_a.id,
    )
    control = await controls_repo.create(db_session, control)

    application = Application(
        tenant_id=tenant_a.id,
        name="Test Application",
        created_by_membership_id=membership_a.id,
    )
    application = await applications_repo.create(db_session, application)

    project_control = ProjectControl(
        tenant_id=tenant_a.id,
        project_id=project.id,
        control_id=control.id,
        control_version_num=control.row_version,
        added_by_membership_id=membership_a.id,
    )
    project_control = await project_controls_repo.create(db_session, project_control)

    pca = ProjectControlApplication(
        tenant_id=tenant_a.id,
        project_control_id=project_control.id,
        application_id=application.id,
        application_version_num=application.row_version,
        added_by_membership_id=membership_a.id,
    )
    pca = await project_control_applications_repo.create(db_session, pca)

    test_attr = TestAttribute(
        tenant_id=tenant_a.id,
        control_id=control.id,
        code="TA-001",
        name="Test Attribute",
        test_procedure="Test procedure",
        expected_evidence="Test evidence",
        created_by_membership_id=membership_a.id,
    )
    test_attr = await test_attributes_repo.create(db_session, test_attr)
    await db_session.commit()

    # Generate first PBC request (draft)
    payload = {"mode": "new", "group_mode": "single_request", "title": "First Request"}
    response = client.post(
        f"/api/v1/projects/{project.id}/pbc/generate",
        json=payload,
        headers=headers,
    )
    assert response.status_code == status.HTTP_201_CREATED
    result1 = response.json()
    first_request_id = result1["pbc_request_id"]

    # Verify first request exists and is draft
    first_request = await pbc_repo.get_request_by_id(
        db_session,
        tenant_id=tenant_a.id,
        pbc_request_id=first_request_id,
        include_deleted=False,
    )
    assert first_request is not None
    assert first_request.status == "draft"
    assert first_request.deleted_at is None

    # Generate second PBC request with replace_drafts mode
    payload = {
        "mode": "replace_drafts",
        "group_mode": "single_request",
        "title": "Second Request",
    }
    response = client.post(
        f"/api/v1/projects/{project.id}/pbc/generate",
        json=payload,
        headers=headers,
    )
    assert response.status_code == status.HTTP_201_CREATED
    result2 = response.json()
    second_request_id = result2["pbc_request_id"]

    # Verify first request is soft-deleted
    first_request_after = await pbc_repo.get_request_by_id(
        db_session,
        tenant_id=tenant_a.id,
        pbc_request_id=first_request_id,
        include_deleted=True,
    )
    assert first_request_after is not None
    assert first_request_after.deleted_at is not None
    assert first_request_after.deleted_by_membership_id == membership_a.id

    # Verify first request's items are also soft-deleted
    first_items = await pbc_repo.list_items_by_request(
        db_session,
        tenant_id=tenant_a.id,
        pbc_request_id=first_request_id,
        include_deleted=True,
    )
    assert len(first_items) > 0
    for item in first_items:
        assert item.deleted_at is not None
        assert item.deleted_by_membership_id == membership_a.id

    # Verify second request exists and is not deleted
    second_request = await pbc_repo.get_request_by_id(
        db_session,
        tenant_id=tenant_a.id,
        pbc_request_id=second_request_id,
        include_deleted=False,
    )
    assert second_request is not None
    assert second_request.deleted_at is None
    assert second_request.status == "draft"


@pytest.mark.asyncio
async def test_create_pbc_request_item_with_project_control_fk(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Create PBC request item with project_control_id FK works."""
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

    # Create project, control, application, test_attribute
    project = Project(
        tenant_id=tenant_a.id,
        name="Test Project",
        status="active",
        created_by_membership_id=membership_a.id,
    )
    db_session.add(project)
    await db_session.flush()

    control = Control(
        tenant_id=tenant_a.id,
        control_code="TC001",
        name="Test Control",
        control_type="preventive",
        created_by_membership_id=membership_a.id,
    )
    db_session.add(control)
    await db_session.flush()

    application = Application(
        tenant_id=tenant_a.id,
        name="Test App",
        application_code="TA001",
        criticality="high",
        created_by_membership_id=membership_a.id,
    )
    db_session.add(application)
    await db_session.flush()

    test_attribute = TestAttribute(
        control_id=control.id,
        name="Test Attribute",
        data_type="boolean",
        is_required=True,
        created_by_membership_id=membership_a.id,
    )
    db_session.add(test_attribute)
    await db_session.flush()

    project_control = ProjectControl(
        tenant_id=tenant_a.id,
        project_id=project.id,
        control_id=control.id,
        created_by_membership_id=membership_a.id,
        is_frozen=False,
    )
    db_session.add(project_control)
    await db_session.flush()

    # Create PBC request
    pbc_request = await pbc_repo.create_request(
        db_session,
        PbcRequest(
            tenant_id=tenant_a.id,
            project_id=project.id,
            title="Test PBC Request",
            status="draft",
            created_by_membership_id=membership_a.id,
            row_version=1,
        )
    )

    # Create PBC request item with FKs
    item_data = {
        "project_control_id": str(project_control.id),
        "application_id": str(application.id),
        "test_attribute_id": str(test_attribute.id),
        "status": "not_started",
    }

    response = client.post(
        f"/v1/pbc/{pbc_request.id}/items",
        json=item_data,
        headers=headers,
    )
    assert response.status_code == 201

    data = response.json()
    assert data["pbc_request_id"] == str(pbc_request.id)
    assert data["project_control_id"] == str(project_control.id)
    assert data["application_id"] == str(application.id)
    assert data["test_attribute_id"] == str(test_attribute.id)
    assert data["status"] == "not_started"


@pytest.mark.asyncio
async def test_create_pbc_request_item_with_control_id_alternative(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Create PBC request item with control_id (alternative to project_control_id)."""
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

    # Create project, control, application, test_attribute
    project = Project(
        tenant_id=tenant_a.id,
        name="Test Project",
        status="active",
        created_by_membership_id=membership_a.id,
    )
    db_session.add(project)
    await db_session.flush()

    control = Control(
        tenant_id=tenant_a.id,
        control_code="TC001",
        name="Test Control",
        control_type="preventive",
        created_by_membership_id=membership_a.id,
    )
    db_session.add(control)
    await db_session.flush()

    application = Application(
        tenant_id=tenant_a.id,
        name="Test App",
        application_code="TA001",
        criticality="high",
        created_by_membership_id=membership_a.id,
    )
    db_session.add(application)
    await db_session.flush()

    test_attribute = TestAttribute(
        control_id=control.id,
        name="Test Attribute",
        data_type="boolean",
        is_required=True,
        created_by_membership_id=membership_a.id,
    )
    db_session.add(test_attribute)
    await db_session.flush()

    # Create PBC request
    pbc_request = await pbc_repo.create_request(
        db_session,
        PbcRequest(
            tenant_id=tenant_a.id,
            project_id=project.id,
            title="Test PBC Request",
            status="draft",
            created_by_membership_id=membership_a.id,
            row_version=1,
        )
    )

    # Create PBC request item with control_id instead of project_control_id
    item_data = {
        "control_id": str(control.id),
        "application_id": str(application.id),
        "test_attribute_id": str(test_attribute.id),
        "status": "not_started",
    }

    response = client.post(
        f"/v1/pbc/{pbc_request.id}/items",
        json=item_data,
        headers=headers,
    )
    assert response.status_code == 201

    data = response.json()
    assert data["pbc_request_id"] == str(pbc_request.id)
    assert data["control_id"] == str(control.id)
    assert data["application_id"] == str(application.id)
    assert data["test_attribute_id"] == str(test_attribute.id)
    assert data["project_control_id"] is None  # Should be null when using control_id


@pytest.mark.asyncio
async def test_create_pbc_request_item_requires_control_reference(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Creating PBC request item requires either project_control_id or control_id."""
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

    # Create project
    project = Project(
        tenant_id=tenant_a.id,
        name="Test Project",
        status="active",
        created_by_membership_id=membership_a.id,
    )
    db_session.add(project)
    await db_session.flush()

    # Create PBC request
    pbc_request = await pbc_repo.create_request(
        db_session,
        PbcRequest(
            tenant_id=tenant_a.id,
            project_id=project.id,
            title="Test PBC Request",
            status="draft",
            created_by_membership_id=membership_a.id,
            row_version=1,
        )
    )

    # Try to create item without any control reference
    item_data = {
        "status": "not_started",
    }

    response = client.post(
        f"/v1/pbc/{pbc_request.id}/items",
        json=item_data,
        headers=headers,
    )
    assert response.status_code == 400
    assert "Either project_control_id or control_id must be provided" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_pbc_request_item_cross_tenant_rejection(
    client, tenant_a, tenant_b, user_tenant_a, db_session
):
    """Test: Cross-tenant FK references are rejected."""
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

    # Create project in tenant_a
    project_a = Project(
        tenant_id=tenant_a.id,
        name="Project A",
        status="active",
        created_by_membership_id=membership_a.id,
    )
    db_session.add(project_a)
    await db_session.flush()

    # Create control in tenant_b (cross-tenant)
    control_b = Control(
        tenant_id=tenant_b.id,
        control_code="TB001",
        name="Tenant B Control",
        control_type="preventive",
        created_by_membership_id=membership_a.id,  # This won't work in real scenario
    )
    db_session.add(control_b)
    await db_session.flush()

    # Create PBC request in tenant_a
    pbc_request = await pbc_repo.create_request(
        db_session,
        PbcRequest(
            tenant_id=tenant_a.id,
            project_id=project_a.id,
            title="Test PBC Request",
            status="draft",
            created_by_membership_id=membership_a.id,
            row_version=1,
        )
    )

    # Try to create item with cross-tenant control reference
    item_data = {
        "control_id": str(control_b.id),
        "status": "not_started",
    }

    response = client.post(
        f"/v1/pbc/{pbc_request.id}/items",
        json=item_data,
        headers=headers,
    )
    assert response.status_code == 404
    assert "Control not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_pbc_request_item_wrong_project_rejection(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: project_control_id from different project than PBC request is rejected."""
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

    # Create two projects
    project_a = Project(
        tenant_id=tenant_a.id,
        name="Project A",
        status="active",
        created_by_membership_id=membership_a.id,
    )
    db_session.add(project_a)

    project_b = Project(
        tenant_id=tenant_a.id,
        name="Project B",
        status="active",
        created_by_membership_id=membership_a.id,
    )
    db_session.add(project_b)
    await db_session.flush()

    # Create control
    control = Control(
        tenant_id=tenant_a.id,
        control_code="TC001",
        name="Test Control",
        control_type="preventive",
        created_by_membership_id=membership_a.id,
    )
    db_session.add(control)
    await db_session.flush()

    # Create project_control for project_b
    project_control_b = ProjectControl(
        tenant_id=tenant_a.id,
        project_id=project_b.id,  # Different project
        control_id=control.id,
        created_by_membership_id=membership_a.id,
        is_frozen=False,
    )
    db_session.add(project_control_b)
    await db_session.flush()

    # Create PBC request for project_a
    pbc_request_a = await pbc_repo.create_request(
        db_session,
        PbcRequest(
            tenant_id=tenant_a.id,
            project_id=project_a.id,  # This project
            title="PBC Request A",
            status="draft",
            created_by_membership_id=membership_a.id,
            row_version=1,
        )
    )

    # Try to create item with project_control from different project
    item_data = {
        "project_control_id": str(project_control_b.id),
        "status": "not_started",
    }

    response = client.post(
        f"/v1/pbc/{pbc_request_a.id}/items",
        json=item_data,
        headers=headers,
    )
    assert response.status_code == 400
    assert "must belong to the same project" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_pbc_request_item_test_attribute_validation(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: test_attribute_id must belong to the referenced control."""
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

    # Create project
    project = Project(
        tenant_id=tenant_a.id,
        name="Test Project",
        status="active",
        created_by_membership_id=membership_a.id,
    )
    db_session.add(project)
    await db_session.flush()

    # Create two controls
    control_a = Control(
        tenant_id=tenant_a.id,
        control_code="TCA",
        name="Control A",
        control_type="preventive",
        created_by_membership_id=membership_a.id,
    )
    db_session.add(control_a)

    control_b = Control(
        tenant_id=tenant_a.id,
        control_code="TCB",
        name="Control B",
        control_type="preventive",
        created_by_membership_id=membership_a.id,
    )
    db_session.add(control_b)
    await db_session.flush()

    # Create test attribute for control_b
    test_attribute_b = TestAttribute(
        control_id=control_b.id,  # Belongs to control_b
        name="Test Attribute B",
        data_type="boolean",
        is_required=True,
        created_by_membership_id=membership_a.id,
    )
    db_session.add(test_attribute_b)
    await db_session.flush()

    # Create PBC request
    pbc_request = await pbc_repo.create_request(
        db_session,
        PbcRequest(
            tenant_id=tenant_a.id,
            project_id=project.id,
            title="Test PBC Request",
            status="draft",
            created_by_membership_id=membership_a.id,
            row_version=1,
        )
    )

    # Try to create item with control_a but test_attribute from control_b
    item_data = {
        "control_id": str(control_a.id),
        "test_attribute_id": str(test_attribute_b.id),  # Wrong control
        "status": "not_started",
    }

    response = client.post(
        f"/v1/pbc/{pbc_request.id}/items",
        json=item_data,
        headers=headers,
    )
    assert response.status_code == 400
    assert "must belong to the referenced control" in response.json()["detail"]
