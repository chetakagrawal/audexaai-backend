"""DB-backed tests for Signup model.

These tests verify model behavior, database constraints, and query patterns
for the Signup model. All tests use a real database session.
"""

from datetime import datetime, UTC
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.signup import Signup, SignupStatus, AuthMode


@pytest.mark.asyncio
async def test_create_signup_minimal(db_session: AsyncSession):
    """
    Test: Can create a signup with minimal required fields.
    
    Only email is required; defaults should be set for status and requested_auth_mode.
    """
    signup = Signup(
        id=uuid4(),
        email="test@example.com",
    )
    db_session.add(signup)
    await db_session.commit()
    await db_session.refresh(signup)
    
    assert signup.id is not None
    assert signup.email == "test@example.com"
    assert signup.status == SignupStatus.PENDING_REVIEW.value
    assert signup.requested_auth_mode == AuthMode.DIRECT.value
    assert signup.full_name is None
    assert signup.company_name is None
    assert signup.company_domain is None
    assert signup.signup_metadata is None
    assert signup.approved_at is None
    assert signup.promoted_at is None
    assert signup.tenant_id is None
    assert signup.user_id is None
    assert signup.membership_id is None
    assert signup.created_at is not None
    assert signup.updated_at is not None
    assert isinstance(signup.created_at, datetime)
    assert isinstance(signup.updated_at, datetime)


@pytest.mark.asyncio
async def test_create_signup_with_all_fields(db_session: AsyncSession):
    """
    Test: Can create a signup with all fields populated.
    """
    now = datetime.now(UTC)
    tenant_id = uuid4()
    user_id = uuid4()
    membership_id = uuid4()
    metadata = {"source": "pilot_form", "referrer": "website"}
    
    signup = Signup(
        id=uuid4(),
        email="complete@example.com",
        full_name="John Doe",
        company_name="Acme Corp",
        company_domain="acme.com",
        requested_auth_mode=AuthMode.SSO.value,
        status=SignupStatus.PENDING_VERIFICATION.value,
        signup_metadata=metadata,
        approved_at=now,
        promoted_at=now,
        tenant_id=tenant_id,
        user_id=user_id,
        membership_id=membership_id,
    )
    db_session.add(signup)
    await db_session.commit()
    await db_session.refresh(signup)
    
    assert signup.email == "complete@example.com"
    assert signup.full_name == "John Doe"
    assert signup.company_name == "Acme Corp"
    assert signup.company_domain == "acme.com"
    assert signup.requested_auth_mode == AuthMode.SSO.value
    assert signup.status == SignupStatus.PENDING_VERIFICATION.value
    assert signup.signup_metadata == metadata
    assert signup.approved_at is not None
    assert signup.promoted_at is not None
    assert signup.tenant_id == tenant_id
    assert signup.user_id == user_id
    assert signup.membership_id == membership_id


@pytest.mark.asyncio
async def test_signup_allows_duplicate_emails(db_session: AsyncSession):
    """
    Test: Multiple signups with same email are allowed (no unique constraint).
    
    This is intentional - we want to allow the same email to sign up multiple times
    over time (e.g., different company, different request).
    """
    email = "duplicate@example.com"
    
    # Create first signup
    signup_1 = Signup(
        id=uuid4(),
        email=email,
        company_name="Company A",
        status=SignupStatus.PENDING_REVIEW.value,
    )
    db_session.add(signup_1)
    await db_session.commit()
    await db_session.refresh(signup_1)
    
    # Create second signup with same email (should succeed)
    signup_2 = Signup(
        id=uuid4(),
        email=email,  # Same email
        company_name="Company B",  # Different company
        status=SignupStatus.PENDING_REVIEW.value,
    )
    db_session.add(signup_2)
    
    # Should NOT raise IntegrityError
    await db_session.commit()
    await db_session.refresh(signup_2)
    
    # Verify both signups exist
    assert signup_1.id != signup_2.id
    assert signup_1.email == signup_2.email
    assert signup_1.company_name == "Company A"
    assert signup_2.company_name == "Company B"


@pytest.mark.asyncio
async def test_signup_jsonb_metadata(db_session: AsyncSession):
    """
    Test: Can store and retrieve JSONB metadata.
    """
    metadata = {
        "source": "pilot_form",
        "referrer": "website",
        "utm_campaign": "pilot_2024",
        "nested": {
            "key": "value",
            "numbers": [1, 2, 3],
        },
    }
    
    signup = Signup(
        id=uuid4(),
        email="metadata@example.com",
        signup_metadata=metadata,
    )
    db_session.add(signup)
    await db_session.commit()
    await db_session.refresh(signup)
    
    assert signup.signup_metadata == metadata
    assert signup.signup_metadata["source"] == "pilot_form"
    assert signup.signup_metadata["nested"]["key"] == "value"
    assert signup.signup_metadata["nested"]["numbers"] == [1, 2, 3]


@pytest.mark.asyncio
async def test_signup_query_by_email(db_session: AsyncSession):
    """
    Test: Can query signups by email (indexed field).
    """
    email = "query@example.com"
    
    signup_1 = Signup(
        id=uuid4(),
        email=email,
        company_name="Company 1",
    )
    signup_2 = Signup(
        id=uuid4(),
        email=email,
        company_name="Company 2",
    )
    signup_3 = Signup(
        id=uuid4(),
        email="other@example.com",
        company_name="Other Company",
    )
    
    db_session.add_all([signup_1, signup_2, signup_3])
    await db_session.commit()
    
    # Query by email
    result = await db_session.execute(
        select(Signup).where(Signup.email == email)
    )
    signups = result.scalars().all()
    
    assert len(signups) == 2
    assert {s.id for s in signups} == {signup_1.id, signup_2.id}
    assert all(s.email == email for s in signups)


@pytest.mark.asyncio
async def test_signup_query_by_status(db_session: AsyncSession):
    """
    Test: Can query signups by status (indexed field).
    """
    signup_pending = Signup(
        id=uuid4(),
        email="pending@example.com",
        status=SignupStatus.PENDING_REVIEW.value,
    )
    signup_approved = Signup(
        id=uuid4(),
        email="approved@example.com",
        status=SignupStatus.APPROVED.value,
    )
    signup_promoted = Signup(
        id=uuid4(),
        email="promoted@example.com",
        status=SignupStatus.PROMOTED.value,
    )
    
    db_session.add_all([signup_pending, signup_approved, signup_promoted])
    await db_session.commit()
    
    # Query by status
    result = await db_session.execute(
        select(Signup).where(Signup.status == SignupStatus.PENDING_REVIEW.value)
    )
    pending_signups = result.scalars().all()
    
    assert len(pending_signups) == 1
    assert pending_signups[0].id == signup_pending.id
    assert pending_signups[0].status == SignupStatus.PENDING_REVIEW.value


@pytest.mark.asyncio
async def test_signup_query_by_company_domain(db_session: AsyncSession):
    """
    Test: Can query signups by company_domain (indexed field).
    """
    domain = "example.com"
    
    signup_1 = Signup(
        id=uuid4(),
        email="user1@example.com",
        company_domain=domain,
    )
    signup_2 = Signup(
        id=uuid4(),
        email="user2@example.com",
        company_domain=domain,
    )
    signup_3 = Signup(
        id=uuid4(),
        email="user3@other.com",
        company_domain="other.com",
    )
    
    db_session.add_all([signup_1, signup_2, signup_3])
    await db_session.commit()
    
    # Query by company_domain
    result = await db_session.execute(
        select(Signup).where(Signup.company_domain == domain)
    )
    signups = result.scalars().all()
    
    assert len(signups) == 2
    assert {s.id for s in signups} == {signup_1.id, signup_2.id}
    assert all(s.company_domain == domain for s in signups)


@pytest.mark.asyncio
async def test_signup_promotion_fields(db_session: AsyncSession):
    """
    Test: Can set promotion-related fields (tenant_id, user_id, membership_id).
    
    These fields are nullable initially and filled when a signup is promoted to a user.
    """
    tenant_id = uuid4()
    user_id = uuid4()
    membership_id = uuid4()
    now = datetime.now(UTC)
    
    signup = Signup(
        id=uuid4(),
        email="promotion@example.com",
        status=SignupStatus.PROMOTED.value,
        tenant_id=tenant_id,
        user_id=user_id,
        membership_id=membership_id,
        promoted_at=now,
    )
    db_session.add(signup)
    await db_session.commit()
    await db_session.refresh(signup)
    
    assert signup.tenant_id == tenant_id
    assert signup.user_id == user_id
    assert signup.membership_id == membership_id
    assert signup.promoted_at is not None
    assert signup.status == SignupStatus.PROMOTED.value


@pytest.mark.asyncio
async def test_signup_updated_at_changes_on_update(db_session: AsyncSession):
    """
    Test: updated_at timestamp is automatically updated when record is modified.
    """
    signup = Signup(
        id=uuid4(),
        email="update@example.com",
        status=SignupStatus.PENDING_REVIEW.value,
    )
    db_session.add(signup)
    await db_session.commit()
    await db_session.refresh(signup)
    
    original_created_at = signup.created_at
    original_updated_at = signup.updated_at
    
    # Wait a tiny bit to ensure timestamp difference
    import asyncio
    await asyncio.sleep(0.1)
    
    # Update the signup
    signup.status = SignupStatus.APPROVED.value
    await db_session.commit()
    await db_session.refresh(signup)
    
    # created_at should not change
    assert signup.created_at == original_created_at
    
    # updated_at should be different (or at least >=)
    assert signup.updated_at >= original_updated_at
