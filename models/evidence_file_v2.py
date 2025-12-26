"""Evidence File v2 model - files within evidence artifacts."""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


class EvidenceFileV2(Base):
    """EvidenceFileV2 ORM model - represents a file within an evidence artifact.
    
    Files are stored on disk (or cloud storage) and referenced by storage_key.
    Each file belongs to an artifact and can be linked to multiple PBC requests.
    """

    __tablename__ = "evidence_files_v2"

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
    artifact_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("evidence_artifacts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
    # Audit fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
    created_by_membership_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("user_tenants.id", ondelete="RESTRICT"),
        nullable=False,
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
        Index("ix_evidence_files_v2_tenant_project", "tenant_id", "project_id"),
        Index("ix_evidence_files_v2_tenant_artifact", "tenant_id", "artifact_id"),
        Index("ix_evidence_files_v2_tenant_sha256", "tenant_id", "sha256"),
        {"comment": "Evidence files v2 - files within evidence artifacts"},
    )


# Pydantic schemas
class EvidenceFileV2Base(BaseModel):
    """Base evidence file v2 schema."""

    filename: str
    mime_type: str
    size_bytes: int
    storage_key: str
    sha256: str | None = None


class EvidenceFileV2Response(EvidenceFileV2Base):
    """Schema for evidence file v2 response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    project_id: UUID
    artifact_id: UUID
    uploaded_at: datetime
    created_at: datetime
    created_by_membership_id: UUID
    updated_at: datetime | None = None
    updated_by_membership_id: UUID | None = None
    deleted_at: datetime | None = None
    deleted_by_membership_id: UUID | None = None
    row_version: int

