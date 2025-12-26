"""Integration tests for PBC evidence upload endpoints."""

import io
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
from repos import (
    applications_repo,
    controls_repo,
    project_control_applications_repo,
    project_controls_repo,
    projects_repo,
    test_attributes_repo,
    pbc_repo,
)


@pytest.mark.asyncio
async def test_upload_evidence_files(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Upload 2 files and verify they are linked to PBC request."""
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

    # Create control, application, test attribute
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

    # Upload 2 files
    file1_content = b"Test file 1 content"
    file2_content = b"Test file 2 content"
    
    files = [
        ("files", ("test1.txt", io.BytesIO(file1_content), "text/plain")),
        ("files", ("test2.txt", io.BytesIO(file2_content), "text/plain")),
    ]
    
    response = client.post(
        f"/api/v1/pbc/{pbc_request_id}/evidence/upload",
        files=files,
        headers=headers,
    )
    assert response.status_code == status.HTTP_201_CREATED
    result = response.json()
    
    assert "artifact" in result
    assert "files" in result
    assert "linked_count" in result
    assert result["linked_count"] == 2
    assert len(result["files"]) == 2
    
    artifact = result["artifact"]
    assert artifact["tenant_id"] == str(tenant_a.id)
    assert artifact["project_id"] == str(project.id)
    assert artifact["source"] == "manual"
    
    uploaded_files = result["files"]
    assert uploaded_files[0]["filename"] in ["test1.txt", "test2.txt"]
    assert uploaded_files[1]["filename"] in ["test1.txt", "test2.txt"]
    assert uploaded_files[0]["filename"] != uploaded_files[1]["filename"]
    assert uploaded_files[0]["size_bytes"] == len(file1_content) or uploaded_files[0]["size_bytes"] == len(file2_content)
    assert uploaded_files[0]["artifact_id"] == artifact["id"]
    assert uploaded_files[0]["sha256"] is not None


@pytest.mark.asyncio
async def test_list_evidence_files(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: List evidence files for a PBC request."""
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

    # Create project and PBC request (reuse setup from previous test)
    project = Project(
        tenant_id=tenant_a.id,
        name="Test Project",
        status="active",
        created_by_membership_id=membership_a.id,
    )
    project = await projects_repo.create(db_session, project)
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
    pbc_request_id = response.json()["pbc_request_id"]

    # Upload 2 files
    files = [
        ("files", ("test1.txt", io.BytesIO(b"content1"), "text/plain")),
        ("files", ("test2.txt", io.BytesIO(b"content2"), "text/plain")),
    ]
    response = client.post(
        f"/api/v1/pbc/{pbc_request_id}/evidence/upload",
        files=files,
        headers=headers,
    )
    assert response.status_code == status.HTTP_201_CREATED

    # List evidence files
    response = client.get(
        f"/api/v1/pbc/{pbc_request_id}/evidence",
        headers=headers,
    )
    assert response.status_code == status.HTTP_200_OK
    files_list = response.json()
    assert len(files_list) == 2
    assert all("id" in f for f in files_list)
    assert all("filename" in f for f in files_list)
    assert all("artifact_id" in f for f in files_list)


@pytest.mark.asyncio
async def test_unlink_evidence_file(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Unlink an evidence file from a PBC request."""
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

    # Create project and PBC request
    project = Project(
        tenant_id=tenant_a.id,
        name="Test Project",
        status="active",
        created_by_membership_id=membership_a.id,
    )
    project = await projects_repo.create(db_session, project)
    await db_session.commit()

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
    pbc_request_id = response.json()["pbc_request_id"]

    # Upload 2 files
    files = [
        ("files", ("test1.txt", io.BytesIO(b"content1"), "text/plain")),
        ("files", ("test2.txt", io.BytesIO(b"content2"), "text/plain")),
    ]
    response = client.post(
        f"/api/v1/pbc/{pbc_request_id}/evidence/upload",
        files=files,
        headers=headers,
    )
    assert response.status_code == status.HTTP_201_CREATED
    uploaded_files = response.json()["files"]
    evidence_file_id = uploaded_files[0]["id"]

    # Verify 2 files are linked
    response = client.get(
        f"/api/v1/pbc/{pbc_request_id}/evidence",
        headers=headers,
    )
    assert len(response.json()) == 2

    # Unlink one file
    response = client.delete(
        f"/api/v1/pbc/{pbc_request_id}/evidence/{evidence_file_id}",
        headers=headers,
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify only 1 file remains linked
    response = client.get(
        f"/api/v1/pbc/{pbc_request_id}/evidence",
        headers=headers,
    )
    assert len(response.json()) == 1
    assert response.json()[0]["id"] != evidence_file_id


@pytest.mark.asyncio
async def test_evidence_tenant_isolation(
    client, tenant_a, tenant_b, user_tenant_a, user_tenant_b, db_session
):
    """Test: Different tenant cannot access evidence files."""
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

    # Create project and PBC request in tenant A
    project = Project(
        tenant_id=tenant_a.id,
        name="Test Project",
        status="active",
        created_by_membership_id=membership_a.id,
    )
    project = await projects_repo.create(db_session, project)
    await db_session.commit()

    payload = {
        "mode": "new",
        "group_mode": "single_request",
        "title": "Test PBC Request",
    }
    response = client.post(
        f"/api/v1/projects/{project.id}/pbc/generate",
        json=payload,
        headers=headers_a,
    )
    pbc_request_id = response.json()["pbc_request_id"]

    # Upload file in tenant A
    files = [
        ("files", ("test1.txt", io.BytesIO(b"content1"), "text/plain")),
    ]
    response = client.post(
        f"/api/v1/pbc/{pbc_request_id}/evidence/upload",
        files=files,
        headers=headers_a,
    )
    assert response.status_code == status.HTTP_201_CREATED
    evidence_file_id = response.json()["files"][0]["id"]

    # Try to access from tenant B
    response = client.get(
        f"/api/v1/pbc/{pbc_request_id}/evidence",
        headers=headers_b,
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

    # Try to unlink from tenant B
    response = client.delete(
        f"/api/v1/pbc/{pbc_request_id}/evidence/{evidence_file_id}",
        headers=headers_b,
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_upload_same_file_twice_creates_two_files(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Uploading the same file twice creates two separate file records."""
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

    # Create project and PBC request
    project = Project(
        tenant_id=tenant_a.id,
        name="Test Project",
        status="active",
        created_by_membership_id=membership_a.id,
    )
    project = await projects_repo.create(db_session, project)
    await db_session.commit()

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
    pbc_request_id = response.json()["pbc_request_id"]

    # Upload same file twice
    file_content = b"same content"
    files1 = [
        ("files", ("test.txt", io.BytesIO(file_content), "text/plain")),
    ]
    response1 = client.post(
        f"/api/v1/pbc/{pbc_request_id}/evidence/upload",
        files=files1,
        headers=headers,
    )
    assert response1.status_code == status.HTTP_201_CREATED
    file1_id = response1.json()["files"][0]["id"]

    files2 = [
        ("files", ("test.txt", io.BytesIO(file_content), "text/plain")),
    ]
    response2 = client.post(
        f"/api/v1/pbc/{pbc_request_id}/evidence/upload",
        files=files2,
        headers=headers,
    )
    assert response2.status_code == status.HTTP_201_CREATED
    file2_id = response2.json()["files"][0]["id"]

    # Verify two separate files were created
    assert file1_id != file2_id

    # Verify both are linked
    response = client.get(
        f"/api/v1/pbc/{pbc_request_id}/evidence",
        headers=headers,
    )
    files_list = response.json()
    assert len(files_list) == 2
    file_ids = [f["id"] for f in files_list]
    assert file1_id in file_ids
    assert file2_id in file_ids

