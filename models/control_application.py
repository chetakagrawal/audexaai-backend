"""ControlApplication model - join table linking controls to applications with effective dating."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict
import sqlalchemy as sa
from sqlalchemy import ForeignKey, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from db import Base

if TYPE_CHECKING:
    from models.control import Control
    from models.application import Application


class ControlApplication(Base):
    """ControlApplication ORM model - links controls to applications with effective dating."""

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
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
    added_by_membership_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("user_tenants.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
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

    # Relationships
    control: Mapped["Control"] = relationship(
        "Control",
        foreign_keys=[control_id],
        back_populates="control_applications",
    )
    application: Mapped["Application"] = relationship(
        "Application",
        foreign_keys=[application_id],
        back_populates="control_applications",
    )

    # Partial unique index: (tenant_id, control_id, application_id) must be unique for ACTIVE mappings only
    # This allows re-adding after removal (creates new row with different id, preserving history)
    __table_args__ = (
        Index(
            'ux_control_apps_active',
            'tenant_id',
            'control_id',
            'application_id',
            postgresql_where=sa.text('removed_at IS NULL'),
            unique=True,
        ),
        Index('ix_control_apps_tenant_control', 'tenant_id', 'control_id'),
        Index('ix_control_apps_tenant_application', 'tenant_id', 'application_id'),
        {"comment": "Join table linking controls to applications with effective dating and tenant isolation"},
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
    added_at: datetime
    added_by_membership_id: UUID | None = None
    removed_at: datetime | None = None
    removed_by_membership_id: UUID | None = None
