"""Pytest configuration and fixtures."""

import asyncio
import sys
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

import config
from db import Base
from main import app
from models.auth_identity import AuthIdentity
from models.tenant import Tenant
from models.user import User
from models.user_tenant import UserTenant

# Fix Windows asyncio event loop
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Test database URL (use same DB as dev for now)
TEST_DATABASE_URL = config.settings.DATABASE_URL

# Create test engine
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Create a test database session."""
    from sqlalchemy import text
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Create generic trigger function for version history (works for both controls and applications)
        await conn.execute(text("""
            CREATE OR REPLACE FUNCTION audit_capture_entity_version()
            RETURNS TRIGGER AS $$
            DECLARE
                v_operation TEXT;
                v_changed_by_membership_id UUID;
                v_entity_type TEXT;
            BEGIN
                -- Determine entity_type from table name
                v_entity_type := TG_TABLE_NAME;
                
                -- Determine operation
                IF TG_OP = 'DELETE' THEN
                    v_operation := 'DELETE';
                    v_changed_by_membership_id := NULL;
                ELSE
                    -- UPDATE operation
                    IF OLD.deleted_at IS NULL AND NEW.deleted_at IS NOT NULL THEN
                        -- Soft delete: OLD was active, NEW is deleted
                        v_operation := 'DELETE';
                        v_changed_by_membership_id := NEW.deleted_by_membership_id;
                    ELSE
                        -- Regular update
                        v_operation := 'UPDATE';
                        v_changed_by_membership_id := NEW.updated_by_membership_id;
                    END IF;
                END IF;
                
                -- Insert snapshot into entity_versions
                INSERT INTO entity_versions (
                    tenant_id,
                    entity_type,
                    entity_id,
                    operation,
                    version_num,
                    valid_from,
                    valid_to,
                    changed_by_membership_id,
                    data
                ) VALUES (
                    OLD.tenant_id,
                    v_entity_type,
                    OLD.id,
                    v_operation,
                    OLD.row_version,
                    COALESCE(OLD.updated_at, OLD.created_at),
                    NOW(),
                    v_changed_by_membership_id,
                    to_jsonb(OLD)
                );
                
                -- Return appropriate record
                IF TG_OP = 'DELETE' THEN
                    RETURN OLD;
                ELSE
                    RETURN NEW;
                END IF;
            END;
            $$ LANGUAGE plpgsql;
        """))
        # Create trigger for controls
        await conn.execute(text("""
            DROP TRIGGER IF EXISTS trigger_audit_capture_control_version ON controls;
            CREATE TRIGGER trigger_audit_capture_control_version
            BEFORE UPDATE OR DELETE ON controls
            FOR EACH ROW
            EXECUTE FUNCTION audit_capture_entity_version();
        """))
        # Create trigger for applications
        await conn.execute(text("""
            DROP TRIGGER IF EXISTS trigger_audit_capture_application_version ON applications;
            CREATE TRIGGER trigger_audit_capture_application_version
            BEFORE UPDATE OR DELETE ON applications
            FOR EACH ROW
            EXECUTE FUNCTION audit_capture_entity_version();
        """))
        # Create trigger for test_attributes
        await conn.execute(text("""
            DROP TRIGGER IF EXISTS trigger_audit_capture_test_attribute_version ON test_attributes;
            CREATE TRIGGER trigger_audit_capture_test_attribute_version
            BEFORE UPDATE OR DELETE ON test_attributes
            FOR EACH ROW
            EXECUTE FUNCTION audit_capture_entity_version();
        """))
    
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        # Drop triggers and function
        await conn.execute(text("DROP TRIGGER IF EXISTS trigger_audit_capture_control_version ON controls;"))
        await conn.execute(text("DROP TRIGGER IF EXISTS trigger_audit_capture_application_version ON applications;"))
        await conn.execute(text("DROP TRIGGER IF EXISTS trigger_audit_capture_test_attribute_version ON test_attributes;"))
        await conn.execute(text("DROP FUNCTION IF EXISTS audit_capture_entity_version();"))


@pytest.fixture
def override_get_db(db_session):
    """Override get_db dependency for testing."""
    from api.deps import get_db
    
    async def _get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = _get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client(override_get_db):
    """Create test client."""
    return TestClient(app)


@pytest_asyncio.fixture
async def tenant_a(db_session):
    """Create test tenant A."""
    tenant = Tenant(
        id=uuid4(),
        name="Tenant A",
        slug="tenant-a",
        status="active",
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest_asyncio.fixture
async def tenant_b(db_session):
    """Create test tenant B."""
    tenant = Tenant(
        id=uuid4(),
        name="Tenant B",
        slug="tenant-b",
        status="active",
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


def make_auth_headers(token: str, membership_id: str | None = None) -> dict:
    """
    Helper function to create auth headers with optional X-Membership-Id.
    
    Args:
        token: JWT token
        membership_id: Optional membership ID (UserTenant.id)
    
    Returns:
        Headers dict with Authorization and optionally X-Membership-Id
    """
    headers = {"Authorization": f"Bearer {token}"}
    if membership_id:
        headers["X-Membership-Id"] = str(membership_id)
    return headers


@pytest_asyncio.fixture
async def user_tenant_a(db_session, tenant_a):
    """Create user in Tenant A."""
    user = User(
        id=uuid4(),
        primary_email="user-a@tenant-a.com",
        name="User A",
        is_platform_admin=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    
    membership = UserTenant(
        id=uuid4(),
        user_id=user.id,
        tenant_id=tenant_a.id,
        role="admin",
        is_default=True,
    )
    db_session.add(membership)
    
    auth_identity = AuthIdentity(
        id=uuid4(),
        user_id=user.id,
        provider="dev",
        provider_subject="user-a@tenant-a.com",
        email="user-a@tenant-a.com",
        email_verified=True,
    )
    db_session.add(auth_identity)
    
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(membership)
    
    return user, membership


@pytest_asyncio.fixture
async def user_tenant_b(db_session, tenant_b):
    """Create user in Tenant B."""
    user = User(
        id=uuid4(),
        primary_email="user-b@tenant-b.com",
        name="User B",
        is_platform_admin=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    
    membership = UserTenant(
        id=uuid4(),
        user_id=user.id,
        tenant_id=tenant_b.id,
        role="admin",
        is_default=True,
    )
    db_session.add(membership)
    
    auth_identity = AuthIdentity(
        id=uuid4(),
        user_id=user.id,
        provider="dev",
        provider_subject="user-b@tenant-b.com",
        email="user-b@tenant-b.com",
        email_verified=True,
    )
    db_session.add(auth_identity)
    
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(membership)
    
    return user, membership


@pytest_asyncio.fixture
async def user_no_membership(db_session):
    """Create user without tenant membership."""
    user = User(
        id=uuid4(),
        primary_email="no-tenant@example.com",
        name="No Tenant User",
        is_platform_admin=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()  # Flush to get user.id
    
    auth_identity = AuthIdentity(
        id=uuid4(),
        user_id=user.id,
        provider="dev",
        provider_subject="no-tenant@example.com",
        email="no-tenant@example.com",
        email_verified=True,
    )
    db_session.add(auth_identity)
    
    await db_session.commit()
    await db_session.refresh(user)
    
    return user
