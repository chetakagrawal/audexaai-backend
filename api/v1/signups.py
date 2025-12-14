"""Signup endpoints - public endpoint for pilot signups."""

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db
from models.signup import (
    AuthMode,
    Signup,
    SignupCreate,
    SignupCreateResponse,
    SignupStatus,
)

router = APIRouter()


@router.post("/signups", response_model=SignupCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_signup(
    signup_data: SignupCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new signup.
    
    This is a public endpoint - no authentication required.
    Creates a signup with status 'pending_review'.
    
    Args:
        signup_data: Signup creation data
        db: Database session
    
    Returns:
        SignupCreateResponse: Created signup with id and status
    
    Raises:
        HTTPException: 422 if validation fails, 500 for server errors
    """
    # TODO: Add basic rate limiting here (e.g., per IP address)
    
    try:
        # Normalize email to lowercase
        email_lower = signup_data.email.lower()
        
        # Validate requested_auth_mode
        if signup_data.requested_auth_mode not in [AuthMode.SSO.value, AuthMode.DIRECT.value]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"requested_auth_mode must be one of: {AuthMode.SSO.value}, {AuthMode.DIRECT.value}",
            )
        
        # Create signup with status pending_review
        signup = Signup(
            id=uuid4(),
            email=email_lower,
            full_name=signup_data.full_name,
            company_name=signup_data.company_name,
            company_domain=signup_data.company_domain,
            requested_auth_mode=signup_data.requested_auth_mode,
            status=SignupStatus.PENDING_REVIEW.value,
            signup_metadata=signup_data.metadata,
        )
        
        db.add(signup)
        await db.commit()
        await db.refresh(signup)
        
        return SignupCreateResponse(
            id=signup.id,
            status=signup.status,
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create signup: {str(e)}",
        )
