"""
Samples API endpoints

Manages samples for control testing in audit projects.
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db, get_tenancy_context
from models.pbc_request import PbcRequest
from models.sample import Sample, SampleCreate, SampleResponse, SampleUpdate
from models.user import User
from models.user_tenant import UserTenant

router = APIRouter()


# ============================================================
# Helper Functions
# ============================================================


async def _verify_pbc_request_access(
    pbc_request_id: UUID,
    tenant_id: UUID,
    is_platform_admin: bool,
    db: AsyncSession,
) -> PbcRequest:
    """Verify PBC request exists and user has access to it"""
    query = select(PbcRequest).where(PbcRequest.id == pbc_request_id)
    if not is_platform_admin:
        query = query.where(PbcRequest.tenant_id == tenant_id)

    result = await db.execute(query)
    pbc_request = result.scalar_one_or_none()

    if not pbc_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PBC request not found or access denied",
        )

    return pbc_request


async def _verify_membership_access(
    membership_id: UUID | None,
    tenant_id: UUID,
    is_platform_admin: bool,
    db: AsyncSession,
) -> None:
    """Verify membership exists and belongs to the tenant"""
    if membership_id is None:
        return

    query = select(UserTenant).where(UserTenant.id == membership_id)
    if not is_platform_admin:
        query = query.where(UserTenant.tenant_id == tenant_id)

    result = await db.execute(query)
    membership = result.scalar_one_or_none()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership not found or access denied",
        )


# ============================================================
# Endpoints
# ============================================================


@router.get(
    "/samples",
    response_model=List[SampleResponse],
)
async def list_samples(
    current_user: User = Depends(get_current_user),
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    List all samples for the tenant
    """
    query = select(Sample)
    if not current_user.is_platform_admin:
        query = query.where(Sample.tenant_id == tenancy.tenant_id)

    result = await db.execute(query)
    samples = result.scalars().all()
    return samples


@router.get(
    "/pbc-requests/{pbc_request_id}/samples",
    response_model=List[SampleResponse],
)
async def list_pbc_request_samples(
    pbc_request_id: UUID,
    current_user: User = Depends(get_current_user),
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    List all samples for a specific PBC request
    """
    # Verify access to PBC request
    await _verify_pbc_request_access(
        pbc_request_id,
        tenancy.tenant_id,
        current_user.is_platform_admin,
        db,
    )

    query = select(Sample).where(Sample.pbc_request_id == pbc_request_id)
    if not current_user.is_platform_admin:
        query = query.where(Sample.tenant_id == tenancy.tenant_id)

    result = await db.execute(query)
    samples = result.scalars().all()
    return samples


@router.post(
    "/samples",
    response_model=SampleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_sample(
    sample_data: SampleCreate,
    current_user: User = Depends(get_current_user),
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new sample
    """
    try:
        # Verify access to PBC request
        await _verify_pbc_request_access(
            sample_data.pbc_request_id,
            tenancy.tenant_id,
            current_user.is_platform_admin,
            db,
        )

        # Verify tested_by membership if provided
        if sample_data.tested_by_membership_id:
            await _verify_membership_access(
                sample_data.tested_by_membership_id,
                tenancy.tenant_id,
                current_user.is_platform_admin,
                db,
            )

        sample = Sample(
            tenant_id=tenancy.tenant_id,
            pbc_request_id=sample_data.pbc_request_id,
            sample_number=sample_data.sample_number,
            identifier=sample_data.identifier,
            description=sample_data.description,
            status=sample_data.status,
            test_notes=sample_data.test_notes,
            tested_at=sample_data.tested_at,
            tested_by_membership_id=sample_data.tested_by_membership_id,
        )

        db.add(sample)
        await db.commit()
        await db.refresh(sample)
        return sample

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create sample: {str(e)}",
        )


@router.get(
    "/samples/{sample_id}",
    response_model=SampleResponse,
)
async def get_sample(
    sample_id: UUID,
    current_user: User = Depends(get_current_user),
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific sample by ID
    """
    query = select(Sample).where(Sample.id == sample_id)
    if not current_user.is_platform_admin:
        query = query.where(Sample.tenant_id == tenancy.tenant_id)

    result = await db.execute(query)
    sample = result.scalar_one_or_none()

    if not sample:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sample not found or access denied",
        )

    return sample


@router.put(
    "/samples/{sample_id}",
    response_model=SampleResponse,
)
async def update_sample(
    sample_id: UUID,
    sample_data: SampleUpdate,
    current_user: User = Depends(get_current_user),
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Update an existing sample
    """
    try:
        # Fetch the sample
        query = select(Sample).where(Sample.id == sample_id)
        if not current_user.is_platform_admin:
            query = query.where(Sample.tenant_id == tenancy.tenant_id)

        result = await db.execute(query)
        sample = result.scalar_one_or_none()

        if not sample:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sample not found or access denied",
            )

        # Verify tested_by membership if provided
        if sample_data.tested_by_membership_id:
            await _verify_membership_access(
                sample_data.tested_by_membership_id,
                tenancy.tenant_id,
                current_user.is_platform_admin,
                db,
            )

        # Update fields
        if sample_data.identifier is not None:
            sample.identifier = sample_data.identifier
        if sample_data.description is not None:
            sample.description = sample_data.description
        if sample_data.status is not None:
            sample.status = sample_data.status
        if sample_data.test_notes is not None:
            sample.test_notes = sample_data.test_notes
        if sample_data.tested_at is not None:
            sample.tested_at = sample_data.tested_at
        if sample_data.tested_by_membership_id is not None:
            sample.tested_by_membership_id = sample_data.tested_by_membership_id

        await db.commit()
        await db.refresh(sample)
        return sample

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update sample: {str(e)}",
        )


@router.delete(
    "/samples/{sample_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_sample(
    sample_id: UUID,
    current_user: User = Depends(get_current_user),
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a sample
    """
    try:
        query = select(Sample).where(Sample.id == sample_id)
        if not current_user.is_platform_admin:
            query = query.where(Sample.tenant_id == tenancy.tenant_id)

        result = await db.execute(query)
        sample = result.scalar_one_or_none()

        if not sample:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sample not found or access denied",
            )

        await db.delete(sample)
        await db.commit()

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete sample: {str(e)}",
        )
