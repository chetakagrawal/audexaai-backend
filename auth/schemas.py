"""JWT token payload schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class TokenPayload(BaseModel):
    """JWT token payload structure."""

    sub: str  # user_id (standard JWT claim)
    tenant_id: str | None  # UUID of active tenant (None for platform admins)
    role: str  # Role in the tenant
    is_platform_admin: bool  # Whether user is platform admin
    exp: datetime  # Expiration time (standard JWT claim)

