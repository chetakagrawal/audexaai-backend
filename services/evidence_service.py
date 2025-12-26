"""Service layer for evidence upload and linking (business logic)."""

from datetime import datetime, UTC
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.tenancy import TenancyContext
from models.evidence_artifact import EvidenceArtifact
from models.evidence_file_v2 import EvidenceFileV2
from models.pbc_request_evidence_file import PbcRequestEvidenceFile
from repos import evidence_repo, pbc_repo
from services.storage import generate_storage_key, save_upload


async def upload_and_link(
    session: AsyncSession,
    *,
    membership_ctx: TenancyContext,
    pbc_request_id: UUID,
    files: list[UploadFile],
) -> dict:
    """
    Upload files and link them to a PBC request.
    
    Args:
        session: Database session
        membership_ctx: Tenancy context
        pbc_request_id: PBC request ID to link files to
        files: List of uploaded files
    
    Returns:
        Dict with artifact, files list, and linked_count
    
    Raises:
        HTTPException: 404 if PBC request not found, 400 if validation fails
    """
    tenant_id = membership_ctx.tenant_id
    membership_id = membership_ctx.membership_id
    
    # Validate PBC request exists and belongs to tenant
    pbc_request = await pbc_repo.get_request_by_id(
        session,
        tenant_id=tenant_id,
        pbc_request_id=pbc_request_id,
        include_deleted=False,
    )
    if not pbc_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PBC request not found",
        )
    
    project_id = pbc_request.project_id
    
    # Create evidence artifact
    now = datetime.now(UTC)
    artifact = EvidenceArtifact(
        tenant_id=tenant_id,
        project_id=project_id,
        source="manual",
        created_at=now,
        created_by_membership_id=membership_id,
        row_version=1,
    )
    artifact = await evidence_repo.create_artifact(session, artifact)
    
    # Process each uploaded file
    uploaded_files = []
    for file in files:
        # Create file record first to get ID for storage key
        file_record = EvidenceFileV2(
            tenant_id=tenant_id,
            project_id=project_id,
            artifact_id=artifact.id,
            filename=file.filename or "unnamed",
            mime_type=file.content_type or "application/octet-stream",
            size_bytes=0,  # Will be updated after save
            storage_key="",  # Will be updated after save
            uploaded_at=now,
            created_at=now,
            created_by_membership_id=membership_id,
            row_version=1,
        )
        file_record = await evidence_repo.create_file(session, file_record)
        
        # Generate storage key and save file
        storage_key = generate_storage_key(
            tenant_id=tenant_id,
            project_id=project_id,
            artifact_id=artifact.id,
            file_id=file_record.id,
            filename=file_record.filename,
        )
        
        bytes_written, sha256 = await save_upload(file, storage_key)
        
        # Update file record with actual size and storage info
        file_record.size_bytes = bytes_written
        file_record.storage_key = storage_key
        file_record.sha256 = sha256
        await session.flush()
        
        # Create link to PBC request
        link = PbcRequestEvidenceFile(
            tenant_id=tenant_id,
            project_id=project_id,
            pbc_request_id=pbc_request_id,
            evidence_file_id=file_record.id,
            created_at=now,
            created_by_membership_id=membership_id,
            row_version=1,
        )
        await evidence_repo.link_file_to_pbc(session, link)
        
        uploaded_files.append(file_record)
    
    await session.commit()
    await session.refresh(artifact)
    for f in uploaded_files:
        await session.refresh(f)
    
    return {
        "artifact": artifact,
        "files": uploaded_files,
        "linked_count": len(uploaded_files),
    }


async def list_for_pbc(
    session: AsyncSession,
    *,
    membership_ctx: TenancyContext,
    pbc_request_id: UUID,
) -> list[EvidenceFileV2]:
    """
    List all evidence files linked to a PBC request.
    
    Args:
        session: Database session
        membership_ctx: Tenancy context
        pbc_request_id: PBC request ID
    
    Returns:
        List of EvidenceFileV2 instances
    
    Raises:
        HTTPException: 404 if PBC request not found
    """
    tenant_id = membership_ctx.tenant_id
    
    # Validate PBC request exists
    pbc_request = await pbc_repo.get_request_by_id(
        session,
        tenant_id=tenant_id,
        pbc_request_id=pbc_request_id,
        include_deleted=False,
    )
    if not pbc_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PBC request not found",
        )
    
    return await evidence_repo.list_files_for_pbc(
        session,
        tenant_id=tenant_id,
        pbc_request_id=pbc_request_id,
    )


async def unlink(
    session: AsyncSession,
    *,
    membership_ctx: TenancyContext,
    pbc_request_id: UUID,
    evidence_file_id: UUID,
) -> None:
    """
    Unlink an evidence file from a PBC request (soft delete link).
    
    Args:
        session: Database session
        membership_ctx: Tenancy context
        pbc_request_id: PBC request ID
        evidence_file_id: Evidence file ID to unlink
    
    Raises:
        HTTPException: 404 if PBC request or link not found
    """
    tenant_id = membership_ctx.tenant_id
    membership_id = membership_ctx.membership_id
    
    # Validate PBC request exists
    pbc_request = await pbc_repo.get_request_by_id(
        session,
        tenant_id=tenant_id,
        pbc_request_id=pbc_request_id,
        include_deleted=False,
    )
    if not pbc_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PBC request not found",
        )
    
    try:
        await evidence_repo.unlink_file_from_pbc(
            session,
            tenant_id=tenant_id,
            membership_id=membership_id,
            pbc_request_id=pbc_request_id,
            evidence_file_id=evidence_file_id,
        )
        await session.commit()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

