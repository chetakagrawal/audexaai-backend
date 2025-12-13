# Tenant Isolation Test Matrix

## Summary

**Total Tests:** 33  
**Resources Covered:** Projects, Controls, Project Controls  
**Endpoints Tested:** 8  
**Status:** ✅ All passing

## Endpoint Coverage

### Projects

| Endpoint | Method | Missing Header | Invalid ID | Wrong User | Cross-Tenant Read | Cross-Tenant Write | tenant_id Ignored | Multi-Membership |
|----------|--------|----------------|------------|------------|-------------------|-------------------|-------------------|-----------------|
| `/api/v1/projects` | GET | ✅ | ✅ | ✅ | ✅ | N/A | N/A | ✅ |
| `/api/v1/projects/{id}` | GET | ✅ | N/A | N/A | ✅ | N/A | N/A | ✅ |
| `/api/v1/projects` | POST | ✅ | N/A | N/A | N/A | ✅ | ✅ | ✅ |

**Tests:** 10

### Controls

| Endpoint | Method | Missing Header | Invalid ID | Wrong User | Cross-Tenant Read | Cross-Tenant Write | tenant_id Ignored | Multi-Membership |
|----------|--------|----------------|------------|------------|-------------------|-------------------|-------------------|-----------------|
| `/api/v1/controls` | GET | ✅ | ✅ | ✅ | ✅ | N/A | N/A | ✅ |
| `/api/v1/controls/{id}` | GET | ✅ | N/A | N/A | ✅ | N/A | N/A | ✅ |
| `/api/v1/controls` | POST | ✅ | N/A | N/A | N/A | ✅ | ✅ | ✅ |

**Tests:** 10

### Project Controls

| Endpoint | Method | Missing Header | Invalid ID | Wrong User | Cross-Tenant Read | Cross-Tenant Write | tenant_id Ignored | Multi-Membership |
|----------|--------|----------------|------------|------------|-------------------|-------------------|-------------------|-----------------|
| `/api/v1/projects/{id}/controls` | GET | ✅ | N/A | N/A | ✅ | N/A | N/A | ✅ |
| `/api/v1/projects/{id}/controls` | POST | ✅ | N/A | N/A | N/A | ✅ | N/A | ✅ |

**Tests:** 5

### Membership Enforcement (Cross-Cutting)

| Test Case | Coverage |
|-----------|----------|
| All endpoints require membership | All 8 endpoints |
| Non-existent membership ID | List endpoints |
| Membership ownership validation | All endpoints |
| tenant_id never from client input | POST endpoints |

**Tests:** 4

### Multi-Membership Switching

| Test Case | Coverage |
|-----------|----------|
| Comprehensive isolation | Projects, Controls, Project Controls |
| Immediate context switching | Projects |

**Tests:** 2

## Test Case Definitions

### 1. Missing Header
- **Test:** Request without `X-Membership-Id` header
- **Expected:** 403 Forbidden
- **Message:** "X-Membership-Id header is required"

### 2. Invalid ID
- **Test:** Request with invalid UUID format
- **Expected:** 400 Bad Request or 403 Forbidden
- **Message:** "Invalid X-Membership-Id format"

### 3. Wrong User
- **Test:** Request with membership ID belonging to different user
- **Expected:** 403 Forbidden
- **Message:** "Membership does not belong to user"

### 4. Cross-Tenant Read
- **Test:** Access resource created in different tenant
- **Expected:** 404 Not Found (to avoid leaking existence)
- **Message:** "not found"

### 5. Cross-Tenant Write
- **Test:** Create/update resource with cross-tenant reference
- **Expected:** 404 Not Found or 400 Bad Request
- **Message:** Varies by endpoint

### 6. tenant_id Ignored
- **Test:** Include tenant_id in request payload
- **Expected:** tenant_id ignored; derived from membership context
- **Verification:** Response tenant_id matches membership tenant_id

### 7. Multi-Membership Switching
- **Test:** User with multiple memberships switches context
- **Expected:** Data visibility changes immediately
- **Verification:** Resources only visible in correct tenant context

## Test Files

1. `test_projects_isolation.py` - 10 tests
2. `test_controls_isolation.py` - 10 tests
3. `test_project_controls_isolation.py` - 5 tests
4. `test_membership_enforcement.py` - 4 tests
5. `test_multi_membership_switching.py` - 2 tests

## Running Tests

```bash
# All isolation tests
poetry run pytest tests/isolation/ -v

# Specific resource
poetry run pytest tests/isolation/test_projects_isolation.py -v

# Quick check
poetry run pytest tests/isolation/ -q
```

## Regression Prevention

These tests ensure:
- ✅ Membership requirement cannot be removed
- ✅ Cross-tenant access is always blocked
- ✅ Client-provided tenant_id is never accepted
- ✅ Multi-membership switching works correctly
- ✅ All tenant-scoped endpoints are protected

**All 33 tests must pass before merging any changes.**

