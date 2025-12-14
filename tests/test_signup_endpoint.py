"""Integration tests for signup endpoint."""

import pytest
from fastapi import status


@pytest.mark.asyncio
async def test_create_signup_success(client, db_session):
    """
    Test: Creating a signup with valid data succeeds.
    
    Happy path: POST /api/v1/signups with valid data returns 201 with id and status.
    """
    signup_data = {
        "email": "test@example.com",
        "full_name": "John Doe",
        "company_name": "Acme Corp",
        "company_domain": "acme.com",
        "requested_auth_mode": "direct",
    }
    
    response = client.post("/api/v1/signups", json=signup_data)
    
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert "id" in data
    assert data["status"] == "pending_review"
    assert isinstance(data["id"], str)


@pytest.mark.asyncio
async def test_create_signup_minimal_data(client, db_session):
    """
    Test: Creating a signup with only required email field succeeds.
    """
    signup_data = {
        "email": "minimal@example.com",
    }
    
    response = client.post("/api/v1/signups", json=signup_data)
    
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert "id" in data
    assert data["status"] == "pending_review"


@pytest.mark.asyncio
async def test_create_signup_normalizes_email(client, db_session):
    """
    Test: Email is normalized to lowercase before storing.
    """
    signup_data = {
        "email": "Test@Example.COM",
    }
    
    response = client.post("/api/v1/signups", json=signup_data)
    
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    
    # Verify email was normalized in the database
    from sqlalchemy import select
    from models.signup import Signup
    
    result = await db_session.execute(
        select(Signup).where(Signup.id == data["id"])
    )
    signup = result.scalar_one()
    assert signup.email == "test@example.com"


@pytest.mark.asyncio
async def test_create_signup_invalid_auth_mode(client, db_session):
    """
    Test: Invalid requested_auth_mode is rejected with 422.
    """
    signup_data = {
        "email": "test@example.com",
        "requested_auth_mode": "invalid_mode",
    }
    
    response = client.post("/api/v1/signups", json=signup_data)
    
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_create_signup_valid_auth_modes(client, db_session):
    """
    Test: Both 'sso' and 'direct' auth modes are accepted.
    """
    # Test SSO mode
    signup_data_sso = {
        "email": "sso@example.com",
        "requested_auth_mode": "sso",
    }
    response_sso = client.post("/api/v1/signups", json=signup_data_sso)
    assert response_sso.status_code == status.HTTP_201_CREATED
    
    # Test direct mode
    signup_data_direct = {
        "email": "direct@example.com",
        "requested_auth_mode": "direct",
    }
    response_direct = client.post("/api/v1/signups", json=signup_data_direct)
    assert response_direct.status_code == status.HTTP_201_CREATED


@pytest.mark.asyncio
async def test_create_signup_stores_metadata(client, db_session):
    """
    Test: Metadata JSON is stored correctly.
    """
    metadata = {
        "source": "pilot_form",
        "referrer": "website",
        "utm_campaign": "pilot_2024",
    }
    
    signup_data = {
        "email": "metadata@example.com",
        "metadata": metadata,
    }
    
    response = client.post("/api/v1/signups", json=signup_data)
    
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    
    # Verify metadata was stored
    from sqlalchemy import select
    from models.signup import Signup
    
    result = await db_session.execute(
        select(Signup).where(Signup.id == data["id"])
    )
    signup = result.scalar_one()
    assert signup.signup_metadata == metadata


@pytest.mark.asyncio
async def test_create_signup_missing_email(client, db_session):
    """
    Test: Missing email returns 422 validation error.
    """
    signup_data = {
        "full_name": "John Doe",
    }
    
    response = client.post("/api/v1/signups", json=signup_data)
    
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_create_signup_invalid_email(client, db_session):
    """
    Test: Invalid email format returns 422 validation error.
    """
    signup_data = {
        "email": "not-an-email",
    }
    
    response = client.post("/api/v1/signups", json=signup_data)
    
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_create_signup_no_auth_required(client, db_session):
    """
    Test: Endpoint is public - no authentication required.
    
    This is a public endpoint, so it should work without auth headers.
    """
    signup_data = {
        "email": "public@example.com",
    }
    
    # No auth headers
    response = client.post("/api/v1/signups", json=signup_data)
    
    assert response.status_code == status.HTTP_201_CREATED
