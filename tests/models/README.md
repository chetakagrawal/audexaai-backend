# Model Tests

This directory contains DB-backed tests for SQLAlchemy models.

## Test Structure

These tests verify:
- Model behavior and field defaults
- Database constraints and validations
- Query patterns and indexes
- Data persistence and retrieval

## Running Tests

```bash
# Run all model tests
poetry run pytest tests/models/ -v

# Run specific model tests
poetry run pytest tests/models/test_signup.py -v
```

## Test Categories

### DB-Backed Model Tests
- **Purpose**: Verify model behavior, constraints, and query patterns
- **Scope**: Individual model testing
- **Database**: Uses real database session (via `db_session` fixture)
- **Pattern**: Create → Verify → Query → Assert

### Notes
- These are **not** unit tests (which would mock dependencies)
- These are **not** API integration tests (which test endpoints)
- These tests directly exercise the SQLAlchemy model layer

## Adding New Model Tests

When adding tests for a new model:

1. Create `tests/models/test_<model_name>.py`
2. Follow the pattern established in `test_signup.py`:
   - Test minimal creation
   - Test full field population
   - Test constraints (unique, nullable, etc.)
   - Test query patterns (indexed fields)
   - Test relationships (if applicable)
3. Use the `db_session` fixture from `tests/conftest.py`
4. Clean up after each test (automatically via fixture)
