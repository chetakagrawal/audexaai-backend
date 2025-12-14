"""Setup token model for SSO onboarding."""

from datetime import datetime, timedelta, UTC
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from db import Base


class SetupToken(Base):
    """Setup token ORM model - one-time tokens for SSO onboarding."""

    __tablename__ = "setup_tokens"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
    )
    token: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    signup_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("signups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    def is_valid(self) -> bool:
        """Check if token is valid (not expired and not used)."""
        now = datetime.now(UTC)
        return self.used_at is None and self.expires_at > now


# Pydantic schemas
class SetupTokenCreate(BaseModel):
    """Schema for creating a setup token."""

    user_id: UUID
    signup_id: UUID
    expires_in_days: int = 7  # Default 7 days


class SetupTokenResponse(BaseModel):
    """Schema for setup token response."""

    model_config = ConfigDict(from_attributes=True)

    token: str
    expires_at: datetime
    created_at: datetime


class SetupTokenValidationResponse(BaseModel):
    """Schema for setup token validation response."""

    valid: bool
    user_id: UUID | None = None
    tenant_id: UUID | None = None
    signup_id: UUID | None = None
    reason: str | None = None  # Reason if invalid (expired, used, etc.)
