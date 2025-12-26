"""Repository for evidence artifacts and files (DB-only layer)."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.evidence_artifact import EvidenceArtifact
from models.evidence_file_v2 import EvidenceFileV2
from models.pbc_request_evidence_file import PbcRequestEvidenceFile


async def create_artifact(
    session: AsyncSession,
    artifact: EvidenceArtifact,
) -> EvidenceArtifact:
    """
    Create a new evidence artifact.
    
    Args:
        session: Database session
        artifact: EvidenceArtifact instance to create
    
    Returns:
        Created EvidenceArtifact
    """
    session.add(artifact)
    await session.flush()
    await session.refresh(artifact)
    return artifact


async def create_file(
    session: AsyncSession,
    file: EvidenceFileV2,
) -> EvidenceFileV2:
    """
    Create a new evidence file.
    
    Args:
        session: Database session
        file: EvidenceFileV2 instance to create
    
    Returns:
        Created EvidenceFileV2
    """
    session.add(file)
    await session.flush()
    await session.refresh(file)
    return file


async def link_file_to_pbc(
    session: AsyncSession,
    link: PbcRequestEvidenceFile,
) -> PbcRequestEvidenceFile:
    """
    Link an evidence file to a PBC request.
    
    Args:
        session: Database session
        link: PbcRequestEvidenceFile instance to create
    
    Returns:
        Created PbcRequestEvidenceFile link
    """
    session.add(link)
    await session.flush()
    await session.refresh(link)
    return link


async def list_files_for_pbc(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    pbc_request_id: UUID,
) -> list[EvidenceFileV2]:
    """
    List all evidence files linked to a PBC request (active links only).
    
    Args:
        session: Database session
        tenant_id: Tenant ID to filter by
        pbc_request_id: PBC request ID to filter by
    
    Returns:
        List of EvidenceFileV2 instances
    """
    query = (
        select(EvidenceFileV2)
        .join(
            PbcRequestEvidenceFile,
            EvidenceFileV2.id == PbcRequestEvidenceFile.evidence_file_id,
        )
        .where(
            PbcRequestEvidenceFile.tenant_id == tenant_id,
            PbcRequestEvidenceFile.pbc_request_id == pbc_request_id,
            PbcRequestEvidenceFile.deleted_at.is_(None),
            EvidenceFileV2.deleted_at.is_(None),
        )
    )
    
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_link_by_pbc_and_file(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    pbc_request_id: UUID,
    evidence_file_id: UUID,
) -> PbcRequestEvidenceFile | None:
    """
    Get a link between a PBC request and evidence file.
    
    Args:
        session: Database session
        tenant_id: Tenant ID to filter by
        pbc_request_id: PBC request ID
        evidence_file_id: Evidence file ID
    
    Returns:
        PbcRequestEvidenceFile if found, None otherwise
    """
    query = select(PbcRequestEvidenceFile).where(
        PbcRequestEvidenceFile.tenant_id == tenant_id,
        PbcRequestEvidenceFile.pbc_request_id == pbc_request_id,
        PbcRequestEvidenceFile.evidence_file_id == evidence_file_id,
    )
    
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def unlink_file_from_pbc(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    membership_id: UUID,
    pbc_request_id: UUID,
    evidence_file_id: UUID,
) -> None:
    """
    Soft delete a link between a PBC request and evidence file.
    
    Args:
        session: Database session
        tenant_id: Tenant ID to filter by
        membership_id: Membership ID for audit
        pbc_request_id: PBC request ID
        evidence_file_id: Evidence file ID
    
    Raises:
        ValueError: If link not found
    """
    link = await get_link_by_pbc_and_file(
        session,
        tenant_id=tenant_id,
        pbc_request_id=pbc_request_id,
        evidence_file_id=evidence_file_id,
    )
    
    if not link:
        raise ValueError("Link not found")
    
    if link.deleted_at is not None:
        # Already deleted
        return
    
    now = datetime.now(UTC)
    link.deleted_at = now
    link.deleted_by_membership_id = membership_id
    link.row_version += 1
    
    await session.flush()

