"""Test attributes endpoints - manage test attributes for controls."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db, get_tenancy_context
from api.tenancy import TenancyContext
from models.test_attribute import (
    TestAttributeCreate,
    TestAttributeResponse,
)
from models.user import User
from services.test_attributes_service import (
    create_test_attribute,
    delete_test_attribute,
    list_test_attributes_for_control,
    update_test_attribute,
)

router = APIRouter()


@router.get(
    "/controls/{control_id}/test-attributes",
    response_model=List[TestAttributeResponse],
)
async def list_control_test_attributes(
    control_id: UUID,
    current_user: User = Depends(get_current_user),
    tenancy: TenancyContext = Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    List all test attributes for a control.
    
    Returns:
        List of test attributes for the specified control.
    
    Raises:
        404 if control not found or user doesn't have access.
    """
    return await list_test_attributes_for_control(
        db,
        membership_ctx=tenancy,
        control_id=control_id,
    )


@router.post(
    "/controls/{control_id}/test-attributes",
    response_model=TestAttributeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_test_attribute_endpoint(
    control_id: UUID,
    test_attribute_data: TestAttributeCreate,
    current_user: User = Depends(get_current_user),
    tenancy: TenancyContext = Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a test attribute for a control.
    
    Note: tenant_id and control_id are derived from context, not client input.
    
    Raises:
        404 if control not found or user doesn't have access.
    """
    return await create_test_attribute(
        db,
        membership_ctx=tenancy,
        control_id=control_id,
        payload=test_attribute_data,
    )


@router.get(
    "/test-attributes/{test_attribute_id}",
    response_model=TestAttributeResponse,
)
async def get_test_attribute(
    test_attribute_id: UUID,
    current_user: User = Depends(get_current_user),
    tenancy: TenancyContext = Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific test attribute by ID.
    
    Returns:
        Test attribute if found and user has access.
    
    Raises:
        404 if test attribute not found or user doesn't have access.
    """
    from repos import test_attributes_repo
    
    test_attribute = await test_attributes_repo.get_by_id(
        db,
        tenant_id=tenancy.tenant_id,
        test_attribute_id=test_attribute_id,
        include_deleted=False,
    )
    
    if not test_attribute:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test attribute not found",
        )
    
    return test_attribute


@router.put(
    "/test-attributes/{test_attribute_id}",
    response_model=TestAttributeResponse,
)
async def update_test_attribute_endpoint(
    test_attribute_id: UUID,
    test_attribute_data: TestAttributeCreate,
    current_user: User = Depends(get_current_user),
    tenancy: TenancyContext = Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a test attribute.
    
    Note: tenant_id and control_id cannot be changed via this endpoint.
    
    Raises:
        404 if test attribute not found or user doesn't have access.
    """
    return await update_test_attribute(
        db,
        membership_ctx=tenancy,
        test_attribute_id=test_attribute_id,
        payload=test_attribute_data,
    )


@router.delete(
    "/test-attributes/{test_attribute_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_test_attribute_endpoint(
    test_attribute_id: UUID,
    current_user: User = Depends(get_current_user),
    tenancy: TenancyContext = Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a test attribute.
    
    Raises:
        404 if test attribute not found or user doesn't have access.
    """
    await delete_test_attribute(
        db,
        membership_ctx=tenancy,
        test_attribute_id=test_attribute_id,
    )
    return None
