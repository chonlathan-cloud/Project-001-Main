"""Authoritative Product access resolution for service-authenticated MCP calls."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from uuid import UUID

from app.core.config import Settings, get_settings
from app.schemas.mcp_schema import McpAccessContext, McpPrincipalRequest
from app.services import daily_report_service
from app.services.identity_service import get_admin_by_mcp_principal


def mcp_environment_for_app(app_env: str) -> str | None:
    normalized = str(app_env or "").strip().lower()
    if normalized == "production":
        return "demo"
    if normalized == "prod-beta":
        return "beta"
    if normalized in {"development", "test"}:
        return "demo"
    return None


def _inactive_context(request: McpPrincipalRequest, resolved_at: datetime) -> McpAccessContext:
    opaque_user_id = "unmapped_" + hashlib.sha256(
        f"{request.issuer}|{request.subject}".encode()
    ).hexdigest()[:24]
    return McpAccessContext(
        subject=request.subject,
        issuer=request.issuer,
        client_id=request.client_id,
        user_id=opaque_user_id,
        environment=request.environment,
        active=False,
        external_mcp_enabled=False,
        role="pending",
        permissions=[],
        all_projects_read=False,
        assigned_project_ids=[],
        authorization_revision="unmapped",
        resolved_at=resolved_at,
    )


def _valid_project_ids(values: list[str]) -> list[str]:
    normalized: set[str] = set()
    for value in values:
        try:
            normalized.add(str(UUID(str(value))))
        except (TypeError, ValueError, AttributeError):
            continue
    return sorted(normalized)


def resolve_mcp_access(
    request: McpPrincipalRequest,
    *,
    settings: Settings | None = None,
) -> McpAccessContext:
    resolved_at = datetime.now(UTC)
    app_settings = settings or get_settings()
    expected_environment = mcp_environment_for_app(app_settings.app_env)
    if expected_environment != request.environment:
        return _inactive_context(request, resolved_at)
    if request.client_id not in set(app_settings.mcp_allowed_client_ids):
        return _inactive_context(request, resolved_at)

    entry = get_admin_by_mcp_principal(issuer=request.issuer, subject=request.subject)
    if entry is None:
        return _inactive_context(request, resolved_at)

    assigned_project_ids = _valid_project_ids(
        daily_report_service.list_membership_project_ids(
            principal_type="admin",
            principal_id=entry.email,
        )
    )
    all_projects_read = entry.role == "owner" or entry.mcp_all_projects_read
    role_in_rollout = entry.role in app_settings.mcp_allowed_roles
    effective_external_mcp_enabled = entry.external_mcp_enabled and role_in_rollout
    revision_payload = {
        "id": entry.id,
        "role": entry.role,
        "active": entry.is_active,
        "enabled": effective_external_mcp_enabled,
        "rollout_roles": app_settings.mcp_allowed_roles,
        "permissions": entry.mcp_permissions,
        "all_projects": all_projects_read,
        "projects": assigned_project_ids,
        "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
    }
    revision = hashlib.sha256(
        json.dumps(revision_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:24]
    return McpAccessContext(
        subject=request.subject,
        issuer=request.issuer,
        client_id=request.client_id,
        user_id=entry.id,
        environment=request.environment,
        active=entry.is_active,
        external_mcp_enabled=effective_external_mcp_enabled,
        role=entry.role,
        permissions=entry.mcp_permissions,
        all_projects_read=all_projects_read,
        assigned_project_ids=[] if all_projects_read else assigned_project_ids,
        authorization_revision=revision,
        resolved_at=resolved_at,
    )
