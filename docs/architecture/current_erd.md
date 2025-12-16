# ERD (Reference Only)

This ERD represents the **current data model** for Audexa AI.

**Important**
- This ERD is a **design contract**, not an instruction to auto-generate schema.
- Tables may already exist in the database.
- Migrations must be **incremental and safe**.

## Usage
- Referenced in Cursor prompts when planning migrations

---

```mermaid
erDiagram
  %% Core Identity
  users {
    uuid id PK
    string primary_email UK
    string name
    boolean is_platform_admin
    boolean is_active
    datetime created_at
    datetime updated_at
  }

  tenants {
    uuid id PK
    string name
    string slug UK
    string status
    datetime created_at
    datetime updated_at
  }

  %% "membership" = a user's relationship to a tenant
  user_tenants {
    uuid id PK
    uuid user_id FK
    uuid tenant_id FK
    string role
    boolean is_default
    datetime created_at
  }

  auth_identities {
    uuid id PK
    uuid user_id FK
    string provider
    string provider_subject
    string email
    boolean email_verified
    string password_hash
    string password_algo
    datetime last_login_at
    datetime created_at
  }

  %% Signup & SSO Onboarding
  signups {
    uuid id PK
    string email
    string full_name
    string company_name
    string company_domain
    string requested_auth_mode
    string status
    jsonb signup_metadata
    datetime approved_at
    datetime rejected_at
    datetime promoted_at
    uuid tenant_id FK
    uuid user_id FK
    uuid membership_id FK
    datetime created_at
    datetime updated_at
  }

  setup_tokens {
    uuid id PK
    string token UK
    uuid user_id FK
    uuid signup_id FK
    datetime expires_at
    datetime used_at
    datetime created_at
  }

  tenant_sso_configs {
    uuid id PK
    uuid tenant_id FK
    string provider_type
    string metadata_url
    string entity_id
    string sso_url
    string x509_certificate
    string oidc_client_id
    string oidc_client_secret
    string oidc_discovery_url
    string oidc_redirect_uri
    boolean is_configured
    jsonb config_metadata
    datetime created_at
    datetime updated_at
  }

  %% Audit Domain
  projects {
    uuid id PK
    uuid tenant_id FK
    uuid created_by_membership_id FK
    string name
    string description
    date start_date
    date end_date
    string status
    datetime created_at
    datetime updated_at
  }

  controls {
    uuid id PK
    uuid tenant_id FK
    uuid created_by_membership_id FK
    string control_code UK
    string name
    string category
    string risk_rating
    string control_type
    string frequency
    boolean is_key
    boolean is_automated
    datetime created_at
  }

  project_controls {
    uuid id PK
    uuid tenant_id FK
    uuid project_id FK
    uuid control_id FK
    boolean is_key_override
    string frequency_override
    string notes
    datetime created_at
  }

  test_attributes {
    uuid id PK
    uuid tenant_id FK
    uuid control_id FK
    string code
    string name
    string frequency
    string test_procedure
    string expected_evidence
    datetime created_at
  }

  applications {
    uuid id PK
    uuid tenant_id FK
    string name
    string category
    string scope_rationale
    uuid business_owner_membership_id FK
    uuid it_owner_membership_id FK
    datetime created_at
  }

  project_applications {
    uuid id PK
    uuid tenant_id FK
    uuid project_id FK
    uuid application_id FK
    datetime created_at
  }

  control_applications {
    uuid id PK
    uuid tenant_id FK
    uuid control_id FK
    uuid application_id FK
    datetime created_at
  }

  pbc_requests {
    uuid id PK
    uuid tenant_id FK
    uuid project_id FK
    uuid application_id FK
    uuid control_id FK
    uuid owner_membership_id FK
    string title
    int samples_requested
    date due_date
    string status
    datetime created_at
  }

  %% Relationships
  users   ||--o{ user_tenants     : has
  tenants ||--o{ user_tenants     : has

  users   ||--o{ auth_identities  : has

  users   ||--o{ setup_tokens     : has
  signups ||--o{ setup_tokens     : generates

  tenants ||--|| tenant_sso_configs : has

  tenants ||--o{ projects         : has
  tenants ||--o{ controls         : has
  tenants ||--o{ applications     : has
  tenants ||--o{ test_attributes  : has

  user_tenants ||--o{ projects    : creates
  user_tenants ||--o{ controls    : created_by
  user_tenants ||--o{ applications : business_owns
  user_tenants ||--o{ applications : it_owns

  projects ||--o{ project_controls : has
  controls ||--o{ project_controls : referenced_in
  tenants  ||--o{ project_controls : scopes

  projects ||--o{ project_applications : scopes
  applications ||--o{ project_applications : included_in

  controls ||--o{ control_applications : mapped_to
  applications ||--o{ control_applications : maps

  controls ||--o{ test_attributes : has

  projects ||--o{ pbc_requests : has
  applications ||--o{ pbc_requests : for_app
  controls ||--o{ pbc_requests : for_control
  user_tenants ||--o{ pbc_requests : owned_by
  tenants ||--o{ pbc_requests : scopes

  %% Promotion targets (optional FKs on signups)
  tenants      ||--o{ signups     : promoted_from
  users        ||--o{ signups     : promoted_from
  user_tenants ||--o{ signups     : promoted_from
```
