# Tenant Isolation Regression Test Suite

This directory contains comprehensive regression tests to ensure tenant isolation cannot be accidentally broken.

## Test Coverage Matrix

### Projects Endpoints

| Endpoint | Method | Test Cases | Status |
|----------|--------|------------|--------|
| `/api/v1/projects` | GET | Missing header, Invalid ID, Wrong user, Cross-tenant read | ✅ |
| `/api/v1/projects/{id}` | GET | Missing header, Cross-tenant read, Non-existent | ✅ |
| `/api/v1/projects` | POST | Missing header, tenant_id ignored, Correct tenant | ✅ |

**Total: 10 tests**

### Controls Endpoints

| Endpoint | Method | Test Cases | Status |
|----------|--------|------------|--------|
| `/api/v1/controls` | GET | Missing header, Invalid ID, Wrong user, Cross-tenant read | ✅ |
| `/api/v1/controls/{id}` | GET | Missing header, Cross-tenant read, Non-existent | ✅ |
| `/api/v1/controls` | POST | Missing header, tenant_id ignored, Correct tenant | ✅ |

**Total: 10 tests**

### Project Controls Endpoints

| Endpoint | Method | Test Cases | Status |
|----------|--------|------------|--------|
| `/api/v1/projects/{id}/controls` | GET | Missing header, Cross-tenant read | ✅ |
| `/api/v1/projects/{id}/controls` | POST | Missing header, Cross-tenant attach, Cross-tenant project | ✅ |

**Total: 5 tests**

### Membership Enforcement

| Test Case | Status |
|-----------|--------|
| All endpoints require membership | ✅ |
| Non-existent membership ID | ✅ |
| Membership ownership validation | ✅ |
| tenant_id never from client input | ✅ |

**Total: 4 tests**

### Multi-Membership Switching

| Test Case | Status |
|-----------|--------|
| Comprehensive multi-membership isolation | ✅ |
| Immediate context switching | ✅ |

**Total: 2 tests**

## Test Categories

### 1. Missing Membership Header
- **Expected:** 403 Forbidden
- **Coverage:** All tenant-scoped endpoints

### 2. Invalid Membership ID
- **Expected:** 400 Bad Request or 403 Forbidden
- **Coverage:** List endpoints

### 3. Membership Ownership
- **Expected:** 403 Forbidden if membership belongs to different user
- **Coverage:** All tenant-scoped endpoints

### 4. Cross-Tenant Read Blocked
- **Expected:** 404 Not Found (to avoid leaking existence)
- **Coverage:** GET by ID endpoints

### 5. Cross-Tenant Write Blocked
- **Expected:** 404 Not Found or 400 Bad Request
- **Coverage:** POST endpoints (create operations)

### 6. tenant_id Ignored from Payload
- **Expected:** tenant_id in request body is ignored; derived from membership context
- **Coverage:** POST endpoints

### 7. Multi-Membership Switching
- **Expected:** Data visibility changes immediately when X-Membership-Id changes
- **Coverage:** All endpoints

## Running Tests

```bash
# Run all isolation tests
poetry run pytest tests/isolation/ -v

# Run specific test file
poetry run pytest tests/isolation/test_projects_isolation.py -v

# Run with coverage
poetry run pytest tests/isolation/ --cov=api --cov-report=html
```

## Test Structure

```
tests/isolation/
├── __init__.py
├── conftest.py                    # Shared fixtures and utilities
├── test_projects_isolation.py     # Projects endpoint tests
├── test_controls_isolation.py     # Controls endpoint tests
├── test_project_controls_isolation.py  # Project Controls endpoint tests
├── test_membership_enforcement.py # Membership validation tests
└── test_multi_membership_switching.py  # Multi-membership tests
```

## Key Test Patterns

### Pattern 1: Missing Header
```python
headers = {"Authorization": f"Bearer {token}"}
# Note: NO X-Membership-Id header
response = client.get("/api/v1/projects", headers=headers)
assert response.status_code == status.HTTP_403_FORBIDDEN
```

### Pattern 2: Cross-Tenant Read
```python
# Create resource in Tenant B
# Try to access with Tenant A membership
response = client.get(f"/api/v1/projects/{project_b_id}", headers=headers_a)
assert response.status_code == status.HTTP_404_NOT_FOUND
```

### Pattern 3: tenant_id Ignored
```python
project_data = {
    "name": "Test",
    "tenant_id": str(tenant_b.id),  # Should be ignored
}
response = client.post("/api/v1/projects", json=project_data, headers=headers_a)
assert response.json()["tenant_id"] == str(tenant_a.id)  # From membership
```

## Adding New Tests

When adding new tenant-scoped endpoints:

1. Add tests to the appropriate isolation test file
2. Cover all 6 core test cases:
   - Missing membership header
   - Invalid membership ID
   - Membership ownership validation
   - Cross-tenant read blocked
   - Cross-tenant write blocked (if applicable)
   - tenant_id ignored from payload
3. Add multi-membership switching test if applicable
4. Update this README with the new endpoint

## Regression Prevention

These tests serve as a **regression test suite** to prevent:
- Accidental removal of membership requirement
- Cross-tenant data leaks
- Client-provided tenant_id being accepted
- Broken multi-membership switching

**All tests must pass before merging any changes to tenant-scoped endpoints.**

