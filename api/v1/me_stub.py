"""User endpoint for current authenticated user."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from uuid import UUID

from api.deps import get_current_user
from models.user import User

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

