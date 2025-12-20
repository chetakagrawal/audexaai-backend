"""ProjectControl model - join table linking projects to controls with version freezing."""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict
import sqlalchemy as sa
from sqlalchemy import String, Boolean, ForeignKey, DateTime, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from db import Base


class ProjectControl(Base):
    """ProjectControl ORM model - links projects to controls with version freezing."""

    __tablename__ = "project_controls"

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
    control_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("controls.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Version freezing: captures control.row_version at the moment this control is added to project
    control_version_num: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    # Override fields (project-specific overrides of control attributes)
    is_key_override: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    frequency_override: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    # Audit trail for adding
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
    added_by_membership_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("user_tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Soft delete (removal from project)
    removed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    removed_by_membership_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("user_tenants.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    # Standard audit columns
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
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

    # Partial unique index: (tenant_id, project_id, control_id) WHERE removed_at IS NULL
    # Allows same control to be re-added after removal (creates new row with new version freeze)
    __table_args__ = (
        Index(
            'ux_project_controls_active',
            'tenant_id',
            'project_id',
            'control_id',
            postgresql_where=sa.text('removed_at IS NULL'),
            unique=True,
        ),
        Index('ix_project_controls_tenant_project', 'tenant_id', 'project_id'),
        Index('ix_project_controls_tenant_control', 'tenant_id', 'control_id'),
        {"comment": "Join table linking projects to controls with tenant isolation and version freezing"},
    )


# Pydantic schemas
class ProjectControlBase(BaseModel):
    """Base project control schema."""

    is_key_override: bool | None = None
    frequency_override: str | None = None
    notes: str | None = None


class ProjectControlCreate(ProjectControlBase):
    """Schema for creating a project control.
    
    Note: tenant_id, project_id, and control_version_num are NOT included - they're set from context server-side.
    """

    control_id: UUID


class ProjectControlUpdate(BaseModel):
    """Schema for updating project control overrides.
    
    Only override fields can be updated. Version and control_id are immutable.
    """

    is_key_override: bool | None = None
    frequency_override: str | None = None
    notes: str | None = None


class ProjectControlResponse(ProjectControlBase):
    """Schema for project control response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    project_id: UUID
    control_id: UUID
    control_version_num: int
    added_at: datetime
    added_by_membership_id: UUID
    removed_at: datetime | None = None
    removed_by_membership_id: UUID | None = None
    created_at: datetime
    updated_at: datetime | None = None
    updated_by_membership_id: UUID | None = None
    deleted_at: datetime | None = None
    deleted_by_membership_id: UUID | None = None

