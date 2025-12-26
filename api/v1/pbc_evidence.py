"""PBC Evidence endpoints - upload and manage evidence files for PBC requests."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db, get_tenancy_context
from api.tenancy import TenancyContext
from models.evidence_artifact import EvidenceArtifactResponse
from models.evidence_file_v2 import EvidenceFileV2Response
from models.user import User
from services.evidence_service import list_for_pbc, unlink, upload_and_link

router = APIRouter()


class EvidenceUploadResponse(BaseModel):
    """Response schema for evidence upload."""

    artifact: EvidenceArtifactResponse
    files: List[EvidenceFileV2Response]
    linked_count: int


@router.post(
    "/pbc/{pbc_request_id}/evidence/upload",
    response_model=EvidenceUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_evidence(
    pbc_request_id: UUID,
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    tenancy: TenancyContext = Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload one or more files and link them to a PBC request.
    
    Args:
        pbc_request_id: PBC request ID to link files to
        files: List of files to upload (multipart/form-data)
    
    Returns:
        Upload response with artifact, files, and linked_count
    
    Raises:
        404 if PBC request not found
        400 if no files provided
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one file is required",
        )
    
    try:
        result = await upload_and_link(
            db,
            membership_ctx=tenancy,
            pbc_request_id=pbc_request_id,
            files=files,
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload evidence: {str(e)}",
        )


@router.get(
    "/pbc/{pbc_request_id}/evidence",
    response_model=List[EvidenceFileV2Response],
)
async def list_evidence(
    pbc_request_id: UUID,
    current_user: User = Depends(get_current_user),
    tenancy: TenancyContext = Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    List all evidence files linked to a PBC request.
    
    Args:
        pbc_request_id: PBC request ID
    
    Returns:
        List of evidence files
    
    Raises:
        404 if PBC request not found
    """
    try:
        files = await list_for_pbc(
            db,
            membership_ctx=tenancy,
            pbc_request_id=pbc_request_id,
        )
        return files
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list evidence: {str(e)}",
        )


@router.delete(
    "/pbc/{pbc_request_id}/evidence/{evidence_file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def unlink_evidence(
    pbc_request_id: UUID,
    evidence_file_id: UUID,
    current_user: User = Depends(get_current_user),
    tenancy: TenancyContext = Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Unlink an evidence file from a PBC request (soft delete link).
    
    Note: This does NOT delete the file itself, only the link.
    
    Args:
        pbc_request_id: PBC request ID
        evidence_file_id: Evidence file ID to unlink
    
    Returns:
        204 No Content on success
    
    Raises:
        404 if PBC request or link not found
    """
    try:
        await unlink(
            db,
            membership_ctx=tenancy,
            pbc_request_id=pbc_request_id,
            evidence_file_id=evidence_file_id,
        )
        return None
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unlink evidence: {str(e)}",
        )

