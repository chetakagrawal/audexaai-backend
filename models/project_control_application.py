"""ProjectControlApplication model - join table linking project controls to applications with version freezing."""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict
import sqlalchemy as sa
from sqlalchemy import String, ForeignKey, DateTime, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from db import Base


class ProjectControlApplication(Base):
    """ProjectControlApplication ORM model - links project controls to applications with version freezing."""

    __tablename__ = "project_control_applications"

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
    application_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Version freezing: captures application.row_version at the moment this application is added to project control
    application_version_num: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="manual",
    )
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
    # Soft delete (removal from project control)
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

    # Partial unique index: (tenant_id, project_control_id, application_id) WHERE removed_at IS NULL
    # Allows same application to be re-added after removal (creates new row with new version freeze)
    __table_args__ = (
        Index(
            'ux_project_control_apps_active',
            'tenant_id',
            'project_control_id',
            'application_id',
            postgresql_where=sa.text('removed_at IS NULL'),
            unique=True,
        ),
        Index('ix_pca_tenant_project_control', 'tenant_id', 'project_control_id'),
        Index('ix_pca_tenant_application', 'tenant_id', 'application_id'),
        {"comment": "Join table linking project controls to applications with tenant isolation and version freezing"},
    )


# Pydantic schemas
class ProjectControlApplicationCreate(BaseModel):
    """Schema for creating a project control application mapping.
    
    Note: tenant_id, project_control_id, and application_version_num are NOT included - they're set from context server-side.
    """

    application_id: UUID


class ProjectControlApplicationResponse(BaseModel):
    """Schema for project control application response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    project_control_id: UUID
    application_id: UUID
    application_version_num: int
    source: str
    added_at: datetime
    added_by_membership_id: UUID
    removed_at: datetime | None = None
    removed_by_membership_id: UUID | None = None

