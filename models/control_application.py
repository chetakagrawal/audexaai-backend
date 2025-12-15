"""ControlApplication model - join table linking controls to applications."""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict
from sqlalchemy import ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from db import Base


class ControlApplication(Base):
    """ControlApplication ORM model - links controls to applications."""

    __tablename__ = "control_applications"

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
    control_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("controls.id", ondelete="CASCADE"),
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

    # Composite unique constraint: (tenant_id, control_id, application_id)
    # Ensures an application can only be mapped once per control, scoped by tenant
    __table_args__ = (
        UniqueConstraint("tenant_id", "control_id", "application_id", name="uq_control_application_tenant"),
        {"comment": "Join table linking controls to applications with tenant isolation"},
    )


# Pydantic schemas
class ControlApplicationBase(BaseModel):
    """Base control application schema."""


class ControlApplicationCreate(ControlApplicationBase):
    """Schema for creating a control application.
    
    Note: tenant_id and control_id are NOT included - they're set from context server-side.
    """

    application_id: UUID


class ControlApplicationResponse(ControlApplicationBase):
    """Schema for control application response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    control_id: UUID
    application_id: UUID
    created_at: datetime
