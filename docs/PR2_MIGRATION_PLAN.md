# PR2 Migration Plan: Add tenant_id to Tenant-Owned Tables

## Current State Inventory

### Existing Tables (from models)
- ✅ `tenants` - No tenant_id needed (it IS the tenant)
- ✅ `users` - No tenant_id (multi-tenant via user_tenants)
- ✅ `user_tenants` - **Already has tenant_id FK** ✅
- ✅ `auth_identities` - No tenant_id (belongs to user, not tenant)

### Tables from ERD That Need tenant_id

Based on the ERD, the following tables should have `tenant_id` FK:

#### Direct Tenant-Owned Tables (Primary Resources)
1. `projects` - tenant_id FK
2. `applications` - tenant_id FK
3. `controls` - tenant_id FK
4. `frameworks` - tenant_id FK
5. `test_attributes` - tenant_id FK
6. `pbc_requests` - tenant_id FK
7. `evidence_files` - tenant_id FK
8. `evidence_pages` - tenant_id FK
9. `ai_runs` - tenant_id FK
10. `ai_run_inputs` - tenant_id FK
11. `ai_run_outputs` - tenant_id FK
12. `ai_l1_indexes` - tenant_id FK
13. `ai_l2_indexes` - tenant_id FK
14. `ai_l3_indexes` - tenant_id FK
15. `ai_l4_indexes` - tenant_id FK
16. `findings` - tenant_id FK

#### Join Tables (Derive tenant_id from parent)
17. `project_controls` - tenant_id FK (from project)
18. `control_frameworks` - tenant_id FK (from control)
19. `project_users` - tenant_id FK (from project)
20. `project_applications` - tenant_id FK (from project)
21. `control_applications` - tenant_id FK (from control)
22. `pbc_request_controls` - tenant_id FK (from pbc_request)

---

## Migration Strategy

### Phase 1: Direct Tenant-Owned Tables
**Strategy**: If tables don't exist, create WITH tenant_id from start.
**If tables exist without tenant_id**:
1. Add `tenant_id UUID NULL`
2. Backfill: N/A (must be set during creation or via parent relationship)
3. Set NOT NULL
4. Add FK constraint
5. Add index on `tenant_id`
6. Add composite index `(tenant_id, id)` for efficient tenant-scoped lookups

### Phase 2: Join Tables
**Strategy**: Derive tenant_id from parent relationship
1. Add `tenant_id UUID NULL`
2. Backfill via parent:
   - `project_controls` ← `projects.tenant_id` via `project_id`
   - `control_frameworks` ← `controls.tenant_id` via `control_id`
   - `project_users` ← `projects.tenant_id` via `project_id`
   - `project_applications` ← `projects.tenant_id` via `project_id`
   - `control_applications` ← `controls.tenant_id` via `control_id`
   - `pbc_request_controls` ← `pbc_requests.tenant_id` via `pbc_request_id`
3. Set NOT NULL
4. Add FK constraint
5. Add index on `tenant_id`
6. Add composite unique constraint: `(tenant_id, <fk1>, <fk2>)` where applicable

### Phase 3: Child Tables (Derive from parent)
**Strategy**: Derive tenant_id from immediate parent
1. Add `tenant_id UUID NULL`
2. Backfill:
   - `evidence_files` ← `pbc_requests.tenant_id` via `pbc_request_id`
   - `evidence_pages` ← `evidence_files.tenant_id` via `evidence_file_id`
   - `ai_run_inputs` ← `ai_runs.tenant_id` via `ai_run_id`
   - `ai_run_outputs` ← `ai_runs.tenant_id` via `ai_run_id`
   - `ai_l1_indexes` ← `ai_run_outputs.tenant_id` via `ai_run_output_id`
   - `ai_l2_indexes` ← `ai_run_outputs.tenant_id` via `ai_run_output_id`
   - `ai_l3_indexes` ← `ai_run_outputs.tenant_id` via `ai_run_output_id`
   - `ai_l4_indexes` ← `ai_run_outputs.tenant_id` via `ai_run_output_id`
   - `findings` ← `projects.tenant_id` via `project_id`
3. Set NOT NULL
4. Add FK constraint
5. Add index on `tenant_id`

---

## Backfill SQL Templates

### For Join Tables:
```sql
-- Example: project_controls
UPDATE project_controls pc
SET tenant_id = p.tenant_id
FROM projects p
WHERE pc.project_id = p.id
  AND pc.tenant_id IS NULL;
```

### For Child Tables:
```sql
-- Example: evidence_files
UPDATE evidence_files ef
SET tenant_id = pr.tenant_id
FROM pbc_requests pr
WHERE ef.pbc_request_id = pr.id
  AND ef.tenant_id IS NULL;
```

---

## Index Strategy

For each table with tenant_id:
1. **Single index**: `CREATE INDEX ix_<table>_tenant_id ON <table>(tenant_id);`
2. **Composite index** (for tenant-scoped lookups): `CREATE INDEX ix_<table>_tenant_id_id ON <table>(tenant_id, id);`
3. **Business key composite** (if applicable): `CREATE INDEX ix_<table>_tenant_id_<key> ON <table>(tenant_id, <business_key>);`

---

## Migration Order

1. **Direct tenant-owned tables first** (projects, applications, controls, frameworks, test_attributes)
2. **Then join tables** (can backfill from direct tables)
3. **Then child tables** (can backfill from direct or join tables)
4. **Finally deep child tables** (evidence_pages, ai indexes)

---

## Safety Checks

Before each migration:
- ✅ Verify parent table exists and has tenant_id
- ✅ Verify no orphaned records (FKs point to valid parents)
- ✅ Verify backfill will set all rows (no NULLs remain)
- ✅ Test downgrade path

After each migration:
- ✅ Verify all rows have tenant_id (NOT NULL enforced)
- ✅ Verify FK constraint is valid
- ✅ Verify indexes are created
- ✅ Run tenant isolation tests

