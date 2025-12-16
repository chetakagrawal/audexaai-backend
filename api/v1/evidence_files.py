"""Evidence files endpoints - manage evidence files for PBC requests."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db, get_tenancy_context
from models.evidence_file import (
    EvidenceFile,
    EvidenceFileCreate,
    EvidenceFileResponse,
    EvidenceFileUpdate,
)
from models.pbc_request import PbcRequest
from models.user import User

router = APIRouter()


async def _verify_pbc_request_access(
    pbc_request_id: UUID,
    tenant_id: UUID,
    is_platform_admin: bool,
    db: AsyncSession,
) -> PbcRequest:
    """Verify PBC request exists and user has access."""
    query = select(PbcRequest).where(PbcRequest.id == pbc_request_id)
    if not is_platform_admin:
        query = query.where(PbcRequest.tenant_id == tenant_id)
    
    result = await db.execute(query)
    pbc_request = result.scalar_one_or_none()
    
    if not pbc_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PBC request not found",
        )
    return pbc_request


@router.get(
    "/pbc-requests/{pbc_request_id}/evidence-files",
    response_model=List[EvidenceFileResponse],
)
async def list_pbc_request_evidence_files(
    pbc_request_id: UUID,
    current_user: User = Depends(get_current_user),
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    List all evidence files for a PBC request.
    
    Returns:
        List of evidence files for the specified PBC request.
    
    Raises:
        404 if PBC request not found or user doesn't have access.
    """
    try:
        # Verify PBC request exists and belongs to tenant
        await _verify_pbc_request_access(
            pbc_request_id,
            tenancy.tenant_id,
            current_user.is_platform_admin,
            db,
        )
        
        # List all evidence files for this PBC request
        query = select(EvidenceFile).where(EvidenceFile.pbc_request_id == pbc_request_id)
        if not current_user.is_platform_admin:
            query = query.where(EvidenceFile.tenant_id == tenancy.tenant_id)
        
        # Order by uploaded_at descending (newest first)
        query = query.order_by(EvidenceFile.uploaded_at.desc())
        
        result = await db.execute(query)
        evidence_files = result.scalars().all()
        
        return evidence_files
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list evidence files: {str(e)}",
        )


@router.get(
    "/evidence-files",
    response_model=List[EvidenceFileResponse],
)
async def list_evidence_files(
    current_user: User = Depends(get_current_user),
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    List all evidence files for the tenant.
    
    Returns:
        List of all evidence files accessible to the user.
    """
    try:
        query = select(EvidenceFile)
        if not current_user.is_platform_admin:
            query = query.where(EvidenceFile.tenant_id == tenancy.tenant_id)
        
        # Order by uploaded_at descending (newest first)
        query = query.order_by(EvidenceFile.uploaded_at.desc())
        
        result = await db.execute(query)
        evidence_files = result.scalars().all()
        
        return evidence_files
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list evidence files: {str(e)}",
        )


@router.post(
    "/evidence-files",
    response_model=EvidenceFileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_evidence_file(
    evidence_file_data: EvidenceFileCreate,
    current_user: User = Depends(get_current_user),
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Create an evidence file.
    
    Note: 
    - tenant_id is derived from context, not client input
    - uploaded_by_membership_id is set from auth context
    
    Raises:
        404 if PBC request not found.
    """
    try:
        # Verify PBC request exists and belongs to tenant
        pbc_request = await _verify_pbc_request_access(
            evidence_file_data.pbc_request_id,
            tenancy.tenant_id,
            current_user.is_platform_admin,
            db,
        )
        
        # If sample_id is provided, verify it belongs to the same PBC request
        # (will be implemented when samples table exists)
        
        # If supersedes_file_id is provided, verify it exists
        if evidence_file_data.supersedes_file_id:
            superseded_query = select(EvidenceFile).where(
                EvidenceFile.id == evidence_file_data.supersedes_file_id
            )
            if not current_user.is_platform_admin:
                superseded_query = superseded_query.where(
                    EvidenceFile.tenant_id == tenancy.tenant_id
                )
            
            result = await db.execute(superseded_query)
            superseded_file = result.scalar_one_or_none()
            
            if not superseded_file:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Superseded file not found",
                )
        
        # Create evidence file
        evidence_file = EvidenceFile(
            tenant_id=tenancy.tenant_id,
            pbc_request_id=evidence_file_data.pbc_request_id,
            sample_id=evidence_file_data.sample_id,
            uploaded_by_membership_id=tenancy.membership_id,
            filename=evidence_file_data.filename,
            mime_type=evidence_file_data.mime_type,
            storage_uri=evidence_file_data.storage_uri,
            content_hash=evidence_file_data.content_hash,
            version=evidence_file_data.version,
            supersedes_file_id=evidence_file_data.supersedes_file_id,
            page_count=evidence_file_data.page_count,
        )
        
        db.add(evidence_file)
        await db.commit()
        await db.refresh(evidence_file)
        
        return evidence_file
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create evidence file: {str(e)}",
        )


@router.get(
    "/evidence-files/{evidence_file_id}",
    response_model=EvidenceFileResponse,
)
async def get_evidence_file(
    evidence_file_id: UUID,
    current_user: User = Depends(get_current_user),
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific evidence file by ID.
    
    Returns:
        Evidence file if found and user has access.
    
    Raises:
        404 if evidence file not found or user doesn't have access.
    """
    try:
        query = select(EvidenceFile).where(EvidenceFile.id == evidence_file_id)
        
        if not current_user.is_platform_admin:
            query = query.where(EvidenceFile.tenant_id == tenancy.tenant_id)
        
        result = await db.execute(query)
        evidence_file = result.scalar_one_or_none()
        
        if not evidence_file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evidence file not found",
            )
        
        return evidence_file
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch evidence file: {str(e)}",
        )


@router.put(
    "/evidence-files/{evidence_file_id}",
    response_model=EvidenceFileResponse,
)
async def update_evidence_file(
    evidence_file_id: UUID,
    evidence_file_data: EvidenceFileUpdate,
    current_user: User = Depends(get_current_user),
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Update an evidence file's metadata.
    
    Note: Only filename and page_count can be updated.
    Core file data (storage_uri, content_hash, etc.) is immutable.
    
    Raises:
        404 if evidence file not found or user doesn't have access.
    """
    try:
        query = select(EvidenceFile).where(EvidenceFile.id == evidence_file_id)
        
        if not current_user.is_platform_admin:
            query = query.where(EvidenceFile.tenant_id == tenancy.tenant_id)
        
        result = await db.execute(query)
        evidence_file = result.scalar_one_or_none()
        
        if not evidence_file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evidence file not found",
            )
        
        # Update only provided fields
        if evidence_file_data.filename is not None:
            evidence_file.filename = evidence_file_data.filename
        if evidence_file_data.page_count is not None:
            evidence_file.page_count = evidence_file_data.page_count
        
        await db.commit()
        await db.refresh(evidence_file)
        
        return evidence_file
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update evidence file: {str(e)}",
        )


@router.delete(
    "/evidence-files/{evidence_file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_evidence_file(
    evidence_file_id: UUID,
    current_user: User = Depends(get_current_user),
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete an evidence file.
    
    Note: This only deletes the database record.
    Actual file cleanup from storage should be handled separately.
    
    Raises:
        404 if evidence file not found or user doesn't have access.
    """
    try:
        query = select(EvidenceFile).where(EvidenceFile.id == evidence_file_id)
        
        if not current_user.is_platform_admin:
            query = query.where(EvidenceFile.tenant_id == tenancy.tenant_id)
        
        result = await db.execute(query)
        evidence_file = result.scalar_one_or_none()
        
        if not evidence_file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evidence file not found",
            )
        
        await db.delete(evidence_file)
        await db.commit()
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete evidence file: {str(e)}",
        )
