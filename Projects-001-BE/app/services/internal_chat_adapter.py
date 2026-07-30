"""Internal Chat adapter over the same policy-scoped MCP business contracts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import AuthenticatedUser
from app.core.config import Settings, get_settings
from app.schemas.mcp_schema import McpDashboardSummaryRequest, McpProjectInsightsRequest
from app.services import daily_report_service
from app.services.chat_analytics_service import _detect_intent, _parse_time_scope
from app.services.identity_service import get_admin_by_email
from app.services.mcp_access_service import mcp_environment_for_app
from app.services.mcp_project_operations_service import (
    get_dashboard_summary,
    get_project_insights,
)


@dataclass(frozen=True, slots=True)
class InternalChatAccessContext:
    user_id: str
    active: bool
    role: str
    permissions: set[str]
    all_projects_read: bool
    assigned_project_ids: set[str]
    authorization_revision: str


def _valid_project_ids(values: list[str]) -> set[str]:
    result: set[str] = set()
    for value in values:
        try:
            result.add(str(UUID(value)))
        except (TypeError, ValueError, AttributeError):
            continue
    return result


def resolve_internal_chat_access(user: AuthenticatedUser) -> InternalChatAccessContext:
    if not user.email:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Chat access denied.")
    entry = get_admin_by_email(user.email)
    if entry is None or not entry.is_active or entry.role not in {"owner", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Chat access denied.")
    permissions = set(entry.mcp_permissions)
    if entry.role == "admin" and not {"mcp_access", "financial_data_read"}.issubset(
        permissions
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Chat access denied.")
    assigned = _valid_project_ids(
        daily_report_service.list_membership_project_ids(
            principal_type="admin",
            principal_id=entry.email,
        )
    )
    all_projects = entry.role == "owner" or entry.mcp_all_projects_read
    revision_data = {
        "id": entry.id,
        "role": entry.role,
        "active": entry.is_active,
        "permissions": sorted(permissions),
        "all_projects": all_projects,
        "projects": sorted(assigned),
        "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
    }
    revision = hashlib.sha256(
        json.dumps(revision_data, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:24]
    return InternalChatAccessContext(
        user_id=entry.id,
        active=True,
        role=entry.role,
        permissions=permissions,
        all_projects_read=all_projects,
        assigned_project_ids=set() if all_projects else assigned,
        authorization_revision=revision,
    )


def _principal(user: AuthenticatedUser, settings: Settings) -> dict[str, str]:
    environment = mcp_environment_for_app(settings.app_env)
    if environment not in {"demo", "beta"}:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Internal Chat environment is unavailable.",
        )
    return {
        "subject": user.subject or user.email or "internal-chat-user",
        "issuer": "https://internal.projects-001.invalid",
        "client_id": "internal_chat",
        "environment": environment,
    }


def _money_value(value: object) -> str:
    if isinstance(value, dict):
        amount = str(value.get("amount") or "0.00")
        currency = str(value.get("currency") or "THB")
        return f"{currency} {amount}"
    return "THB 0.00"


def _metric(metric_id: str, label: str, value: object) -> dict[str, str]:
    return {"id": metric_id, "label": label, "value": _money_value(value)}


def _sources(items: list[dict[str, Any]]) -> list[dict[str, str]]:
    sources: list[dict[str, str]] = []
    for index, item in enumerate(items[:50]):
        domain = str(item.get("domain") or "product")
        system = str(item.get("source_system") or "product_backend")
        sources.append(
            {
                "id": f"source-{index + 1}",
                "label": f"{domain.replace('_', ' ').title()} · {system}",
                "description": "Policy-scoped Product source contract.",
            }
        )
    return sources


def _time_scope_payload(value: Any) -> dict[str, str] | None:
    if value is None:
        return None
    return {
        "key": value.key,
        "label": value.label,
        "start_date": value.start.isoformat(),
        "end_date": value.end.isoformat(),
    }


def _dashboard_analysis(
    *,
    contract: dict[str, Any],
    intent: str,
    time_scope: Any,
) -> dict[str, Any]:
    totals = dict(contract.get("totals") or {})
    metrics = [
        _metric("budget", "Budget", totals.get("budget")),
        _metric("actual", "Approved expense", totals.get("actual")),
        _metric("remaining", "Remaining", totals.get("remaining")),
        _metric("pending", "Pending requested", totals.get("pending_requested")),
        _metric("cashflow", "Net approved cashflow", totals.get("net_approved_cashflow")),
    ]
    summary = (
        f"Across {int(contract.get('returned_count') or 0)} authorized projects, "
        f"budget is {metrics[0]['value']}, approved expense is {metrics[1]['value']}, "
        f"and remaining budget is {metrics[2]['value']}."
    )
    return {
        "reply": summary,
        "summary": summary,
        "intent": intent,
        "metrics": metrics,
        "next_actions": [],
        "sources": _sources(list(contract.get("source_references") or [])),
        "time_scope": _time_scope_payload(time_scope),
        "project_id": None,
        "project_name": "All authorized projects",
        "context_item_count": int(contract.get("returned_count") or 0),
        "grounding": {
            "contract": "get_dashboard_summary",
            "calculation_method": contract.get("calculation_method"),
            "authorization_revision": None,
        },
    }


def _project_analysis(
    *,
    contract: dict[str, Any],
    intent: str,
    time_scope: Any,
) -> dict[str, Any]:
    financial = dict(contract.get("financial") or {})
    metrics = [
        _metric("budget", "Budget", financial.get("budget")),
        _metric("actual", "Approved expense", financial.get("actual")),
        _metric("remaining", "Remaining", financial.get("remaining")),
    ]
    inspection = contract.get("inspection") if isinstance(contract.get("inspection"), dict) else {}
    daily = contract.get("daily_reports") if isinstance(contract.get("daily_reports"), dict) else {}
    metrics.extend(
        [
            {
                "id": "open_inspections",
                "label": "Open inspections",
                "value": str(inspection.get("open_items") or 0),
            },
            {
                "id": "latest_progress",
                "label": "Latest progress",
                "value": (
                    f"{daily.get('latest_progress_percent')}%"
                    if daily.get("latest_progress_percent") is not None
                    else "Not available"
                ),
            },
        ]
    )
    project_name = str(financial.get("project_name") or "Authorized project")
    summary = (
        f"{project_name} has budget {metrics[0]['value']}, approved expense "
        f"{metrics[1]['value']}, and remaining budget {metrics[2]['value']}."
    )
    return {
        "reply": summary,
        "summary": summary,
        "intent": intent,
        "metrics": metrics,
        "next_actions": [],
        "sources": _sources(list(contract.get("source_references") or [])),
        "time_scope": _time_scope_payload(time_scope),
        "project_id": str(contract.get("project_id") or ""),
        "project_name": project_name,
        "context_item_count": len(contract.get("source_references") or []),
        "grounding": {
            "contract": "get_project_insights",
            "calculation_method": contract.get("calculation_method"),
            "authorization_revision": None,
        },
    }


async def analyze_internal_chat_question(
    db: AsyncSession,
    *,
    user: AuthenticatedUser,
    question: str,
    project_id: UUID | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    app_settings = settings or get_settings()
    access = resolve_internal_chat_access(user)
    principal = _principal(user, app_settings)
    time_scope = _parse_time_scope(question)
    date_from: date | None = time_scope.start if time_scope else None
    date_to: date | None = time_scope.end if time_scope else None
    intent = _detect_intent(question)
    if project_id is None:
        contract = await get_dashboard_summary(
            db,
            McpDashboardSummaryRequest(
                **principal,
                date_from=date_from,
                date_to=date_to,
                fresh=True,
            ),
            settings=app_settings,
            access_context=access,
        )
        analysis = _dashboard_analysis(contract=contract, intent=intent, time_scope=time_scope)
    else:
        contract = await get_project_insights(
            db,
            McpProjectInsightsRequest(
                **principal,
                project_id=project_id,
                date_from=date_from,
                date_to=date_to,
            ),
            settings=app_settings,
            access_context=access,
        )
        analysis = _project_analysis(contract=contract, intent=intent, time_scope=time_scope)
    analysis["grounding"]["authorization_revision"] = access.authorization_revision
    analysis["llm_context"] = {
        "intent": analysis["intent"],
        "summary": analysis["summary"],
        "metrics": analysis["metrics"],
        "sources": analysis["sources"],
        "time_scope": analysis["time_scope"],
    }
    return analysis
