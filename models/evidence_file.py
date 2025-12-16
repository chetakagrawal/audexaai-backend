"""Evidence File model - files uploaded as evidence for PBC requests."""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict
from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


class EvidenceFile(Base):
    """EvidenceFile ORM model - represents a file uploaded as evidence.
    
    Evidence files can be:
    - Linked to a PBC request (general evidence)
    - Linked to a specific sample within a PBC request (granular evidence)
    - Versioned (supersedes_file_id tracks previous versions)
    """

    __tablename__ = "evidence_files"

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
    pbc_request_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("pbc_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sample_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        # FK to samples.id will be added when samples table is implemented
        nullable=True,
        index=True,
    )
    uploaded_by_membership_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("user_tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_uri: Mapped[str] = mapped_column(String(512), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    supersedes_file_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("evidence_files.id", ondelete="SET NULL"),
        nullable=True,
    )
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    __table_args__ = (
        {"comment": "Evidence files uploaded for PBC requests and samples"},
    )


# Pydantic schemas
class EvidenceFileBase(BaseModel):
    """Base evidence file schema."""

    filename: str
    mime_type: str
    storage_uri: str
    content_hash: str
    version: int = 1
    supersedes_file_id: UUID | None = None
    page_count: int | None = None


class EvidenceFileCreate(BaseModel):
    """Schema for creating an evidence file.
    
    Note: 
    - tenant_id is set from context server-side
    - pbc_request_id is required
    - sample_id is optional (for granular linking)
    - uploaded_by_membership_id is set from auth context
    """

    pbc_request_id: UUID
    sample_id: UUID | None = None
    filename: str
    mime_type: str
    storage_uri: str
    content_hash: str
    version: int = 1
    supersedes_file_id: UUID | None = None
    page_count: int | None = None


class EvidenceFileUpdate(BaseModel):
    """Schema for updating an evidence file.
    
    Note: Most fields are immutable after creation.
    Only metadata fields can be updated.
    """

    filename: str | None = None
    page_count: int | None = None


class EvidenceFileResponse(EvidenceFileBase):
    """Schema for evidence file response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    pbc_request_id: UUID
    sample_id: UUID | None
    uploaded_by_membership_id: UUID
    uploaded_at: datetime
