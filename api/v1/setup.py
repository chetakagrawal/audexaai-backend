"""Setup token and SSO configuration endpoints."""

from datetime import datetime, timedelta, UTC
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db
from models.auth_identity import AuthIdentity
from models.setup_token import SetupToken
from models.signup import Signup, AuthMode
from models.tenant import Tenant
from models.tenant_sso_config import (
    TenantSSOConfig,
    SSOConfigRequest,
    SSOConfigResponse,
    SAMLConfig,
    OIDCConfig,
)
from models.user import User
from models.user_tenant import UserTenant

router = APIRouter()


class SetupTokenValidationResponse(BaseModel):
    """Response schema for setup token validation."""

    valid: bool
    user_id: UUID | None = None
    tenant_id: UUID | None = None
    signup_id: UUID | None = None
    user_name: str | None = None
    user_email: str | None = None
    tenant_name: str | None = None
    tenant_slug: str | None = None
    reason: str | None = None  # Reason if invalid (expired, used, etc.)


@router.get("/setup/validate", response_model=SetupTokenValidationResponse)
async def validate_setup_token(
    token: str = Query(..., description="Setup token to validate"),
    db: AsyncSession = Depends(get_db),
):
    """
    Validate a setup token for SSO onboarding.
    
    Returns user and tenant information if token is valid.
    Token must be unused and not expired.
    
    Args:
        token: Setup token from email link
        db: Database session
    
    Returns:
        SetupTokenValidationResponse: User and tenant info if valid, error reason if invalid
    """
    # Find token
    result = await db.execute(
        select(SetupToken).where(SetupToken.token == token)
    )
    setup_token = result.scalar_one_or_none()
    
    if not setup_token:
        return SetupTokenValidationResponse(
            valid=False,
            reason="Token not found"
        )
    
    # Check if token is valid (not used, not expired)
    if not setup_token.is_valid():
        if setup_token.used_at:
            reason = "Token has already been used"
        elif setup_token.expires_at <= datetime.now(UTC):
            reason = "Token has expired"
        else:
            reason = "Token is invalid"
        
        return SetupTokenValidationResponse(
            valid=False,
            reason=reason
        )
    
    # Get user info
    result = await db.execute(
        select(User).where(User.id == setup_token.user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        return SetupTokenValidationResponse(
            valid=False,
            reason="User not found"
        )
    
    # Get tenant info from user's default membership
    result = await db.execute(
        select(UserTenant, Tenant)
        .join(Tenant, UserTenant.tenant_id == Tenant.id)
        .where(
            UserTenant.user_id == user.id,
            UserTenant.is_default == True
        )
        .order_by(UserTenant.created_at.desc())
    )
    membership_result = result.first()
    
    if not membership_result:
        return SetupTokenValidationResponse(
            valid=False,
            reason="User has no tenant membership"
        )
    
    user_tenant, tenant = membership_result
    
    return SetupTokenValidationResponse(
        valid=True,
        user_id=user.id,
        tenant_id=tenant.id,
        signup_id=setup_token.signup_id,
        user_name=user.name,
        user_email=user.primary_email,
        tenant_name=tenant.name,
        tenant_slug=tenant.slug,
    )


def generate_setup_token() -> str:
    """Generate a secure random token string."""
    return str(uuid4())


async def create_setup_token(
    db: AsyncSession,
    user_id: UUID,
    signup_id: UUID,
    expires_in_days: int = 7,
) -> SetupToken:
    """
    Create a new setup token for SSO onboarding.
    
    Args:
        db: Database session
        user_id: User ID
        signup_id: Signup ID
        expires_in_days: Number of days until token expires (default 7)
    
    Returns:
        SetupToken: Created setup token
    """
    token_str = generate_setup_token()
    expires_at = datetime.now(UTC) + timedelta(days=expires_in_days)
    
    setup_token = SetupToken(
        id=uuid4(),
        token=token_str,
        user_id=user_id,
        signup_id=signup_id,
        expires_at=expires_at,
    )
    
    db.add(setup_token)
    await db.flush()
    
    return setup_token


def send_setup_email_stub(email: str, token: str) -> None:
    """
    Stub for sending setup email.
    
    TODO: Replace with real email service when admin email is configured.
    
    For now, just logs the token so it can be manually retrieved during development.
    """
    # In production, this would send an email with a link like:
    # https://app.audexaai.com/onboarding?token={token}
    
    print(f"\n{'='*60}")
    print(f"SETUP EMAIL STUB - SSO Onboarding")
    print(f"{'='*60}")
    print(f"To: {email}")
    print(f"Subject: Complete Your SSO Setup - Audexa AI")
    print(f"\nSetup Link: https://app.audexaai.com/onboarding?token={token}")
    print(f"Token: {token}")
    print(f"\nThis token expires in 7 days.")
    print(f"{'='*60}\n")


# Helper function to get user/tenant from setup token
async def get_setup_token_context(
    db: AsyncSession,
    token: str,
) -> tuple[SetupToken, User, Tenant] | None:
    """
    Get user and tenant context from setup token.
    
    Returns None if token is invalid.
    """
    result = await db.execute(
        select(SetupToken).where(SetupToken.token == token)
    )
    setup_token = result.scalar_one_or_none()
    
    if not setup_token or not setup_token.is_valid():
        return None
    
    # Get user
    result = await db.execute(
        select(User).where(User.id == setup_token.user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return None
    
    # Get tenant from default membership
    result = await db.execute(
        select(UserTenant, Tenant)
        .join(Tenant, UserTenant.tenant_id == Tenant.id)
        .where(
            UserTenant.user_id == user.id,
            UserTenant.is_default == True
        )
    )
    membership_result = result.first()
    if not membership_result:
        return None
    
    _, tenant = membership_result
    return (setup_token, user, tenant)


@router.post("/setup/sso/configure", response_model=SSOConfigResponse)
async def configure_sso(
    config: SSOConfigRequest,
    token: str = Query(..., description="Setup token for authentication"),
    db: AsyncSession = Depends(get_db),
):
    """
    Configure SSO for a tenant (requires valid setup token).
    
    Args:
        config: SSO configuration (SAML or OIDC)
        token: Setup token for authentication
        db: Database session
    
    Returns:
        SSOConfigResponse: Created/updated SSO configuration
    """
    # Validate setup token and get context
    context = await get_setup_token_context(db, token)
    if not context:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired setup token",
        )
    
    setup_token, user, tenant = context
    
    # Validate provider type
    if config.provider_type not in ["saml", "oidc"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="provider_type must be 'saml' or 'oidc'",
        )
    
    # Check if SSO config already exists
    result = await db.execute(
        select(TenantSSOConfig).where(TenantSSOConfig.tenant_id == tenant.id)
    )
    existing_config = result.scalar_one_or_none()
    
    if existing_config:
        # Update existing config
        existing_config.provider_type = config.provider_type
        existing_config.is_configured = False  # Will be set to True after test
        
        if config.provider_type == "saml" and config.saml_config:
            existing_config.metadata_url = config.saml_config.metadata_url
            existing_config.entity_id = config.saml_config.entity_id
            existing_config.sso_url = config.saml_config.sso_url
            existing_config.x509_certificate = config.saml_config.x509_certificate
        elif config.provider_type == "oidc" and config.oidc_config:
            existing_config.oidc_client_id = config.oidc_config.client_id
            existing_config.oidc_client_secret = config.oidc_config.client_secret
            existing_config.oidc_discovery_url = config.oidc_config.discovery_url
            existing_config.oidc_redirect_uri = config.oidc_config.redirect_uri or f"https://app.audexaai.com/auth/oidc/callback"
        
        existing_config.updated_at = datetime.now(UTC)
        sso_config = existing_config
    else:
        # Create new config
        sso_config = TenantSSOConfig(
            id=uuid4(),
            tenant_id=tenant.id,
            provider_type=config.provider_type,
            is_configured=False,  # Will be set to True after successful test
        )
        
        if config.provider_type == "saml" and config.saml_config:
            sso_config.metadata_url = config.saml_config.metadata_url
            sso_config.entity_id = config.saml_config.entity_id
            sso_config.sso_url = config.saml_config.sso_url
            sso_config.x509_certificate = config.saml_config.x509_certificate
        elif config.provider_type == "oidc" and config.oidc_config:
            sso_config.oidc_client_id = config.oidc_config.client_id
            sso_config.oidc_client_secret = config.oidc_config.client_secret
            sso_config.oidc_discovery_url = config.oidc_config.discovery_url
            sso_config.oidc_redirect_uri = config.oidc_config.redirect_uri or f"https://app.audexaai.com/auth/oidc/callback"
        
        db.add(sso_config)
    
    await db.commit()
    await db.refresh(sso_config)
    
    return SSOConfigResponse(
        id=sso_config.id,
        tenant_id=sso_config.tenant_id,
        provider_type=sso_config.provider_type,
        is_configured=sso_config.is_configured,
        created_at=sso_config.created_at,
        updated_at=sso_config.updated_at,
    )


@router.post("/setup/sso/test")
async def test_sso_connection(
    config: SSOConfigRequest,
    token: str = Query(..., description="Setup token for authentication"),
    db: AsyncSession = Depends(get_db),
):
    """
    Test SSO configuration connection (requires valid setup token).
    
    This is a stub - in production, this would actually validate the SSO configuration
    by connecting to the SSO provider and testing authentication.
    
    Args:
        config: SSO configuration to test
        token: Setup token for authentication
        db: Database session
    
    Returns:
        Dict with success status and message
    """
    # Validate setup token
    context = await get_setup_token_context(db, token)
    if not context:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired setup token",
        )
    
    # Basic validation (stub - real implementation would test actual connection)
    if config.provider_type == "saml" and config.saml_config:
        if not config.saml_config.metadata_url and not (config.saml_config.entity_id and config.saml_config.sso_url):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SAML configuration requires either metadata_url or (entity_id and sso_url)",
            )
    elif config.provider_type == "oidc" and config.oidc_config:
        if not config.oidc_config.client_id or not config.oidc_config.client_secret or not config.oidc_config.discovery_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OIDC configuration requires client_id, client_secret, and discovery_url",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid provider_type or missing {config.provider_type}_config",
        )
    
    # TODO: In production, actually test the SSO connection here
    # For now, just return success if configuration is valid
    
    # Get or create SSO config
    setup_token, user, tenant = context
    result = await db.execute(
        select(TenantSSOConfig).where(TenantSSOConfig.tenant_id == tenant.id)
    )
    sso_config = result.scalar_one_or_none()
    
    # If config doesn't exist yet, create it first (should have been created by configure endpoint)
    if not sso_config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SSO configuration not found. Please configure SSO first.",
        )
    
    return {
        "success": True,
        "message": "SSO configuration is valid. Connection test is stubbed - will validate in production.",
        "config_id": str(sso_config.id),
    }


@router.post("/setup/sso/complete")
async def complete_sso_setup(
    token: str = Query(..., description="Setup token for authentication"),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark SSO setup as complete and invalidate setup token.
    
    After SSO is successfully configured and tested, call this endpoint to:
    - Mark SSO as configured
    - Update signup metadata
    - Invalidate setup token (mark as used)
    - User must now use SSO login
    
    Args:
        token: Setup token for authentication
        db: Database session
    
    Returns:
        Dict with success message
    """
    # Validate setup token
    context = await get_setup_token_context(db, token)
    if not context:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired setup token",
        )
    
    setup_token, user, tenant = context
    
    # Check if SSO config exists and is configured
    result = await db.execute(
        select(TenantSSOConfig).where(TenantSSOConfig.tenant_id == tenant.id)
    )
    sso_config = result.scalar_one_or_none()
    
    if not sso_config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SSO configuration not found. Please configure SSO first.",
        )
    
    # Mark SSO as configured
    sso_config.is_configured = True
    sso_config.updated_at = datetime.now(UTC)
    
    # Update signup metadata
    result = await db.execute(
        select(Signup).where(Signup.id == setup_token.signup_id)
    )
    signup = result.scalar_one_or_none()
    
    if signup:
        if signup.signup_metadata is None:
            signup.signup_metadata = {}
        signup.signup_metadata["sso_status"] = "configured"
        signup.signup_metadata["sso_configured_at"] = datetime.now(UTC).isoformat()
    
    # Mark token as used
    setup_token.used_at = datetime.now(UTC)
    
    # Update AuthIdentity email_verified if needed
    result = await db.execute(
        select(AuthIdentity).where(
            AuthIdentity.user_id == user.id,
            AuthIdentity.provider == "oidc"
        )
    )
    auth_identity = result.scalar_one_or_none()
    if auth_identity:
        auth_identity.email_verified = True
    
    await db.commit()
    
    return {
        "success": True,
        "message": "SSO setup completed successfully. You can now login via SSO.",
    }

