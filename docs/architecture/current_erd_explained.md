# ERD Explained (Practical)

This document explains the ERD in **plain terms**, using real-world audit examples.

## Core Identity

### Tenant
A company using the product.
Example:
- Acme Corp
- Globex Inc

### User
A real person.
Example:
- Alex (external auditor)

### UserTenant (Membership)
Connects a user to a tenant with a role.
Example:
- Alex is an auditor for Acme
- Alex is also an auditor for Globex

This is the **authorization boundary**.

### AuthIdentity
How a user logs in.
Examples:
- Google login
- Microsoft login
- SAML (Okta)

---

## Signup & SSO Onboarding

### Signup
A signup request for the pilot program.
Example:
- "john@acme.com" requests access, status: "pending_review"

### SetupToken
One-time token for SSO onboarding (expires in 7 days).
Example:
- Token generated when SSO signup is promoted
- Used to access SSO configuration page

### TenantSSOConfig
SSO configuration for a tenant (SAML 2.0 or OIDC).
Example:
- Acme Corp has Okta SSO configured
- One config per tenant

---

## Audit Domain

### Project
An engagement within a tenant.
Example:
- "FY25 SOX Audit" for Acme Corp

### Control (RACM)
A SOX control owned by the tenant with full audit trail tracking.
Example:
- User access provisioning control

**Audit Metadata:**
- `row_version`: Tracks version for optimistic locking (increments on each update)
- `updated_at`: Timestamp of last modification
- `updated_by_membership_id`: Who last updated the control
- `deleted_at`: Soft delete timestamp (NULL if active)
- `deleted_by_membership_id`: Who deleted the control

**Uniqueness:**
- `control_code` must be unique per tenant for **active** controls only
- Allows reusing control codes after soft delete

**Version History:**
- All updates and deletes are automatically captured in `entity_versions` table
- Each change creates a snapshot of the OLD row state before modification
- Soft deletes are tracked as DELETE operations
- Version history is queryable via service layer (`controls_versions_service`)

### ProjectControl
Overrides control behavior for a specific audit.
Example:
- Control is "key" this year but not last year

### Application
A business application within a tenant (e.g., ERP system, CRM, etc.).
Example:
- "SAP ERP" for Acme Corp
- "Salesforce CRM" for Acme Corp

**Audit Metadata:**
- `created_by_membership_id`: Who created the application
- `updated_at`: Timestamp of last modification
- `updated_by_membership_id`: Who last updated the application
- `deleted_at`: Soft delete timestamp (NULL if active)
- `deleted_by_membership_id`: Who deleted the application
- `row_version`: Tracks version for optimistic locking (increments on each update)

**Uniqueness:**
- `name` must be unique per tenant for **active** applications only (WHERE deleted_at IS NULL)
- Allows reusing application names after soft delete

**Ownership:**
- `business_owner_membership_id`: Business owner of the application (nullable)
- `it_owner_membership_id`: IT owner of the application (nullable)

**Version History:**
- All updates and deletes are automatically captured in `entity_versions` table
- Each change creates a snapshot of the OLD row state before modification
- Soft deletes are tracked as DELETE operations
- Version history is queryable via service layer (`applications_versions_service`)

---

### EntityVersion (Version History)

Generic table that stores version snapshots for any entity type (currently `controls` and `applications`).

**How It Works:**
- Postgres triggers automatically capture OLD row state before UPDATE/DELETE
- Each snapshot includes the full row data as JSONB
- Tracks `version_num` (from OLD.row_version), `valid_from`/`valid_to` timestamps
- Records who made the change via `changed_by_membership_id`

**Fields:**
- `entity_type`: Table name (e.g., 'controls', 'applications')
- `entity_id`: ID of the entity being versioned
- `operation`: 'UPDATE' or 'DELETE'
- `version_num`: The row_version that was captured (OLD.row_version)
- `valid_from`: When this version was valid (COALESCE(OLD.updated_at, OLD.created_at))
- `valid_to`: When this version ended (NOW() when snapshot was created)
- `data`: Full JSONB snapshot of the OLD row

**Usage:**
- Query all versions: `get_control_versions()` or `get_application_versions()`
- Query state at point in time: `get_control_as_of()` or `get_application_as_of()`
- All queries are tenant-scoped for security