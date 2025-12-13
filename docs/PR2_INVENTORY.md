# PR2 Inventory: Tenant-Owned Tables Checklist

## Current Database State

**Existing Tables:**
- ✅ `tenants` - No tenant_id needed
- ✅ `users` - No tenant_id (multi-tenant via user_tenants)
- ✅ `user_tenants` - **Already has tenant_id FK** ✅
- ✅ `auth_identities` - No tenant_id (belongs to user)

**Note**: All other tables from ERD do not exist yet. They will be created WITH tenant_id from the start.

---

## Tables Requiring tenant_id (From ERD)

### ✅ Status Legend
- ✅ = tenant_id exists
- ❌ = tenant_id missing (needs migration)
- 🆕 = Table doesn't exist yet (will create with tenant_id)

---

### Direct Tenant-Owned Tables

| Table | Status | tenant_id Source | Backfill Strategy |
|-------|--------|------------------|-------------------|
| `projects` | 🆕 | Direct FK to tenants | Create with tenant_id |
| `applications` | 🆕 | Direct FK to tenants | Create with tenant_id |
| `controls` | 🆕 | Direct FK to tenants | Create with tenant_id |
| `frameworks` | 🆕 | Direct FK to tenants | Create with tenant_id |
| `test_attributes` | 🆕 | Direct FK to tenants | Create with tenant_id |
| `pbc_requests` | 🆕 | Direct FK to tenants | Create with tenant_id |
| `evidence_files` | 🆕 | Direct FK to tenants | Create with tenant_id |
| `evidence_pages` | 🆕 | Direct FK to tenants | Create with tenant_id |
| `ai_runs` | 🆕 | Direct FK to tenants | Create with tenant_id |
| `ai_run_inputs` | 🆕 | Direct FK to tenants | Create with tenant_id |
| `ai_run_outputs` | 🆕 | Direct FK to tenants | Create with tenant_id |
| `ai_l1_indexes` | 🆕 | Direct FK to tenants | Create with tenant_id |
| `ai_l2_indexes` | 🆕 | Direct FK to tenants | Create with tenant_id |
| `ai_l3_indexes` | 🆕 | Direct FK to tenants | Create with tenant_id |
| `ai_l4_indexes` | 🆕 | Direct FK to tenants | Create with tenant_id |
| `findings` | 🆕 | Direct FK to tenants | Create with tenant_id |

### Join Tables

| Table | Status | tenant_id Source | Backfill Strategy |
|-------|--------|------------------|-------------------|
| `project_controls` | 🆕 | From `projects.tenant_id` | `UPDATE ... FROM projects WHERE project_id = projects.id` |
| `control_frameworks` | 🆕 | From `controls.tenant_id` | `UPDATE ... FROM controls WHERE control_id = controls.id` |
| `project_users` | 🆕 | From `projects.tenant_id` | `UPDATE ... FROM projects WHERE project_id = projects.id` |
| `project_applications` | 🆕 | From `projects.tenant_id` | `UPDATE ... FROM projects WHERE project_id = projects.id` |
| `control_applications` | 🆕 | From `controls.tenant_id` | `UPDATE ... FROM controls WHERE control_id = controls.id` |
| `pbc_request_controls` | 🆕 | From `pbc_requests.tenant_id` | `UPDATE ... FROM pbc_requests WHERE pbc_request_id = pbc_requests.id` |

---

## Migration Plan Summary

Since all tables are new (🆕), the strategy is:

1. **Create all tables WITH tenant_id from the start**
   - No backfill needed
   - tenant_id is NOT NULL from creation
   - FK constraint added immediately
   - Indexes added immediately

2. **For join tables**: Still include tenant_id even though it can be derived
   - Provides query performance (direct filtering)
   - Ensures data integrity (tenant_id must match parent)
   - Enables composite unique constraints

3. **Composite Unique Constraints for Join Tables**:
   - `project_controls`: `UNIQUE(tenant_id, project_id, control_id)`
   - `control_frameworks`: `UNIQUE(tenant_id, control_id, framework_id)`
   - `project_users`: `UNIQUE(tenant_id, project_id, membership_id)`
   - `project_applications`: `UNIQUE(tenant_id, project_id, application_id)`
   - `control_applications`: `UNIQUE(tenant_id, control_id, application_id)`
   - `pbc_request_controls`: `UNIQUE(tenant_id, pbc_request_id, control_id)`

---

## If Tables Already Exist (Fallback Plan)

If any table exists without tenant_id, use this 4-step process:

### Step 1: Add Nullable Column
```sql
ALTER TABLE <table_name> 
ADD COLUMN tenant_id UUID NULL;
```

### Step 2: Backfill (if applicable)
```sql
-- For join/child tables only
UPDATE <table_name> t
SET tenant_id = p.tenant_id
FROM <parent_table> p
WHERE t.<parent_fk> = p.id
  AND t.tenant_id IS NULL;
```

### Step 3: Add Index
```sql
CREATE INDEX ix_<table_name>_tenant_id ON <table_name>(tenant_id);
CREATE INDEX ix_<table_name>_tenant_id_id ON <table_name>(tenant_id, id);
```

### Step 4: Enforce NOT NULL + FK
```sql
ALTER TABLE <table_name>
ALTER COLUMN tenant_id SET NOT NULL,
ADD CONSTRAINT fk_<table_name>_tenant_id 
FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;
```

---

## Next Steps

1. ✅ Inventory complete
2. ⏳ Create models with tenant_id
3. ⏳ Create migrations
4. ⏳ Add tenant isolation tests

