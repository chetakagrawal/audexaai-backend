# SSO Onboarding Implementation TODO

## Overview
Implement onboarding flow for users who sign up requesting SSO. Users must complete SSO configuration before accessing the portal. Once configured, they can only login via SSO.

## Backend Tasks

### Phase 1: Setup Token / Magic Link System

- [ ] **Create setup token model/schema**
  - Add `setup_tokens` table or use existing mechanism
  - Fields: `token` (UUID), `user_id` (FK), `signup_id` (FK), `expires_at`, `used_at`, `created_at`
  - Token expires after 7 days (configurable)
  - One-time use only

- [ ] **Generate setup token after promotion**
  - When signup is promoted with `requested_auth_mode: 'sso'`
  - Generate unique token and store it
  - Create token record linked to user/signup

- [ ] **Create setup token validation endpoint**
  - `GET /api/v1/setup/{token}` or `POST /api/v1/setup/validate`
  - Validates token, checks expiration
  - Returns user info and tenant info if valid
  - Marks token as used after validation

- [ ] **Create setup token authentication dependency**
  - Similar to `get_current_user` but for setup tokens
  - `get_setup_token_user(token: str)` dependency
  - Returns user and tenant context for onboarding page

### Phase 2: SSO Configuration Endpoints

- [ ] **Create SSO configuration schema/model**
  - Store SSO provider details per tenant
  - Fields: `tenant_id`, `provider_type` (saml/oidc), `metadata_url`, `entity_id`, `sso_url`, `x509_certificate`, `oidc_client_id`, `oidc_client_secret`, `oidc_discovery_url`, `status` (configured/not_configured), `created_at`, `updated_at`

- [ ] **Create SSO configuration endpoint**
  - `POST /api/v1/setup/sso/configure` (requires setup token auth)
  - Accepts SSO provider configuration (SAML or OIDC)
  - Validates configuration format
  - Stores configuration for tenant
  - Tests connection to SSO provider

- [ ] **Create SSO test connection endpoint**
  - `POST /api/v1/setup/sso/test` (requires setup token auth)
  - Validates SSO configuration
  - Tests connection to SSO provider
  - Returns success/failure

- [ ] **Update signup/user on SSO completion**
  - When SSO successfully configured:
    - Update `signup.signup_metadata["sso_status"]` to `"configured"`
    - Update AuthIdentity `email_verified` to `true` (if applicable)
    - Invalidate/expire setup token
    - Create audit log entry

- [ ] **Update promotion endpoint**
  - After creating AuthIdentity for SSO user
  - Generate and store setup token
  - Return setup token in promotion response (or email it separately)

### Phase 3: Middleware / Access Control

- [ ] **Create middleware to check SSO status**
  - For SSO users with `sso_status: "not_configured"`
  - Check if they're using setup token (allow)
  - Otherwise redirect to onboarding
  - Only allow access to onboarding page and setup endpoints

- [ ] **Update portal route protection**
  - Check SSO status before allowing portal access
  - If SSO requested but not configured → redirect to onboarding
  - If using setup token → allow onboarding page only

- [ ] **Update existing dev-login check**
  - Already implemented: blocks dev-login for SSO users
  - Verify it works with setup token exception (if needed)

### Phase 4: Email / Notification

- [ ] **Create setup email template**
  - Welcome email after promotion
  - Includes setup token link: `https://app.domain.com/onboarding?token={token}`
  - Instructions for SSO setup
  - Expiration notice

- [ ] **Send setup email after promotion**
  - Integrate email service (if exists) or stub for now
  - Send email with setup link to user's email

## Frontend Tasks

### Phase 1: Onboarding Page

- [ ] **Create onboarding page route**
  - `src/app/onboarding/page.tsx`
  - Requires setup token in URL query param or cookie
  - If no token → show error / redirect to login

- [ ] **Create onboarding layout/design**
  - Welcome message
  - Progress indicator (step 1: SSO setup, step 2: complete)
  - Clean, focused UI for configuration

- [ ] **Add setup token validation on page load**
  - Call `GET /api/v1/setup/validate?token={token}`
  - Store token for subsequent API calls
  - Handle invalid/expired token gracefully
  - Fetch user/tenant info after validation

### Phase 2: SSO Configuration Form

- [ ] **Create SSO provider selection**
  - Radio buttons or dropdown: SAML 2.0, OIDC, etc.
  - Based on selection, show relevant fields

- [ ] **Create SAML configuration form**
  - Metadata URL input (primary method)
  - OR manual fields: Entity ID, SSO URL, x509 Certificate
  - Validation for required fields

- [ ] **Create OIDC configuration form**
  - Client ID input
  - Client Secret input
  - Discovery URL input
  - Redirect URI (auto-generated, show to user)

- [ ] **Add configuration validation**
  - Client-side validation for URL formats
  - Certificate format validation (if manual SAML)

- [ ] **Add test connection button**
  - Calls `POST /api/v1/setup/sso/test`
  - Shows loading state
  - Displays success/error message

- [ ] **Add save/submit configuration**
  - Calls `POST /api/v1/setup/sso/configure`
  - Shows loading state
  - On success: redirect to portal dashboard
  - On error: display error message

### Phase 3: Integration

- [ ] **Update login page**
  - SSO login button (once SSO is configured)
  - Detect if SSO is available for user's email domain
  - Redirect to SSO provider

- [ ] **Update portal access checks**
  - Check SSO status on portal routes
  - Redirect to onboarding if `sso_status: "not_configured"`

- [ ] **Add API client functions**
  - `setupApi.validateToken(token: string)`
  - `setupApi.configureSSO(config: SSOConfig)`
  - `setupApi.testSSO(config: SSOConfig)`

## Testing Tasks

- [ ] **Backend unit tests**
  - Setup token generation and validation
  - SSO configuration storage and retrieval
  - Token expiration logic
  - SSO status updates

- [ ] **Backend integration tests**
  - Complete flow: promotion → token generation → SSO setup → access
  - Test token expiration
  - Test SSO configuration validation
  - Test middleware redirects

- [ ] **Frontend tests**
  - Onboarding page renders correctly
  - SSO form validation
  - API integration

- [ ] **End-to-end testing**
  - Signup with SSO → approve → promote → receive email → setup SSO → login via SSO

## Documentation

- [ ] **Update API documentation**
  - Document setup token endpoints
  - Document SSO configuration endpoints
  - Include example requests/responses

- [ ] **Create SSO setup guide**
  - Instructions for different SSO providers (Okta, Azure AD, Google Workspace)
  - Screenshots or step-by-step guide
  - Common issues and troubleshooting

- [ ] **Update user flow documentation**
  - Document complete signup → promotion → onboarding → SSO login flow

## Open Questions / Decisions Needed

1. **Token Storage**: Use dedicated `setup_tokens` table or store in existing `signups` table metadata?
2. **Email Service**: Use existing email service or create stub for now?
3. **SSO Provider Support**: Start with SAML 2.0 only, or support OIDC from day 1?
4. **Token Expiration**: 7 days default? Make it configurable?
5. **Onboarding Page URL**: `/onboarding?token=xxx` or `/setup/onboarding?token=xxx`?
6. **SSO Configuration Storage**: New `tenant_sso_config` table or store in `tenants` table JSONB field?
7. **Test Connection**: Should we actually test the SSO connection, or just validate the configuration format?

## Notes

- Dev-login blocking for SSO users is already implemented ✅
- Backend promotion endpoint already creates oidc AuthIdentity for SSO users ✅
- Need to ensure setup token is secure and properly validated
- Consider rate limiting on setup token validation endpoint
- SSO login flow itself (OAuth/SAML redirect) is a separate phase after onboarding is complete
