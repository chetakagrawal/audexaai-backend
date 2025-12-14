# Signup → Promote Workflow

## Overview

Pilot signups flow through a review and promotion process to create active tenant accounts.

## Status Flow

```
pending_review → [pending_verification] → verified → approved → promoted
                                    ↓
                                 rejected
```

### Status Definitions

- **`pending_review``** - Initial signup submitted, awaiting review
- **`pending_verification`** (optional) - Email verification pending
- **`verified`** (optional) - Email verified, awaiting approval
- **`approved`** - Approved for promotion, ready to create account
- **`promoted`** - Account created, signup is complete
- **`rejected`** - Signup declined, no account created

## Signup Data Model

The `pilot_signups` table stores:

- `id` (UUID, PK)
- `email` (string, required, unique)
- `company_name` (string, nullable - "Individual" if `is_individual=true`)
- `is_individual` (boolean, default false)
- `status` (enum: pending_review, pending_verification, verified, approved, promoted, rejected)
- `submitted_at` (datetime)
- `reviewed_at` (datetime, nullable)
- `reviewed_by` (UUID, FK to users.id, nullable - platform admin)
- `promoted_at` (datetime, nullable)
- `notes` (text, nullable - internal review notes)

## Promotion Process

When a signup is **promoted**, the system creates:

1. **Tenant** (`tenants` table)
   - `name`: From `company_name` or "Individual" if `is_individual=true`
   - `slug`: Generated from name (lowercase, hyphenated)
   - `status`: "active"

2. **User** (`users` table)
   - `primary_email`: From signup email
   - `name`: Extracted from email or default
   - `is_platform_admin`: false
   - `is_active`: true

3. **UserTenant** (`user_tenants` table)
   - `user_id`: FK to created user
   - `tenant_id`: FK to created tenant
   - `role`: "admin" (first user is admin)
   - `is_default`: true

4. **AuthIdentity** (`auth_identities` table)
   - `user_id`: FK to created user
   - `provider`: "dev" (or "email" for email-based auth)
   - `provider_subject`: Email address
   - `email`: Email address
   - `email_verified`: true (after promotion)

## Security Rules

1. **Signups are unauthenticated** - Anyone can submit a signup form
2. **Promotion requires platform admin** - Only users with `is_platform_admin=true` can promote signups
3. **Email uniqueness** - `users.primary_email` must be unique; handle duplicates during promotion
4. **Audit trail** - Track `reviewed_by` and `promoted_at` for accountability

## API Endpoints (Future)

- `POST /api/v1/pilot/signup` - Public endpoint, creates signup with `pending_review`
- `GET /api/v1/admin/signups` - Platform admin only, list signups
- `PATCH /api/v1/admin/signups/{id}/approve` - Platform admin only, set status to `approved`
- `POST /api/v1/admin/signups/{id}/promote` - Platform admin only, creates tenant/user and sets status to `promoted`
- `PATCH /api/v1/admin/signups/{id}/reject` - Platform admin only, set status to `rejected`

