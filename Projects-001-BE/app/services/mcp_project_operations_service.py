"""Bounded Phase 4 Inspection, Daily Report, Dashboard and Insight reads."""

from __future__ import annotations

import asyncio
import hashlib
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.core.config import Settings, get_settings
from app.models.boq import BOQItem, Project
from app.models.input_request import InputPayment, InputRequest
from app.schemas.mcp_schema import (
    McpDailyReportRequest,
    McpDailyReportsListRequest,
    McpDailyReportVersionsRequest,
    McpDashboardSummaryRequest,
    McpFetchRequest,
    McpInspectionListRequest,
    McpInspectionRequest,
    McpProjectFinancialSummaryRequest,
    McpProjectInsightsRequest,
    McpSearchRequest,
)
from app.services import daily_report_service, inspection_service
from app.services.mcp_finance_document_service import (
    FINANCE_PERMISSION,
    get_project_financial_summary,
)
from app.services.mcp_read_service import (
    McpInvalidInput,
    McpNotFoundOrForbidden,
    _authorize,
    _decode_cursor,
    _encode_cursor,
    _money,
    _project_scope,
    _project_url,
    _utc_now,
)

MAX_SOURCE_SCAN = 250
MAX_DASHBOARD_PROJECTS = 50
MAX_INSPECTION_EVENTS = 50


def _principal(request: Any) -> dict[str, Any]:
    return request.model_dump(
        include={"contract_version", "subject", "issuer", "client_id", "environment"}
    )


def _scope_key(prefix: str, values: dict[str, Any]) -> str:
    material = "|".join(f"{key}={values[key]}" for key in sorted(values))
    digest = hashlib.sha256(material.encode()).hexdigest()[:20]
    return f"{prefix}:{digest}"


def _clean(value: object, *, max_chars: int = 2000) -> str | None:
    text = str(value or "").strip()
    return text[:max_chars] if text else None


def _as_date(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)) if value else None
    except ValueError:
        return None


def _source_error(exc: Exception) -> None:
    if isinstance(exc, HTTPException) and exc.status_code in {
        status.HTTP_403_FORBIDDEN,
        status.HTTP_404_NOT_FOUND,
    }:
        raise McpNotFoundOrForbidden from exc
    raise exc


async def _require_project(db: AsyncSession, project_id: UUID) -> Project:
    project = (
        await db.execute(select(Project).options(noload("*")).where(Project.id == project_id))
    ).scalar_one_or_none()
    if project is None:
        raise McpNotFoundOrForbidden
    return project


def _inspection_documents(item: dict[str, Any]) -> list[str]:
    project_id = str(item.get("project_id") or "")
    file_ids = [
        *list(item.get("before_file_ids") or []),
        *list(item.get("after_file_ids") or []),
    ]
    return [
        f"inspection.{project_id}.{file_id}"
        for file_id in dict.fromkeys(str(value) for value in file_ids if value)
    ][:50]


def _safe_inspection_item(item: dict[str, Any], settings: Settings) -> dict[str, Any]:
    due_date = _as_date(item.get("due_date"))
    status_value = str(item.get("status") or "").upper()
    project_id = str(item.get("project_id") or "")
    return {
        "item_id": str(item.get("id") or ""),
        "project_id": project_id,
        "round_id": _clean(item.get("round_id"), max_chars=255),
        "zone_id": _clean(item.get("zone_id"), max_chars=255),
        "display_no": _clean(item.get("display_no"), max_chars=64),
        "title": _clean(item.get("title"), max_chars=500),
        "description": _clean(item.get("description")),
        "category": _clean(item.get("category"), max_chars=128),
        "status": status_value,
        "severity": str(item.get("severity") or "").upper(),
        "due_date": due_date,
        "overdue": bool(
            due_date and due_date < datetime.now(UTC).date() and status_value != "RESOLVED"
        ),
        "assigned_subcontractor_name": _clean(
            item.get("assigned_subcontractor_name"), max_chars=255
        ),
        "document_ids": _inspection_documents(item),
        "created_at": item.get("created_at"),
        "updated_at": item.get("updated_at"),
        "product_url": _project_url(project_id, settings),
    }


def _inspection_matches(item: dict[str, Any], request: McpInspectionListRequest) -> bool:
    statuses = {value.upper() for value in request.statuses}
    severities = {value.upper() for value in request.severities}
    item_status = str(item.get("status") or "").upper()
    item_severity = str(item.get("severity") or "").upper()
    due_date = _as_date(item.get("due_date"))
    if statuses and item_status not in statuses:
        return False
    if severities and item_severity not in severities:
        return False
    if request.due_before and (due_date is None or due_date > request.due_before):
        return False
    overdue = bool(
        due_date and due_date < datetime.now(UTC).date() and item_status != "RESOLVED"
    )
    return request.overdue is None or overdue == request.overdue


async def list_inspection_items(
    db: AsyncSession,
    request: McpInspectionListRequest,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    app_settings = settings or get_settings()
    _authorize(request, project_id=str(request.project_id), settings=app_settings)
    await _require_project(db, request.project_id)
    scope = _scope_key(
        f"inspection:{request.project_id}",
        {
            "statuses": sorted(value.upper() for value in request.statuses),
            "severities": sorted(value.upper() for value in request.severities),
            "due_before": request.due_before,
            "overdue": request.overdue,
        },
    )
    offset = _decode_cursor(request.cursor, scope, app_settings)
    try:
        raw_items = await asyncio.to_thread(
            inspection_service.list_defects,
            project_id=str(request.project_id),
            round_id=None,
            filters={},
            limit=min(app_settings.mcp_document_scan_limit, MAX_SOURCE_SCAN),
        )
    except Exception as exc:
        _source_error(exc)
    items = [
        _safe_inspection_item(item, app_settings)
        for item in raw_items
        if _inspection_matches(item, request)
    ]
    page = items[offset : offset + request.limit]
    has_more = offset + len(page) < len(items)
    source_scan_truncated = len(raw_items) >= min(
        app_settings.mcp_document_scan_limit, MAX_SOURCE_SCAN
    )
    return {
        "project_id": str(request.project_id),
        "items": page,
        "returned_count": len(page),
        "next_cursor": (
            _encode_cursor(scope, offset + len(page), app_settings) if has_more else None
        ),
        "partial": source_scan_truncated,
        "warnings": (
            [
                {
                    "code": "PARTIAL_RESULT",
                    "message": "Inspection source scan reached its bounded limit.",
                }
            ]
            if source_scan_truncated
            else []
        ),
        "source_read_at": _utc_now(),
    }


async def get_inspection_item(
    db: AsyncSession,
    request: McpInspectionRequest,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    app_settings = settings or get_settings()
    _authorize(request, project_id=str(request.project_id), settings=app_settings)
    await _require_project(db, request.project_id)
    try:
        item = await asyncio.to_thread(
            inspection_service.get_defect_for_mcp,
            project_id=str(request.project_id),
            defect_id=request.item_id,
        )
        events = await asyncio.to_thread(
            inspection_service.list_events_for_mcp,
            project_id=str(request.project_id),
            round_id=str(item.get("round_id") or ""),
            defect_id=request.item_id,
            limit=MAX_INSPECTION_EVENTS,
        )
    except Exception as exc:
        _source_error(exc)
    return {
        **_safe_inspection_item(item, app_settings),
        "events": [
            {
                "event_id": str(event.get("id") or ""),
                "event_type": _clean(event.get("event_type"), max_chars=64),
                "from_status": _clean(event.get("from_status"), max_chars=64),
                "to_status": _clean(event.get("to_status"), max_chars=64),
                "comment": _clean(event.get("comment"), max_chars=1000),
                "actor_role": _clean(event.get("actor_role"), max_chars=64),
                "created_at": event.get("created_at"),
            }
            for event in events
        ],
        "source_read_at": _utc_now(),
    }


def _safe_issue(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return {
            key: cleaned
            for key in ("title", "description", "severity", "status")
            if (cleaned := _clean(value.get(key), max_chars=1000)) is not None
        }
    return {"title": _clean(value, max_chars=1000)}


def _safe_report(
    report: dict[str, Any],
    settings: Settings,
    *,
    snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data = snapshot or report
    project_id = str(report.get("project_id") or data.get("project_id") or "")
    return {
        "report_id": str(report.get("id") or data.get("report_id") or ""),
        "project_id": project_id,
        "project_name": _clean(data.get("project_name"), max_chars=255),
        "report_date": _as_date(data.get("report_date")),
        "status": "PUBLISHED" if snapshot is not None else str(report.get("status") or "").upper(),
        "title": _clean(data.get("title"), max_chars=500),
        "summary": _clean(data.get("summary"), max_chars=8000),
        "progress_percent": data.get("progress_percent"),
        "manpower_total": int(data.get("manpower_total") or 0),
        "issues": [_safe_issue(item) for item in list(data.get("issues") or [])[:100]],
        "tomorrow_plan": _clean(data.get("tomorrow_plan"), max_chars=4000),
        "customer_note": _clean(data.get("customer_note"), max_chars=2000),
        "published_version": int(report.get("published_version") or 0) or None,
        "published_at": report.get("published_at"),
        "delivery_status": _clean(report.get("delivery_status"), max_chars=64),
        "created_at": report.get("created_at"),
        "updated_at": report.get("updated_at"),
        "product_url": _project_url(project_id, settings),
    }


async def list_daily_reports(
    db: AsyncSession,
    request: McpDailyReportsListRequest,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    app_settings = settings or get_settings()
    _authorize(request, project_id=str(request.project_id), settings=app_settings)
    await _require_project(db, request.project_id)
    scope = _scope_key(
        f"daily-reports:{request.project_id}",
        {
            "date_from": request.date_from,
            "date_to": request.date_to,
            "statuses": sorted(value.upper() for value in request.statuses),
        },
    )
    offset = _decode_cursor(request.cursor, scope, app_settings)
    try:
        raw_items = await asyncio.to_thread(
            daily_report_service.list_reports_for_mcp,
            project_id=str(request.project_id),
            limit=min(app_settings.mcp_document_scan_limit, MAX_SOURCE_SCAN),
        )
    except Exception as exc:
        _source_error(exc)
    statuses = {value.upper() for value in request.statuses}
    items = []
    for item in raw_items:
        report_date = _as_date(item.get("report_date"))
        if request.date_from and (report_date is None or report_date < request.date_from):
            continue
        if request.date_to and (report_date is None or report_date > request.date_to):
            continue
        if statuses and str(item.get("status") or "").upper() not in statuses:
            continue
        items.append(_safe_report(item, app_settings))
    page = items[offset : offset + request.limit]
    has_more = offset + len(page) < len(items)
    source_scan_truncated = len(raw_items) >= min(
        app_settings.mcp_document_scan_limit, MAX_SOURCE_SCAN
    )
    return {
        "project_id": str(request.project_id),
        "items": page,
        "returned_count": len(page),
        "next_cursor": (
            _encode_cursor(scope, offset + len(page), app_settings) if has_more else None
        ),
        "partial": source_scan_truncated,
        "warnings": (
            [
                {
                    "code": "PARTIAL_RESULT",
                    "message": "Daily Report source scan reached its bounded limit.",
                }
            ]
            if source_scan_truncated
            else []
        ),
        "source_read_at": _utc_now(),
    }


async def _authorized_report(
    request: McpDailyReportRequest | McpDailyReportVersionsRequest,
    settings: Settings,
) -> dict[str, Any]:
    _authorize(request, settings=settings)
    try:
        report = await asyncio.to_thread(
            daily_report_service.get_report_for_mcp,
            report_id=request.report_id,
        )
    except Exception as exc:
        _source_error(exc)
    project_id = str(report.get("project_id") or "")
    _authorize(request, project_id=project_id, settings=settings)
    return report


async def get_daily_report(
    db: AsyncSession,
    request: McpDailyReportRequest,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    app_settings = settings or get_settings()
    report = await _authorized_report(request, app_settings)
    await _require_project(db, UUID(str(report["project_id"])))
    selected_version = None
    snapshot = None
    if request.version:
        try:
            selected_version = await asyncio.to_thread(
                daily_report_service.get_report_version_for_mcp,
                report_id=request.report_id,
                version=request.version,
            )
        except Exception as exc:
            _source_error(exc)
        snapshot = dict(selected_version.get("snapshot") or {})
    data = _safe_report(report, app_settings, snapshot=snapshot)
    data["selected_version"] = (
        {
            "version_id": selected_version.get("id"),
            "version_number": int(selected_version.get("version") or 0),
            "published_at": selected_version.get("published_at"),
            "publication_note": _clean(selected_version.get("publication_note"), max_chars=1000),
            "immutable": True,
        }
        if selected_version
        else None
    )
    data["source_read_at"] = _utc_now()
    return data


async def list_daily_report_versions(
    db: AsyncSession,
    request: McpDailyReportVersionsRequest,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    app_settings = settings or get_settings()
    report = await _authorized_report(request, app_settings)
    await _require_project(db, UUID(str(report["project_id"])))
    scope = f"daily-report-versions:{request.report_id}"
    offset = _decode_cursor(request.cursor, scope, app_settings)
    try:
        versions = await asyncio.to_thread(
            daily_report_service.list_versions_for_mcp,
            report_id=request.report_id,
            limit=MAX_SOURCE_SCAN,
        )
    except Exception as exc:
        _source_error(exc)
    page = versions[offset : offset + request.limit]
    has_more = offset + len(page) < len(versions)
    return {
        "report_id": request.report_id,
        "project_id": str(report["project_id"]),
        "items": [
            {
                "version_id": str(item.get("id") or ""),
                "version_number": int(item.get("version") or 0),
                "publication_note": _clean(item.get("publication_note"), max_chars=1000),
                "published_at": item.get("published_at"),
                "immutable": True,
            }
            for item in page
        ],
        "returned_count": len(page),
        "next_cursor": (
            _encode_cursor(scope, offset + len(page), app_settings) if has_more else None
        ),
        "source_read_at": _utc_now(),
    }


def _decimal_map(rows: list[Any]) -> dict[str, Decimal]:
    return {str(project_id): Decimal(str(amount or 0)) for project_id, amount in rows}


async def get_dashboard_summary(
    db: AsyncSession,
    request: McpDashboardSummaryRequest,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    app_settings = settings or get_settings()
    access = _authorize(
        request,
        required_permissions=FINANCE_PERMISSION,
        settings=app_settings,
    )
    allowed = _project_scope(access)
    requested = {str(value) for value in request.project_ids}
    if allowed is not None and requested and not requested.issubset(allowed):
        raise McpNotFoundOrForbidden
    selected = requested or allowed
    statement = select(Project).options(noload("*")).order_by(Project.name, Project.id)
    if selected is not None:
        if not selected:
            projects: list[Project] = []
        else:
            statement = statement.where(Project.id.in_([UUID(value) for value in selected]))
            projects = list(
                (await db.execute(statement.limit(MAX_DASHBOARD_PROJECTS + 1))).scalars().all()
            )
    else:
        projects = list(
            (await db.execute(statement.limit(MAX_DASHBOARD_PROJECTS + 1))).scalars().all()
        )
    truncated = len(projects) > MAX_DASHBOARD_PROJECTS
    projects = projects[:MAX_DASHBOARD_PROJECTS]
    ids = [project.id for project in projects]
    if not ids:
        return {
            "items": [],
            "totals": {
                "budget": _money(0),
                "actual": _money(0),
                "paid_in_period": _money(0),
                "remaining": _money(0),
                "pending_requested": _money(0),
                "approved_income": _money(0),
                "net_approved_cashflow": _money(0),
                "period": {
                    "approved_expense": _money(0),
                    "approved_income": _money(0),
                    "paid": _money(0),
                    "net_approved_cashflow": _money(0),
                },
            },
            "trend": {
                "over_budget_project_count": 0,
                "negative_period_cashflow_project_count": 0,
                "interpretation": (
                    "Signals are descriptive source facts, not a forecast or inferred cause."
                ),
            },
            "returned_count": 0,
            "requested_period": {"date_from": request.date_from, "date_to": request.date_to},
            "calculation_method": "exact_decimal_scoped_dashboard_v1",
            "source_references": [],
            "source_read_at": _utc_now(),
        }

    budget_rows = (
        await db.execute(
            select(BOQItem.project_id, func.coalesce(func.sum(BOQItem.grand_total), 0))
            .where(
                BOQItem.project_id.in_(ids),
                BOQItem.valid_to.is_(None),
                BOQItem.parent_id.is_(None),
                func.upper(func.trim(BOQItem.boq_type)) == "CUSTOMER",
            )
            .group_by(BOQItem.project_id)
        )
    ).all()
    amount_value = func.coalesce(InputRequest.approved_amount, InputRequest.amount)
    approved_expense_value = case(
        (
            and_(
                InputRequest.entry_type == "EXPENSE",
                InputRequest.status.in_(["APPROVED", "PAID"]),
            ),
            amount_value,
        ),
        else_=0,
    )
    approved_income_value = case(
        (
            and_(
                InputRequest.entry_type == "INCOME",
                InputRequest.status.in_(["APPROVED", "PAID"]),
            ),
            amount_value,
        ),
        else_=0,
    )
    pending_expense_value = case(
        (
            and_(
                InputRequest.entry_type == "EXPENSE",
                InputRequest.status.in_(["DRAFT", "PENDING_ADMIN"]),
            ),
            InputRequest.amount,
        ),
        else_=0,
    )
    request_rows = (
        await db.execute(
            select(
                InputRequest.project_id,
                func.coalesce(func.sum(approved_expense_value), 0),
                func.coalesce(func.sum(approved_income_value), 0),
                func.coalesce(func.sum(pending_expense_value), 0),
            )
            .where(InputRequest.project_id.in_(ids))
            .group_by(InputRequest.project_id)
        )
    ).all()
    period_request_statement = select(
        InputRequest.project_id,
        func.coalesce(func.sum(approved_expense_value), 0),
        func.coalesce(func.sum(approved_income_value), 0),
    ).where(InputRequest.project_id.in_(ids))
    if request.date_from:
        period_request_statement = period_request_statement.where(
            InputRequest.request_date >= request.date_from
        )
    if request.date_to:
        period_request_statement = period_request_statement.where(
            InputRequest.request_date <= request.date_to
        )
    period_request_rows = (
        await db.execute(period_request_statement.group_by(InputRequest.project_id))
    ).all()
    payment_statement = (
        select(InputRequest.project_id, func.coalesce(func.sum(InputPayment.amount), 0))
        .join(InputPayment, InputPayment.input_request_id == InputRequest.id)
        .where(InputRequest.project_id.in_(ids))
    )
    if request.date_from:
        payment_statement = payment_statement.where(InputPayment.payment_date >= request.date_from)
    if request.date_to:
        payment_statement = payment_statement.where(InputPayment.payment_date <= request.date_to)
    payment_rows = (await db.execute(payment_statement.group_by(InputRequest.project_id))).all()

    budget_by = _decimal_map(list(budget_rows))
    paid_by = _decimal_map(list(payment_rows))
    requests_by = {
        str(project_id): tuple(Decimal(str(value or 0)) for value in values)
        for project_id, *values in request_rows
    }
    period_requests_by = {
        str(project_id): tuple(Decimal(str(value or 0)) for value in values)
        for project_id, *values in period_request_rows
    }
    items: list[dict[str, Any]] = []
    total_budget = total_actual = total_paid = total_pending = total_income = Decimal("0")
    total_period_expense = total_period_income = Decimal("0")
    over_budget_count = negative_period_cashflow_count = 0
    for project in projects:
        project_id = str(project.id)
        approved_expense, approved_income, pending = requests_by.get(
            project_id, (Decimal("0"), Decimal("0"), Decimal("0"))
        )
        budget = budget_by.get(project_id, Decimal("0"))
        paid = paid_by.get(project_id, Decimal("0"))
        period_expense, period_income = period_requests_by.get(
            project_id, (Decimal("0"), Decimal("0"))
        )
        period_net = period_income - period_expense
        remaining = budget - approved_expense
        total_budget += budget
        total_actual += approved_expense
        total_paid += paid
        total_pending += pending
        total_income += approved_income
        total_period_expense += period_expense
        total_period_income += period_income
        over_budget_count += int(remaining < 0)
        negative_period_cashflow_count += int(period_net < 0)
        items.append(
            {
                "project_id": project_id,
                "project_name": project.name,
                "project_status": project.status,
                "budget": _money(budget),
                "actual": _money(approved_expense),
                "paid_in_period": _money(paid),
                "remaining": _money(remaining),
                "pending_requested": _money(pending),
                "approved_income": _money(approved_income),
                "period": {
                    "approved_expense": _money(period_expense),
                    "approved_income": _money(period_income),
                    "paid": _money(paid),
                    "net_approved_cashflow": _money(period_net),
                },
                "over_budget": remaining < 0,
                "product_url": _project_url(project.id, app_settings),
            }
        )
    return {
        "items": items,
        "totals": {
            "budget": _money(total_budget),
            "actual": _money(total_actual),
            "paid_in_period": _money(total_paid),
            "remaining": _money(total_budget - total_actual),
            "pending_requested": _money(total_pending),
            "approved_income": _money(total_income),
            "net_approved_cashflow": _money(total_income - total_actual),
            "period": {
                "approved_expense": _money(total_period_expense),
                "approved_income": _money(total_period_income),
                "paid": _money(total_paid),
                "net_approved_cashflow": _money(
                    total_period_income - total_period_expense
                ),
            },
        },
        "trend": {
            "over_budget_project_count": over_budget_count,
            "negative_period_cashflow_project_count": negative_period_cashflow_count,
            "interpretation": (
                "Signals are descriptive source facts, not a forecast or inferred cause."
            ),
        },
        "requested_period": {"date_from": request.date_from, "date_to": request.date_to},
        "returned_count": len(items),
        "partial": truncated,
        "warnings": (
            [
                {
                    "code": "PARTIAL_RESULT",
                    "message": "Dashboard project scope exceeded the 50-project bound.",
                }
            ]
            if truncated
            else []
        ),
        "calculation_method": "current_customer_boq_and_exact_approved_request_totals_v1",
        "source_references": [
            {
                "domain": "finance_payments",
                "record_id": item["project_id"],
                "source_system": "product_backend",
                "product_url": item["product_url"],
            }
            for item in items
        ],
        "source_read_at": _utc_now(),
    }


async def get_project_insights(
    db: AsyncSession,
    request: McpProjectInsightsRequest,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    app_settings = settings or get_settings()
    _authorize(
        request,
        project_id=str(request.project_id),
        required_permissions=FINANCE_PERMISSION,
        settings=app_settings,
    )
    financial = await get_project_financial_summary(
        db,
        McpProjectFinancialSummaryRequest(
            **_principal(request), project_id=request.project_id, fresh=True
        ),
        settings=app_settings,
    )
    inspection_result, report_result = await asyncio.gather(
        asyncio.to_thread(
            inspection_service.list_defects,
            project_id=str(request.project_id),
            round_id=None,
            filters={},
            limit=MAX_SOURCE_SCAN,
        ),
        asyncio.to_thread(
            daily_report_service.list_reports_for_mcp,
            project_id=str(request.project_id),
            limit=MAX_SOURCE_SCAN,
        ),
        return_exceptions=True,
    )
    warnings: list[dict[str, str]] = []
    source_status = {
        "finance": "available",
        "inspection": "available",
        "daily_reports": "available",
    }
    source_references = [
        {
            "domain": "finance_payments",
            "record_id": str(request.project_id),
            "source_system": "product_backend",
            "last_updated_at": financial.get("source_read_at"),
            "product_url": financial.get("product_url"),
        }
    ]
    if isinstance(inspection_result, BaseException):
        source_status["inspection"] = "unavailable"
        warnings.append(
            {
                "code": "SOURCE_UNAVAILABLE",
                "message": (
                    "Inspection facts were unavailable; no inspection conclusion was inferred."
                ),
            }
        )
        inspection_items: list[dict[str, Any]] = []
    else:
        inspection_items = list(inspection_result)
        source_references.append(
            {
                "domain": "inspection",
                "record_id": str(request.project_id),
                "source_system": "firestore",
            }
        )
    if isinstance(report_result, BaseException):
        source_status["daily_reports"] = "unavailable"
        warnings.append(
            {
                "code": "SOURCE_UNAVAILABLE",
                "message": (
                    "Daily Report facts were unavailable; no progress conclusion was inferred."
                ),
            }
        )
        reports: list[dict[str, Any]] = []
    else:
        reports = [
            item
            for item in report_result
            if (
                not request.date_from
                or (_as_date(item.get("report_date")) or date.min) >= request.date_from
            )
            and (
                not request.date_to
                or (_as_date(item.get("report_date")) or date.max) <= request.date_to
            )
        ]
        source_references.append(
            {
                "domain": "daily_reports",
                "record_id": str(request.project_id),
                "source_system": "firestore",
            }
        )

    open_items = [
        item for item in inspection_items if str(item.get("status") or "").upper() != "RESOLVED"
    ]
    overdue_items = [
        item
        for item in open_items
        if (_as_date(item.get("due_date")) or date.max) < datetime.now(UTC).date()
    ]
    latest_report = reports[0] if reports else None
    progress = latest_report.get("progress_percent") if latest_report else None
    if progress is not None and Decimal(str(progress)) >= Decimal("100") and open_items:
        warnings.append(
            {
                "code": "SOURCE_INCONSISTENCY",
                "message": (
                    "Latest Daily Report shows full progress while unresolved "
                    "inspection items remain."
                ),
            }
        )
    risks = []
    if financial.get("over_budget"):
        risks.append({"code": "OVER_BUDGET", "severity": "high", "evidence_source": "finance"})
    if overdue_items:
        risks.append(
            {
                "code": "OVERDUE_INSPECTIONS",
                "severity": "high",
                "count": len(overdue_items),
                "evidence_source": "inspection",
            }
        )
    return {
        "project_id": str(request.project_id),
        "financial": {key: value for key, value in financial.items() if key != "source_read_at"},
        "inspection": {
            "total_items": len(inspection_items),
            "open_items": len(open_items),
            "overdue_items": len(overdue_items),
        }
        if source_status["inspection"] == "available"
        else None,
        "daily_reports": {
            "report_count": len(reports),
            "latest_report_id": str(latest_report.get("id") or "") if latest_report else None,
            "latest_report_date": _as_date(latest_report.get("report_date"))
            if latest_report
            else None,
            "latest_progress_percent": progress,
        }
        if source_status["daily_reports"] == "available"
        else None,
        "risks": risks,
        "source_status": source_status,
        "source_references": source_references,
        "warnings": warnings,
        "partial": any(value == "unavailable" for value in source_status.values()),
        "calculation_method": "independent_finance_inspection_daily_report_signals_v1",
        "source_read_at": _utc_now(),
    }


async def search_phase4_hits(
    db: AsyncSession,
    request: McpSearchRequest,
    *,
    settings: Settings,
) -> list[dict[str, Any]]:
    domains = set(request.domains)
    if not domains.intersection({"inspection", "daily_reports"}):
        return []
    access = _authorize(
        request,
        project_id=str(request.project_id) if request.project_id else None,
        settings=settings,
    )
    project_ids = (
        [str(request.project_id)]
        if request.project_id
        else sorted(_project_scope(access) or [])[:10]
    )
    if not project_ids and _project_scope(access) is None:
        project_ids = [
            str(value)
            for value in (await db.execute(select(Project.id).order_by(Project.id).limit(10)))
            .scalars()
            .all()
        ]
    query = request.query.casefold()
    hits: list[dict[str, Any]] = []
    for project_id in project_ids:
        if "inspection" in domains and (
            not request.record_types or "inspection_item" in request.record_types
        ):
            result = await list_inspection_items(
                db,
                McpInspectionListRequest(
                    **_principal(request), project_id=UUID(project_id), limit=min(request.limit, 50)
                ),
                settings=settings,
            )
            for item in result["items"]:
                haystack = " ".join(
                    str(item.get(key) or "")
                    for key in ("display_no", "title", "description", "category")
                ).casefold()
                if query in haystack:
                    hits.append(
                        {
                            "reference": f"inspection:item:{project_id}.{item['item_id']}",
                            "domain": "inspection",
                            "record_type": "inspection_item",
                            "title": item.get("title")
                            or item.get("display_no")
                            or "Inspection item",
                            "snippet": f"{item.get('severity') or ''} · {item.get('status') or ''}",
                            "project_id": project_id,
                            "product_url": item.get("product_url"),
                        }
                    )
        if "daily_reports" in domains and (
            not request.record_types or "daily_report" in request.record_types
        ):
            result = await list_daily_reports(
                db,
                McpDailyReportsListRequest(
                    **_principal(request),
                    project_id=UUID(project_id),
                    date_from=request.date_from,
                    date_to=request.date_to,
                    limit=min(request.limit, 50),
                ),
                settings=settings,
            )
            for item in result["items"]:
                haystack = " ".join(
                    str(item.get(key) or "")
                    for key in ("title", "summary", "report_date", "status")
                ).casefold()
                if query in haystack:
                    hits.append(
                        {
                            "reference": f"daily_reports:report:{project_id}.{item['report_id']}",
                            "domain": "daily_reports",
                            "record_type": "daily_report",
                            "title": item.get("title")
                            or f"Daily Report {item.get('report_date')}",
                            "snippet": (
                                f"{item.get('report_date') or ''} · "
                                f"{item.get('status') or ''}"
                            ),
                            "project_id": project_id,
                            "product_url": item.get("product_url"),
                        }
                    )
    return hits[:100]


async def fetch_phase4(
    db: AsyncSession,
    request: McpFetchRequest,
    *,
    settings: Settings,
) -> dict[str, Any] | None:
    domain, record_type, opaque_id = request.reference.split(":", 2)
    project_part, separator, record_id = opaque_id.partition(".")
    if domain not in {"inspection", "daily_reports"}:
        return None
    if not separator:
        raise McpInvalidInput("Invalid project operation reference.")
    try:
        project_id = UUID(project_part)
    except ValueError as exc:
        raise McpInvalidInput("Invalid project operation reference.") from exc
    if (
        domain == "inspection"
        and record_type == "item"
        and not request.version
        and not request.as_of
    ):
        return await get_inspection_item(
            db,
            McpInspectionRequest(**_principal(request), project_id=project_id, item_id=record_id),
            settings=settings,
        )
    if domain == "daily_reports" and record_type == "report" and request.as_of is None:
        return await get_daily_report(
            db,
            McpDailyReportRequest(
                **_principal(request), report_id=record_id, version=request.version
            ),
            settings=settings,
        )
    raise McpNotFoundOrForbidden
