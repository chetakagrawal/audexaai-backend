"""Application model - tenant-owned business application."""

from datetime import datetime
from typing import List
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict
import sqlalchemy as sa
from sqlalchemy import String, ForeignKey, DateTime, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from db import Base


class Application(Base):
    """Application ORM model - represents a business application within a tenant."""

    __tablename__ = "applications"

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
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    scope_rationale: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    business_owner_membership_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("user_tenants.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    it_owner_membership_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("user_tenants.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
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

    # Relationship to ControlApplication rows (not direct to Control)
    control_applications: Mapped[List["ControlApplication"]] = relationship(
        "ControlApplication",
        foreign_keys="ControlApplication.application_id",
        back_populates="application",
    )

    # Partial unique index: name must be unique per tenant for ACTIVE applications only
    # This allows reusing name after soft delete
    __table_args__ = (
        # Partial unique index for PostgreSQL: unique (tenant_id, name) WHERE deleted_at IS NULL
        Index(
            'ux_applications_tenant_name_active',
            'tenant_id',
            'name',
            postgresql_where=sa.text('deleted_at IS NULL'),
            unique=True,
        ),
        {"comment": "Applications are tenant-owned business applications"},
    )


# Pydantic schemas
class ApplicationBase(BaseModel):
    """Base application schema."""

    name: str
    category: str | None = None
    scope_rationale: str | None = None
    business_owner_membership_id: UUID | None = None
    it_owner_membership_id: UUID | None = None


class ApplicationCreate(ApplicationBase):
    """Schema for creating an application.
    
    Note: tenant_id is NOT included - it's set from membership context server-side.
    """


class ApplicationUpdate(BaseModel):
    """Schema for updating an application. All fields are optional."""

    name: str | None = None
    category: str | None = None
    scope_rationale: str | None = None
    business_owner_membership_id: UUID | None = None
    it_owner_membership_id: UUID | None = None


class ApplicationResponse(ApplicationBase):
    """Schema for application response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    created_at: datetime
    created_by_membership_id: UUID | None = None
    updated_at: datetime
    updated_by_membership_id: UUID | None = None
    deleted_at: datetime | None = None
    deleted_by_membership_id: UUID | None = None
    row_version: int
