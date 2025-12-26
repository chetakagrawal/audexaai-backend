"""PBC Request Evidence File link model - links evidence files to PBC requests."""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict
import sqlalchemy as sa
from sqlalchemy import DateTime, ForeignKey, Integer, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


class PbcRequestEvidenceFile(Base):
    """PbcRequestEvidenceFile ORM model - link table between PBC requests and evidence files.
    
    This is a many-to-many relationship with soft delete support.
    Unlinking a file from a request soft-deletes the link but keeps the file.
    """

    __tablename__ = "pbc_request_evidence_files"

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
    pbc_request_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("pbc_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    evidence_file_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("evidence_files_v2.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
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
        # Unique partial index for active links
        Index(
            "ux_pbc_request_evidence_files_active",
            "tenant_id",
            "pbc_request_id",
            "evidence_file_id",
            unique=True,
            postgresql_where=sa.text("deleted_at IS NULL"),
        ),
        {"comment": "Links between PBC requests and evidence files"},
    )


# Pydantic schemas
class PbcRequestEvidenceFileResponse(BaseModel):
    """Schema for PBC request evidence file link response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    project_id: UUID
    pbc_request_id: UUID
    evidence_file_id: UUID
    created_at: datetime
    created_by_membership_id: UUID
    deleted_at: datetime | None = None
    deleted_by_membership_id: UUID | None = None
    row_version: int

