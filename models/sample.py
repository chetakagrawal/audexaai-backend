"""
Sample model

Represents individual samples for control testing in audit projects.
Each sample links to a PBC request and tracks testing details.
"""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


class Sample(Base):
    """
    Sample model for control testing.
    
    Each sample represents a specific item or transaction being tested
    as part of a PBC request. Auditors test individual samples and record
    their findings.
    """

    __tablename__ = "samples"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4, index=True
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pbc_request_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("pbc_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sample_number: Mapped[int] = mapped_column(Integer, nullable=False)
    identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    test_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    tested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    tested_by_membership_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("user_tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    __table_args__ = (
        {"comment": "Samples for control testing in audit projects"},
    )


# ============================================================
# Pydantic Schemas
# ============================================================


class SampleBase(BaseModel):
    """Base schema for Sample with common fields"""

    sample_number: int
    identifier: str
    description: str | None = None
    status: str = "pending"
    test_notes: str | None = None
    tested_at: datetime | None = None
    tested_by_membership_id: UUID | None = None


class SampleCreate(BaseModel):
    """Schema for creating a new Sample"""

    pbc_request_id: UUID
    sample_number: int
    identifier: str
    description: str | None = None
    status: str = "pending"
    test_notes: str | None = None
    tested_at: datetime | None = None
    tested_by_membership_id: UUID | None = None


class SampleUpdate(BaseModel):
    """Schema for updating an existing Sample"""

    identifier: str | None = None
    description: str | None = None
    status: str | None = None
    test_notes: str | None = None
    tested_at: datetime | None = None
    tested_by_membership_id: UUID | None = None


class SampleResponse(SampleBase):
    """Schema for Sample responses"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    pbc_request_id: UUID
    created_at: datetime
