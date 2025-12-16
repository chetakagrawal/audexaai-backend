"""PBC requests endpoints - manage PBC (Prepared By Client) requests for evidence collection."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db, get_tenancy_context
from models.application import Application
from models.control import Control
from models.pbc_request import (
    PbcRequest,
    PbcRequestCreate,
    PbcRequestResponse,
    PbcRequestUpdate,
)
from models.project import Project
from models.user import User
from models.user_tenant import UserTenant

router = APIRouter()


async def _verify_project_access(
    project_id: UUID,
    tenant_id: UUID,
    is_platform_admin: bool,
    db: AsyncSession,
) -> Project:
    """Verify project exists and user has access."""
    query = select(Project).where(Project.id == project_id)
    if not is_platform_admin:
        query = query.where(Project.tenant_id == tenant_id)
    
    result = await db.execute(query)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return project


async def _verify_application_access(
    application_id: UUID,
    tenant_id: UUID,
    is_platform_admin: bool,
    db: AsyncSession,
) -> Application:
    """Verify application exists and user has access."""
    query = select(Application).where(Application.id == application_id)
    if not is_platform_admin:
        query = query.where(Application.tenant_id == tenant_id)
    
    result = await db.execute(query)
    application = result.scalar_one_or_none()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )
    return application


async def _verify_control_access(
    control_id: UUID,
    tenant_id: UUID,
    is_platform_admin: bool,
    db: AsyncSession,
) -> Control:
    """Verify control exists and user has access."""
    query = select(Control).where(Control.id == control_id)
    if not is_platform_admin:
        query = query.where(Control.tenant_id == tenant_id)
    
    result = await db.execute(query)
    control = result.scalar_one_or_none()
    
    if not control:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Control not found",
        )
    return control


async def _verify_membership_access(
    membership_id: UUID,
    tenant_id: UUID,
    is_platform_admin: bool,
    db: AsyncSession,
) -> UserTenant:
    """Verify membership exists and belongs to tenant."""
    query = select(UserTenant).where(UserTenant.id == membership_id)
    if not is_platform_admin:
        query = query.where(UserTenant.tenant_id == tenant_id)
    
    result = await db.execute(query)
    membership = result.scalar_one_or_none()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Owner membership not found",
        )
    return membership


@router.get(
    "/projects/{project_id}/pbc-requests",
    response_model=List[PbcRequestResponse],
)
async def list_project_pbc_requests(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    List all PBC requests for a project.
    
    Returns:
        List of PBC requests for the specified project.
    
    Raises:
        404 if project not found or user doesn't have access.
    """
    try:
        # Verify project exists and belongs to tenant
        await _verify_project_access(
            project_id,
            tenancy.tenant_id,
            current_user.is_platform_admin,
            db,
        )
        
        # List all PBC requests for this project
        query = select(PbcRequest).where(PbcRequest.project_id == project_id)
        if not current_user.is_platform_admin:
            query = query.where(PbcRequest.tenant_id == tenancy.tenant_id)
        
        result = await db.execute(query)
        pbc_requests = result.scalars().all()
        
        return pbc_requests
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list PBC requests: {str(e)}",
        )


@router.get(
    "/pbc-requests",
    response_model=List[PbcRequestResponse],
)
async def list_pbc_requests(
    current_user: User = Depends(get_current_user),
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    List all PBC requests for the tenant.
    
    Returns:
        List of all PBC requests accessible to the user.
    """
    try:
        query = select(PbcRequest)
        if not current_user.is_platform_admin:
            query = query.where(PbcRequest.tenant_id == tenancy.tenant_id)
        
        result = await db.execute(query)
        pbc_requests = result.scalars().all()
        
        return pbc_requests
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list PBC requests: {str(e)}",
        )


@router.post(
    "/pbc-requests",
    response_model=PbcRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_pbc_request(
    pbc_request_data: PbcRequestCreate,
    current_user: User = Depends(get_current_user),
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a PBC request.
    
    Note: tenant_id is derived from context, not client input.
    
    Raises:
        404 if project, application, control, or owner membership not found.
    """
    try:
        # Verify all referenced entities exist and belong to tenant
        await _verify_project_access(
            pbc_request_data.project_id,
            tenancy.tenant_id,
            current_user.is_platform_admin,
            db,
        )
        await _verify_application_access(
            pbc_request_data.application_id,
            tenancy.tenant_id,
            current_user.is_platform_admin,
            db,
        )
        await _verify_control_access(
            pbc_request_data.control_id,
            tenancy.tenant_id,
            current_user.is_platform_admin,
            db,
        )
        await _verify_membership_access(
            pbc_request_data.owner_membership_id,
            tenancy.tenant_id,
            current_user.is_platform_admin,
            db,
        )
        
        # Create PBC request
        pbc_request = PbcRequest(
            tenant_id=tenancy.tenant_id,
            project_id=pbc_request_data.project_id,
            application_id=pbc_request_data.application_id,
            control_id=pbc_request_data.control_id,
            owner_membership_id=pbc_request_data.owner_membership_id,
            title=pbc_request_data.title,
            samples_requested=pbc_request_data.samples_requested,
            due_date=pbc_request_data.due_date,
            status=pbc_request_data.status,
        )
        
        db.add(pbc_request)
        await db.commit()
        await db.refresh(pbc_request)
        
        return pbc_request
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create PBC request: {str(e)}",
        )


@router.get(
    "/pbc-requests/{pbc_request_id}",
    response_model=PbcRequestResponse,
)
async def get_pbc_request(
    pbc_request_id: UUID,
    current_user: User = Depends(get_current_user),
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific PBC request by ID.
    
    Returns:
        PBC request if found and user has access.
    
    Raises:
        404 if PBC request not found or user doesn't have access.
    """
    try:
        query = select(PbcRequest).where(PbcRequest.id == pbc_request_id)
        
        if not current_user.is_platform_admin:
            query = query.where(PbcRequest.tenant_id == tenancy.tenant_id)
        
        result = await db.execute(query)
        pbc_request = result.scalar_one_or_none()
        
        if not pbc_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="PBC request not found",
            )
        
        return pbc_request
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch PBC request: {str(e)}",
        )


@router.put(
    "/pbc-requests/{pbc_request_id}",
    response_model=PbcRequestResponse,
)
async def update_pbc_request(
    pbc_request_id: UUID,
    pbc_request_data: PbcRequestUpdate,
    current_user: User = Depends(get_current_user),
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a PBC request.
    
    Note: IDs (tenant_id, project_id, application_id, control_id, owner_membership_id)
    cannot be changed via this endpoint.
    
    Raises:
        404 if PBC request not found or user doesn't have access.
    """
    try:
        query = select(PbcRequest).where(PbcRequest.id == pbc_request_id)
        
        if not current_user.is_platform_admin:
            query = query.where(PbcRequest.tenant_id == tenancy.tenant_id)
        
        result = await db.execute(query)
        pbc_request = result.scalar_one_or_none()
        
        if not pbc_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="PBC request not found",
            )
        
        # Update only provided fields
        if pbc_request_data.title is not None:
            pbc_request.title = pbc_request_data.title
        if pbc_request_data.samples_requested is not None:
            pbc_request.samples_requested = pbc_request_data.samples_requested
        if pbc_request_data.due_date is not None:
            pbc_request.due_date = pbc_request_data.due_date
        if pbc_request_data.status is not None:
            pbc_request.status = pbc_request_data.status
        
        await db.commit()
        await db.refresh(pbc_request)
        
        return pbc_request
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update PBC request: {str(e)}",
        )


@router.delete(
    "/pbc-requests/{pbc_request_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_pbc_request(
    pbc_request_id: UUID,
    current_user: User = Depends(get_current_user),
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a PBC request.
    
    Raises:
        404 if PBC request not found or user doesn't have access.
    """
    try:
        query = select(PbcRequest).where(PbcRequest.id == pbc_request_id)
        
        if not current_user.is_platform_admin:
            query = query.where(PbcRequest.tenant_id == tenancy.tenant_id)
        
        result = await db.execute(query)
        pbc_request = result.scalar_one_or_none()
        
        if not pbc_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="PBC request not found",
            )
        
        await db.delete(pbc_request)
        await db.commit()
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete PBC request: {str(e)}",
        )
