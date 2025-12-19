# Unit Tests

This directory contains unit tests for the application layers (repos, services, and endpoints).

## Test Structure

Tests are organized by **domain/model** (not by layer), which groups all related tests together:

```
tests/unit_tests/
  controls/
    test_repo.py      # Repository layer tests
    test_service.py   # Service layer tests
  applications/
    test_repo.py
    test_service.py
  projects/
    test_repo.py
    test_service.py
```

### Test Categories

**Repository Tests** (`test_repo.py`):
- Database operations in isolation
- Query patterns and filtering
- Data persistence and retrieval
- No business logic, no HTTP concepts

**Service Tests** (`test_service.py`):
- Business logic and validation
- Tenant scoping and isolation
- Audit metadata handling
- Error handling and exceptions
- No database access (uses repo layer)

**Endpoint Tests** (if needed):
- Request/response handling
- Authentication and authorization
- Input validation
- Response serialization

## Running Tests

```bash
# Run all unit tests
poetry run pytest tests/unit_tests/ -v

# Run all tests for a specific domain
poetry run pytest tests/unit_tests/controls/ -v

# Run all repo tests across all domains
poetry run pytest tests/unit_tests/*/test_repo.py -v

# Run all service tests across all domains
poetry run pytest tests/unit_tests/*/test_service.py -v

# Run specific test file
poetry run pytest tests/unit_tests/controls/test_service.py -v
```

## Why Organize by Domain?

1. **Matches existing patterns**: `tests/models/` is also organized by domain
2. **Groups related tests**: All control tests (repo, service) are together
3. **Easier navigation**: Find all tests for a feature in one place
4. **Scales better**: As you add repos/services, they naturally group by domain
5. **Still flexible**: Can run by layer if needed: `pytest tests/unit_tests/*/test_repo.py`

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

## Adding New Unit Tests

### For a New Domain (e.g., "applications")

1. Create domain directory: `tests/unit_tests/applications/`
2. Create `__init__.py` in the directory
3. Add `test_repo.py` for repository tests
4. Add `test_service.py` for service tests
5. Follow existing patterns from `tests/unit_tests/controls/`

### For Repository Tests

```python
"""Unit tests for applications repository layer."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from repos import applications_repo

@pytest.mark.asyncio
async def test_repo_get_by_id_found(db_session: AsyncSession):
    """Test: Repository can retrieve an application by ID."""
    # Setup, test, assert
```

### For Service Tests

```python
"""Unit tests for applications service layer."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from services.applications_service import create_application

@pytest.mark.asyncio
async def test_service_create_application_sets_metadata(db_session: AsyncSession):
    """Test: Creating an application sets audit metadata."""
    # Setup, test, assert
```

## Notes

- These are **unit tests** that may use real database sessions (for repo/service tests)
- Integration tests (full HTTP request/response) are in `tests/integration/` and `tests/test_*_integration.py`
- Model tests (SQLAlchemy model behavior) are in `tests/models/`
