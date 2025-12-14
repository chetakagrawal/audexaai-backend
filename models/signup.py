"""Signup model and schema."""

from datetime import datetime, UTC
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, EmailStr
from sqlalchemy import String, DateTime, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
import enum

from db import Base


class SignupStatus(str, enum.Enum):
    """Signup status enum."""

    PENDING_REVIEW = "pending_review"
    PENDING_VERIFICATION = "pending_verification"
    VERIFIED = "verified"
    APPROVED = "approved"
    PROMOTED = "promoted"
    REJECTED = "rejected"


class AuthMode(str, enum.Enum):
    """Authentication mode enum."""

    SSO = "sso"
    DIRECT = "direct"


class Signup(Base):
    """Signup ORM model - staging area for pilot signups."""

    __tablename__ = "signups"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    company_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    company_domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    requested_auth_mode: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=AuthMode.DIRECT.value,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=SignupStatus.PENDING_REVIEW.value,
        index=True,
    )
    signup_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    # Promotion tracking
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    promoted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Created resources (filled on promotion)
    tenant_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    user_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    membership_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


# Pydantic schemas
class SignupBase(BaseModel):
    """Base signup schema."""

    email: EmailStr
    full_name: Optional[str] = None
    company_name: Optional[str] = None
    company_domain: Optional[str] = None
    requested_auth_mode: str = AuthMode.DIRECT.value


class SignupCreate(SignupBase):
    """Schema for creating a signup."""

    metadata: Optional[dict] = None


class SignupCreateResponse(BaseModel):
    """Simple response schema for signup creation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str


class SignupResponse(SignupBase):
    """Schema for signup response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    created_at: datetime
    updated_at: datetime

