# Multi-Tenant Architecture (With Examples)

This app uses a **pooled multi-tenant architecture**.

One app. One database. Many companies.

---

## Core Idea

Every request answers:
1. Who is the user?
2. Which tenant are they acting in?
3. What data is allowed?

---

## Example: Consultant with Multiple Clients

Alex is an auditor.

- Alex works with Acme Corp
- Alex works with Globex Inc

Alex logs in once, then **selects a membership**:
- "I am working on Acme now"

The client sends:
```
X-Membership-Id: <membership_id>
```

The server:
- Resolves tenant_id from membership
- Filters all queries by tenant_id

---

## Why tenant_id Exists Everywhere

Two tenants can both have:
- Project named "FY25 SOX Audit"
- Application named "SAP"

Without tenant_id:
- Data leaks are inevitable

With tenant_id:
- Queries are always scoped safely

---

## Why We Use UserTenant for Ownership

Bad:
- Project.owner_user_id = user_id

Problem:
- User may belong to multiple tenants

Correct:
- Project.owner_membership_id = user_tenant_id

Now the database proves:
- The owner belongs to the tenant

---

## Security Rule (Non-Negotiable)

- The client NEVER sends tenant_id
- Tenant context is always derived from membership
- Membership is validated on every request

---

## Why This Scales

This model supports:
- Consultants working across clients
- Future enterprise SSO
- Strong isolation without separate databases

Later, high-compliance customers can be moved to
schema-per-tenant or DB-per-tenant if needed.
