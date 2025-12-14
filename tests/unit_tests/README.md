# Unit Tests for Endpoints

This directory contains unit tests for API endpoint handlers and logic.

## Test Structure

These tests verify:
- Endpoint handler function logic
- Request validation and parsing
- Response serialization
- Error handling and exception paths
- Business logic specific to endpoints

## Running Tests

```bash
# Run all unit tests
poetry run pytest tests/unit_tests/ -v

# Run specific endpoint unit tests
poetry run pytest tests/unit_tests/test_signup_endpoints.py -v
```

## Test Categories

### Unit Tests for Endpoints
- **Purpose**: Test endpoint handler logic in isolation
- **Scope**: Individual endpoint/handler testing
- **Mocks**: Database, services, auth, and other dependencies
- **Pattern**: Mock → Call → Assert

### Notes
- These are **unit tests** that mock all dependencies
- These are **NOT** integration tests (which test full HTTP request/response)
- Integration tests for endpoints are in `tests/integration/` directory
- These tests do NOT start an HTTP server or make network calls

## Separation from Integration Tests

### Unit Tests (`tests/unit_tests/`)
- Test endpoint handler functions in isolation
- Mock all dependencies (DB, services, auth)
- Focus on logic, validation, error handling
- Fast execution, no external dependencies

### Integration Tests (`tests/integration/`)
- Test full HTTP request/response cycle
- Use `httpx.AsyncClient` to call actual endpoints
- Test routing, auth middleware, serialization
- Verify complete end-to-end behavior

## Adding New Endpoint Unit Tests

When adding unit tests for a new endpoint:

1. Create `tests/unit_tests/test_<endpoint_name>_<method>.py` or `test_<router_name>_endpoints.py`
2. Follow the pattern:
   - Mock required dependencies (db_session, services, auth)
   - Test handler function directly
   - Test request validation
   - Test error cases
   - Test response serialization
3. Use standard pytest fixtures and mocks
4. Keep tests focused on the endpoint's specific logic

## Example Structure

```python
from unittest.mock import AsyncMock, patch
import pytest

@patch('api.v1.signup.signup_service')
async def test_create_signup_handler(mock_service):
    """Test signup POST handler logic."""
    # Arrange
    mock_service.create_signup.return_value = {...}
    request_data = {...}
    
    # Act
    result = await create_signup_handler(request_data, db_session=AsyncMock())
    
    # Assert
    assert result.status_code == 201
    mock_service.create_signup.assert_called_once()
```
