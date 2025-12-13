"""Database models."""

from db import Base

# Import all models so Alembic can detect them
from models.tenant import Tenant
from models.user import User
from models.user_tenant import UserTenant
from models.auth_identity import AuthIdentity

__all__ = ["Base", "Tenant", "User", "UserTenant", "AuthIdentity"]

