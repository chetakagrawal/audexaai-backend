# SSO Setup Guide

This guide provides step-by-step instructions for configuring Single Sign-On (SSO) with Audexa AI. The platform supports both SAML 2.0 and OIDC (OpenID Connect) providers.

## Overview

After your signup is approved and promoted, you'll receive an email with a setup link. Use this link to access the onboarding page where you can configure SSO for your organization.

### Supported Providers

- **SAML 2.0**: Okta, Azure AD (SAML), Google Workspace (SAML), OneLogin, Auth0 (SAML), and other SAML 2.0 compliant providers
- **OIDC**: Azure AD (OIDC), Google Workspace (OIDC), Auth0 (OIDC), Okta (OIDC), and other OIDC compliant providers

## Prerequisites

1. Admin access to your SSO provider
2. Setup token link from your onboarding email (valid for 7 days)
3. Knowledge of your SSO provider's configuration settings

## SSO Configuration Flow

1. **Receive Setup Email**: After promotion, you'll receive an email with a setup link
2. **Access Onboarding Page**: Click the link to access `/onboarding?token={your-token}`
3. **Select Provider Type**: Choose SAML 2.0 or OIDC
4. **Configure SSO**: Enter your SSO provider configuration details
5. **Test Connection**: Verify the configuration works
6. **Complete Setup**: Finalize SSO configuration

## SAML 2.0 Configuration

### Required Information

For SAML configuration, you can use either:
- **Metadata URL** (recommended): Direct link to your SAML metadata XML
- **Manual Configuration**: Entity ID, SSO URL, and x509 Certificate

### Configuration Steps

#### Option 1: Using Metadata URL (Recommended)

1. **Obtain Metadata URL from your SSO provider**
   - This is typically a URL ending in `/metadata` or `/FederationMetadata/2007-06/FederationMetadata.xml`
   - Example: `https://yourcompany.okta.com/app/abc123/sso/saml/metadata`

2. **Enter Metadata URL in onboarding form**
   - Paste the metadata URL in the "Metadata URL" field
   - The system will automatically extract Entity ID, SSO URL, and certificate

#### Option 2: Manual Configuration

If metadata URL is not available, provide:

1. **Entity ID (Service Provider Entity ID)**
   - Also known as Audience URI or SP Entity ID
   - Example: `https://app.audexaai.com/auth/saml/metadata`
   - This identifies your application to the identity provider

2. **SSO URL (Single Sign-On URL)**
   - The URL where users are redirected for authentication
   - Example: `https://yourcompany.okta.com/app/abc123/sso/saml`
   - Also called "SSO Endpoint URL" or "Sign-in URL"

3. **x509 Certificate**
   - The public certificate used to verify SAML assertions
   - Copy the full certificate including `-----BEGIN CERTIFICATE-----` and `-----END CERTIFICATE-----`
   - Usually found in your SSO provider's SAML configuration

### Provider-Specific Instructions

#### Okta (SAML)

1. Log in to Okta Admin Console
2. Navigate to **Applications** → **Applications**
3. Click **Create App Integration**
4. Select **SAML 2.0** and click **Next**
5. Configure General Settings:
   - App name: `Audexa AI`
   - App logo: (optional)
6. Configure SAML:
   - **Single sign-on URL**: `https://app.audexaai.com/auth/saml/acs`
   - **Audience URI (SP Entity ID)**: `https://app.audexaai.com/auth/saml/metadata`
   - **Default RelayState**: (leave blank)
   - **Name ID format**: `EmailAddress`
   - **Application username**: `Email`
   - **Attribute statements** (optional):
     - `email` → `${user.email}`
     - `firstName` → `${user.firstName}`
     - `lastName` → `${user.lastName}`
7. Click **Next** → **Finish**
8. Copy the **Metadata URL** from the "SAML 2.0" section (or use manual configuration)
9. Assign users/groups to the application
10. Use the Metadata URL in Audexa AI onboarding form

#### Azure AD (SAML)

1. Log in to Azure Portal
2. Navigate to **Azure Active Directory** → **Enterprise Applications**
3. Click **New application** → **Create your own application**
4. Enter name: `Audexa AI` → Select **Integrate any other application you don't find in the gallery**
5. Click **Create**
6. In the application overview, click **Set up single sign-on**
7. Select **SAML**
8. Configure Basic SAML Configuration:
   - **Identifier (Entity ID)**: `https://app.audexaai.com/auth/saml/metadata`
   - **Reply URL (Assertion Consumer Service URL)**: `https://app.audexaai.com/auth/saml/acs`
   - **Sign on URL**: `https://app.audexaai.com/auth/saml/acs`
9. In **Attributes & Claims**:
   - Ensure `http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress` is mapped to `user.mail`
10. In **SAML Signing Certificate**:
    - Download Certificate (Base64) - this is your x509 certificate
11. Copy the **App Federation Metadata Url** from "Set up [Application Name]" section
12. Use the Metadata URL in Audexa AI onboarding form

#### Google Workspace (SAML)

1. Log in to Google Admin Console
2. Navigate to **Apps** → **Web and mobile apps**
3. Click **Add app** → **Add custom SAML app**
4. Enter app name: `Audexa AI`
5. Configure Service Provider Details:
   - **ACS URL**: `https://app.audexaai.com/auth/saml/acs`
   - **Entity ID**: `https://app.audexaai.com/auth/saml/metadata`
6. Configure User Attributes:
   - Map `Primary email` → `http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress`
   - Map `First name` → `http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname`
   - Map `Last name` → `http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname`
7. Download the **Certificate** (this is your x509 certificate)
8. Copy the **SSO URL** and **Entity ID**
9. Use either the SSO URL + Entity ID + Certificate, or download the Metadata XML and host it
10. If using metadata URL, you'll need to upload the XML to a publicly accessible URL

## OIDC Configuration

### Required Information

For OIDC configuration, you need:
- **Client ID**: The application/client identifier
- **Client Secret**: The application/client secret
- **Discovery URL**: The OpenID Connect discovery document URL

### Configuration Steps

1. **Create OIDC Application in your SSO Provider**
   - Register a new application/client
   - Set redirect URI: `https://app.audexaai.com/auth/oidc/callback`
   - Copy Client ID and Client Secret

2. **Get Discovery URL**
   - This is typically: `https://your-provider.com/.well-known/openid-configuration`
   - Example (Okta): `https://yourcompany.okta.com/.well-known/openid-configuration`
   - Example (Azure AD): `https://login.microsoftonline.com/{tenant-id}/.well-known/openid-configuration`

3. **Enter Configuration in Audexa AI**
   - Client ID: Your application's client ID
   - Client Secret: Your application's client secret
   - Discovery URL: The OIDC discovery document URL

### Provider-Specific Instructions

#### Okta (OIDC)

1. Log in to Okta Admin Console
2. Navigate to **Applications** → **Applications**
3. Click **Create App Integration**
4. Select **OIDC - OpenID Connect** → **Web Application** → **Next**
5. Configure Application:
   - App name: `Audexa AI`
   - Sign-in redirect URIs: `https://app.audexaai.com/auth/oidc/callback`
   - Sign-out redirect URIs: (optional)
   - Controlled access: Assign to users/groups
6. Click **Save**
7. Copy:
   - **Client ID** from the application overview
   - **Client Secret** (click "Client Secret" to reveal)
   - **Discovery URL**: `https://yourcompany.okta.com/.well-known/openid-configuration`
8. Use these values in Audexa AI onboarding form

#### Azure AD (OIDC)

1. Log in to Azure Portal
2. Navigate to **Azure Active Directory** → **App registrations**
3. Click **New registration**
4. Configure:
   - Name: `Audexa AI`
   - Supported account types: Choose appropriate (Single tenant, Multi-tenant, etc.)
   - Redirect URI: `https://app.audexaai.com/auth/oidc/callback` (Platform: Web)
5. Click **Register**
6. Copy:
   - **Application (client) ID** (this is your Client ID)
7. Navigate to **Certificates & secrets**
8. Create a new client secret:
   - Description: `Audexa AI SSO`
   - Expires: Choose expiration (recommended: 24 months)
   - Click **Add**
   - **Copy the Value immediately** (this is your Client Secret - you won't be able to see it again)
9. Get Discovery URL:
   - Format: `https://login.microsoftonline.com/{your-tenant-id}/.well-known/openid-configuration`
   - Or use: `https://login.microsoftonline.com/common/.well-known/openid-configuration` (for multi-tenant)
10. Use these values in Audexa AI onboarding form

#### Google Workspace (OIDC)

1. Log in to Google Cloud Console
2. Navigate to **APIs & Services** → **Credentials**
3. Click **Create Credentials** → **OAuth client ID**
4. Configure:
   - Application type: `Web application`
   - Name: `Audexa AI`
   - Authorized redirect URIs: `https://app.audexaai.com/auth/oidc/callback`
5. Click **Create**
6. Copy:
   - **Client ID**
   - **Client Secret** (click to reveal)
   - **Discovery URL**: `https://accounts.google.com/.well-known/openid-configuration`
7. Use these values in Audexa AI onboarding form

## Testing Your Configuration

After entering your SSO configuration:

1. Click **Test Connection** button
   - This validates your configuration format
   - For SAML: Checks that required fields are present
   - For OIDC: Validates discovery URL and credentials

2. Review any error messages
   - Common issues are listed in the Troubleshooting section below

3. Once test succeeds, click **Save Configuration**

## Completing Setup

1. After successful configuration, click **Complete Setup**
   - This marks SSO as configured for your tenant
   - The setup token is invalidated (one-time use)
   - Users can now log in via SSO

2. You'll be redirected to the portal dashboard

3. **Important**: After SSO setup is complete:
   - Users must log in using SSO (not direct login)
   - The setup token cannot be reused
   - If you need to update SSO configuration later, contact support

## Troubleshooting

### Common Issues

#### SAML Configuration Issues

**Issue**: "Invalid certificate format"
- **Solution**: Ensure the certificate includes `-----BEGIN CERTIFICATE-----` and `-----END CERTIFICATE-----` lines
- Copy the entire certificate including header and footer

**Issue**: "Metadata URL not accessible"
- **Solution**: 
  - Verify the metadata URL is publicly accessible (try opening in a browser)
  - Check if your SSO provider requires authentication to access metadata
  - Use manual configuration instead if metadata URL is not available

**Issue**: "Entity ID mismatch"
- **Solution**: 
  - Ensure Entity ID in Audexa AI matches the Audience URI/SP Entity ID in your SSO provider
  - For Audexa AI: Use `https://app.audexaai.com/auth/saml/metadata`
  - Verify this matches exactly in your SSO provider configuration

**Issue**: "SSO URL not working"
- **Solution**:
  - Verify the SSO URL is correct (copy directly from SSO provider)
  - Ensure the URL uses HTTPS
  - Check if your SSO provider requires specific query parameters

#### OIDC Configuration Issues

**Issue**: "Invalid discovery URL"
- **Solution**:
  - Verify the discovery URL is accessible (try opening in a browser)
  - Ensure the URL ends with `/.well-known/openid-configuration`
  - For Azure AD, ensure you're using the correct tenant ID or `common`

**Issue**: "Client ID or Client Secret invalid"
- **Solution**:
  - Verify Client ID and Client Secret are copied correctly (no extra spaces)
  - Ensure the client secret hasn't expired (Azure AD secrets expire)
  - For Azure AD, check if you copied the "Value" not the "Secret ID"

**Issue**: "Redirect URI mismatch"
- **Solution**:
  - Ensure redirect URI in SSO provider matches exactly: `https://app.audexaai.com/auth/oidc/callback`
  - Check for trailing slashes or case sensitivity issues
  - Verify the redirect URI is registered in your SSO provider

#### General Issues

**Issue**: "Setup token expired or invalid"
- **Solution**:
  - Setup tokens expire after 7 days
  - Request a new setup token from your administrator
  - Ensure you're using the token from the most recent email

**Issue**: "Configuration saved but login not working"
- **Solution**:
  - Ensure you clicked "Complete Setup" after configuring SSO
  - Verify SSO is marked as "configured" in the system
  - Check that users are assigned to the application in your SSO provider
  - Verify user email addresses match between SSO provider and Audexa AI

**Issue**: "Cannot access portal after SSO setup"
- **Solution**:
  - Ensure SSO setup is complete (sso_status = "configured")
  - Try logging in via SSO (not direct login)
  - Clear browser cookies and try again
  - Contact support if issue persists

## Security Best Practices

1. **Protect Setup Tokens**
   - Setup tokens are valid for 7 days - use them promptly
   - Don't share setup tokens - they're tied to your account
   - If compromised, contact support immediately

2. **Client Secrets**
   - Store client secrets securely
   - Rotate secrets periodically (especially for Azure AD which has expiration)
   - Never commit secrets to version control

3. **Certificate Management**
   - Keep certificates up to date
   - Monitor certificate expiration dates
   - Rotate certificates before expiration

4. **Access Control**
   - Only assign necessary users/groups to the SSO application
   - Review access regularly
   - Use principle of least privilege

## Configuration Examples

### SAML Configuration Example

```yaml
Provider Type: SAML 2.0
Metadata URL: https://yourcompany.okta.com/app/abc123/sso/saml/metadata

# OR Manual:
Entity ID: https://app.audexaai.com/auth/saml/metadata
SSO URL: https://yourcompany.okta.com/app/abc123/sso/saml
Certificate: |
  -----BEGIN CERTIFICATE-----
  MIIE... (certificate content)
  -----END CERTIFICATE-----
```

### OIDC Configuration Example

```yaml
Provider Type: OIDC
Client ID: 0oa1abc2def3ghi4jkl5
Client Secret: xyz789_secret_key_abc123
Discovery URL: https://yourcompany.okta.com/.well-known/openid-configuration
Redirect URI: https://app.audexaai.com/auth/oidc/callback (auto-generated, shown to user)
```

## Next Steps

After completing SSO setup:

1. **Test Login**: Verify you can log in using SSO
2. **User Onboarding**: Instruct your users to log in via SSO
3. **Monitor**: Keep an eye on login activity and any issues
4. **Support**: Contact support if you need to update SSO configuration

## Support

If you encounter issues not covered in this guide:

1. Check the troubleshooting section above
2. Review your SSO provider's documentation
3. Verify all configuration values are correct
4. Contact Audexa AI support with:
   - Your tenant ID
   - SSO provider type (SAML/OIDC)
   - Error messages (if any)
   - Screenshots of configuration (redact sensitive information)

## Additional Resources

- [SAML 2.0 Specification](https://docs.oasis-open.org/security/saml/v2.0/)
- [OpenID Connect Specification](https://openid.net/connect/)
- [Okta SAML Documentation](https://developer.okta.com/docs/guides/saml-application-setup/)
- [Azure AD SAML Documentation](https://docs.microsoft.com/en-us/azure/active-directory/manage-apps/configure-single-sign-on-saml-based)
- [Google Workspace SAML Documentation](https://support.google.com/a/answer/6087519)
