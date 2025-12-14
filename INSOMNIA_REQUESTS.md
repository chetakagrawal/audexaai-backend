# Insomnia Requests for Admin Signup Management

## Step 1: Get Platform Admin JWT Token

**POST** `http://localhost:8000/api/v1/auth/dev-login`

**Headers:**
```
Content-Type: application/json
```

**Body (JSON):**
```json
{
  "email": "admin@audexaai.com",
  "tenant_slug": "any-slug",
  "name": "Platform Admin",
  "role": "admin"
}
```

**Response:** Copy the `access_token` from the response.

---

## Step 2: Get Signup ID (if needed)

**GET** `http://localhost:8000/api/v1/admin/signups?status=pending_review`

**Headers:**
```
Authorization: Bearer YOUR_ACCESS_TOKEN_HERE
Content-Type: application/json
```

**Response:** List of signups with their IDs.

**Current Signup ID:** `fdb9ac04-d593-41e2-9d6e-2ce43af8a2a6`

---

## Step 3: Approve Signup

**POST** `http://localhost:8000/api/v1/admin/signups/fdb9ac04-d593-41e2-9d6e-2ce43af8a2a6/approve`

**Headers:**
```
Authorization: Bearer YOUR_ACCESS_TOKEN_HERE
Content-Type: application/json
```

**Body:** (empty - no body required)

**Expected Response (200 OK):**
```json
{
  "id": "fdb9ac04-d593-41e2-9d6e-2ce43af8a2a6",
  "email": "chetak90@gmail.com",
  "full_name": "...",
  "company_name": "...",
  "company_domain": "...",
  "requested_auth_mode": "direct",
  "status": "approved",
  "created_at": "...",
  "updated_at": "...",
  "approved_at": "..."
}
```

---

## Step 4: Reject Signup (Alternative)

**POST** `http://localhost:8000/api/v1/admin/signups/fdb9ac04-d593-41e2-9d6e-2ce43af8a2a6/reject`

**Headers:**
```
Authorization: Bearer YOUR_ACCESS_TOKEN_HERE
Content-Type: application/json
```

**Body (JSON - reason is optional):**
```json
{
  "reason": "Does not meet pilot program requirements"
}
```

Or with no reason:
```json
{}
```

**Expected Response (200 OK):**
```json
{
  "id": "fdb9ac04-d593-41e2-9d6e-2ce43af8a2a6",
  "email": "chetak90@gmail.com",
  "full_name": "...",
  "company_name": "...",
  "company_domain": "...",
  "requested_auth_mode": "direct",
  "status": "rejected",
  "created_at": "...",
  "updated_at": "...",
  "metadata": {
    "rejection_reason": "Does not meet pilot program requirements"
  }
}
```

---

## Step 5: List All Signups (Optional)

**GET** `http://localhost:8000/api/v1/admin/signups`

**Query Parameters (optional):**
- `status`: Filter by status (e.g., `pending_review`, `approved`, `rejected`)
- `limit`: Number of results (default: 50)
- `offset`: Pagination offset (default: 0)

**Example:**
```
GET http://localhost:8000/api/v1/admin/signups?status=pending_review&limit=10
```

**Headers:**
```
Authorization: Bearer YOUR_ACCESS_TOKEN_HERE
Content-Type: application/json
```

---

## Notes

- Replace `YOUR_ACCESS_TOKEN_HERE` with the actual token from Step 1
- Replace `fdb9ac04-d593-41e2-9d6e-2ce43af8a2a6` with the actual signup ID you want to approve/reject
- Platform admin email: `admin@audexaai.com`
- All admin endpoints require platform admin authentication
- Cannot approve/reject a signup that's already rejected (will return 409 Conflict)
