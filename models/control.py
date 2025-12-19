"""Control model - tenant-owned SOX control."""

from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict
import sqlalchemy as sa
from sqlalchemy import String, Boolean, ForeignKey, DateTime, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from uuid import UUID, uuid4

from db import Base


class Control(Base):
    """Control ORM model - represents a SOX control owned by a tenant."""

    __tablename__ = "controls"

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
    created_by_membership_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("user_tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    control_code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    risk_rating: Mapped[str | None] = mapped_column(String(50), nullable=True)
    control_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    frequency: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_key: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_automated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
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

    # Relationship to ControlApplication rows (not direct to Application)
    control_applications: Mapped[List["ControlApplication"]] = relationship(
        "ControlApplication",
        foreign_keys="ControlApplication.control_id",
        back_populates="control",
    )

    # Partial unique index: control_code must be unique per tenant for ACTIVE controls only
    # This allows reusing control_code after soft delete
    # The partial unique index is created both in the model (for create_all()) and via Alembic migration
    # Migration: f1a2b3c4d5e6_add_audit_metadata_to_controls creates ux_controls_tenant_code_active
    __table_args__ = (
        # Partial unique index for PostgreSQL: unique (tenant_id, control_code) WHERE deleted_at IS NULL
        Index(
            'ux_controls_tenant_code_active',
            'tenant_id',
            'control_code',
            postgresql_where=sa.text('deleted_at IS NULL'),
            unique=True,
        ),
        {"comment": "Controls are tenant-owned SOX controls"},
    )


# Pydantic schemas
class ControlBase(BaseModel):
    """Base control schema."""

    control_code: str
    name: str
    category: str | None = None
    risk_rating: str | None = None
    control_type: str | None = None
    frequency: str | None = None
    is_key: bool = False
    is_automated: bool = False


class ControlCreate(ControlBase):
    """Schema for creating a control.
    
    Note: tenant_id is NOT included - it's set from membership context server-side.
    """
    
    application_ids: list[UUID] | None = None


class ControlResponse(ControlBase):
    """Schema for control response.
    
    Note: applications field removed - applications are managed via control_applications endpoints.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    created_by_membership_id: UUID
    created_at: datetime
    updated_at: datetime
    updated_by_membership_id: UUID | None = None
    deleted_at: datetime | None = None
    deleted_by_membership_id: UUID | None = None
    row_version: int

