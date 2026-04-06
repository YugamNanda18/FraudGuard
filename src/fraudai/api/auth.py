"""Authentication and authorization skeleton for FraudAI Agent API.

Implements OAuth2 + JWT with RBAC by tier (Free/Pro/Enterprise) as
required by SR-010. This module provides FastAPI dependency-injection
callables; actual token validation logic will be implemented in F4.

Security requirements addressed:
- SR-010: OAuth2/JWT authentication, RBAC per tier, rate limiting
- SR-009: Tenant isolation via user.tenant_id
- SEC-004: Audit trail (user identity propagated to all handlers)
"""

from __future__ import annotations

from typing import Literal

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


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


async def get_current_user(
    token: str = Depends(oauth2_scheme),
) -> User:
    """Validate JWT and return the authenticated user.

    In development mode (ENVIRONMENT=development), accepts any non-empty
    token and returns a dev user with enterprise tier.

    In production, will:
    1. Decode and verify JWT signature (RS256).
    2. Check token expiration and revocation.
    3. Load user profile and tier from the token claims.
    4. Enforce rate limits based on tier.

    Raises:
        HTTPException 401: Invalid or expired token.
    """
    from fraudai.core.config import settings

    if settings.environment == "development":
        return _DEV_USER

    # Production JWT validation — not yet implemented
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="JWT validation not yet implemented for production.",
        headers={"WWW-Authenticate": "Bearer"},
    )


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
