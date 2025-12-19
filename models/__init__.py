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
from models.application import Application
from models.project_application import ProjectApplication
from models.control_application import ControlApplication
from models.test_attribute import TestAttribute
from models.pbc_request import PbcRequest
from models.sample import Sample
from models.evidence_file import EvidenceFile
from models.signup import Signup
from models.setup_token import SetupToken
from models.tenant_sso_config import TenantSSOConfig
from models.entity_version import EntityVersion
from models.entity_version import EntityVersion

__all__ = [
    "Base",
    "Tenant",
    "User",
    "UserTenant",
    "AuthIdentity",
    "Project",
    "Control",
    "ProjectControl",
    "Application",
    "ProjectApplication",
    "ControlApplication",
    "TestAttribute",
    "PbcRequest",
    "Sample",
    "EvidenceFile",
    "Signup",
    "SetupToken",
    "TenantSSOConfig",
    "EntityVersion",
]

