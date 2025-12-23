"""PBC Request model - PBC (Prepared By Client) requests for evidence collection."""

from datetime import date, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict
import sqlalchemy as sa
from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


class PbcRequest(Base):
    """PbcRequest ORM model v2 - container for PBC requests with line items.
    
    Each PBC request is associated with:
    - A project (the audit engagement)
    - Contains multiple line items (via pbc_request_items)
    """

    __tablename__ = "pbc_requests"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="draft",
    )  # draft|issued|in_progress|submitted|accepted|returned|closed
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Audit fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
    created_by_membership_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("user_tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        onupdate=datetime.utcnow,
    )
    updated_by_membership_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("user_tenants.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    deleted_by_membership_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("user_tenants.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    row_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    __table_args__ = (
        # Indexes are created by migration m1n2o3p4q5r6
        {"comment": "PBC requests v2 - containers for evidence collection requests"},
    )


# Pydantic schemas
class PbcRequestBase(BaseModel):
    """Base PBC request schema."""

    title: str
    due_date: date | None = None
    status: str = "draft"
    instructions: str | None = None


class PbcRequestCreate(PbcRequestBase):
    """Schema for creating a PBC request.
    
    Note: tenant_id and project_id are set from context/server-side.
    """

    pass


class PbcRequestUpdate(BaseModel):
    """Schema for updating a PBC request.
    
    Note: IDs cannot be changed after creation.
    """

    title: str | None = None
    due_date: date | None = None
    status: str | None = None
    instructions: str | None = None


class PbcRequestResponse(PbcRequestBase):
    """Schema for PBC request response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    project_id: UUID
    created_at: datetime
    created_by_membership_id: UUID
    updated_at: datetime | None = None
    updated_by_membership_id: UUID | None = None
    deleted_at: datetime | None = None
    deleted_by_membership_id: UUID | None = None
    row_version: int
