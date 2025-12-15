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
A SOX control owned by the tenant.
Example:
- User access provisioning control

### ProjectControl
Overrides control behavior for a specific audit.
Example:
- Control is "key" this year but not last year
