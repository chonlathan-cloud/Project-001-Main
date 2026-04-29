"""
Authentication and role dependencies for API routes.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.core.security import verify_session_token
from app.services.identity_service import is_email_authorized_admin

security = HTTPBearer(auto_error=False)


@dataclass(slots=True)
class AuthenticatedUser:
    subject: str
    role: str
    email: str | None = None
    display_name: str | None = None
    subcontractor_id: str | None = None
    is_development_override: bool = False


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> AuthenticatedUser:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    payload = verify_session_token(credentials.credentials)
    return AuthenticatedUser(
        subject=str(payload.get("sub") or ""),
        role=str(payload.get("role") or ""),
        email=str(payload.get("email") or "").strip() or None,
        display_name=str(payload.get("display_name") or "").strip() or None,
        subcontractor_id=str(payload.get("subcontractor_id") or "").strip() or None,
    )


def require_subcontractor_user(
    user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    if user.role != "subcontractor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Subcontractor access is required.",
        )
    return user


def require_admin_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    x_debug_admin_email: str | None = Header(default=None, alias="X-Debug-Admin-Email"),
) -> AuthenticatedUser:
    settings = get_settings()

    if credentials is None and settings.is_development:
        email = (x_debug_admin_email or f"dev-admin@{settings.admin_email_domain or 'localhost'}").strip()
        return AuthenticatedUser(
            subject=email,
            role="admin",
            email=email,
            display_name="Development Admin",
            is_development_override=True,
        )

    user = get_current_user(credentials)
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access is required.",
        )
    if user.email and not is_email_authorized_admin(user.email):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access is no longer active for this account.",
        )
    return user
