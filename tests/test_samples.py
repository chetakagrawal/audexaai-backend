"""
Integration tests for Samples API endpoints.

Tests CRUD operations, tenant isolation, and access control.
"""

import pytest
from datetime import datetime
from uuid import uuid4

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.jwt import create_dev_token
from models.project import Project
from models.application import Application
from models.control import Control
from models.pbc_request import PbcRequest
from models.sample import Sample


@pytest.mark.asyncio
async def test_create_sample_success(
    client, tenant_a, user_tenant_a, db_session
):
    """Test successful sample creation"""
    # Setup project, application, control
    user_a, membership_a = user_tenant_a

    project = Project(
        id=uuid4(),
        tenant_id=tenant_a.id,
        created_by_membership_id=membership_a.id,
        name="Test Project",
        status="active",
    )
    db_session.add(project)
    await db_session.flush()

    application = Application(
        id=uuid4(),
        tenant_id=tenant_a.id,
        name="Test App",
        category="Web Application",
    )
    db_session.add(application)
    await db_session.flush()

    control = Control(
        id=uuid4(),
        tenant_id=tenant_a.id,
        created_by_membership_id=membership_a.id,
        control_code="AC-001",
        name="Access Control",
        is_key=True,
        is_automated=False,
    )
    db_session.add(control)
    await db_session.flush()

    pbc_request = PbcRequest(
        id=uuid4(),
        tenant_id=tenant_a.id,
        project_id=project.id,
        application_id=application.id,
        control_id=control.id,
        owner_membership_id=membership_a.id,
        title="Request Access Logs",
        status="pending",
    )
    db_session.add(pbc_request)
    await db_session.commit()

    project_id = str(project.id)
    application_id = str(application.id)
    control_id = str(control.id)
    pbc_request_id = str(pbc_request.id)

    # Create auth token
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

    # Create sample
    sample_data = {
        "pbc_request_id": pbc_request_id,
        "sample_number": 1,
        "identifier": "TXN-2025-001",
        "description": "User login transaction",
        "status": "pending",
    }

    response = client.post(
        "/api/v1/samples",
        json=sample_data,
        headers=headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    sample = response.json()
    assert sample["pbc_request_id"] == pbc_request_id
    assert sample["sample_number"] == 1
    assert sample["identifier"] == "TXN-2025-001"
    assert sample["description"] == "User login transaction"
    assert sample["status"] == "pending"
    assert sample["tenant_id"] == str(tenant_a.id)


@pytest.mark.asyncio
async def test_create_sample_with_tested_info(
    client, tenant_a, user_tenant_a, db_session
):
    """Test creating sample with testing information"""
    # Setup project, application, control
    user_a, membership_a = user_tenant_a

    project = Project(
        id=uuid4(),
        tenant_id=tenant_a.id,
        created_by_membership_id=membership_a.id,
        name="Test Project",
        status="active",
    )
    db_session.add(project)
    await db_session.flush()

    application = Application(
        id=uuid4(),
        tenant_id=tenant_a.id,
        name="Test App",
        category="Web Application",
    )
    db_session.add(application)
    await db_session.flush()

    control = Control(
        id=uuid4(),
        tenant_id=tenant_a.id,
        created_by_membership_id=membership_a.id,
        control_code="AC-001",
        name="Access Control",
        is_key=True,
        is_automated=False,
    )
    db_session.add(control)
    await db_session.flush()

    pbc_request = PbcRequest(
        id=uuid4(),
        tenant_id=tenant_a.id,
        project_id=project.id,
        application_id=application.id,
        control_id=control.id,
        owner_membership_id=membership_a.id,
        title="Request Access Logs",
        status="pending",
    )
    db_session.add(pbc_request)
    await db_session.commit()

    pbc_request_id = str(pbc_request.id)

    # Create auth token
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

    # Create sample with tested information
    tested_at = datetime.utcnow().isoformat()
    sample_data = {
        "pbc_request_id": pbc_request_id,
        "sample_number": 1,
        "identifier": "TXN-2025-001",
        "status": "tested",
        "test_notes": "Verified access controls",
        "tested_at": tested_at,
        "tested_by_membership_id": str(membership_a.id),
    }

    response = client.post(
        "/api/v1/samples",
        json=sample_data,
        headers=headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    sample = response.json()
    assert sample["status"] == "tested"
    assert sample["test_notes"] == "Verified access controls"
    assert sample["tested_by_membership_id"] == str(membership_a.id)


@pytest.mark.asyncio
async def test_list_samples(client, tenant_a, user_tenant_a, db_session):
    """Test listing all samples"""
    # Setup project, application, control
    user_a, membership_a = user_tenant_a

    project = Project(
        id=uuid4(),
        tenant_id=tenant_a.id,
        created_by_membership_id=membership_a.id,
        name="Test Project",
        status="active",
    )
    db_session.add(project)
    await db_session.flush()

    application = Application(
        id=uuid4(),
        tenant_id=tenant_a.id,
        name="Test App",
        category="Web Application",
    )
    db_session.add(application)
    await db_session.flush()

    control = Control(
        id=uuid4(),
        tenant_id=tenant_a.id,
        created_by_membership_id=membership_a.id,
        control_code="AC-001",
        name="Access Control",
        is_key=True,
        is_automated=False,
    )
    db_session.add(control)
    await db_session.flush()

    pbc_request = PbcRequest(
        id=uuid4(),
        tenant_id=tenant_a.id,
        project_id=project.id,
        application_id=application.id,
        control_id=control.id,
        owner_membership_id=membership_a.id,
        title="Request Access Logs",
        status="pending",
    )
    db_session.add(pbc_request)
    await db_session.flush()

    # Create samples
    sample1 = Sample(
        id=uuid4(),
        tenant_id=tenant_a.id,
        pbc_request_id=pbc_request.id,
        sample_number=1,
        identifier="TXN-001",
    )
    sample2 = Sample(
        id=uuid4(),
        tenant_id=tenant_a.id,
        pbc_request_id=pbc_request.id,
        sample_number=2,
        identifier="TXN-002",
    )
    db_session.add_all([sample1, sample2])
    await db_session.commit()

    # Create auth token
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

    # List samples
    response = client.get("/api/v1/samples", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    samples = response.json()
    assert len(samples) == 2


@pytest.mark.asyncio
async def test_list_pbc_request_samples(
    client, tenant_a, user_tenant_a, db_session
):
    """Test listing samples for a specific PBC request"""
    # Setup project, application, control
    user_a, membership_a = user_tenant_a

    project = Project(
        id=uuid4(),
        tenant_id=tenant_a.id,
        created_by_membership_id=membership_a.id,
        name="Test Project",
        status="active",
    )
    db_session.add(project)
    await db_session.flush()

    application = Application(
        id=uuid4(),
        tenant_id=tenant_a.id,
        name="Test App",
        category="Web Application",
    )
    db_session.add(application)
    await db_session.flush()

    control = Control(
        id=uuid4(),
        tenant_id=tenant_a.id,
        created_by_membership_id=membership_a.id,
        control_code="AC-001",
        name="Access Control",
        is_key=True,
        is_automated=False,
    )
    db_session.add(control)
    await db_session.flush()

    pbc_request1 = PbcRequest(
        id=uuid4(),
        tenant_id=tenant_a.id,
        project_id=project.id,
        application_id=application.id,
        control_id=control.id,
        owner_membership_id=membership_a.id,
        title="Request 1",
        status="pending",
    )
    pbc_request2 = PbcRequest(
        id=uuid4(),
        tenant_id=tenant_a.id,
        project_id=project.id,
        application_id=application.id,
        control_id=control.id,
        owner_membership_id=membership_a.id,
        title="Request 2",
        status="pending",
    )
    db_session.add_all([pbc_request1, pbc_request2])
    await db_session.flush()

    # Create samples for each PBC request
    sample1 = Sample(
        id=uuid4(),
        tenant_id=tenant_a.id,
        pbc_request_id=pbc_request1.id,
        sample_number=1,
        identifier="TXN-001",
    )
    sample2 = Sample(
        id=uuid4(),
        tenant_id=tenant_a.id,
        pbc_request_id=pbc_request1.id,
        sample_number=2,
        identifier="TXN-002",
    )
    sample3 = Sample(
        id=uuid4(),
        tenant_id=tenant_a.id,
        pbc_request_id=pbc_request2.id,
        sample_number=1,
        identifier="TXN-003",
    )
    db_session.add_all([sample1, sample2, sample3])
    await db_session.commit()

    pbc_request1_id = str(pbc_request1.id)

    # Create auth token
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

    # List samples for pbc_request1
    response = client.get(
        f"/api/v1/pbc-requests/{pbc_request1_id}/samples",
        headers=headers,
    )
    assert response.status_code == status.HTTP_200_OK
    samples = response.json()
    assert len(samples) == 2
    assert all(s["pbc_request_id"] == pbc_request1_id for s in samples)


@pytest.mark.asyncio
async def test_get_sample(client, tenant_a, user_tenant_a, db_session):
    """Test getting a specific sample"""
    # Setup project, application, control
    user_a, membership_a = user_tenant_a

    project = Project(
        id=uuid4(),
        tenant_id=tenant_a.id,
        created_by_membership_id=membership_a.id,
        name="Test Project",
        status="active",
    )
    db_session.add(project)
    await db_session.flush()

    application = Application(
        id=uuid4(),
        tenant_id=tenant_a.id,
        name="Test App",
        category="Web Application",
    )
    db_session.add(application)
    await db_session.flush()

    control = Control(
        id=uuid4(),
        tenant_id=tenant_a.id,
        created_by_membership_id=membership_a.id,
        control_code="AC-001",
        name="Access Control",
        is_key=True,
        is_automated=False,
    )
    db_session.add(control)
    await db_session.flush()

    pbc_request = PbcRequest(
        id=uuid4(),
        tenant_id=tenant_a.id,
        project_id=project.id,
        application_id=application.id,
        control_id=control.id,
        owner_membership_id=membership_a.id,
        title="Request Access Logs",
        status="pending",
    )
    db_session.add(pbc_request)
    await db_session.flush()

    sample = Sample(
        id=uuid4(),
        tenant_id=tenant_a.id,
        pbc_request_id=pbc_request.id,
        sample_number=1,
        identifier="TXN-001",
    )
    db_session.add(sample)
    await db_session.commit()

    sample_id = str(sample.id)

    # Create auth token
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

    # Get sample
    response = client.get(f"/api/v1/samples/{sample_id}", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    sample_data = response.json()
    assert sample_data["id"] == sample_id
    assert sample_data["identifier"] == "TXN-001"


@pytest.mark.asyncio
async def test_update_sample(client, tenant_a, user_tenant_a, db_session):
    """Test updating a sample"""
    # Setup project, application, control
    user_a, membership_a = user_tenant_a

    project = Project(
        id=uuid4(),
        tenant_id=tenant_a.id,
        created_by_membership_id=membership_a.id,
        name="Test Project",
        status="active",
    )
    db_session.add(project)
    await db_session.flush()

    application = Application(
        id=uuid4(),
        tenant_id=tenant_a.id,
        name="Test App",
        category="Web Application",
    )
    db_session.add(application)
    await db_session.flush()

    control = Control(
        id=uuid4(),
        tenant_id=tenant_a.id,
        created_by_membership_id=membership_a.id,
        control_code="AC-001",
        name="Access Control",
        is_key=True,
        is_automated=False,
    )
    db_session.add(control)
    await db_session.flush()

    pbc_request = PbcRequest(
        id=uuid4(),
        tenant_id=tenant_a.id,
        project_id=project.id,
        application_id=application.id,
        control_id=control.id,
        owner_membership_id=membership_a.id,
        title="Request Access Logs",
        status="pending",
    )
    db_session.add(pbc_request)
    await db_session.flush()

    sample = Sample(
        id=uuid4(),
        tenant_id=tenant_a.id,
        pbc_request_id=pbc_request.id,
        sample_number=1,
        identifier="TXN-001",
        status="pending",
    )
    db_session.add(sample)
    await db_session.commit()

    sample_id = str(sample.id)

    # Create auth token
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

    # Update sample
    tested_at = datetime.utcnow().isoformat()
    update_data = {
        "status": "tested",
        "test_notes": "Control is working as expected",
        "tested_at": tested_at,
        "tested_by_membership_id": str(membership_a.id),
    }

    response = client.put(
        f"/api/v1/samples/{sample_id}",
        json=update_data,
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK
    updated_sample = response.json()
    assert updated_sample["status"] == "tested"
    assert updated_sample["test_notes"] == "Control is working as expected"
    assert updated_sample["tested_by_membership_id"] == str(membership_a.id)


@pytest.mark.asyncio
async def test_delete_sample(client, tenant_a, user_tenant_a, db_session):
    """Test deleting a sample"""
    # Setup project, application, control
    user_a, membership_a = user_tenant_a

    project = Project(
        id=uuid4(),
        tenant_id=tenant_a.id,
        created_by_membership_id=membership_a.id,
        name="Test Project",
        status="active",
    )
    db_session.add(project)
    await db_session.flush()

    application = Application(
        id=uuid4(),
        tenant_id=tenant_a.id,
        name="Test App",
        category="Web Application",
    )
    db_session.add(application)
    await db_session.flush()

    control = Control(
        id=uuid4(),
        tenant_id=tenant_a.id,
        created_by_membership_id=membership_a.id,
        control_code="AC-001",
        name="Access Control",
        is_key=True,
        is_automated=False,
    )
    db_session.add(control)
    await db_session.flush()

    pbc_request = PbcRequest(
        id=uuid4(),
        tenant_id=tenant_a.id,
        project_id=project.id,
        application_id=application.id,
        control_id=control.id,
        owner_membership_id=membership_a.id,
        title="Request Access Logs",
        status="pending",
    )
    db_session.add(pbc_request)
    await db_session.flush()

    sample = Sample(
        id=uuid4(),
        tenant_id=tenant_a.id,
        pbc_request_id=pbc_request.id,
        sample_number=1,
        identifier="TXN-001",
    )
    db_session.add(sample)
    await db_session.commit()

    sample_id = str(sample.id)

    # Create auth token
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

    # Delete sample
    response = client.delete(f"/api/v1/samples/{sample_id}", headers=headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify deletion
    get_response = client.get(f"/api/v1/samples/{sample_id}", headers=headers)
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_create_sample_invalid_pbc_request(
    client, tenant_a, user_tenant_a, db_session
):
    """Test creating sample with non-existent PBC request"""
    user_a, membership_a = user_tenant_a
    
    # Create auth token
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

    # Create sample with invalid PBC request
    sample_data = {
        "pbc_request_id": str(uuid4()),
        "sample_number": 1,
        "identifier": "TXN-001",
    }

    response = client.post(
        "/api/v1/samples",
        json=sample_data,
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "PBC request not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_tenant_isolation_samples(
    client, tenant_a, tenant_b, user_tenant_a, user_tenant_b, db_session
):
    """Test that samples are isolated by tenant"""
    # Setup for tenant A
    user_a, membership_a = user_tenant_a

    project_a = Project(
        id=uuid4(),
        tenant_id=tenant_a.id,
        created_by_membership_id=membership_a.id,
        name="Project A",
        status="active",
    )
    db_session.add(project_a)
    await db_session.flush()

    application_a = Application(
        id=uuid4(),
        tenant_id=tenant_a.id,
        name="App A",
        category="Web Application",
    )
    db_session.add(application_a)
    await db_session.flush()

    control_a = Control(
        id=uuid4(),
        tenant_id=tenant_a.id,
        created_by_membership_id=membership_a.id,
        control_code="AC-001",
        name="Control A",
        is_key=True,
        is_automated=False,
    )
    db_session.add(control_a)
    await db_session.flush()

    pbc_request_a = PbcRequest(
        id=uuid4(),
        tenant_id=tenant_a.id,
        project_id=project_a.id,
        application_id=application_a.id,
        control_id=control_a.id,
        owner_membership_id=membership_a.id,
        title="Request A",
        status="pending",
    )
    db_session.add(pbc_request_a)
    await db_session.flush()

    sample_a = Sample(
        id=uuid4(),
        tenant_id=tenant_a.id,
        pbc_request_id=pbc_request_a.id,
        sample_number=1,
        identifier="TXN-A-001",
    )
    db_session.add(sample_a)
    await db_session.commit()

    sample_a_id = str(sample_a.id)

    # Create auth token for tenant B
    user_b, membership_b = user_tenant_b
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

    # Try to access tenant A's sample from tenant B
    response = client.get(f"/api/v1/samples/{sample_a_id}", headers=headers_b)
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_create_sample_invalid_membership(
    client, tenant_a, tenant_b, user_tenant_a, user_tenant_b, db_session
):
    """Test creating sample with membership from another tenant"""
    # Setup for tenant A
    user_a, membership_a = user_tenant_a
    user_b, membership_b = user_tenant_b

    project_a = Project(
        id=uuid4(),
        tenant_id=tenant_a.id,
        created_by_membership_id=membership_a.id,
        name="Project A",
        status="active",
    )
    db_session.add(project_a)
    await db_session.flush()

    application_a = Application(
        id=uuid4(),
        tenant_id=tenant_a.id,
        name="App A",
        category="Web Application",
    )
    db_session.add(application_a)
    await db_session.flush()

    control_a = Control(
        id=uuid4(),
        tenant_id=tenant_a.id,
        created_by_membership_id=membership_a.id,
        control_code="AC-001",
        name="Control A",
        is_key=True,
        is_automated=False,
    )
    db_session.add(control_a)
    await db_session.flush()

    pbc_request_a = PbcRequest(
        id=uuid4(),
        tenant_id=tenant_a.id,
        project_id=project_a.id,
        application_id=application_a.id,
        control_id=control_a.id,
        owner_membership_id=membership_a.id,
        title="Request A",
        status="pending",
    )
    db_session.add(pbc_request_a)
    await db_session.commit()

    pbc_request_a_id = str(pbc_request_a.id)

    # Create auth token for tenant A
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

    # Try to create sample with membership from tenant B
    sample_data = {
        "pbc_request_id": pbc_request_a_id,
        "sample_number": 1,
        "identifier": "TXN-001",
        "tested_by_membership_id": str(membership_b.id),
    }

    response = client.post(
        "/api/v1/samples",
        json=sample_data,
        headers=headers_a,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Membership not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_sample_not_found(client, tenant_a, user_tenant_a, db_session):
    """Test getting a non-existent sample"""
    user_a, membership_a = user_tenant_a
    
    # Create auth token
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

    # Try to get non-existent sample
    fake_id = str(uuid4())
    response = client.get(f"/api/v1/samples/{fake_id}", headers=headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND
