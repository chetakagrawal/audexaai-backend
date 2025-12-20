# Active Membership Contract

This document defines the contract for multi-tenant authentication and authorization using active membership selection.

## Overview

Users can belong to multiple tenants. After authentication, the client must select an **active membership** (UserTenant.id) to indicate which tenant context they are operating in. All tenant-scoped API requests derive `tenant_id` from that membership on the server.

**Key Principle:** The client **never** sends `tenant_id` for authorization. Tenant context is always derived from the active membership.

---

## Login Response

After successful authentication, the login endpoint returns:

```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "user_id": "uuid",
  "tenant_id": "uuid",
  "role": "admin",
  "is_platform_admin": false,
  "memberships": [
    {
      "membership_id": "uuid",  // UserTenant.id
      "tenant_id": "uuid",
      "tenant_name": "Acme Corp",
      "role": "admin"
    },
    {
      "membership_id": "uuid",
      "tenant_id": "uuid",
      "tenant_name": "Globex Inc",
      "role": "viewer"
    }
  ]
}
```

The `memberships` array contains all memberships for the authenticated user. The client should:
1. Display these memberships to the user
2. Allow the user to select which tenant they want to work in
3. Store the selected `membership_id` for subsequent API calls

---

## Required Header for Tenant-Scoped Endpoints

All tenant-scoped endpoints require the `X-Membership-Id` header:

```
X-Membership-Id: <uuid>
```

Where `<uuid>` is the `membership_id` (UserTenant.id) from the login response.

### Example Request

```http
GET /api/v1/projects HTTP/1.1
Authorization: Bearer <token>
X-Membership-Id: 123e4567-e89b-12d3-a456-426614174000
```

---

## Error Responses

### Missing Header (403 Forbidden)

If `X-Membership-Id` is missing:

```json
{
  "detail": "X-Membership-Id header is required for tenant-scoped operations"
}
```

### Invalid Membership (403 Forbidden)

If the membership doesn't belong to the authenticated user:

```json
{
  "detail": "Membership does not belong to user"
}
```

### Invalid Format (400 Bad Request)

If `X-Membership-Id` is not a valid UUID:

```json
{
  "detail": "Invalid X-Membership-Id format (must be UUID)"
}
```

---

## Switching Tenants

To switch tenants, the client simply changes the `X-Membership-Id` header value:

1. **Tenant A Context:**
   ```http
   X-Membership-Id: <membership_id_for_tenant_a>
   ```
   - All queries return data for Tenant A
   - Created resources belong to Tenant A

2. **Tenant B Context:**
   ```http
   X-Membership-Id: <membership_id_for_tenant_b>
   ```
   - All queries return data for Tenant B
   - Created resources belong to Tenant B

**Important:** The same JWT token is used for both contexts. Only the `X-Membership-Id` header changes.

---

## Tenant-Scoped Endpoints

The following endpoints require `X-Membership-Id`:

- `GET /api/v1/projects` - List projects
- `POST /api/v1/projects` - Create project
- `GET /api/v1/projects/{project_id}` - Get project
- `GET /api/v1/controls` - List controls
- `POST /api/v1/controls` - Create control
- `GET /api/v1/controls/{control_id}` - Get control
- `PUT /api/v1/controls/{control_id}` - Update control
- `DELETE /api/v1/controls/{control_id}` - Delete control (soft delete)
- `GET /api/v1/projects/{project_id}/controls` - List project controls
- `POST /api/v1/projects/{project_id}/controls` - Attach control to project
- `GET /api/v1/applications` - List applications
- `POST /api/v1/applications` - Create application
- `GET /api/v1/applications/{application_id}` - Get application
- `PUT /api/v1/applications/{application_id}` - Update application
- `DELETE /api/v1/applications/{application_id}` - Delete application (soft delete)

**Note:** All updates and deletes on `controls` and `applications` are automatically tracked in version history. Version history is accessible via service layer (`controls_versions_service` and `applications_versions_service`). API endpoints for querying version history may be added in the future.

---

## Security Rules

1. **Never accept `tenant_id` from client input** - All `tenant_id` values are derived from the membership context
2. **Validate membership ownership** - The server verifies that the `X-Membership-Id` belongs to the authenticated user
3. **Platform admins** - Platform admins may bypass tenant scoping (implementation-specific)

---

## Client Implementation Example

```typescript
// After login
const loginResponse = await login(email, password);
const memberships = loginResponse.memberships;

// Store token and selected membership
localStorage.setItem('token', loginResponse.access_token);
localStorage.setItem('activeMembershipId', memberships[0].membership_id);

// Make API calls with header
async function listProjects() {
  const token = localStorage.getItem('token');
  const membershipId = localStorage.getItem('activeMembershipId');
  
  const response = await fetch('/api/v1/projects', {
    headers: {
      'Authorization': `Bearer ${token}`,
      'X-Membership-Id': membershipId
    }
  });
  
  return response.json();
}

// Switch tenant
function switchTenant(membershipId: string) {
  localStorage.setItem('activeMembershipId', membershipId);
  // Subsequent API calls will use the new membership
}
```

---

## Platform Admins

Platform admins (`is_platform_admin: true`) may have special behavior:
- They may not require `X-Membership-Id` for certain operations
- They may be able to access data across tenants
- Implementation details are endpoint-specific

Check individual endpoint documentation for platform admin behavior.

