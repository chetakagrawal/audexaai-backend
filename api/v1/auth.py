"""Authentication endpoints (DEV-ONLY)."""

from datetime import datetime, UTC
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import config
from api.deps import get_db
from api.v1.admin.utils import ensure_unique_slug, generate_slug
from auth.jwt import create_dev_token
from models.auth_identity import AuthIdentity
from models.signup import AuthMode, Signup
from models.tenant import Tenant
from models.user import User
from models.user_tenant import UserTenant

router = APIRouter()


class DevLoginRequest(BaseModel):
    """Request schema for dev login."""

    email: EmailStr
    tenant_slug: str | None = None  # Optional - only used if user has no existing memberships
    name: str | None = None
    role: str = "admin"


class MembershipInfo(BaseModel):
    """Schema for membership information in login response."""

    membership_id: str  # UserTenant.id
    tenant_id: str
    tenant_name: str
    role: str


class DevLoginResponse(BaseModel):
    """Response schema for dev login."""

    access_token: str
    token_type: str = "bearer"
    user_id: str
    tenant_id: str | None
    role: str
    is_platform_admin: bool
    memberships: list[MembershipInfo]  # List of all user memberships
    default_membership_id: str | None  # ID of default membership (where is_default=true)
    next_url: str  # Next URL to navigate to after login


@router.post("/auth/dev-login", response_model=DevLoginResponse)
async def dev_login(
    request: DevLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    DEV-ONLY endpoint to login user and return JWT token.

    This endpoint:
    - Finds or creates a user by email
    - For existing users: uses their existing default membership (prevents duplicate tenants)
    - For new users: creates a tenant (from tenant_slug if provided, or generates from email)
    - Creates/finds AuthIdentity with provider="dev"
    - Returns a signed JWT with user_id, tenant_id, role, is_platform_admin

    Args:
        request: Login request with email, optional tenant_slug (only used for new users), optional name and role
        db: Database session

    Returns:
        DevLoginResponse: JWT token and user information
    """
    # Check if dev environment
    if config.settings.APP_ENV == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dev login is not available in production",
        )

    email_lower = request.email.lower()

    # Check if user has a signup that requested SSO or already has an oidc AuthIdentity
    # SSO users MUST use SSO login - dev-login is not allowed in any environment
    result = await db.execute(
        select(Signup).where(Signup.email == email_lower).order_by(Signup.created_at.desc())
    )
    signup = result.scalar_one_or_none()
    
    # Check if signup requested SSO
    if signup and signup.requested_auth_mode == AuthMode.SSO.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account requires SSO authentication. Direct login is not available. Please use your company's SSO provider to sign in.",
        )
    
    # Also check if user already has an oidc AuthIdentity (created during SSO promotion)
    result = await db.execute(
        select(AuthIdentity).where(
            AuthIdentity.provider == "oidc",
            AuthIdentity.provider_subject == email_lower,
        )
    )
    existing_oidc_identity = result.scalar_one_or_none()
    
    if existing_oidc_identity:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account requires SSO authentication. Direct login is not available. Please use your company's SSO provider to sign in.",
        )

    # Find or create user by primary_email
    result = await db.execute(
        select(User).where(User.primary_email == email_lower)
    )
    user = result.scalar_one_or_none()

    if not user:
        # Create new user
        user_name = request.name or request.email.split("@")[0].replace(".", " ").title()
        user = User(
            id=uuid4(),
            primary_email=email_lower,
            name=user_name,
            is_platform_admin=False,  # Dev login doesn't create platform admins
            is_active=True,
        )
        db.add(user)
        await db.flush()  # Flush to get user.id

    # Check if user has existing memberships FIRST
    # This prevents creating duplicate tenants for users who already have them
    # IMPORTANT: Always check this BEFORE creating any tenant
    result = await db.execute(
        select(UserTenant, Tenant)
        .join(Tenant, UserTenant.tenant_id == Tenant.id)
        .where(UserTenant.user_id == user.id)
        .order_by(UserTenant.is_default.desc(), UserTenant.created_at.desc())
    )
    existing_memberships = result.all()

    # If user has existing memberships, ALWAYS use the default one (or most recent)
    # IGNORE tenant_slug from request completely - user already has a tenant(s)
    if existing_memberships:
        user_tenant, tenant = existing_memberships[0]  # First is default or most recent
        
        # Update role if provided and different
        if request.role and user_tenant.role != request.role:
            user_tenant.role = request.role
    else:
        # New user - need to create tenant and membership
        # Generate tenant slug from email if not provided
        if request.tenant_slug:
            tenant_slug = request.tenant_slug
        else:
            # Generate default slug from email local part
            email_local = email_lower.split("@")[0]
            base_slug = generate_slug(f"{email_local} workspace")
            tenant_slug = await ensure_unique_slug(db, base_slug)
        
        # Find or create tenant
        result = await db.execute(
            select(Tenant).where(Tenant.slug == tenant_slug)
        )
        tenant = result.scalar_one_or_none()

        if not tenant:
            # Create new tenant
            tenant = Tenant(
                id=uuid4(),
                name=tenant_slug.replace("-", " ").title(),
                slug=tenant_slug,
                status="active",
            )
            db.add(tenant)
            await db.flush()  # Flush to get tenant.id

        # Create user-tenant relationship (first membership, so it's default)
        user_tenant = UserTenant(
            id=uuid4(),
            user_id=user.id,
            tenant_id=tenant.id,
            role=request.role,
            is_default=True,  # First membership is always default
        )
        db.add(user_tenant)

    # Find or create auth identity
    result = await db.execute(
        select(AuthIdentity).where(
            AuthIdentity.provider == "dev",
            AuthIdentity.provider_subject == email_lower,
        )
    )
    auth_identity = result.scalar_one_or_none()

    if not auth_identity:
        # Create new auth identity
        auth_identity = AuthIdentity(
            id=uuid4(),
            user_id=user.id,
            provider="dev",
            provider_subject=email_lower,
            email=email_lower,
            email_verified=True,  # Dev login assumes verified
        )
        db.add(auth_identity)

    # Update last login
    auth_identity.last_login_at = datetime.now(UTC)

    await db.commit()

    # Create JWT token
    access_token = create_dev_token(
        user_id=user.id,
        tenant_id=tenant.id,
        role=user_tenant.role,
        is_platform_admin=user.is_platform_admin,
    )

    # Get all memberships for this user
    result = await db.execute(
        select(UserTenant, Tenant)
        .join(Tenant, UserTenant.tenant_id == Tenant.id)
        .where(UserTenant.user_id == user.id)
        .order_by(UserTenant.created_at.desc())
    )
    membership_rows = result.all()

    memberships = [
        MembershipInfo(
            membership_id=str(membership.id),
            tenant_id=str(membership.tenant_id),
            tenant_name=tenant_row.name,
            role=membership.role,
        )
        for membership, tenant_row in membership_rows
    ]

    # Determine default_membership_id from the membership where is_default=true
    # If multiple, pick the most recent (already ordered by created_at desc)
    default_membership_id = None
    for membership, _ in membership_rows:
        if membership.is_default:
            default_membership_id = str(membership.id)
            break

    # Set next_url based on whether user has at least one membership
    # UI should: login → store JWT → call /api/v1/me/memberships →
    # pick default_membership_id and send as X-Membership-Id on tenant-scoped calls → navigate to next_url
    next_url = "/portal/dashboard" if len(memberships) > 0 else "/no-access"

    return DevLoginResponse(
        access_token=access_token,
        user_id=str(user.id),
        tenant_id=str(tenant.id),
        role=user_tenant.role,
        is_platform_admin=user.is_platform_admin,
        memberships=memberships,
        default_membership_id=default_membership_id,
        next_url=next_url,
    )
