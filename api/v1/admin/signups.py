"""Admin endpoints for managing signups."""

from datetime import datetime, UTC
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db
from models.signup import Signup, SignupRejectRequest, SignupResponse, SignupStatus
from models.user import User

router = APIRouter()


def require_platform_admin(current_user: User = Depends(get_current_user)) -> None:
    """
    Dependency to require platform admin access.
    
    Args:
        current_user: Current authenticated user
    
    Raises:
        HTTPException: 403 if user is not a platform admin
    """
    if not current_user.is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires platform admin access",
        )


@router.get("/admin/signups", response_model=List[SignupResponse])
async def list_signups(
    status: Optional[str] = Query(None, alias="status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    _platform_admin: None = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    List signups (platform admin only).
    
    Args:
        status: Optional filter by status
        limit: Maximum number of results (1-1000, default 100)
        offset: Number of results to skip (default 0)
        _platform_admin: Dependency that ensures user is platform admin
        db: Database session
    
    Returns:
        List[SignupResponse]: List of signups
    """
    try:
        query = select(Signup).order_by(Signup.created_at.desc())
        
        # Filter by status if provided
        if status:
            try:
                status_enum = SignupStatus(status)
                query = query.where(Signup.status == status_enum.value)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status: {status}",
                )
        
        # Apply pagination
        query = query.limit(limit).offset(offset)
        
        result = await db.execute(query)
        signups = result.scalars().all()
        
        return signups
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch signups: {str(e)}",
        )


@router.post("/admin/signups/{signup_id}/approve", response_model=SignupResponse)
async def approve_signup(
    signup_id: UUID,
    _platform_admin: None = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Approve a signup (platform admin only).
    
    Sets status to 'approved' and records approved_at timestamp.
    Cannot approve already rejected signups.
    
    Args:
        signup_id: ID of the signup to approve
        _platform_admin: Dependency that ensures user is platform admin
        db: Database session
    
    Returns:
        SignupResponse: Updated signup
    
    Raises:
        HTTPException: 404 if signup not found, 409 if already rejected
    """
    try:
        result = await db.execute(
            select(Signup).where(Signup.id == signup_id)
        )
        signup = result.scalar_one_or_none()
        
        if not signup:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Signup not found",
            )
        
        # Cannot approve rejected signups
        if signup.status == SignupStatus.REJECTED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot approve a rejected signup",
            )
        
        # Update signup
        signup.status = SignupStatus.APPROVED.value
        signup.approved_at = datetime.now(UTC)
        
        await db.commit()
        await db.refresh(signup)
        
        return signup
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve signup: {str(e)}",
        )


@router.post("/admin/signups/{signup_id}/reject", response_model=SignupResponse)
async def reject_signup(
    signup_id: UUID,
    reject_data: SignupRejectRequest,
    _platform_admin: None = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Reject a signup (platform admin only).
    
    Sets status to 'rejected' and optionally saves rejection_reason in metadata.
    Cannot reject already rejected signups.
    
    Args:
        signup_id: ID of the signup to reject
        reject_data: Request body with optional rejection reason (saved in metadata.rejection_reason)
        _platform_admin: Dependency that ensures user is platform admin
        db: Database session
    
    Returns:
        SignupResponse: Updated signup
    
    Raises:
        HTTPException: 404 if signup not found, 409 if already rejected
    """
    try:
        result = await db.execute(
            select(Signup).where(Signup.id == signup_id)
        )
        signup = result.scalar_one_or_none()
        
        if not signup:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Signup not found",
            )
        
        # Cannot reject already rejected signups
        if signup.status == SignupStatus.REJECTED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Signup is already rejected",
            )
        
        # Update signup
        signup.status = SignupStatus.REJECTED.value
        
        # Update metadata with rejection reason if provided
        if reject_data.reason:
            if signup.signup_metadata is None:
                signup.signup_metadata = {}
            signup.signup_metadata["rejection_reason"] = reject_data.reason
        
        await db.commit()
        await db.refresh(signup)
        
        return signup
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reject signup: {str(e)}",
        )
