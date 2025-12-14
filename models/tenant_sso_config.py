"""Tenant SSO configuration model."""

from datetime import datetime, UTC
from typing import Optional
from uuid import UUID, uuid4
import enum

from pydantic import BaseModel, ConfigDict
from sqlalchemy import String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB

from db import Base


class SSOProviderType(str, enum.Enum):
    """SSO provider type enum."""

    SAML = "saml"
    OIDC = "oidc"


class TenantSSOConfig(Base):
    """Tenant SSO configuration ORM model."""

    __tablename__ = "tenant_sso_configs"

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
        unique=True,  # One SSO config per tenant
        index=True,
    )
    provider_type: Mapped[str] = mapped_column(String(50), nullable=False)  # saml or oidc
    
    # SAML fields
    metadata_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    entity_id: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    sso_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    x509_certificate: Mapped[Optional[str]] = mapped_column(String(5000), nullable=True)
    
    # OIDC fields
    oidc_client_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    oidc_client_secret: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # Encrypted in production
    oidc_discovery_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    oidc_redirect_uri: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Status
    is_configured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    # Additional metadata (for storing provider-specific settings)
    config_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
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
class SAMLConfig(BaseModel):
    """SAML configuration schema."""

    metadata_url: Optional[str] = None  # Primary method
    # OR manual fields
    entity_id: Optional[str] = None
    sso_url: Optional[str] = None
    x509_certificate: Optional[str] = None


class OIDCConfig(BaseModel):
    """OIDC configuration schema."""

    client_id: str
    client_secret: str
    discovery_url: str
    redirect_uri: Optional[str] = None  # Auto-generated if not provided


class SSOConfigRequest(BaseModel):
    """Request schema for SSO configuration."""

    provider_type: str  # saml or oidc
    saml_config: Optional[SAMLConfig] = None
    oidc_config: Optional[OIDCConfig] = None


class SSOConfigResponse(BaseModel):
    """Response schema for SSO configuration."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    provider_type: str
    is_configured: bool
    created_at: datetime
    updated_at: datetime
