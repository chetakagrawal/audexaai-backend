"""ProjectApplication model - join table linking projects to applications."""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict
from sqlalchemy import ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from db import Base


class ProjectApplication(Base):
    """ProjectApplication ORM model - links projects to applications."""

    __tablename__ = "project_applications"

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
    application_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    # Composite unique constraint: (tenant_id, project_id, application_id)
    # Ensures an application can only be added once per project, scoped by tenant
    __table_args__ = (
        UniqueConstraint("tenant_id", "project_id", "application_id", name="uq_project_application_tenant"),
        {"comment": "Join table linking projects to applications with tenant isolation"},
    )


# Pydantic schemas
class ProjectApplicationBase(BaseModel):
    """Base project application schema."""


class ProjectApplicationCreate(ProjectApplicationBase):
    """Schema for creating a project application.
    
    Note: tenant_id and project_id are NOT included - they're set from context server-side.
    """

    application_id: UUID


class ProjectApplicationResponse(ProjectApplicationBase):
    """Schema for project application response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    project_id: UUID
    application_id: UUID
    created_at: datetime
