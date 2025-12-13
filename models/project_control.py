"""ProjectControl model - join table linking projects to controls."""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict
from sqlalchemy import String, Boolean, ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from db import Base


class ProjectControl(Base):
    """ProjectControl ORM model - links projects to controls with overrides."""

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
        ForeignKey("controls.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_key_override: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    frequency_override: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    # Composite unique constraint: (tenant_id, project_id, control_id)
    # Ensures a control can only be added once per project, scoped by tenant
    __table_args__ = (
        UniqueConstraint("tenant_id", "project_id", "control_id", name="uq_project_control_tenant"),
        {"comment": "Join table linking projects to controls with tenant isolation"},
    )


# Pydantic schemas
class ProjectControlBase(BaseModel):
    """Base project control schema."""

    is_key_override: bool | None = None
    frequency_override: str | None = None
    notes: str | None = None


class ProjectControlCreate(ProjectControlBase):
    """Schema for creating a project control.
    
    Note: tenant_id is NOT included - it's set from membership context server-side.
    """

    project_id: UUID
    control_id: UUID


class ProjectControlResponse(ProjectControlBase):
    """Schema for project control response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    project_id: UUID
    control_id: UUID
    created_at: datetime

