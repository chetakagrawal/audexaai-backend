# Multi-Tenant Auth Model - Usage Examples

This document walks through practical examples for common multi-tenant scenarios using the `Tenant`, `User`, `UserTenant`, and `AuthIdentity` models.

---

## 📋 Model Overview

- **Tenant**: Represents a company/organization (e.g., "Acme Corp", "Pilot Customer 1")
- **User**: Represents a person (can belong to multiple tenants)
- **UserTenant**: Links users to tenants with roles (many-to-many relationship)
- **AuthIdentity**: Authentication provider credentials (dev, SSO, etc.)

---

## 1️⃣ Company Signup: Creating Tenant and Users

**Scenario**: Acme Corporation signs up for your tool. You need to:
1. Create a tenant for Acme
2. Add their users to the tenant
3. Set up authentication

### Step-by-Step Process

1. **Create the Tenant**
   - Name: "Acme Corporation"
   - Slug: "acme-corp" (URL-friendly identifier)
   - Status: "active"

2. **Create the Admin User**
   - Email: "john.doe@acme.com"
   - Name: "John Doe"
   - Platform Admin: No (regular user)
   - Active: Yes

3. **Link User to Tenant**
   - User: John Doe
   - Tenant: Acme Corporation
   - Role: "admin" (admin role within this tenant)
   - Is Default: Yes (this is John's first/primary tenant)

4. **Create Auth Identity**
   - User: John Doe
   - Provider: "dev" (or "okta", "azure_ad" for SSO)
   - Provider Subject: "john.doe@acme.com"
   - Email: "john.doe@acme.com"
   - Email Verified: Yes

### Database Records After Setup

```
tenants table:
┌─────────────────────┬──────────────────────┬─────────────┬──────────┐
│ id                  │ name                 │ slug        │ status   │
├─────────────────────┼──────────────────────┼─────────────┼──────────┤
│ uuid-acme-tenant    │ Acme Corporation     │ acme-corp   │ active   │
└─────────────────────┴──────────────────────┴─────────────┴──────────┘

users table:
┌─────────────────────┬──────────────────────┬──────────────────────┬──────────────────┐
│ id                  │ primary_email        │ name                 │ is_platform_admin│
├─────────────────────┼──────────────────────┼──────────────────────┼──────────────────┤
│ uuid-john-doe       │ john.doe@acme.com   │ John Doe             │ false            │
└─────────────────────┴──────────────────────┴──────────────────────┴──────────────────┘

user_tenants table:
┌─────────────────────┬─────────────────────┬─────────────────────┬────────┬─────────────┐
│ id                  │ user_id            │ tenant_id           │ role   │ is_default  │
├─────────────────────┼─────────────────────┼─────────────────────┼────────┼─────────────┤
│ uuid-user-tenant-1  │ uuid-john-doe      │ uuid-acme-tenant    │ admin  │ true        │
└─────────────────────┴─────────────────────┴─────────────────────┴────────┴─────────────┘

auth_identities table:
┌─────────────────────┬─────────────────────┬──────────┬──────────────────────┬──────────────────────┐
│ id                  │ user_id            │ provider │ provider_subject      │ email                 │
├─────────────────────┼─────────────────────┼──────────┼──────────────────────┼──────────────────────┤
│ uuid-auth-1         │ uuid-john-doe      │ dev      │ john.doe@acme.com    │ john.doe@acme.com    │
└─────────────────────┴─────────────────────┴──────────┴──────────────────────┴──────────────────────┘
```

### Adding More Users to the Tenant

**Scenario**: Add Jane Smith as an auditor to Acme Corp.

**Process:**
1. Create User: "jane.smith@acme.com", "Jane Smith"
2. Create UserTenant link: Jane → Acme Corp, role="auditor"
3. Create AuthIdentity: Jane, provider="dev"

**Updated Database Records:**

```
users table (new record):
┌─────────────────────┬──────────────────────┬──────────────────────┬──────────────────┐
│ id                  │ primary_email        │ name                 │ is_platform_admin│
├─────────────────────┼──────────────────────┼──────────────────────┼──────────────────┤
│ uuid-jane-smith     │ jane.smith@acme.com │ Jane Smith           │ false            │
└─────────────────────┴──────────────────────┴──────────────────────┴──────────────────┘

user_tenants table (new record):
┌─────────────────────┬─────────────────────┬─────────────────────┬────────┬─────────────┐
│ id                  │ user_id            │ tenant_id           │ role   │ is_default  │
├─────────────────────┼─────────────────────┼─────────────────────┼────────┼─────────────┤
│ uuid-user-tenant-2  │ uuid-jane-smith    │ uuid-acme-tenant    │ auditor│ true        │
└─────────────────────┴─────────────────────┴─────────────────────┴────────┴─────────────┘

auth_identities table (new record):
┌─────────────────────┬─────────────────────┬──────────┬──────────────────────┬──────────────────────┐
│ id                  │ user_id            │ provider │ provider_subject      │ email                 │
├─────────────────────┼─────────────────────┼─────────────────────┼──────────────────────┼──────────────────────┤
│ uuid-auth-2         │ uuid-jane-smith     │ dev      │ jane.smith@acme.com  │ jane.smith@acme.com   │
└─────────────────────┴─────────────────────┴──────────┴──────────────────────┴──────────────────────┘
```

---

## 2️⃣ Multiple Teams from Same Company

**Scenario**: Acme Corporation has two teams that need separate tenants:
- **Acme Finance Team** (finance department)
- **Acme IT Team** (IT department)

Both are from the same company but need separate tenants for data isolation.

### Step-by-Step Process

**For Finance Team:**
1. Create Tenant: "Acme Corporation - Finance Team", slug="acme-finance"
2. Create User: "finance.admin@acme.com", "Finance Admin"
3. Link User to Tenant: Finance Admin → Finance Tenant, role="admin"
4. Create AuthIdentity: Finance Admin, provider="dev"

**For IT Team:**
1. Create Tenant: "Acme Corporation - IT Team", slug="acme-it"
2. Create User: "it.admin@acme.com", "IT Admin"
3. Link User to Tenant: IT Admin → IT Tenant, role="admin"
4. Create AuthIdentity: IT Admin, provider="dev"

### Database Records After Setup

```
tenants table:
┌─────────────────────┬──────────────────────────────────────┬──────────────────┬──────────┐
│ id                  │ name                                 │ slug              │ status   │
├─────────────────────┼──────────────────────────────────────┼──────────────────┼──────────┤
│ uuid-finance-tenant │ Acme Corporation - Finance Team     │ acme-finance      │ active   │
│ uuid-it-tenant      │ Acme Corporation - IT Team            │ acme-it           │ active   │
└─────────────────────┴──────────────────────────────────────┴──────────────────┴──────────┘

users table:
┌─────────────────────┬──────────────────────────┬──────────────────────┬──────────────────┐
│ id                  │ primary_email            │ name                 │ is_platform_admin│
├─────────────────────┼──────────────────────────┼──────────────────────┼──────────────────┤
│ uuid-finance-admin  │ finance.admin@acme.com  │ Finance Admin        │ false            │
│ uuid-it-admin       │ it.admin@acme.com       │ IT Admin             │ false            │
└─────────────────────┴──────────────────────────┴──────────────────────┴──────────────────┘

user_tenants table:
┌─────────────────────┬─────────────────────┬─────────────────────┬────────┬─────────────┐
│ id                  │ user_id              │ tenant_id           │ role   │ is_default  │
├─────────────────────┼─────────────────────┼─────────────────────┼────────┼─────────────┤
│ uuid-ut-finance     │ uuid-finance-admin  │ uuid-finance-tenant │ admin  │ true        │
│ uuid-ut-it          │ uuid-it-admin       │ uuid-it-tenant      │ admin  │ true        │
└─────────────────────┴─────────────────────┴─────────────────────┴────────┴─────────────┘

auth_identities table:
┌─────────────────────┬─────────────────────┬──────────┬──────────────────────────┬──────────────────────────┐
│ id                  │ user_id              │ provider │ provider_subject         │ email                    │
├─────────────────────┼─────────────────────┼──────────┼──────────────────────────┼──────────────────────────┤
│ uuid-auth-finance   │ uuid-finance-admin  │ dev      │ finance.admin@acme.com  │ finance.admin@acme.com   │
│ uuid-auth-it        │ uuid-it-admin       │ dev      │ it.admin@acme.com        │ it.admin@acme.com        │
└─────────────────────┴─────────────────────┴──────────┴──────────────────────────┴──────────────────────────┘
```

### User Belonging to Multiple Tenants

**Scenario**: A user works in both Finance and IT teams.

**Process:**
1. User already exists: "shared.user@acme.com", "Shared User"
2. Create UserTenant link #1: Shared User → Finance Tenant, role="auditor"
3. Create UserTenant link #2: Shared User → IT Tenant, role="user"
4. First tenant becomes default (is_default=true for Finance)

**Updated Database Records:**

```
users table (existing user):
┌─────────────────────┬──────────────────────┬──────────────────────┬──────────────────┐
│ id                  │ primary_email        │ name                 │ is_platform_admin│
├─────────────────────┼──────────────────────┼──────────────────────┼──────────────────┤
│ uuid-shared-user    │ shared.user@acme.com │ Shared User          │ false            │
└─────────────────────┴──────────────────────┴──────────────────────┴──────────────────┘

user_tenants table (two records for same user):
┌─────────────────────┬─────────────────────┬─────────────────────┬────────┬─────────────┐
│ id                  │ user_id             │ tenant_id           │ role   │ is_default  │
├─────────────────────┼─────────────────────┼─────────────────────┼────────┼─────────────┤
│ uuid-ut-shared-fin  │ uuid-shared-user   │ uuid-finance-tenant │ auditor│ true        │
│ uuid-ut-shared-it   │ uuid-shared-user   │ uuid-it-tenant      │ user   │ false       │
└─────────────────────┴─────────────────────┴─────────────────────┴────────┴─────────────┘
```

**Key Points:**
- Same user can belong to multiple tenants
- Each UserTenant record has its own role per tenant
- `is_default` flag marks the user's primary/default tenant
- When user logs in, they specify which tenant they want to access (via tenant_slug)

---

## 3️⃣ Pilot Customers: Ensuring Data Isolation

**Scenario**: You have 2 pilot customers who must only see their own data when they log in.

### Step-by-Step Process

**For Pilot Customer 1:**
1. Create Tenant: "Pilot Customer 1", slug="pilot-customer-1"
2. Create User: "admin@pilot1.com", "Pilot 1 Admin"
3. Link User to Tenant: Pilot 1 Admin → Pilot 1 Tenant, role="admin"
4. Create AuthIdentity: Pilot 1 Admin, provider="dev"
5. **Important**: `is_platform_admin = false` (pilot customers are NOT platform admins)

**For Pilot Customer 2:**
1. Create Tenant: "Pilot Customer 2", slug="pilot-customer-2"
2. Create User: "admin@pilot2.com", "Pilot 2 Admin"
3. Link User to Tenant: Pilot 2 Admin → Pilot 2 Tenant, role="admin"
4. Create AuthIdentity: Pilot 2 Admin, provider="dev"
5. **Important**: `is_platform_admin = false`

### Database Records After Setup

```
tenants table:
┌─────────────────────┬──────────────────────┬──────────────────────┬──────────┐
│ id                  │ name                 │ slug                 │ status   │
├─────────────────────┼──────────────────────┼──────────────────────┼──────────┤
│ uuid-pilot1-tenant  │ Pilot Customer 1     │ pilot-customer-1     │ active   │
│ uuid-pilot2-tenant  │ Pilot Customer 2     │ pilot-customer-2     │ active   │
└─────────────────────┴──────────────────────┴──────────────────────┴──────────┘

users table:
┌─────────────────────┬──────────────────────┬──────────────────────┬──────────────────┐
│ id                  │ primary_email        │ name                 │ is_platform_admin│
├─────────────────────┼──────────────────────┼──────────────────────┼──────────────────┤
│ uuid-pilot1-admin   │ admin@pilot1.com     │ Pilot 1 Admin        │ false            │
│ uuid-pilot2-admin   │ admin@pilot2.com     │ Pilot 2 Admin        │ false            │
└─────────────────────┴──────────────────────┴──────────────────────┴──────────────────┘

user_tenants table:
┌─────────────────────┬─────────────────────┬─────────────────────┬────────┬─────────────┐
│ id                  │ user_id             │ tenant_id            │ role   │ is_default  │
├─────────────────────┼─────────────────────┼─────────────────────┼────────┼─────────────┤
│ uuid-ut-pilot1      │ uuid-pilot1-admin  │ uuid-pilot1-tenant  │ admin  │ true        │
│ uuid-ut-pilot2      │ uuid-pilot2-admin  │ uuid-pilot2-tenant  │ admin  │ true        │
└─────────────────────┴─────────────────────┴─────────────────────┴────────┴─────────────┘

auth_identities table:
┌─────────────────────┬─────────────────────┬──────────┬──────────────────────┬──────────────────────┐
│ id                  │ user_id             │ provider │ provider_subject     │ email                │
├─────────────────────┼─────────────────────┼──────────────────────┼──────────────────────┼──────────────────────┤
│ uuid-auth-pilot1    │ uuid-pilot1-admin   │ dev      │ admin@pilot1.com     │ admin@pilot1.com     │
│ uuid-auth-pilot2    │ uuid-pilot2-admin   │ dev      │ admin@pilot2.com     │ admin@pilot2.com     │
└─────────────────────┴─────────────────────┴──────────────────────┴──────────────────────┴──────────────────────┘
```

### How Data Isolation Works

**Login Flow:**

1. **Pilot 1 logs in:**
   - Request: `POST /api/v1/auth/dev-login` with `email="admin@pilot1.com"`, `tenant_slug="pilot-customer-1"`
   - Backend finds/creates tenant: `uuid-pilot1-tenant`
   - Backend finds/creates user: `uuid-pilot1-admin`
   - Backend verifies UserTenant link exists: `uuid-pilot1-admin` → `uuid-pilot1-tenant`
   - Backend creates JWT token with:
     - `sub`: `uuid-pilot1-admin` (user ID)
     - `tenant_id`: `uuid-pilot1-tenant`
     - `role`: `admin`
     - `is_platform_admin`: `false`

2. **Pilot 1 makes API requests:**
   - Every request includes: `Authorization: Bearer <token>`
   - Backend's `get_current_user()` dependency:
     - Decodes JWT token
     - Extracts `tenant_id = uuid-pilot1-tenant`
     - Loads user from database
     - **Verifies UserTenant record exists**: Checks `user_tenants` table to ensure user belongs to tenant
     - Attaches `active_tenant_id = uuid-pilot1-tenant` to user object

3. **Data queries are filtered:**
   - All queries include: `WHERE tenant_id = uuid-pilot1-tenant`
   - Pilot 1 can ONLY see data where `tenant_id = uuid-pilot1-tenant`
   - Pilot 2 can ONLY see data where `tenant_id = uuid-pilot2-tenant`

**Example: Projects Table**

```
projects table (hypothetical):
┌─────────────────────┬─────────────────────┬─────────────────────┬──────────────┐
│ id                  │ tenant_id            │ name                 │ status       │
├─────────────────────┼─────────────────────┼─────────────────────┼──────────────┤
│ uuid-project-1      │ uuid-pilot1-tenant   │ Pilot 1 Project A   │ active       │
│ uuid-project-2      │ uuid-pilot1-tenant   │ Pilot 1 Project B    │ active       │
│ uuid-project-3      │ uuid-pilot2-tenant  │ Pilot 2 Project A    │ active       │
│ uuid-project-4      │ uuid-pilot2-tenant  │ Pilot 2 Project B    │ active       │
└─────────────────────┴─────────────────────┴─────────────────────┴──────────────┘
```

**When Pilot 1 queries projects:**
- Query: `SELECT * FROM projects WHERE tenant_id = uuid-pilot1-tenant`
- Result: Only `uuid-project-1` and `uuid-project-2` (Pilot 1's projects)
- Pilot 1 **cannot** see `uuid-project-3` or `uuid-project-4` (Pilot 2's projects)

**When Pilot 2 queries projects:**
- Query: `SELECT * FROM projects WHERE tenant_id = uuid-pilot2-tenant`
- Result: Only `uuid-project-3` and `uuid-project-4` (Pilot 2's projects)
- Pilot 2 **cannot** see `uuid-project-1` or `uuid-project-2` (Pilot 1's projects)

### Security Guarantees

1. **JWT Token Contains Tenant ID**: User cannot fake tenant_id (it's signed in token)
2. **UserTenant Verification**: Backend verifies user belongs to tenant via `user_tenants` table
3. **All Queries Filter by Tenant**: Every data query includes `tenant_id` filter
4. **Platform Admins Are Special**: Only users with `is_platform_admin=true` and `tenant_id=null` can see all data

---

## 🔐 Platform Admins

**Scenario**: Internal platform administrators who need access to all tenants.

### Database Records

```
users table:
┌─────────────────────┬──────────────────────┬──────────────────────┬──────────────────┐
│ id                  │ primary_email        │ name                 │ is_platform_admin│
├─────────────────────┼──────────────────────┼──────────────────────┼──────────────────┤
│ uuid-platform-admin│ admin@audexaai.com   │ Platform Admin       │ true             │
└─────────────────────┴──────────────────────┴──────────────────────┴──────────────────┘

user_tenants table:
┌─────────────────────┬─────────────────────┬─────────────────────┬────────┬─────────────┐
│ id                  │ user_id          │ tenant_id            │ role   │ is_default  │
│ (NO RECORDS)        │                  │                      │        │             │
└─────────────────────┴─────────────────────┴─────────────────────┴────────┴─────────────┘
```

**Key Points:**
- Platform admin has `is_platform_admin = true`
- Platform admin has **NO** UserTenant records (not linked to any tenant)
- When platform admin logs in, JWT token has `tenant_id = null`
- Platform admin can see all tenants' data (special handling in queries)

---

## 📊 Complete Example: Mixed Scenario

**Scenario**: You have:
- 1 company (Acme Corp) with 1 tenant
- 1 company (Beta Inc) with 2 teams (Finance, IT)
- 2 pilot customers
- 1 platform admin

### Complete Database State

```
tenants table:
┌─────────────────────┬──────────────────────────────────────┬──────────────────┬──────────┐
│ id                  │ name                                 │ slug              │ status   │
├─────────────────────┼──────────────────────────────────────┼──────────────────┼──────────┤
│ uuid-acme           │ Acme Corporation                     │ acme-corp         │ active   │
│ uuid-beta-finance   │ Beta Inc - Finance Team              │ beta-finance      │ active   │
│ uuid-beta-it        │ Beta Inc - IT Team                   │ beta-it           │ active   │
│ uuid-pilot1         │ Pilot Customer 1                     │ pilot-customer-1  │ active   │
│ uuid-pilot2         │ Pilot Customer 2                     │ pilot-customer-2  │ active   │
└─────────────────────┴──────────────────────────────────────┴──────────────────┴──────────┘

users table:
┌─────────────────────┬──────────────────────┬──────────────────────┬──────────────────┐
│ id                  │ primary_email        │ name                 │ is_platform_admin│
├─────────────────────┼──────────────────────┼──────────────────────┼──────────────────┤
│ uuid-acme-admin     │ admin@acme.com       │ Acme Admin           │ false            │
│ uuid-beta-fin-admin │ finance@beta.com    │ Beta Finance Admin   │ false            │
│ uuid-beta-it-admin  │ it@beta.com         │ Beta IT Admin        │ false            │
│ uuid-shared-user    │ shared@beta.com     │ Shared User          │ false            │
│ uuid-pilot1-admin   │ admin@pilot1.com    │ Pilot 1 Admin        │ false            │
│ uuid-pilot2-admin   │ admin@pilot2.com    │ Pilot 2 Admin        │ false            │
│ uuid-platform-admin │ admin@audexaai.com   │ Platform Admin       │ true             │
└─────────────────────┴──────────────────────┴──────────────────────┴──────────────────┘

user_tenants table:
┌─────────────────────┬─────────────────────┬─────────────────────┬────────┬─────────────┐
│ id                  │ user_id             │ tenant_id            │ role   │ is_default  │
├─────────────────────┼─────────────────────┼─────────────────────┼────────┼─────────────┤
│ uuid-ut-1           │ uuid-acme-admin     │ uuid-acme           │ admin  │ true        │
│ uuid-ut-2           │ uuid-beta-fin-admin │ uuid-beta-finance    │ admin  │ true        │
│ uuid-ut-3           │ uuid-beta-it-admin  │ uuid-beta-it        │ admin  │ true        │
│ uuid-ut-4           │ uuid-shared-user    │ uuid-beta-finance    │ auditor│ true        │
│ uuid-ut-5           │ uuid-shared-user    │ uuid-beta-it         │ user   │ false       │
│ uuid-ut-6           │ uuid-pilot1-admin   │ uuid-pilot1          │ admin  │ true        │
│ uuid-ut-7           │ uuid-pilot2-admin   │ uuid-pilot2          │ admin  │ true        │
└─────────────────────┴─────────────────────┴─────────────────────┴────────┴─────────────┘
(Note: Platform admin has NO user_tenants records)

auth_identities table:
┌─────────────────────┬─────────────────────┬──────────┬──────────────────────┬──────────────────────┐
│ id                  │ user_id              │ provider │ provider_subject      │ email                 │
├─────────────────────┼─────────────────────┼──────────┼──────────────────────┼──────────────────────┤
│ uuid-auth-1         │ uuid-acme-admin     │ dev      │ admin@acme.com        │ admin@acme.com        │
│ uuid-auth-2         │ uuid-beta-fin-admin │ dev      │ finance@beta.com     │ finance@beta.com      │
│ uuid-auth-3         │ uuid-beta-it-admin  │ dev      │ it@beta.com          │ it@beta.com           │
│ uuid-auth-4         │ uuid-shared-user    │ dev      │ shared@beta.com      │ shared@beta.com       │
│ uuid-auth-5         │ uuid-pilot1-admin   │ dev      │ admin@pilot1.com     │ admin@pilot1.com      │
│ uuid-auth-6         │ uuid-pilot2-admin   │ dev      │ admin@pilot2.com     │ admin@pilot2.com      │
│ uuid-auth-7         │ uuid-platform-admin │ dev      │ admin@audexaai.com   │ admin@audexaai.com    │
└─────────────────────┴─────────────────────┴──────────┴──────────────────────┴──────────────────────┘
```

### Access Patterns

**Acme Admin logs in:**
- JWT: `tenant_id = uuid-acme`
- Can see: Only data where `tenant_id = uuid-acme`
- Cannot see: Beta Inc data, Pilot data

**Beta Finance Admin logs in:**
- JWT: `tenant_id = uuid-beta-finance`
- Can see: Only data where `tenant_id = uuid-beta-finance`
- Cannot see: Beta IT data, Acme data, Pilot data

**Shared User logs in (chooses Finance tenant):**
- JWT: `tenant_id = uuid-beta-finance`
- Can see: Only data where `tenant_id = uuid-beta-finance`
- Role: "auditor" in Finance tenant

**Shared User logs in (chooses IT tenant):**
- JWT: `tenant_id = uuid-beta-it`
- Can see: Only data where `tenant_id = uuid-beta-it`
- Role: "user" in IT tenant

**Pilot 1 Admin logs in:**
- JWT: `tenant_id = uuid-pilot1`
- Can see: Only data where `tenant_id = uuid-pilot1`
- Cannot see: Pilot 2 data, any other tenant data

**Platform Admin logs in:**
- JWT: `tenant_id = null`, `is_platform_admin = true`
- Can see: All data from all tenants (special handling)
- Can manage: All tenants, all users

---

## ✅ Summary

1. **Company Signup**: Create `Tenant`, `User`, `UserTenant`, and `AuthIdentity` records
2. **Multiple Teams**: Create separate `Tenant` records for each team; users can belong to multiple via `UserTenant`
3. **Pilot Customers**: Each gets isolated `Tenant`; `get_current_user()` ensures data isolation via tenant filtering
4. **Data Isolation**: Every query filters by `tenant_id`; `get_current_user()` verifies user belongs to tenant via `UserTenant` table

The key is that **every data query must filter by `tenant_id`**, and the authentication system ensures users can only access their tenant's data.
