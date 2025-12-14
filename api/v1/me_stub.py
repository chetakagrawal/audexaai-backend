"""User endpoint for current authenticated user."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from api.deps import get_current_user, get_db
from models.user import User
from models.user_tenant import UserTenant
from models.tenant import Tenant

router = APIRouter()


class MeResponse(BaseModel):
    """Response schema for /me endpoint."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str  # primary_email
    name: str
    tenant_id: UUID | None  # active_tenant_id
    role: str | None  # active_role
    is_platform_admin: bool


class MembershipInfo(BaseModel):
    """Schema for membership information."""

    membership_id: UUID
    tenant_id: UUID
    tenant_name: str
    tenant_slug: str
    role: str
    is_default: bool


class MembershipsResponse(BaseModel):
    """Response schema for /me/memberships endpoint."""

    default_membership_id: UUID | None
    memberships: list[MembershipInfo]


@router.get("/me", response_model=MeResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user.

    Returns:
        MeResponse: Current user data including id, email, name, tenant_id, role, is_platform_admin
    """
    return MeResponse(
        id=current_user.id,
        email=current_user.primary_email,
        name=current_user.name,
        tenant_id=getattr(current_user, "active_tenant_id", None),
        role=getattr(current_user, "active_role", None),
        is_platform_admin=current_user.is_platform_admin,
    )


@router.get("/me/memberships", response_model=MembershipsResponse)
async def get_me_memberships(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all memberships for the current authenticated user.

    This endpoint does NOT require X-Membership-Id header. It returns all memberships
    the user belongs to, along with the default membership ID (if any).

    UI flow:
    1. User logs in → receives JWT token
    2. Call /api/v1/me/memberships → get all memberships and default_membership_id
    3. Pick default_membership_id and send it as X-Membership-Id header on tenant-scoped calls
    4. Navigate to next_url from login response

    Returns:
        MembershipsResponse: All user memberships with tenant details and default membership ID
    """
    # Query all UserTenant rows for the current user, join Tenant to include tenant_name and tenant_slug
    result = await db.execute(
        select(UserTenant, Tenant)
        .join(Tenant, UserTenant.tenant_id == Tenant.id)
        .where(UserTenant.user_id == current_user.id)
        .order_by(UserTenant.created_at.desc())
    )
    membership_rows = result.all()

    memberships = [
        MembershipInfo(
            membership_id=membership.id,
            tenant_id=membership.tenant_id,
            tenant_name=tenant.name,
            tenant_slug=tenant.slug,
            role=membership.role,
            is_default=membership.is_default,
        )
        for membership, tenant in membership_rows
    ]

    # Determine default_membership_id from the membership where is_default=true
    # If multiple, pick the most recent (already ordered by created_at desc)
    default_membership_id = None
    for membership, _ in membership_rows:
        if membership.is_default:
            default_membership_id = membership.id
            break

    return MembershipsResponse(
        default_membership_id=default_membership_id,
        memberships=memberships,
    )

