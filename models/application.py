"""Application model - tenant-owned business application."""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict
from sqlalchemy import String, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column
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
    business_owner_membership_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("user_tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    it_owner_membership_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("user_tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    __table_args__ = (
        {"comment": "Applications are tenant-owned business applications"},
    )


# Pydantic schemas
class ApplicationBase(BaseModel):
    """Base application schema."""

    name: str
    category: str | None = None
    scope_rationale: str | None = None
    business_owner_membership_id: UUID
    it_owner_membership_id: UUID


class ApplicationCreate(ApplicationBase):
    """Schema for creating an application.
    
    Note: tenant_id is NOT included - it's set from membership context server-side.
    """


class ApplicationResponse(ApplicationBase):
    """Schema for application response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    created_at: datetime
