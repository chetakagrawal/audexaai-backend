"""PBC Request model - PBC (Prepared By Client) requests for evidence collection."""

from datetime import date, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


class PbcRequest(Base):
    """PbcRequest ORM model - represents a PBC request for evidence collection.
    
    Each PBC request is associated with:
    - A project (the audit engagement)
    - An application (the system being audited)
    - A control (the specific control being tested)
    - An owner (the person responsible for fulfilling the request)
    """

    __tablename__ = "pbc_requests"

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
    application_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    control_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("controls.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    owner_membership_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("user_tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    samples_requested: Mapped[int | None] = mapped_column(Integer, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    __table_args__ = (
        {"comment": "PBC requests track evidence requests for control testing"},
    )


# Pydantic schemas
class PbcRequestBase(BaseModel):
    """Base PBC request schema."""

    title: str
    samples_requested: int | None = None
    due_date: date | None = None
    status: str = "pending"


class PbcRequestCreate(PbcRequestBase):
    """Schema for creating a PBC request.
    
    Note: 
    - tenant_id is set from context server-side
    - project_id, application_id, control_id, owner_membership_id are required
    """

    project_id: UUID
    application_id: UUID
    control_id: UUID
    owner_membership_id: UUID


class PbcRequestUpdate(BaseModel):
    """Schema for updating a PBC request.
    
    Note: IDs cannot be changed after creation.
    """

    title: str | None = None
    samples_requested: int | None = None
    due_date: date | None = None
    status: str | None = None


class PbcRequestResponse(PbcRequestBase):
    """Schema for PBC request response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    project_id: UUID
    application_id: UUID
    control_id: UUID
    owner_membership_id: UUID
    created_at: datetime
