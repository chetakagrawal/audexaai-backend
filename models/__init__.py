"""Database models."""

from db import Base

# Import all models so Alembic can detect them
from models.tenant import Tenant
from models.user import User
from models.user_tenant import UserTenant
from models.auth_identity import AuthIdentity
from models.project import Project
from models.control import Control
from models.project_control import ProjectControl
from models.signup import Signup
from models.setup_token import SetupToken
from models.tenant_sso_config import TenantSSOConfig

__all__ = [
    "Base",
    "Tenant",
    "User",
    "UserTenant",
    "AuthIdentity",
    "Project",
    "Control",
    "ProjectControl",
    "Signup",
    "SetupToken",
    "TenantSSOConfig",
]

