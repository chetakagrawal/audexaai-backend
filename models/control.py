"""Control model - tenant-owned SOX control."""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict
from sqlalchemy import String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from db import Base


class Control(Base):
    """Control ORM model - represents a SOX control owned by a tenant."""

    __tablename__ = "controls"

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
    control_code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    risk_rating: Mapped[str | None] = mapped_column(String(50), nullable=True)
    control_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    frequency: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_key: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_automated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    # Composite unique constraint: control_code must be unique per tenant
    __table_args__ = (
        {"comment": "Controls are tenant-owned SOX controls"},
    )


# Pydantic schemas
class ControlBase(BaseModel):
    """Base control schema."""

    control_code: str
    name: str
    category: str | None = None
    risk_rating: str | None = None
    control_type: str | None = None
    frequency: str | None = None
    is_key: bool = False
    is_automated: bool = False


class ControlCreate(ControlBase):
    """Schema for creating a control.
    
    Note: tenant_id is NOT included - it's set from membership context server-side.
    """


class ControlResponse(ControlBase):
    """Schema for control response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    created_at: datetime

