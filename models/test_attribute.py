"""Test Attribute model - test attributes for controls."""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict
from sqlalchemy import String, ForeignKey, DateTime, Text, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
import sqlalchemy as sa

from db import Base


class TestAttribute(Base):
    """TestAttribute ORM model - represents a test attribute for a control."""

    __tablename__ = "test_attributes"

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
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    frequency: Mapped[str | None] = mapped_column(String(50), nullable=True)
    test_procedure: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
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
        # Partial unique index: (tenant_id, control_id, code) must be unique for ACTIVE test attributes
        Index(
            'ux_test_attributes_active_code',
            'tenant_id',
            'control_id',
            'code',
            postgresql_where=sa.text('deleted_at IS NULL'),
            unique=True,
        ),
        {"comment": "Test attributes define test procedures and expected evidence for controls"},
    )


# Pydantic schemas
class TestAttributeBase(BaseModel):
    """Base test attribute schema."""

    code: str
    name: str
    frequency: str | None = None
    test_procedure: str | None = None
    expected_evidence: str | None = None


class TestAttributeCreate(TestAttributeBase):
    """Schema for creating a test attribute.
    
    Note: tenant_id and control_id are NOT included - they're set from context server-side.
    """


class TestAttributeResponse(TestAttributeBase):
    """Schema for test attribute response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    control_id: UUID
    created_at: datetime
    created_by_membership_id: UUID | None = None
    updated_at: datetime | None = None
    updated_by_membership_id: UUID | None = None
    deleted_at: datetime | None = None
    deleted_by_membership_id: UUID | None = None
    row_version: int
