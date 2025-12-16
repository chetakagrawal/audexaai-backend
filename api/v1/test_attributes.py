"""Test attributes endpoints - manage test attributes for controls."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db, get_tenancy_context
from models.control import Control
from models.test_attribute import (
    TestAttribute,
    TestAttributeCreate,
    TestAttributeResponse,
)
from models.user import User

router = APIRouter()


@router.get(
    "/controls/{control_id}/test-attributes",
    response_model=List[TestAttributeResponse],
)
async def list_control_test_attributes(
    control_id: UUID,
    current_user: User = Depends(get_current_user),
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    List all test attributes for a control.
    
    Returns:
        List of test attributes for the specified control.
    
    Raises:
        404 if control not found or user doesn't have access.
    """
    try:
        # Verify control exists and belongs to tenant
        control_query = select(Control).where(Control.id == control_id)
        if not current_user.is_platform_admin:
            control_query = control_query.where(Control.tenant_id == tenancy.tenant_id)
        
        result = await db.execute(control_query)
        control = result.scalar_one_or_none()
        
        if not control:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Control not found",
            )
        
        # List all test attributes for this control
        query = select(TestAttribute).where(TestAttribute.control_id == control_id)
        if not current_user.is_platform_admin:
            query = query.where(TestAttribute.tenant_id == tenancy.tenant_id)
        
        result = await db.execute(query)
        test_attributes = result.scalars().all()
        
        return test_attributes
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list test attributes: {str(e)}",
        )


@router.post(
    "/controls/{control_id}/test-attributes",
    response_model=TestAttributeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_test_attribute(
    control_id: UUID,
    test_attribute_data: TestAttributeCreate,
    current_user: User = Depends(get_current_user),
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a test attribute for a control.
    
    Note: tenant_id and control_id are derived from context, not client input.
    
    Raises:
        404 if control not found or user doesn't have access.
    """
    try:
        # Verify control exists and belongs to tenant
        control_query = select(Control).where(Control.id == control_id)
        if not current_user.is_platform_admin:
            control_query = control_query.where(Control.tenant_id == tenancy.tenant_id)
        
        result = await db.execute(control_query)
        control = result.scalar_one_or_none()
        
        if not control:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Control not found",
            )
        
        # Create test attribute
        test_attribute = TestAttribute(
            tenant_id=tenancy.tenant_id,
            control_id=control_id,
            code=test_attribute_data.code,
            name=test_attribute_data.name,
            frequency=test_attribute_data.frequency,
            test_procedure=test_attribute_data.test_procedure,
            expected_evidence=test_attribute_data.expected_evidence,
        )
        
        db.add(test_attribute)
        await db.commit()
        await db.refresh(test_attribute)
        
        return test_attribute
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create test attribute: {str(e)}",
        )


@router.get(
    "/test-attributes/{test_attribute_id}",
    response_model=TestAttributeResponse,
)
async def get_test_attribute(
    test_attribute_id: UUID,
    current_user: User = Depends(get_current_user),
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific test attribute by ID.
    
    Returns:
        Test attribute if found and user has access.
    
    Raises:
        404 if test attribute not found or user doesn't have access.
    """
    try:
        # Build query with tenant filtering
        query = select(TestAttribute).where(TestAttribute.id == test_attribute_id)
        
        if not current_user.is_platform_admin:
            # Regular users: must filter by tenant_id
            query = query.where(TestAttribute.tenant_id == tenancy.tenant_id)
        
        result = await db.execute(query)
        test_attribute = result.scalar_one_or_none()
        
        if not test_attribute:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Test attribute not found",
            )
        
        return test_attribute
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch test attribute: {str(e)}",
        )


@router.put(
    "/test-attributes/{test_attribute_id}",
    response_model=TestAttributeResponse,
)
async def update_test_attribute(
    test_attribute_id: UUID,
    test_attribute_data: TestAttributeCreate,
    current_user: User = Depends(get_current_user),
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a test attribute.
    
    Note: tenant_id and control_id cannot be changed via this endpoint.
    
    Raises:
        404 if test attribute not found or user doesn't have access.
    """
    try:
        # Build query with tenant filtering
        query = select(TestAttribute).where(TestAttribute.id == test_attribute_id)
        
        if not current_user.is_platform_admin:
            # Regular users: must filter by tenant_id
            query = query.where(TestAttribute.tenant_id == tenancy.tenant_id)
        
        result = await db.execute(query)
        test_attribute = result.scalar_one_or_none()
        
        if not test_attribute:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Test attribute not found",
            )
        
        # Update fields (tenant_id and control_id cannot be changed)
        test_attribute.code = test_attribute_data.code
        test_attribute.name = test_attribute_data.name
        test_attribute.frequency = test_attribute_data.frequency
        test_attribute.test_procedure = test_attribute_data.test_procedure
        test_attribute.expected_evidence = test_attribute_data.expected_evidence
        
        await db.commit()
        await db.refresh(test_attribute)
        
        return test_attribute
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update test attribute: {str(e)}",
        )


@router.delete(
    "/test-attributes/{test_attribute_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_test_attribute(
    test_attribute_id: UUID,
    current_user: User = Depends(get_current_user),
    tenancy=Depends(get_tenancy_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a test attribute.
    
    Raises:
        404 if test attribute not found or user doesn't have access.
    """
    try:
        # Build query with tenant filtering
        query = select(TestAttribute).where(TestAttribute.id == test_attribute_id)
        
        if not current_user.is_platform_admin:
            # Regular users: must filter by tenant_id
            query = query.where(TestAttribute.tenant_id == tenancy.tenant_id)
        
        result = await db.execute(query)
        test_attribute = result.scalar_one_or_none()
        
        if not test_attribute:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Test attribute not found",
            )
        
        await db.delete(test_attribute)
        await db.commit()
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete test attribute: {str(e)}",
        )
