"""Admin endpoints for managing signups."""

from datetime import datetime, UTC
from typing import List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db
from api.v1.admin.utils import ensure_unique_slug, generate_slug
from models.auth_identity import AuthIdentity
from models.signup import (
    AuthMode,
    Signup,
    SignupPromoteResponse,
    SignupRejectRequest,
    SignupResponse,
    SignupStatus,
)
from models.tenant import Tenant
from models.user import User
from models.user_tenant import UserTenant

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
        
        # Convert to SignupResponse list to ensure metadata field is included
        return [
            SignupResponse(
                id=signup.id,
                email=signup.email,
                full_name=signup.full_name,
                company_name=signup.company_name,
                company_domain=signup.company_domain,
                requested_auth_mode=signup.requested_auth_mode,
                status=signup.status,
                created_at=signup.created_at,
                updated_at=signup.updated_at,
                approved_at=signup.approved_at,
                rejected_at=signup.rejected_at,
                promoted_at=signup.promoted_at,
                metadata=signup.signup_metadata,  # Map signup_metadata to metadata
            )
            for signup in signups
        ]
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
        
        # Convert to SignupResponse to ensure metadata field is included
        return SignupResponse(
            id=signup.id,
            email=signup.email,
            full_name=signup.full_name,
            company_name=signup.company_name,
            company_domain=signup.company_domain,
            requested_auth_mode=signup.requested_auth_mode,
            status=signup.status,
            created_at=signup.created_at,
            updated_at=signup.updated_at,
            approved_at=signup.approved_at,
            promoted_at=signup.promoted_at,
            metadata=signup.signup_metadata,  # Map signup_metadata to metadata
        )
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
        signup.rejected_at = datetime.now(UTC)
        
        # Update metadata with rejection reason if provided
        if reject_data.reason:
            if signup.signup_metadata is None:
                signup.signup_metadata = {}
            signup.signup_metadata["rejection_reason"] = reject_data.reason
        
        await db.commit()
        await db.refresh(signup)
        
        # Convert to SignupResponse to ensure metadata field is included
        return SignupResponse(
            id=signup.id,
            email=signup.email,
            full_name=signup.full_name,
            company_name=signup.company_name,
            company_domain=signup.company_domain,
            requested_auth_mode=signup.requested_auth_mode,
            status=signup.status,
            created_at=signup.created_at,
            updated_at=signup.updated_at,
            approved_at=signup.approved_at,
            promoted_at=signup.promoted_at,
            metadata=signup.signup_metadata,  # Map signup_metadata to metadata
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reject signup: {str(e)}",
        )


@router.post("/admin/signups/{signup_id}/promote", response_model=SignupPromoteResponse)
async def promote_signup(
    signup_id: UUID,
    _platform_admin: None = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Promote a signup to create tenant, user, membership, and auth identity.
    
    This endpoint is idempotent - if signup is already promoted, returns existing IDs.
    Requires signup status to be 'approved' or 'verified'.
    All operations run in a single database transaction for safety.
    
    Args:
        signup_id: ID of the signup to promote
        _platform_admin: Dependency that ensures user is platform admin
        db: Database session
    
    Returns:
        SignupPromoteResponse: Created tenant_id, user_id, membership_id, and status
    
    Raises:
        HTTPException: 404 if signup not found, 400 if status invalid
    """
    try:
        # Load signup
        result = await db.execute(
            select(Signup).where(Signup.id == signup_id)
        )
        signup = result.scalar_one_or_none()
        
        if not signup:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Signup not found",
            )
        
        # Check if already promoted (idempotency)
        if signup.status == SignupStatus.PROMOTED.value:
            if signup.tenant_id and signup.user_id and signup.membership_id:
                return SignupPromoteResponse(
                    tenant_id=signup.tenant_id,
                    user_id=signup.user_id,
                    membership_id=signup.membership_id,
                    status=signup.status,
                )
        
        # Require status to be approved or verified
        if signup.status not in [SignupStatus.APPROVED.value, SignupStatus.VERIFIED.value]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Signup must be approved or verified to promote. Current status: {signup.status}",
            )
        
        email_lower = signup.email.lower()
        email_local = email_lower.split("@")[0]
        
        # 1. Create or get Tenant
        tenant_name = signup.company_name
        if not tenant_name:
            # Fallback to email local-part + "Workspace"
            tenant_name = f"{email_local.title()} Workspace"
        
        base_slug = generate_slug(tenant_name)
        tenant_slug = await ensure_unique_slug(db, base_slug)
        
        tenant = Tenant(
            id=uuid4(),
            name=tenant_name,
            slug=tenant_slug,
            status="active",
        )
        db.add(tenant)
        await db.flush()  # Flush to get tenant.id
        
        # 2. Upsert User by primary_email (case-insensitive check)
        result = await db.execute(
            select(User).where(User.primary_email == email_lower)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            user_name = signup.full_name or email_local.title()
            user = User(
                id=uuid4(),
                primary_email=email_lower,
                name=user_name,
                is_platform_admin=False,
                is_active=True,
            )
            db.add(user)
            await db.flush()  # Flush to get user.id
        
        # 3. Create UserTenant membership
        membership = UserTenant(
            id=uuid4(),
            user_id=user.id,
            tenant_id=tenant.id,
            role="owner",
            is_default=True,
        )
        db.add(membership)
        await db.flush()  # Flush to get membership.id
        
        # 4. Create AuthIdentity placeholder
        if signup.requested_auth_mode == AuthMode.SSO.value:
            provider = "oidc"
            # Mark SSO as not configured in metadata
            if signup.signup_metadata is None:
                signup.signup_metadata = {}
            signup.signup_metadata["sso_status"] = "not_configured"
        else:
            provider = "dev"
        
        auth_identity = AuthIdentity(
            id=uuid4(),
            user_id=user.id,
            provider=provider,
            provider_subject=email_lower,
            email=email_lower,
            email_verified=False,  # Will be verified after SSO setup or password setup
        )
        db.add(auth_identity)
        
        # 5. Update signup
        signup.status = SignupStatus.PROMOTED.value
        signup.promoted_at = datetime.now(UTC)
        signup.tenant_id = tenant.id
        signup.user_id = user.id
        signup.membership_id = membership.id
        
        # Commit transaction
        await db.commit()
        await db.refresh(signup)
        
        return SignupPromoteResponse(
            tenant_id=tenant.id,
            user_id=user.id,
            membership_id=membership.id,
            status=signup.status,
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to promote signup: {str(e)}",
        )
