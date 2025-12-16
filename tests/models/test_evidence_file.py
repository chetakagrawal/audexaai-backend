"""DB-backed tests for EvidenceFile model.

These tests verify model behavior, database constraints, and query patterns
for the EvidenceFile model. All tests use a real database session.
"""

from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.application import Application
from models.control import Control
from models.evidence_file import EvidenceFile
from models.pbc_request import PbcRequest
from models.project import Project
from models.tenant import Tenant
from models.user import User
from models.user_tenant import UserTenant


@pytest.mark.asyncio
async def test_create_evidence_file_minimal(db_session: AsyncSession):
    """Test: Can create an evidence file with minimal required fields."""
    # Create tenant
    tenant = Tenant(
        id=uuid4(),
        name="Test Tenant",
        slug="test-tenant",
        status="active",
    )
    db_session.add(tenant)
    await db_session.flush()
    
    # Create user and membership
    user = User(
        id=uuid4(),
        primary_email="user@example.com",
        name="User",
        is_platform_admin=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    
    membership = UserTenant(
        id=uuid4(),
        user_id=user.id,
        tenant_id=tenant.id,
        role="admin",
        is_default=True,
    )
    db_session.add(membership)
    await db_session.flush()
    
    # Create project, application, control
    project = Project(
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        name="Test Project",
        status="active",
    )
    db_session.add(project)
    
    application = Application(
        id=uuid4(),
        tenant_id=tenant.id,
        name="Test Application",
    )
    db_session.add(application)
    
    control = Control(
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-001",
        name="Test Control",
    )
    db_session.add(control)
    await db_session.flush()
    
    # Create PBC request
    pbc_request = PbcRequest(
        id=uuid4(),
        tenant_id=tenant.id,
        project_id=project.id,
        application_id=application.id,
        control_id=control.id,
        owner_membership_id=membership.id,
        title="Test PBC Request",
    )
    db_session.add(pbc_request)
    await db_session.flush()
    
    # Create evidence file (minimal)
    evidence_file = EvidenceFile(
        id=uuid4(),
        tenant_id=tenant.id,
        pbc_request_id=pbc_request.id,
        uploaded_by_membership_id=membership.id,
        filename="evidence.pdf",
        mime_type="application/pdf",
        storage_uri="s3://bucket/evidence.pdf",
        content_hash="abc123hash",
    )
    db_session.add(evidence_file)
    await db_session.commit()
    await db_session.refresh(evidence_file)
    
    assert evidence_file.id is not None
    assert evidence_file.tenant_id == tenant.id
    assert evidence_file.pbc_request_id == pbc_request.id
    assert evidence_file.sample_id is None
    assert evidence_file.uploaded_by_membership_id == membership.id
    assert evidence_file.filename == "evidence.pdf"
    assert evidence_file.mime_type == "application/pdf"
    assert evidence_file.storage_uri == "s3://bucket/evidence.pdf"
    assert evidence_file.content_hash == "abc123hash"
    assert evidence_file.version == 1
    assert evidence_file.supersedes_file_id is None
    assert evidence_file.page_count is None
    assert evidence_file.uploaded_at is not None
    assert isinstance(evidence_file.uploaded_at, datetime)


@pytest.mark.asyncio
async def test_create_evidence_file_with_all_fields(db_session: AsyncSession):
    """Test: Can create an evidence file with all fields populated."""
    # Setup (similar to minimal test)
    tenant = Tenant(
        id=uuid4(),
        name="Test Tenant Full",
        slug="test-tenant-full",
        status="active",
    )
    db_session.add(tenant)
    await db_session.flush()
    
    user = User(
        id=uuid4(),
        primary_email="user@example.com",
        name="User",
        is_platform_admin=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    
    membership = UserTenant(
        id=uuid4(),
        user_id=user.id,
        tenant_id=tenant.id,
        role="admin",
        is_default=True,
    )
    db_session.add(membership)
    await db_session.flush()
    
    project = Project(
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        name="Test Project",
        status="active",
    )
    db_session.add(project)
    
    application = Application(
        id=uuid4(),
        tenant_id=tenant.id,
        name="Test Application",
    )
    db_session.add(application)
    
    control = Control(
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-002",
        name="Test Control",
    )
    db_session.add(control)
    await db_session.flush()
    
    pbc_request = PbcRequest(
        id=uuid4(),
        tenant_id=tenant.id,
        project_id=project.id,
        application_id=application.id,
        control_id=control.id,
        owner_membership_id=membership.id,
        title="Test PBC Request",
    )
    db_session.add(pbc_request)
    await db_session.flush()
    
    # Create first version of file
    v1_file = EvidenceFile(
        id=uuid4(),
        tenant_id=tenant.id,
        pbc_request_id=pbc_request.id,
        uploaded_by_membership_id=membership.id,
        filename="evidence_v1.pdf",
        mime_type="application/pdf",
        storage_uri="s3://bucket/evidence_v1.pdf",
        content_hash="v1hash",
        version=1,
    )
    db_session.add(v1_file)
    await db_session.flush()
    
    # Create evidence file with all fields
    sample_id = uuid4()  # Would reference samples table when implemented
    
    evidence_file = EvidenceFile(
        id=uuid4(),
        tenant_id=tenant.id,
        pbc_request_id=pbc_request.id,
        sample_id=sample_id,
        uploaded_by_membership_id=membership.id,
        filename="evidence_v2.pdf",
        mime_type="application/pdf",
        storage_uri="s3://bucket/evidence_v2.pdf",
        content_hash="v2hash",
        version=2,
        supersedes_file_id=v1_file.id,
        page_count=15,
    )
    db_session.add(evidence_file)
    await db_session.commit()
    await db_session.refresh(evidence_file)
    
    assert evidence_file.filename == "evidence_v2.pdf"
    assert evidence_file.sample_id == sample_id
    assert evidence_file.version == 2
    assert evidence_file.supersedes_file_id == v1_file.id
    assert evidence_file.page_count == 15


@pytest.mark.asyncio
async def test_evidence_file_query_by_pbc_request(db_session: AsyncSession):
    """Test: Can query evidence files by pbc_request_id."""
    # Setup
    tenant = Tenant(
        id=uuid4(),
        name="Test Tenant Query",
        slug="test-tenant-query",
        status="active",
    )
    db_session.add(tenant)
    await db_session.flush()
    
    user = User(
        id=uuid4(),
        primary_email="user@example.com",
        name="User",
        is_platform_admin=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    
    membership = UserTenant(
        id=uuid4(),
        user_id=user.id,
        tenant_id=tenant.id,
        role="admin",
        is_default=True,
    )
    db_session.add(membership)
    await db_session.flush()
    
    project = Project(
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        name="Test Project",
        status="active",
    )
    db_session.add(project)
    
    application = Application(
        id=uuid4(),
        tenant_id=tenant.id,
        name="Test Application",
    )
    db_session.add(application)
    
    control = Control(
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-003",
        name="Test Control",
    )
    db_session.add(control)
    await db_session.flush()
    
    pbc_request = PbcRequest(
        id=uuid4(),
        tenant_id=tenant.id,
        project_id=project.id,
        application_id=application.id,
        control_id=control.id,
        owner_membership_id=membership.id,
        title="Test PBC Request",
    )
    db_session.add(pbc_request)
    await db_session.flush()
    
    # Create multiple evidence files for the same PBC request
    file1 = EvidenceFile(
        id=uuid4(),
        tenant_id=tenant.id,
        pbc_request_id=pbc_request.id,
        uploaded_by_membership_id=membership.id,
        filename="file1.pdf",
        mime_type="application/pdf",
        storage_uri="s3://bucket/file1.pdf",
        content_hash="hash1",
    )
    file2 = EvidenceFile(
        id=uuid4(),
        tenant_id=tenant.id,
        pbc_request_id=pbc_request.id,
        uploaded_by_membership_id=membership.id,
        filename="file2.xlsx",
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        storage_uri="s3://bucket/file2.xlsx",
        content_hash="hash2",
    )
    db_session.add(file1)
    db_session.add(file2)
    await db_session.commit()
    
    # Query by pbc_request_id
    result = await db_session.execute(
        select(EvidenceFile).where(EvidenceFile.pbc_request_id == pbc_request.id)
    )
    files = result.scalars().all()
    
    assert len(files) == 2
    filenames = [f.filename for f in files]
    assert "file1.pdf" in filenames
    assert "file2.xlsx" in filenames


@pytest.mark.asyncio
async def test_evidence_file_cascade_delete_on_pbc_request(db_session: AsyncSession):
    """Test: Deleting a PBC request cascades to delete evidence files."""
    # Setup
    tenant = Tenant(
        id=uuid4(),
        name="Test Tenant Cascade",
        slug="test-tenant-cascade",
        status="active",
    )
    db_session.add(tenant)
    await db_session.flush()
    
    user = User(
        id=uuid4(),
        primary_email="user@example.com",
        name="User",
        is_platform_admin=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    
    membership = UserTenant(
        id=uuid4(),
        user_id=user.id,
        tenant_id=tenant.id,
        role="admin",
        is_default=True,
    )
    db_session.add(membership)
    await db_session.flush()
    
    project = Project(
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        name="Test Project",
        status="active",
    )
    db_session.add(project)
    
    application = Application(
        id=uuid4(),
        tenant_id=tenant.id,
        name="Test Application",
    )
    db_session.add(application)
    
    control = Control(
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-004",
        name="Test Control",
    )
    db_session.add(control)
    await db_session.flush()
    
    pbc_request = PbcRequest(
        id=uuid4(),
        tenant_id=tenant.id,
        project_id=project.id,
        application_id=application.id,
        control_id=control.id,
        owner_membership_id=membership.id,
        title="Test PBC Request",
    )
    db_session.add(pbc_request)
    await db_session.flush()
    
    evidence_file = EvidenceFile(
        id=uuid4(),
        tenant_id=tenant.id,
        pbc_request_id=pbc_request.id,
        uploaded_by_membership_id=membership.id,
        filename="test.pdf",
        mime_type="application/pdf",
        storage_uri="s3://bucket/test.pdf",
        content_hash="testhash",
    )
    db_session.add(evidence_file)
    await db_session.commit()
    
    file_id = evidence_file.id
    
    # Delete PBC request (should cascade)
    await db_session.delete(pbc_request)
    await db_session.commit()
    
    # Verify evidence file is deleted
    result = await db_session.execute(
        select(EvidenceFile).where(EvidenceFile.id == file_id)
    )
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_evidence_file_cascade_delete_on_tenant(db_session: AsyncSession):
    """Test: Deleting a tenant cascades to delete evidence files."""
    # Setup
    tenant = Tenant(
        id=uuid4(),
        name="Test Tenant Del",
        slug="test-tenant-del",
        status="active",
    )
    db_session.add(tenant)
    await db_session.flush()
    
    user = User(
        id=uuid4(),
        primary_email="user@example.com",
        name="User",
        is_platform_admin=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    
    membership = UserTenant(
        id=uuid4(),
        user_id=user.id,
        tenant_id=tenant.id,
        role="admin",
        is_default=True,
    )
    db_session.add(membership)
    await db_session.flush()
    
    project = Project(
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        name="Test Project",
        status="active",
    )
    db_session.add(project)
    
    application = Application(
        id=uuid4(),
        tenant_id=tenant.id,
        name="Test Application",
    )
    db_session.add(application)
    
    control = Control(
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-005",
        name="Test Control",
    )
    db_session.add(control)
    await db_session.flush()
    
    pbc_request = PbcRequest(
        id=uuid4(),
        tenant_id=tenant.id,
        project_id=project.id,
        application_id=application.id,
        control_id=control.id,
        owner_membership_id=membership.id,
        title="Test PBC Request",
    )
    db_session.add(pbc_request)
    await db_session.flush()
    
    evidence_file = EvidenceFile(
        id=uuid4(),
        tenant_id=tenant.id,
        pbc_request_id=pbc_request.id,
        uploaded_by_membership_id=membership.id,
        filename="test.pdf",
        mime_type="application/pdf",
        storage_uri="s3://bucket/test.pdf",
        content_hash="testhash",
    )
    db_session.add(evidence_file)
    await db_session.commit()
    
    file_id = evidence_file.id
    
    # Delete tenant (should cascade)
    await db_session.delete(tenant)
    await db_session.commit()
    
    # Verify evidence file is deleted
    result = await db_session.execute(
        select(EvidenceFile).where(EvidenceFile.id == file_id)
    )
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_evidence_file_tenant_isolation(db_session: AsyncSession):
    """Test: Evidence files are isolated by tenant."""
    # Create two tenants
    tenant_a = Tenant(
        id=uuid4(),
        name="Tenant A",
        slug="tenant-a-evf",
        status="active",
    )
    tenant_b = Tenant(
        id=uuid4(),
        name="Tenant B",
        slug="tenant-b-evf",
        status="active",
    )
    db_session.add(tenant_a)
    db_session.add(tenant_b)
    await db_session.flush()
    
    # Create users and memberships
    user_a = User(
        id=uuid4(),
        primary_email="user_a@example.com",
        name="User A",
        is_platform_admin=False,
        is_active=True,
    )
    user_b = User(
        id=uuid4(),
        primary_email="user_b@example.com",
        name="User B",
        is_platform_admin=False,
        is_active=True,
    )
    db_session.add(user_a)
    db_session.add(user_b)
    await db_session.flush()
    
    membership_a = UserTenant(
        id=uuid4(),
        user_id=user_a.id,
        tenant_id=tenant_a.id,
        role="admin",
        is_default=True,
    )
    membership_b = UserTenant(
        id=uuid4(),
        user_id=user_b.id,
        tenant_id=tenant_b.id,
        role="admin",
        is_default=True,
    )
    db_session.add(membership_a)
    db_session.add(membership_b)
    await db_session.flush()
    
    # Create projects, apps, controls for both tenants
    project_a = Project(id=uuid4(), tenant_id=tenant_a.id, created_by_membership_id=membership_a.id, name="Project A", status="active")
    project_b = Project(id=uuid4(), tenant_id=tenant_b.id, created_by_membership_id=membership_b.id, name="Project B", status="active")
    app_a = Application(id=uuid4(), tenant_id=tenant_a.id, name="App A")
    app_b = Application(id=uuid4(), tenant_id=tenant_b.id, name="App B")
    control_a = Control(id=uuid4(), tenant_id=tenant_a.id, created_by_membership_id=membership_a.id, control_code="AC-001", name="Control A")
    control_b = Control(id=uuid4(), tenant_id=tenant_b.id, created_by_membership_id=membership_b.id, control_code="AC-001", name="Control B")
    db_session.add_all([project_a, project_b, app_a, app_b, control_a, control_b])
    await db_session.flush()
    
    # Create PBC requests
    pbc_a = PbcRequest(id=uuid4(), tenant_id=tenant_a.id, project_id=project_a.id, application_id=app_a.id, control_id=control_a.id, owner_membership_id=membership_a.id, title="PBC A")
    pbc_b = PbcRequest(id=uuid4(), tenant_id=tenant_b.id, project_id=project_b.id, application_id=app_b.id, control_id=control_b.id, owner_membership_id=membership_b.id, title="PBC B")
    db_session.add(pbc_a)
    db_session.add(pbc_b)
    await db_session.flush()
    
    # Create evidence files
    file_a = EvidenceFile(
        id=uuid4(),
        tenant_id=tenant_a.id,
        pbc_request_id=pbc_a.id,
        uploaded_by_membership_id=membership_a.id,
        filename="file_a.pdf",
        mime_type="application/pdf",
        storage_uri="s3://bucket/file_a.pdf",
        content_hash="hash_a",
    )
    file_b = EvidenceFile(
        id=uuid4(),
        tenant_id=tenant_b.id,
        pbc_request_id=pbc_b.id,
        uploaded_by_membership_id=membership_b.id,
        filename="file_b.pdf",
        mime_type="application/pdf",
        storage_uri="s3://bucket/file_b.pdf",
        content_hash="hash_b",
    )
    db_session.add(file_a)
    db_session.add(file_b)
    await db_session.commit()
    
    # Query for tenant_a - should only see tenant_a's files
    result = await db_session.execute(
        select(EvidenceFile).where(EvidenceFile.tenant_id == tenant_a.id)
    )
    files_a = result.scalars().all()
    
    assert len(files_a) == 1
    assert files_a[0].id == file_a.id
    assert files_a[0].tenant_id == tenant_a.id
    
    # Query for tenant_b - should only see tenant_b's files
    result = await db_session.execute(
        select(EvidenceFile).where(EvidenceFile.tenant_id == tenant_b.id)
    )
    files_b = result.scalars().all()
    
    assert len(files_b) == 1
    assert files_b[0].id == file_b.id
    assert files_b[0].tenant_id == tenant_b.id


@pytest.mark.asyncio
async def test_evidence_file_versioning_relationship(db_session: AsyncSession):
    """Test: Evidence file versioning with supersedes_file_id."""
    # Setup
    tenant = Tenant(
        id=uuid4(),
        name="Test Tenant Version",
        slug="test-tenant-version",
        status="active",
    )
    db_session.add(tenant)
    await db_session.flush()
    
    user = User(
        id=uuid4(),
        primary_email="user@example.com",
        name="User",
        is_platform_admin=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    
    membership = UserTenant(
        id=uuid4(),
        user_id=user.id,
        tenant_id=tenant.id,
        role="admin",
        is_default=True,
    )
    db_session.add(membership)
    await db_session.flush()
    
    project = Project(
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        name="Test Project",
        status="active",
    )
    db_session.add(project)
    
    application = Application(
        id=uuid4(),
        tenant_id=tenant.id,
        name="Test Application",
    )
    db_session.add(application)
    
    control = Control(
        id=uuid4(),
        tenant_id=tenant.id,
        created_by_membership_id=membership.id,
        control_code="AC-006",
        name="Test Control",
    )
    db_session.add(control)
    await db_session.flush()
    
    pbc_request = PbcRequest(
        id=uuid4(),
        tenant_id=tenant.id,
        project_id=project.id,
        application_id=application.id,
        control_id=control.id,
        owner_membership_id=membership.id,
        title="Test PBC Request",
    )
    db_session.add(pbc_request)
    await db_session.flush()
    
    # Create v1
    v1 = EvidenceFile(
        id=uuid4(),
        tenant_id=tenant.id,
        pbc_request_id=pbc_request.id,
        uploaded_by_membership_id=membership.id,
        filename="doc_v1.pdf",
        mime_type="application/pdf",
        storage_uri="s3://bucket/doc_v1.pdf",
        content_hash="v1hash",
        version=1,
    )
    db_session.add(v1)
    await db_session.flush()
    
    # Create v2 that supersedes v1
    v2 = EvidenceFile(
        id=uuid4(),
        tenant_id=tenant.id,
        pbc_request_id=pbc_request.id,
        uploaded_by_membership_id=membership.id,
        filename="doc_v2.pdf",
        mime_type="application/pdf",
        storage_uri="s3://bucket/doc_v2.pdf",
        content_hash="v2hash",
        version=2,
        supersedes_file_id=v1.id,
    )
    db_session.add(v2)
    await db_session.commit()
    await db_session.refresh(v2)
    
    assert v2.supersedes_file_id == v1.id
    assert v2.version == 2
    
    # Verify both exist
    result = await db_session.execute(
        select(EvidenceFile).where(
            EvidenceFile.pbc_request_id == pbc_request.id
        ).order_by(EvidenceFile.version)
    )
    versions = result.scalars().all()
    
    assert len(versions) == 2
    assert versions[0].version == 1
    assert versions[1].version == 2
    assert versions[1].supersedes_file_id == versions[0].id
