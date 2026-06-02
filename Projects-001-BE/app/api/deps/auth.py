"""
Authentication and role dependencies for API routes.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.core.security import verify_session_token
from app.services.identity_service import get_authorized_admin_role

security = HTTPBearer(auto_error=False)
ADMIN_ROLE = "admin"
OWNER_ROLE = "owner"
SUBCONTRACTOR_ROLE = "subcontractor"
ADMIN_OR_OWNER_ROLES = {ADMIN_ROLE, OWNER_ROLE}


@dataclass(slots=True)
class AuthenticatedUser:
    subject: str
    role: str
    email: str | None = None
    display_name: str | None = None
    subcontractor_id: str | None = None
    is_development_override: bool = False


def role_permissions(role: str) -> list[str]:
    normalized_role = str(role or "").strip().lower()
    if normalized_role == OWNER_ROLE:
        return [
            "dashboard:view",
            "chat:use",
            "approvals:view",
            "approvals:mutate",
            "projects:view",
            "projects:mutate",
            "settings:view",
            "settings:mutate",
            "insights:view",
        ]
    if normalized_role == ADMIN_ROLE:
        return [
            "approvals:view",
            "projects:view",
            "settings:view",
            "insights:view",
        ]
    if normalized_role == SUBCONTRACTOR_ROLE:
        return [
            "input:create",
            "input:view",
            "profile:view",
        ]
    return []


def _debug_admin_role(value: str | None) -> str:
    cleaned = str(value or "").strip().lower()
    return cleaned if cleaned in ADMIN_OR_OWNER_ROLES else OWNER_ROLE


def _admin_access_user(user: AuthenticatedUser) -> AuthenticatedUser:
    if user.role not in ADMIN_OR_OWNER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access is required.",
        )
    if not user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin session is missing an email address.",
        )

    authorized_role = get_authorized_admin_role(user.email)
    if authorized_role is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access is no longer active for this account.",
        )

    return AuthenticatedUser(
        subject=user.subject,
        role=authorized_role,
        email=user.email,
        display_name=user.display_name,
        subcontractor_id=user.subcontractor_id,
        is_development_override=user.is_development_override,
    )


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
        role=str(payload.get("role") or "").strip().lower(),
        email=str(payload.get("email") or "").strip() or None,
        display_name=str(payload.get("display_name") or "").strip() or None,
        subcontractor_id=str(payload.get("subcontractor_id") or "").strip() or None,
    )


def require_subcontractor_user(
    user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    if user.role != SUBCONTRACTOR_ROLE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Subcontractor access is required.",
        )
    return user


def require_admin_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    x_debug_admin_email: str | None = Header(default=None, alias="X-Debug-Admin-Email"),
    x_debug_admin_role: str | None = Header(default=None, alias="X-Debug-Admin-Role"),
) -> AuthenticatedUser:
    settings = get_settings()

    if credentials is None and settings.is_development:
        email = (x_debug_admin_email or f"dev-admin@{settings.admin_email_domain or 'localhost'}").strip()
        role = _debug_admin_role(x_debug_admin_role)
        return AuthenticatedUser(
            subject=email,
            role=role,
            email=email,
            display_name="Development Owner" if role == OWNER_ROLE else "Development Admin",
            is_development_override=True,
        )

    user = get_current_user(credentials)
    return _admin_access_user(user)


def require_owner_user(
    user: AuthenticatedUser = Depends(require_admin_user),
) -> AuthenticatedUser:
    if user.role != OWNER_ROLE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner access is required.",
        )
    return user
