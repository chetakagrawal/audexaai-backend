"""EntityVersion model - generic version history table."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict
import sqlalchemy as sa
from sqlalchemy import Text, Integer, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB

from db import Base


class EntityVersion(Base):
    """EntityVersion ORM model - stores version snapshots for any entity type."""

    __tablename__ = "entity_versions"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
        index=True,
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    operation: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        # CHECK constraint enforced at DB level
    )
    version_num: Mapped[int] = mapped_column(Integer, nullable=False)
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    valid_to: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )
    changed_by_membership_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)

    __table_args__ = (
        # Indexes are created in migration
        {"comment": "Generic version history table for entity snapshots"},
    )


# Pydantic schemas
class EntityVersionResponse(BaseModel):
    """Schema for entity version response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    entity_type: str
    entity_id: UUID
    operation: str
    version_num: int
    valid_from: datetime
    valid_to: datetime
    changed_at: datetime
    changed_by_membership_id: UUID | None = None
    data: dict

