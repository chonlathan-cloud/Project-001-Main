"""
Authentication and role dependencies for API routes.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.core.security import verify_session_token
from app.services.identity_service import get_authorized_admin_roles

security = HTTPBearer(auto_error=False)
ADMIN_ROLE = "admin"
OWNER_ROLE = "owner"
SUBCONTRACTOR_ROLE = "subcontractor"
INSPECTOR_ROLE = "inspector"
PENDING_ROLE = "pending"
ADMIN_OR_OWNER_ROLES = {ADMIN_ROLE, OWNER_ROLE}
INSPECTION_STAFF_ROLES = {ADMIN_ROLE, OWNER_ROLE, INSPECTOR_ROLE}


def normalize_roles(value: object, fallback: str | None = None) -> tuple[str, ...]:
    raw_values = value if isinstance(value, list) else []
    normalized: list[str] = []
    seen: set[str] = set()
    for item in raw_values:
        cleaned = str(item or "").strip().lower()
        if cleaned and cleaned not in seen:
            normalized.append(cleaned)
            seen.add(cleaned)

    fallback_role = str(fallback or "").strip().lower()
    if fallback_role and fallback_role not in seen:
        normalized.insert(0, fallback_role)

    return tuple(normalized)


@dataclass(slots=True)
class AuthenticatedUser:
    subject: str
    role: str
    roles: tuple[str, ...] = field(default_factory=tuple)
    email: str | None = None
    display_name: str | None = None
    subcontractor_id: str | None = None
    line_uid: str | None = None
    auth_provider: str | None = None
    access_request_id: str | None = None
    access_status: str | None = None
    rejection_reason: str | None = None
    is_development_override: bool = False

    def has_role(self, role: str) -> bool:
        normalized_role = str(role or "").strip().lower()
        return normalized_role == self.role or normalized_role in self.roles

    def has_any_role(self, roles: set[str]) -> bool:
        normalized_roles = {str(role or "").strip().lower() for role in roles}
        return self.role in normalized_roles or any(role in normalized_roles for role in self.roles)


def role_permissions(role: str, roles: list[str] | tuple[str, ...] | None = None) -> list[str]:
    normalized_role = str(role or "").strip().lower()
    normalized_roles = set(normalize_roles(list(roles or []), normalized_role))
    permissions: list[str] = []

    def add(items: list[str]) -> None:
        for item in items:
            if item not in permissions:
                permissions.append(item)

    if OWNER_ROLE in normalized_roles:
        add([
            "dashboard:view",
            "chat:use",
            "approvals:view",
            "approvals:mutate",
            "projects:view",
            "projects:mutate",
            "settings:view",
            "settings:mutate",
            "insights:view",
            "inspection:view",
            "inspection:mutate",
            "inspection:verify",
        ])
    if ADMIN_ROLE in normalized_roles:
        add([
            "approvals:view",
            "projects:view",
            "settings:view",
            "insights:view",
            "inspection:view",
            "inspection:mutate",
            "inspection:verify",
        ])
    if INSPECTOR_ROLE in normalized_roles:
        add([
            "projects:view",
            "inspection:view",
            "inspection:mutate",
            "inspection:verify",
        ])
    if SUBCONTRACTOR_ROLE in normalized_roles:
        add([
            "input:create",
            "input:view",
            "profile:view",
            "inspection:view_assigned",
            "inspection:submit_evidence",
        ])
    if PENDING_ROLE in normalized_roles:
        add([
            "access_request:view",
        ])
    return permissions


def _debug_admin_role(value: str | None) -> str:
    cleaned = str(value or "").strip().lower()
    return cleaned if cleaned in ADMIN_OR_OWNER_ROLES else OWNER_ROLE


def _admin_access_user(user: AuthenticatedUser) -> AuthenticatedUser:
    if not user.has_any_role(ADMIN_OR_OWNER_ROLES):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access is required.",
        )
    if not user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin session is missing an email address.",
        )

    authorized_roles = get_authorized_admin_roles(user.email)
    if not authorized_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access is no longer active for this account.",
        )
    if not set(authorized_roles).intersection(ADMIN_OR_OWNER_ROLES):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access is required.",
        )
    role = OWNER_ROLE if OWNER_ROLE in authorized_roles else ADMIN_ROLE

    return AuthenticatedUser(
        subject=user.subject,
        role=role,
        roles=tuple(authorized_roles),
        email=user.email,
        display_name=user.display_name,
        subcontractor_id=user.subcontractor_id,
        is_development_override=user.is_development_override,
    )


def get_current_user_allow_pending(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> AuthenticatedUser:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    payload = verify_session_token(credentials.credentials)
    role = str(payload.get("role") or "").strip().lower()
    roles = normalize_roles(payload.get("roles"), role)
    return AuthenticatedUser(
        subject=str(payload.get("sub") or ""),
        role=role,
        roles=roles,
        email=str(payload.get("email") or "").strip() or None,
        display_name=str(payload.get("display_name") or "").strip() or None,
        subcontractor_id=str(payload.get("subcontractor_id") or "").strip() or None,
        line_uid=str(payload.get("line_uid") or "").strip() or None,
        auth_provider=str(payload.get("auth_provider") or "").strip() or None,
        access_request_id=str(payload.get("access_request_id") or "").strip() or None,
        access_status=str(payload.get("access_status") or "").strip() or None,
        rejection_reason=str(payload.get("rejection_reason") or "").strip() or None,
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> AuthenticatedUser:
    user = get_current_user_allow_pending(credentials)
    if user.has_role(PENDING_ROLE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access approval is pending for this account.",
        )
    return user


def require_subcontractor_user(
    user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    if not user.has_role(SUBCONTRACTOR_ROLE):
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
            roles=(role,),
            email=email,
            display_name="Development Owner" if role == OWNER_ROLE else "Development Admin",
            is_development_override=True,
        )

    user = get_current_user(credentials)
    return _admin_access_user(user)


def require_owner_user(
    user: AuthenticatedUser = Depends(require_admin_user),
) -> AuthenticatedUser:
    if not user.has_role(OWNER_ROLE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner access is required.",
        )
    return user
