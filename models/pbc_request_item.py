"""PBC Request Item model - line item snapshots within a PBC request."""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict
import sqlalchemy as sa
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


class PbcRequestItem(Base):
    """PbcRequestItem ORM model - snapshot of a line item (Control × Application × Test Attribute).
    
    Stores snapshot of effective procedure/evidence at generation time.
    Future overrides or RACM changes must NOT mutate existing items.
    """

    __tablename__ = "pbc_request_items"

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
    pbc_request_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("pbc_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # FK-based entity references (preferred approach)
    project_control_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("project_controls.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    control_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("controls.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    application_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    test_attribute_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("test_attributes.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    # SNAPSHOT FIELDS (immutable after creation)
    pinned_control_version_num: Mapped[int] = mapped_column(Integer, nullable=False)
    pinned_test_attribute_version_num: Mapped[int] = mapped_column(Integer, nullable=False)
    effective_procedure_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    effective_evidence_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_snapshot: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # base|project_global_override|project_app_override
    override_id_snapshot: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
    )
    # WORKFLOW FIELDS (mutable)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="not_started",
    )  # not_started|requested|received|in_review|complete|exception
    assignee_membership_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("user_tenants.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    instructions_extra: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
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
        Index("ix_pbc_request_items_control_id", "control_id"),
        # Unique constraint ensuring no duplicate line items per request
        # Note: Partial index created by migration to handle soft deletes
        {"comment": "PBC request line items with FK-based entity references"},
    )


# Pydantic schemas
class PbcRequestItemBase(BaseModel):
    """Base PBC request item schema."""

    status: str = "not_started"
    assignee_membership_id: UUID | None = None
    instructions_extra: str | None = None
    notes: str | None = None


class PbcRequestItemCreate(BaseModel):
    """Schema for creating a PBC request item with FK-based entity references."""

    # Entity references (at least one of project_control_id or control_id must be provided)
    project_control_id: UUID | None = None
    control_id: UUID | None = None
    application_id: UUID | None = None
    test_attribute_id: UUID | None = None

    # Workflow fields (optional on creation)
    status: str = "not_started"
    assignee_membership_id: UUID | None = None
    instructions_extra: str | None = None
    notes: str | None = None


class PbcRequestItemUpdate(BaseModel):
    """Schema for updating a PBC request item workflow fields."""

    status: str | None = None
    assignee_membership_id: UUID | None = None
    instructions_extra: str | None = None
    notes: str | None = None


class PbcRequestItemResponse(BaseModel):
    """Schema for PBC request item response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    project_id: UUID
    pbc_request_id: UUID
    project_control_id: UUID | None
    control_id: UUID | None
    application_id: UUID | None
    test_attribute_id: UUID | None
    # Snapshot fields
    pinned_control_version_num: int
    pinned_test_attribute_version_num: int
    effective_procedure_snapshot: str | None
    effective_evidence_snapshot: str | None
    source_snapshot: str
    override_id_snapshot: UUID | None
    # Workflow fields
    status: str
    assignee_membership_id: UUID | None
    instructions_extra: str | None
    notes: str | None
    # Audit fields
    created_at: datetime
    created_by_membership_id: UUID
    updated_at: datetime | None = None
    updated_by_membership_id: UUID | None = None
    deleted_at: datetime | None = None
    deleted_by_membership_id: UUID | None = None
    row_version: int

