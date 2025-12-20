"""ProjectTestAttributeOverride model - project-level overrides for test attributes."""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict
import sqlalchemy as sa
from sqlalchemy import ForeignKey, DateTime, Text, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from db import Base


class ProjectTestAttributeOverride(Base):
    """ProjectTestAttributeOverride ORM model - project-level customization of test attributes."""

    __tablename__ = "project_test_attribute_overrides"

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
    project_control_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("project_controls.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    test_attribute_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("test_attributes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # NULL means applies to all apps for this project_control
    application_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    # Freeze from test_attributes.row_version at creation
    base_test_attribute_version_num: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    # Override fields - NULL means no override for that field
    name_override: Mapped[str | None] = mapped_column(Text, nullable=True)
    frequency_override: Mapped[str | None] = mapped_column(Text, nullable=True)
    procedure_override: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_evidence_override: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Version-ready metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
    created_by_membership_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("user_tenants.id", ondelete="RESTRICT"),
        nullable=True,
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
        # Partial unique index: control-wide overrides (application_id IS NULL)
        Index(
            'ux_ptao_active_global',
            'tenant_id',
            'project_control_id',
            'test_attribute_id',
            postgresql_where=sa.text('deleted_at IS NULL AND application_id IS NULL'),
            unique=True,
        ),
        # Partial unique index: app-specific overrides (application_id IS NOT NULL)
        Index(
            'ux_ptao_active_app',
            'tenant_id',
            'project_control_id',
            'application_id',
            'test_attribute_id',
            postgresql_where=sa.text('deleted_at IS NULL AND application_id IS NOT NULL'),
            unique=True,
        ),
        # Supporting indexes
        Index('ix_ptao_tenant_project_control', 'tenant_id', 'project_control_id'),
        Index('ix_ptao_tenant_test_attribute', 'tenant_id', 'test_attribute_id'),
        {"comment": "Project-level overrides for test attributes with tenant isolation and version freezing"},
    )


# Pydantic schemas
class ProjectTestAttributeOverrideUpsert(BaseModel):
    """Schema for creating/updating a project test attribute override."""
    
    application_id: UUID | None = None
    name_override: str | None = None
    frequency_override: str | None = None
    procedure_override: str | None = None
    expected_evidence_override: str | None = None
    notes: str | None = None


class ProjectTestAttributeOverrideResponse(BaseModel):
    """Schema for project test attribute override response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    project_control_id: UUID
    test_attribute_id: UUID
    application_id: UUID | None
    base_test_attribute_version_num: int
    name_override: str | None
    frequency_override: str | None
    procedure_override: str | None
    expected_evidence_override: str | None
    notes: str | None
    created_at: datetime
    created_by_membership_id: UUID | None
    updated_at: datetime | None
    updated_by_membership_id: UUID | None
    deleted_at: datetime | None
    deleted_by_membership_id: UUID | None
    row_version: int


class EffectiveTestAttributeResponse(BaseModel):
    """Schema for resolved/effective test attribute with overrides applied."""

    # Base fields from test_attribute
    test_attribute_id: UUID
    code: str
    name: str
    frequency: str | None
    test_procedure: str | None
    expected_evidence: str | None
    
    # Metadata about override source
    source: str  # 'base' | 'project_global_override' | 'project_app_override'
    override_id: UUID | None  # ID of the override if applicable
    base_test_attribute_version_num: int  # Version from base or override

