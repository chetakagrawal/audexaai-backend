"""JWT token creation and validation."""

from datetime import datetime, timedelta
from uuid import UUID

from jose import jwt, JWTError

import config
from auth.schemas import TokenPayload


def create_dev_token(
    user_id: UUID,
    tenant_id: UUID | None,
    role: str,
    is_platform_admin: bool,
    expires_in_hours: int = 24,
) -> str:
    """
    Create a JWT token for development login.

    Args:
        user_id: User UUID
        tenant_id: Tenant UUID (None for platform admins)
        role: User role in tenant
        is_platform_admin: Whether user is platform admin
        expires_in_hours: Token expiration in hours

    Returns:
        Encoded JWT token string
    """
    exp = datetime.utcnow() + timedelta(hours=expires_in_hours)
    
    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id) if tenant_id else None,
        "role": role,
        "is_platform_admin": is_platform_admin,
        "exp": int(exp.timestamp()),  # JWT expects Unix timestamp
    }
    
    return jwt.encode(
        payload,
        config.settings.JWT_SECRET,
        algorithm=config.settings.JWT_ALGORITHM,
    )


def decode_token(token: str) -> TokenPayload:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token string

    Returns:
        TokenPayload with decoded claims

    Raises:
        JWTError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            config.settings.JWT_SECRET,
            algorithms=[config.settings.JWT_ALGORITHM],
        )
        
        return TokenPayload(
            sub=payload["sub"],
            tenant_id=payload.get("tenant_id"),
            role=payload["role"],
            is_platform_admin=payload["is_platform_admin"],
            exp=datetime.fromtimestamp(payload["exp"]),
        )
    except JWTError as e:
        raise JWTError(f"Invalid token: {str(e)}") from e

