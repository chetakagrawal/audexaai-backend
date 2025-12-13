"""AuthIdentity model - authentication provider identities."""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, EmailStr
from sqlalchemy import String, DateTime, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from db import Base


class AuthIdentity(Base):
    """AuthIdentity ORM model - links users to authentication providers."""

    __tablename__ = "auth_identities"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # dev, okta, azure_ad, etc.
    provider_subject: Mapped[str] = mapped_column(String(255), nullable=False)  # Provider's user ID
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_algo: Mapped[str | None] = mapped_column(String(50), nullable=True)  # bcrypt, argon2, etc.
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    __table_args__ = (
        UniqueConstraint("provider", "provider_subject", name="uq_provider_subject"),
    )


# Pydantic schemas
class AuthIdentityBase(BaseModel):
    """Base auth identity schema."""

    provider: str
    provider_subject: str
    email: EmailStr
    email_verified: bool = False


class AuthIdentityCreate(AuthIdentityBase):
    """Schema for creating an auth identity."""

    user_id: UUID
    password_hash: str | None = None
    password_algo: str | None = None


class AuthIdentityResponse(AuthIdentityBase):
    """Schema for auth identity response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    last_login_at: datetime | None
    created_at: datetime

