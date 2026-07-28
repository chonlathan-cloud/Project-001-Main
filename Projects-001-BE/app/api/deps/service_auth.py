"""Google-signed service identity authentication for internal MCP contracts."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import id_token as google_id_token

from app.core.config import Settings, get_settings

service_security = HTTPBearer(auto_error=False)
TokenVerifier = Callable[[str, GoogleAuthRequest, str], dict[str, Any]]


@dataclass(frozen=True, slots=True)
class ServicePrincipal:
    subject: str
    email: str
    audience: str


async def require_mcp_service(
    credentials: HTTPAuthorizationCredentials | None = Depends(service_security),
    settings: Settings = Depends(get_settings),
) -> ServicePrincipal:
    """Require the exact environment-specific MCP Cloud Run service account."""
    if not settings.mcp_internal_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Internal MCP contracts are disabled.",
        )
    if not settings.mcp_backend_audience or not settings.mcp_allowed_service_accounts:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Internal MCP service authentication is not configured.",
        )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Service authentication required.",
        )

    try:
        claims = await asyncio.to_thread(
            google_id_token.verify_oauth2_token,
            credentials.credentials,
            GoogleAuthRequest(),
            settings.mcp_backend_audience,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid service identity.",
        ) from exc

    issuer = str(claims.get("iss") or "").rstrip("/")
    email = str(claims.get("email") or "").strip().lower()
    subject = str(claims.get("sub") or "").strip()
    email_verified = claims.get("email_verified") in {True, "true", "True"}
    allowed_accounts = {
        item.strip().lower() for item in settings.mcp_allowed_service_accounts if item.strip()
    }
    if (
        issuer not in {"https://accounts.google.com", "accounts.google.com"}
        or not email_verified
        or not subject
        or email not in allowed_accounts
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Service identity is not authorized for MCP contracts.",
        )
    return ServicePrincipal(
        subject=subject,
        email=email,
        audience=settings.mcp_backend_audience,
    )
