# Integration Tests

This directory contains integration tests for API endpoints.

## Test Structure

These tests verify:
- Full HTTP request/response cycle
- Endpoint routing
- Authentication and authorization
- Request validation
- Response serialization
- Error handling

## Running Tests

```bash
# Run all integration tests
poetry run pytest tests/integration/ -v

# Run specific endpoint integration tests
poetry run pytest tests/integration/test_signup_endpoint.py -v
```

## Test Categories

### Endpoint Integration Tests
- **Purpose**: Test complete endpoint behavior via HTTP
- **Scope**: Full request/response cycle
- **Client**: Uses `httpx.AsyncClient` via `client` fixture
- **Pattern**: Make HTTP request → Assert response → Verify side effects

### Notes
- These tests use the `client` fixture from `tests/conftest.py`
- They make real HTTP requests to the FastAPI app
- They verify complete endpoint behavior including auth, validation, etc.
- These are **NOT** unit tests (which mock dependencies)

## Separation from Other Test Types

### Integration Tests (`tests/integration/`)
- Test full HTTP request/response via `httpx.AsyncClient`
- Verify routing, auth, validation, serialization
- Test complete end-to-end behavior

### Unit Tests (`tests/unit_tests/`)
- Test endpoint handler functions in isolation
- Mock all dependencies (DB, services, auth)
- Fast execution, no external dependencies

### Model Tests (`tests/models/`)
- Test SQLAlchemy model behavior
- Test database constraints and queries
- Use real database session

### Isolation Tests (`tests/isolation/`)
- Specialized integration tests for tenant isolation
- Verify cross-tenant access is blocked
- Regression tests for multi-tenancy safety

## Adding New Integration Tests

When adding integration tests for a new endpoint:

1. Create `tests/integration/test_<endpoint_name>.py`
2. Follow the pattern:
   - Use `client` fixture for HTTP requests
   - Use `db_session` fixture if you need to verify DB state
   - Test happy path, validation errors, auth failures
   - Test error cases and edge cases
3. Include all required test cases per `.cursorrules` section 8.3:
   - Happy path
   - Auth failure (missing, invalid, or expired token)
   - Validation failure
   - Tenant isolation (if applicable)

## Example Structure

```python
import pytest
from fastapi import status

@pytest.mark.asyncio
async def test_create_resource_success(client, db_session):
    """Test: Creating a resource succeeds."""
    data = {...}
    response = client.post("/api/v1/resources", json=data)
    
    assert response.status_code == status.HTTP_201_CREATED
    result = response.json()
    assert result["id"] is not None
```
