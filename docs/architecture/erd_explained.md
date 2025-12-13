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

## Audit Domain

### Project
An engagement within a tenant.
Example:
- "FY25 SOX Audit" for Acme Corp

### Application
An IT system in scope.
Example:
- SAP
- Workday

### Control (RACM)
A SOX control owned by the tenant.
Example:
- User access provisioning control

### ProjectControl
Overrides control behavior for a specific audit.
Example:
- Control is "key" this year but not last year

---

## Evidence & Testing

### PBC Request
A request sent to the client.
Example:
- "Provide user access listing for SAP"

### EvidenceFile
Uploaded proof.
Example:
- CSV export of SAP users

### EvidencePage
A page or image derived from evidence.

---

## AI Pipeline

### AI_RUN
One AI execution.
Examples:
- OCR extraction
- Evidence validation
- Control-level conclusion

### AI_L1–L4 Index Tables
Thin tables for fast querying of AI results by level.

---

## Findings
Issues raised during the audit.
Example:
- Terminated user still active in SAP
