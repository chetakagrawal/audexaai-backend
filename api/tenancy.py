"""Tenancy context and helpers for cross-tenant leak prevention."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Query

from models.user import User
from models.user_tenant import UserTenant


class TenancyContext:
    """Context for tenant-scoped operations."""

    def __init__(self, membership_id: UUID, tenant_id: UUID, role: str):
        """
        Initialize tenancy context.

        Args:
            membership_id: UserTenant.id (membership record ID)
            tenant_id: Tenant ID
            role: User's role in the tenant
        """
        self.membership_id = membership_id
        self.tenant_id = tenant_id
        self.role = role

    @classmethod
    def from_user(cls, user: User) -> "TenancyContext | None":
        """
        Create TenancyContext from user object.

        Args:
            user: User object with active_tenant_id and active_role attached

        Returns:
            TenancyContext if user has active tenant, None otherwise
        """
        tenant_id = getattr(user, "active_tenant_id", None)
        role = getattr(user, "active_role", None)
        membership_id = getattr(user, "active_membership_id", None)

        if not tenant_id or not role or not membership_id:
            return None

        return cls(membership_id=membership_id, tenant_id=tenant_id, role=role)


async def require_membership(
    active_membership_id: UUID | None,
    user_id: UUID,
    db: AsyncSession,
) -> UserTenant:
    """
    Verify user has active membership and return membership record.

    Args:
        active_membership_id: UserTenant.id from token/context
        user_id: User ID to verify
        db: Database session

    Returns:
        UserTenant: The membership record

    Raises:
        HTTPException: 403 if membership is invalid or user doesn't have access
    """
    if not active_membership_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active membership. User must belong to a tenant.",
        )

    # Load membership record
    result = await db.execute(
        select(UserTenant).where(UserTenant.id == active_membership_id)
    )
    membership = result.scalar_one_or_none()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Membership not found",
        )

    # Verify membership belongs to the user
    if membership.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Membership does not belong to user",
        )

    return membership


def tenant_filter(query: Query, tenant_id: UUID, tenant_id_column=None):
    """
    Filter query to only return results for the specified tenant.

    Args:
        query: SQLAlchemy query object
        tenant_id: Tenant ID to filter by
        tenant_id_column: Optional column to filter on (auto-detected if model has tenant_id)

    Returns:
        Query: Filtered query

    Example:
        query = select(Project)
        filtered = tenant_filter(query, tenant_id, Project.tenant_id)
    """
    if tenant_id_column is None:
        # Try to auto-detect tenant_id column from the query
        # This is a simple implementation - may need refinement
        try:
            # Get the first entity from the query
            entities = query.column_descriptions
            if entities:
                entity = entities[0]["entity"]
                if hasattr(entity, "tenant_id"):
                    tenant_id_column = entity.tenant_id
        except (AttributeError, KeyError):
            pass

    if tenant_id_column is None:
        raise ValueError(
            "Cannot auto-detect tenant_id column. Please provide tenant_id_column parameter."
        )

    return query.where(tenant_id_column == tenant_id)

