"""Authentication and authorization for FraudAI Agent API.

Implements OAuth2 + JWT with RBAC by tier (Free/Pro/Enterprise) as
required by SR-010. Uses PyJWT with HS256 for the MVP; RS256 planned
for production.

Security requirements addressed:
- SR-010: OAuth2/JWT authentication, RBAC per tier, rate limiting
- SR-009: Tenant isolation via user.tenant_id
- SEC-004: Audit trail (user identity propagated to all handlers)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

# JWT configuration — algorithm and expiration.
# Secret is read from settings at call time to respect env overrides.
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24


class User(BaseModel):
    """Authenticated user context injected into route handlers."""

    user_id: str
    tenant_id: str
    email: str
    tier: Literal["free", "pro", "enterprise"]
    is_admin: bool = False


_DEV_USER = User(
    user_id="dev-user",
    tenant_id="dev-tenant",
    email="dev@fraudai.local",
    tier="enterprise",
    is_admin=True,
)


def create_token(
    user_id: str,
    tenant_id: str,
    tier: str,
    *,
    email: str = "",
    is_admin: bool = False,
) -> str:
    """Create a signed JWT token.

    Args:
        user_id: Subject claim (``sub``).
        tenant_id: Tenant identifier for isolation (SR-009).
        tier: User subscription tier (``free`` / ``pro`` / ``enterprise``).
        email: Optional email claim.
        is_admin: Whether the user has admin privileges.

    Returns:
        Encoded JWT string.
    """
    from fraudai.core.config import settings

    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "tier": tier,
        "email": email,
        "is_admin": is_admin,
        "exp": datetime.now(UTC) + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
) -> User:
    """Validate JWT and return the authenticated user.

    In development/staging mode, the special ``dev-token`` value bypasses
    JWT validation and returns a dev user with enterprise tier. Any other
    token is still validated as a real JWT so that the dev environment
    can exercise the full auth flow.

    In production:
    1. Decodes and verifies the JWT signature (HS256 MVP).
    2. Checks token expiration.
    3. Builds the User model from token claims.

    Raises:
        HTTPException 401: Invalid or expired token.
    """
    from fraudai.core.config import settings

    # Dev mode bypass — accept the literal "dev-token" string
    if settings.environment in ("development", "staging") and token == "dev-token":
        return _DEV_USER

    # JWT validation (works in all environments)
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[JWT_ALGORITHM],
        )
        return User(
            user_id=payload["sub"],
            tenant_id=payload["tenant_id"],
            email=payload.get("email", ""),
            tier=payload.get("tier", "free"),
            is_admin=payload.get("is_admin", False),
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def get_admin_user(
    user: User = Depends(get_current_user),
) -> User:
    """Require admin privileges for sensitive endpoints (e.g. /admin/metrics).

    Raises:
        HTTPException 403: User is not an admin.
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required.",
        )
    return user
