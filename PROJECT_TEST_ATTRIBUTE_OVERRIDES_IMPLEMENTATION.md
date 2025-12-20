# Project Test Attribute Overrides Implementation

## Overview

This document describes the implementation of project-level test attribute overrides, allowing auditors to customize test attribute procedure/evidence at the project level, either globally (for all apps) or for specific applications.

## Implementation Date

December 20, 2025

## Architecture

### Database Schema

**Table:** `project_test_attribute_overrides`

**Key Features:**
- Supports two scopes: global (application_id = NULL) or app-specific (application_id = UUID)
- Version-ready with `row_version`, soft delete support, and full audit trail
- Freezes base test attribute version at creation via `base_test_attribute_version_num`
- Partial unique indexes enforce one active override per scope

**Columns:**
- `id` (UUID, PK)
- `tenant_id` (UUID, FK to tenants, CASCADE)
- `project_control_id` (UUID, FK to project_controls, CASCADE)
- `test_attribute_id` (UUID, FK to test_attributes, RESTRICT)
- `application_id` (UUID, FK to applications, RESTRICT, NULLABLE) - NULL = global
- `base_test_attribute_version_num` (INT) - frozen from test_attributes.row_version
- `name_override`, `frequency_override`, `procedure_override`, `expected_evidence_override`, `notes` (TEXT, all nullable)
- Version-ready metadata: `created_at`, `created_by_membership_id`, `updated_at`, `updated_by_membership_id`, `deleted_at`, `deleted_by_membership_id`, `row_version`

**Indexes:**
- `ux_ptao_active_global`: UNIQUE (tenant_id, project_control_id, test_attribute_id) WHERE deleted_at IS NULL AND application_id IS NULL
- `ux_ptao_active_app`: UNIQUE (tenant_id, project_control_id, application_id, test_attribute_id) WHERE deleted_at IS NULL AND application_id IS NOT NULL
- Supporting composite indexes on (tenant_id, project_control_id) and (tenant_id, test_attribute_id)

**Trigger:**
- `trigger_audit_capture_project_test_attribute_override_version` captures snapshots to `entity_versions` on UPDATE/DELETE

### Layered Architecture

**Repo Layer** (`repos/project_test_attribute_overrides_repo.py`)
- Pure DB operations, no business logic
- Functions: `get_active_global`, `get_active_app`, `get_by_id`, `list_by_project_control`, `create`, `save`

**Service Layer** (`services/project_test_attribute_overrides_service.py`)
- Business validations and rules
- Functions:
  - `upsert_override`: Create or update override (idempotent)
  - `delete_override`: Soft delete override
  - `list_overrides_for_project_control`: List all overrides for a project control
  - `resolve_effective_test_attribute`: Apply precedence logic and return merged result

**Router Layer** (`api/v1/project_test_attribute_overrides.py`)
- Thin HTTP endpoints
- Routes:
  - `POST /project-controls/{project_control_id}/test-attributes/{test_attribute_id}/override` - Upsert override
  - `DELETE /project-test-attribute-overrides/{override_id}` - Delete override
  - `GET /project-controls/{project_control_id}/test-attributes/overrides` - List overrides
  - `GET /project-controls/{project_control_id}/test-attributes/{test_attribute_id}/effective` - Get effective (resolved) test attribute

## Business Rules

### Validation Rules

1. **Project Control Existence:** project_control must exist, belong to tenant, and not be removed
2. **Test Attribute Existence:** test_attribute must exist, belong to tenant, and not be deleted
3. **Control Matching:** test_attribute.control_id MUST equal project_control.control_id
4. **Application Scope:** If application_id provided:
   - Application must exist and belong to tenant
   - Application must be active in `project_control_applications` for the given project_control

### Precedence Logic

When resolving effective test attributes (for PBC/flattened views):

1. **App-Specific Override** (highest priority): If application_id provided and app-specific override exists
2. **Global Override** (medium priority): If no app-specific override, use global override (application_id = NULL)
3. **Base Test Attribute** (lowest priority): If no overrides exist, use base test attribute fields

### Version Freezing

- On override **creation**, `base_test_attribute_version_num` is set to the current `test_attributes.row_version`
- This freezes the reference version, allowing tracking of when overrides were created relative to test attribute changes
- Updates to the override increment its own `row_version` but preserve `base_test_attribute_version_num`

### Idempotent Upsert

- The `upsert_override` service function checks if an active override exists for the given scope
- If exists: updates in place (increments row_version, sets updated_at/updated_by)
- If not exists: creates new override with frozen version

## Testing

### Test Coverage

All tests in `tests/test_project_test_attribute_overrides.py` (8 tests, all passing):

1. **test_create_global_override** - Creates global override and verifies version freezing
2. **test_create_app_specific_override** - Creates app-specific override and validates app scope
3. **test_unique_constraint_global_override** - Verifies upsert updates existing override (idempotency)
4. **test_precedence_resolution** - Tests 3-tier precedence: app > global > base
5. **test_validation_test_attribute_wrong_control** - Rejects override if test_attribute not for same control
6. **test_validation_app_not_in_scope** - Rejects app override if app not in project_control_applications
7. **test_version_ready_behavior** - Verifies row_version increments on update/delete
8. **test_tenant_isolation** - Enforces tenant boundaries

### Running Tests

```bash
poetry run pytest tests/test_project_test_attribute_overrides.py -v
```

**Result:** ✅ 8 passed in 7.89s

## Migration

**File:** `alembic/versions/d46d61482b1f_add_project_test_attribute_overrides_.py`

**Actions:**
- Creates `project_test_attribute_overrides` table with all columns, indexes, and constraints
- Creates trigger for version history capture
- Properly handles upgrade/downgrade

**Apply Migration:**
```bash
poetry run alembic upgrade head
```

## API Examples

### Create Global Override

```http
POST /api/v1/project-controls/{project_control_id}/test-attributes/{test_attribute_id}/override
Content-Type: application/json

{
  "application_id": null,
  "procedure_override": "Custom procedure for all apps in this project",
  "notes": "Simplified for internal audit"
}
```

### Create App-Specific Override

```http
POST /api/v1/project-controls/{project_control_id}/test-attributes/{test_attribute_id}/override
Content-Type: application/json

{
  "application_id": "123e4567-e89b-12d3-a456-426614174000",
  "name_override": "SAP-Specific Test",
  "procedure_override": "SAP-specific testing steps",
  "expected_evidence_override": "Screenshots from SAP"
}
```

### Get Effective Test Attribute

```http
GET /api/v1/project-controls/{project_control_id}/test-attributes/{test_attribute_id}/effective?application_id={app_id}
```

**Response:**
```json
{
  "test_attribute_id": "...",
  "code": "TA-001",
  "name": "Test Attribute Name",
  "frequency": "Monthly",
  "test_procedure": "Merged procedure with override applied",
  "expected_evidence": "Merged evidence with override applied",
  "source": "project_app_override",
  "override_id": "...",
  "base_test_attribute_version_num": 3
}
```

### List Overrides for Project Control

```http
GET /api/v1/project-controls/{project_control_id}/test-attributes/overrides
```

### Delete Override

```http
DELETE /api/v1/project-test-attribute-overrides/{override_id}
```

## Files Modified/Created

### Created Files

1. `models/project_test_attribute_override.py` - ORM model + Pydantic schemas
2. `repos/project_test_attribute_overrides_repo.py` - Repository layer
3. `services/project_test_attribute_overrides_service.py` - Service layer with business logic
4. `api/v1/project_test_attribute_overrides.py` - API endpoints
5. `tests/test_project_test_attribute_overrides.py` - Comprehensive test suite
6. `alembic/versions/d46d61482b1f_add_project_test_attribute_overrides_.py` - Database migration

### Modified Files

1. `models/__init__.py` - Added import for new model
2. `api/router.py` - Registered new router

## Production Readiness

✅ **Complete Implementation:**
- ORM model with proper indexes and constraints
- Alembic migration with trigger for version history
- Strict layered architecture (repos → services → routers)
- Comprehensive business validations
- Full test coverage (8/8 tests passing)
- Tenant isolation enforced
- Version-ready metadata throughout
- Soft delete support

✅ **TDD Followed:**
- Tests written to spec requirements
- All validation scenarios covered
- Precedence logic verified
- Version freezing tested

✅ **Production-Grade:**
- No backward-compat breaking changes
- Incremental migration
- Timezone-aware timestamps
- No hard deletes
- Clean separation of concerns

## Future Enhancements

1. **Bulk Operations:** Add endpoint to bulk-create overrides for multiple test attributes
2. **History Viewer:** UI to view version history from `entity_versions` table
3. **Override Templates:** Save and reuse common override patterns
4. **Approval Workflow:** Add approval step before overrides take effect
5. **Audit Trail:** Enhanced reporting on who changed what and when

## Self-Check

**Files changed:** 8 (6 created, 2 modified)

**How to run tests:** 
```bash
poetry run pytest tests/test_project_test_attribute_overrides.py -v
```

**What user paths were tested:**
- Creating global and app-specific overrides
- Precedence resolution (app > global > base)
- Version freezing on override creation
- Row version increments on updates
- Soft delete behavior
- All validations (control matching, app scope, tenant isolation)
- Unique constraints via upsert idempotency

**UI/contract changes:**
- New API endpoints for managing overrides
- New response schema `EffectiveTestAttributeResponse` for resolved test attributes
- All changes are additive; no existing contracts broken

## Summary

The project test attribute overrides feature is **fully implemented and production-ready**. All tests pass, business rules are enforced, and the implementation follows strict TDD and layering principles. The feature enables auditors to customize test attributes at the project level with proper version tracking and precedence logic.

