"""Integration tests for evidence files endpoints."""

from uuid import uuid4

import pytest
from fastapi import status

from auth.jwt import create_dev_token


@pytest.mark.asyncio
async def test_create_evidence_file_success(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Creating an evidence file succeeds."""
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
    
    # Create project, application, control
    project_response = client.post(
        "/api/v1/projects",
        json={"name": "Test Project", "status": "active"},
        headers=headers,
    )
    project_id = project_response.json()["id"]
    
    app_response = client.post(
        "/api/v1/applications",
        json={"name": "Test Application"},
        headers=headers,
    )
    application_id = app_response.json()["id"]
    
    control_response = client.post(
        "/api/v1/controls",
        json={"control_code": "EV-001", "name": "Test Control", "is_key": False, "is_automated": False},
        headers=headers,
    )
    control_id = control_response.json()["id"]
    
    # Create PBC request
    pbc_data = {
        "project_id": project_id,
        "application_id": application_id,
        "control_id": control_id,
        "owner_membership_id": str(membership_a.id),
        "title": "Test PBC Request",
    }
    pbc_response = client.post("/api/v1/pbc-requests", json=pbc_data, headers=headers)
    pbc_request_id = pbc_response.json()["id"]
    
    # Create evidence file
    evidence_data = {
        "pbc_request_id": pbc_request_id,
        "filename": "evidence.pdf",
        "mime_type": "application/pdf",
        "storage_uri": "s3://bucket/evidence.pdf",
        "content_hash": "abc123hash",
        "version": 1,
        "page_count": 10,
    }
    
    response = client.post("/api/v1/evidence-files", json=evidence_data, headers=headers)
    
    assert response.status_code == status.HTTP_201_CREATED
    
    evidence_file = response.json()
    assert evidence_file["filename"] == "evidence.pdf"
    assert evidence_file["mime_type"] == "application/pdf"
    assert evidence_file["storage_uri"] == "s3://bucket/evidence.pdf"
    assert evidence_file["content_hash"] == "abc123hash"
    assert evidence_file["version"] == 1
    assert evidence_file["page_count"] == 10
    assert evidence_file["pbc_request_id"] == pbc_request_id
    assert evidence_file["sample_id"] is None
    assert evidence_file["supersedes_file_id"] is None
    assert evidence_file["tenant_id"] == str(tenant_a.id)
    assert evidence_file["uploaded_by_membership_id"] == str(membership_a.id)
    assert "id" in evidence_file
    assert "uploaded_at" in evidence_file


@pytest.mark.asyncio
async def test_create_evidence_file_minimal_fields(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Creating evidence file with minimal fields succeeds."""
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
    
    # Create dependencies
    project_response = client.post(
        "/api/v1/projects",
        json={"name": "Test Project 2", "status": "active"},
        headers=headers,
    )
    project_id = project_response.json()["id"]
    
    app_response = client.post(
        "/api/v1/applications",
        json={"name": "Test Application 2"},
        headers=headers,
    )
    application_id = app_response.json()["id"]
    
    control_response = client.post(
        "/api/v1/controls",
        json={"control_code": "EV-002", "name": "Test Control 2", "is_key": False, "is_automated": False},
        headers=headers,
    )
    control_id = control_response.json()["id"]
    
    pbc_data = {
        "project_id": project_id,
        "application_id": application_id,
        "control_id": control_id,
        "owner_membership_id": str(membership_a.id),
        "title": "Test PBC Request 2",
    }
    pbc_response = client.post("/api/v1/pbc-requests", json=pbc_data, headers=headers)
    pbc_request_id = pbc_response.json()["id"]
    
    # Create evidence file with minimal fields
    evidence_data = {
        "pbc_request_id": pbc_request_id,
        "filename": "minimal.txt",
        "mime_type": "text/plain",
        "storage_uri": "s3://bucket/minimal.txt",
        "content_hash": "minimalhash",
    }
    
    response = client.post("/api/v1/evidence-files", json=evidence_data, headers=headers)
    
    assert response.status_code == status.HTTP_201_CREATED
    evidence_file = response.json()
    assert evidence_file["version"] == 1
    assert evidence_file["page_count"] is None
    assert evidence_file["supersedes_file_id"] is None


@pytest.mark.asyncio
async def test_list_pbc_request_evidence_files(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Listing evidence files for a PBC request returns all files."""
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
    
    # Create dependencies
    project_response = client.post(
        "/api/v1/projects",
        json={"name": "Test Project List", "status": "active"},
        headers=headers,
    )
    project_id = project_response.json()["id"]
    
    app_response = client.post(
        "/api/v1/applications",
        json={"name": "Test Application List"},
        headers=headers,
    )
    application_id = app_response.json()["id"]
    
    control_response = client.post(
        "/api/v1/controls",
        json={"control_code": "EV-003", "name": "Test Control List", "is_key": False, "is_automated": False},
        headers=headers,
    )
    control_id = control_response.json()["id"]
    
    pbc_data = {
        "project_id": project_id,
        "application_id": application_id,
        "control_id": control_id,
        "owner_membership_id": str(membership_a.id),
        "title": "Test PBC Request List",
    }
    pbc_response = client.post("/api/v1/pbc-requests", json=pbc_data, headers=headers)
    pbc_request_id = pbc_response.json()["id"]
    
    # Create multiple evidence files
    for i in range(3):
        evidence_data = {
            "pbc_request_id": pbc_request_id,
            "filename": f"file_{i}.pdf",
            "mime_type": "application/pdf",
            "storage_uri": f"s3://bucket/file_{i}.pdf",
            "content_hash": f"hash{i}",
        }
        client.post("/api/v1/evidence-files", json=evidence_data, headers=headers)
    
    # List evidence files
    response = client.get(
        f"/api/v1/pbc-requests/{pbc_request_id}/evidence-files",
        headers=headers,
    )
    
    assert response.status_code == status.HTTP_200_OK
    files = response.json()
    assert len(files) == 3
    filenames = [f["filename"] for f in files]
    assert "file_0.pdf" in filenames
    assert "file_1.pdf" in filenames
    assert "file_2.pdf" in filenames


@pytest.mark.asyncio
async def test_list_all_evidence_files(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Listing all evidence files returns tenant's files."""
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
    
    # Create dependencies
    project_response = client.post(
        "/api/v1/projects",
        json={"name": "Test Project All", "status": "active"},
        headers=headers,
    )
    project_id = project_response.json()["id"]
    
    app_response = client.post(
        "/api/v1/applications",
        json={"name": "Test Application All"},
        headers=headers,
    )
    application_id = app_response.json()["id"]
    
    control_response = client.post(
        "/api/v1/controls",
        json={"control_code": "EV-004", "name": "Test Control All", "is_key": False, "is_automated": False},
        headers=headers,
    )
    control_id = control_response.json()["id"]
    
    pbc_data = {
        "project_id": project_id,
        "application_id": application_id,
        "control_id": control_id,
        "owner_membership_id": str(membership_a.id),
        "title": "Test PBC Request All",
    }
    pbc_response = client.post("/api/v1/pbc-requests", json=pbc_data, headers=headers)
    pbc_request_id = pbc_response.json()["id"]
    
    # Create evidence files
    evidence_data = {
        "pbc_request_id": pbc_request_id,
        "filename": "all_test.pdf",
        "mime_type": "application/pdf",
        "storage_uri": "s3://bucket/all_test.pdf",
        "content_hash": "allhash",
    }
    client.post("/api/v1/evidence-files", json=evidence_data, headers=headers)
    
    # List all evidence files
    response = client.get("/api/v1/evidence-files", headers=headers)
    
    assert response.status_code == status.HTTP_200_OK
    files = response.json()
    assert len(files) >= 1


@pytest.mark.asyncio
async def test_get_evidence_file(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Getting a specific evidence file succeeds."""
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
    
    # Create dependencies
    project_response = client.post(
        "/api/v1/projects",
        json={"name": "Test Project Get", "status": "active"},
        headers=headers,
    )
    project_id = project_response.json()["id"]
    
    app_response = client.post(
        "/api/v1/applications",
        json={"name": "Test Application Get"},
        headers=headers,
    )
    application_id = app_response.json()["id"]
    
    control_response = client.post(
        "/api/v1/controls",
        json={"control_code": "EV-005", "name": "Test Control Get", "is_key": False, "is_automated": False},
        headers=headers,
    )
    control_id = control_response.json()["id"]
    
    pbc_data = {
        "project_id": project_id,
        "application_id": application_id,
        "control_id": control_id,
        "owner_membership_id": str(membership_a.id),
        "title": "Test PBC Request Get",
    }
    pbc_response = client.post("/api/v1/pbc-requests", json=pbc_data, headers=headers)
    pbc_request_id = pbc_response.json()["id"]
    
    # Create evidence file
    evidence_data = {
        "pbc_request_id": pbc_request_id,
        "filename": "get_test.pdf",
        "mime_type": "application/pdf",
        "storage_uri": "s3://bucket/get_test.pdf",
        "content_hash": "gethash",
    }
    create_response = client.post("/api/v1/evidence-files", json=evidence_data, headers=headers)
    evidence_file_id = create_response.json()["id"]
    
    # Get evidence file
    response = client.get(f"/api/v1/evidence-files/{evidence_file_id}", headers=headers)
    
    assert response.status_code == status.HTTP_200_OK
    evidence_file = response.json()
    assert evidence_file["id"] == evidence_file_id
    assert evidence_file["filename"] == "get_test.pdf"


@pytest.mark.asyncio
async def test_update_evidence_file(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Updating evidence file metadata succeeds."""
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
    
    # Create dependencies
    project_response = client.post(
        "/api/v1/projects",
        json={"name": "Test Project Update", "status": "active"},
        headers=headers,
    )
    project_id = project_response.json()["id"]
    
    app_response = client.post(
        "/api/v1/applications",
        json={"name": "Test Application Update"},
        headers=headers,
    )
    application_id = app_response.json()["id"]
    
    control_response = client.post(
        "/api/v1/controls",
        json={"control_code": "EV-006", "name": "Test Control Update", "is_key": False, "is_automated": False},
        headers=headers,
    )
    control_id = control_response.json()["id"]
    
    pbc_data = {
        "project_id": project_id,
        "application_id": application_id,
        "control_id": control_id,
        "owner_membership_id": str(membership_a.id),
        "title": "Test PBC Request Update",
    }
    pbc_response = client.post("/api/v1/pbc-requests", json=pbc_data, headers=headers)
    pbc_request_id = pbc_response.json()["id"]
    
    # Create evidence file
    evidence_data = {
        "pbc_request_id": pbc_request_id,
        "filename": "original.pdf",
        "mime_type": "application/pdf",
        "storage_uri": "s3://bucket/original.pdf",
        "content_hash": "originalhash",
    }
    create_response = client.post("/api/v1/evidence-files", json=evidence_data, headers=headers)
    evidence_file_id = create_response.json()["id"]
    
    # Update evidence file
    update_data = {
        "filename": "updated.pdf",
        "page_count": 25,
    }
    
    response = client.put(f"/api/v1/evidence-files/{evidence_file_id}", json=update_data, headers=headers)
    
    assert response.status_code == status.HTTP_200_OK
    updated = response.json()
    assert updated["filename"] == "updated.pdf"
    assert updated["page_count"] == 25
    # Immutable fields should not change
    assert updated["storage_uri"] == "s3://bucket/original.pdf"
    assert updated["content_hash"] == "originalhash"


@pytest.mark.asyncio
async def test_delete_evidence_file(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Deleting an evidence file succeeds."""
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
    
    # Create dependencies
    project_response = client.post(
        "/api/v1/projects",
        json={"name": "Test Project Delete", "status": "active"},
        headers=headers,
    )
    project_id = project_response.json()["id"]
    
    app_response = client.post(
        "/api/v1/applications",
        json={"name": "Test Application Delete"},
        headers=headers,
    )
    application_id = app_response.json()["id"]
    
    control_response = client.post(
        "/api/v1/controls",
        json={"control_code": "EV-007", "name": "Test Control Delete", "is_key": False, "is_automated": False},
        headers=headers,
    )
    control_id = control_response.json()["id"]
    
    pbc_data = {
        "project_id": project_id,
        "application_id": application_id,
        "control_id": control_id,
        "owner_membership_id": str(membership_a.id),
        "title": "Test PBC Request Delete",
    }
    pbc_response = client.post("/api/v1/pbc-requests", json=pbc_data, headers=headers)
    pbc_request_id = pbc_response.json()["id"]
    
    # Create evidence file
    evidence_data = {
        "pbc_request_id": pbc_request_id,
        "filename": "delete_test.pdf",
        "mime_type": "application/pdf",
        "storage_uri": "s3://bucket/delete_test.pdf",
        "content_hash": "deletehash",
    }
    create_response = client.post("/api/v1/evidence-files", json=evidence_data, headers=headers)
    evidence_file_id = create_response.json()["id"]
    
    # Delete evidence file
    response = client.delete(f"/api/v1/evidence-files/{evidence_file_id}", headers=headers)
    
    assert response.status_code == status.HTTP_204_NO_CONTENT
    
    # Verify it's deleted
    get_response = client.get(f"/api/v1/evidence-files/{evidence_file_id}", headers=headers)
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_cannot_create_evidence_file_for_nonexistent_pbc_request(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Cannot create evidence file for non-existent PBC request."""
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
    
    fake_pbc_id = str(uuid4())
    
    evidence_data = {
        "pbc_request_id": fake_pbc_id,
        "filename": "test.pdf",
        "mime_type": "application/pdf",
        "storage_uri": "s3://bucket/test.pdf",
        "content_hash": "testhash",
    }
    
    response = client.post("/api/v1/evidence-files", json=evidence_data, headers=headers)
    
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "PBC request not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_tenant_isolation_evidence_files(
    client, tenant_a, tenant_b, user_tenant_a, user_tenant_b, db_session
):
    """Test: Tenant A cannot access Tenant B's evidence files."""
    user_a, membership_a = user_tenant_a
    user_b, membership_b = user_tenant_b
    
    # User A creates evidence file in Tenant A
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
    
    # Create dependencies in Tenant A
    project_response = client.post(
        "/api/v1/projects",
        json={"name": "Tenant A Project", "status": "active"},
        headers=headers_a,
    )
    project_id = project_response.json()["id"]
    
    app_response = client.post(
        "/api/v1/applications",
        json={"name": "Tenant A App"},
        headers=headers_a,
    )
    application_id = app_response.json()["id"]
    
    control_response = client.post(
        "/api/v1/controls",
        json={"control_code": "EV-008", "name": "Tenant A Control", "is_key": False, "is_automated": False},
        headers=headers_a,
    )
    control_id = control_response.json()["id"]
    
    pbc_data = {
        "project_id": project_id,
        "application_id": application_id,
        "control_id": control_id,
        "owner_membership_id": str(membership_a.id),
        "title": "Tenant A PBC",
    }
    pbc_response = client.post("/api/v1/pbc-requests", json=pbc_data, headers=headers_a)
    pbc_request_id = pbc_response.json()["id"]
    
    # Create evidence file
    evidence_data = {
        "pbc_request_id": pbc_request_id,
        "filename": "tenant_a_file.pdf",
        "mime_type": "application/pdf",
        "storage_uri": "s3://bucket/tenant_a_file.pdf",
        "content_hash": "ahash",
    }
    file_response = client.post("/api/v1/evidence-files", json=evidence_data, headers=headers_a)
    file_a_id = file_response.json()["id"]
    
    # User B tries to access Tenant A's evidence file
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
    
    # Should return 404 (file not found in Tenant B)
    response = client.get(f"/api/v1/evidence-files/{file_a_id}", headers=headers_b)
    
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_nonexistent_evidence_file(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Getting a non-existent evidence file returns 404."""
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
    
    fake_id = str(uuid4())
    response = client.get(f"/api/v1/evidence-files/{fake_id}", headers=headers)
    
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Evidence file not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_evidence_file_versioning(
    client, tenant_a, user_tenant_a, db_session
):
    """Test: Creating versioned evidence files with supersedes_file_id."""
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
    
    # Create dependencies
    project_response = client.post(
        "/api/v1/projects",
        json={"name": "Test Project Version", "status": "active"},
        headers=headers,
    )
    project_id = project_response.json()["id"]
    
    app_response = client.post(
        "/api/v1/applications",
        json={"name": "Test Application Version"},
        headers=headers,
    )
    application_id = app_response.json()["id"]
    
    control_response = client.post(
        "/api/v1/controls",
        json={"control_code": "EV-009", "name": "Test Control Version", "is_key": False, "is_automated": False},
        headers=headers,
    )
    control_id = control_response.json()["id"]
    
    pbc_data = {
        "project_id": project_id,
        "application_id": application_id,
        "control_id": control_id,
        "owner_membership_id": str(membership_a.id),
        "title": "Test PBC Request Version",
    }
    pbc_response = client.post("/api/v1/pbc-requests", json=pbc_data, headers=headers)
    pbc_request_id = pbc_response.json()["id"]
    
    # Create v1
    v1_data = {
        "pbc_request_id": pbc_request_id,
        "filename": "doc_v1.pdf",
        "mime_type": "application/pdf",
        "storage_uri": "s3://bucket/doc_v1.pdf",
        "content_hash": "v1hash",
        "version": 1,
    }
    v1_response = client.post("/api/v1/evidence-files", json=v1_data, headers=headers)
    v1_id = v1_response.json()["id"]
    
    # Create v2 that supersedes v1
    v2_data = {
        "pbc_request_id": pbc_request_id,
        "filename": "doc_v2.pdf",
        "mime_type": "application/pdf",
        "storage_uri": "s3://bucket/doc_v2.pdf",
        "content_hash": "v2hash",
        "version": 2,
        "supersedes_file_id": v1_id,
    }
    v2_response = client.post("/api/v1/evidence-files", json=v2_data, headers=headers)
    
    assert v2_response.status_code == status.HTTP_201_CREATED
    v2 = v2_response.json()
    assert v2["version"] == 2
    assert v2["supersedes_file_id"] == v1_id
