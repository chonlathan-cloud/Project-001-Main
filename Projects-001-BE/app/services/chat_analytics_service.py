"""
Intent-based analytics layer for Chat AI.

This service classifies the user's question into a supported strategic intent,
parses lightweight time filters, aggregates grounded metrics from the live
database, and produces a structured response that the chat endpoint can return
directly or hand to an LLM for optional polishing.
"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.models.boq import BOQItem, Project
from app.models.finance import Installment, Transaction
from app.models.input_request import InputRequest

PENDING_INSTALLMENT_STATUSES = {"PENDING", "PENDING_ADMIN", "ADVANCE"}
OPEN_RECEIVABLE_STATUSES = {"PENDING", "PENDING_ADMIN", "ADVANCE", "BILLING", "RE-BILLING"}
OPEN_OVERDUE_EXCLUDED_STATUSES = {"APPROVED", "PAID", "ACCEPT"}
APPROVED_INPUT_STATUSES = {"APPROVED", "PAID"}

INTENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "budget_risk": (
        "budget risk",
        "cost overrun",
        "over budget",
        "budget",
        "variance",
        "margin",
        "งบ",
        "บานปลาย",
        "เกินงบ",
        "risk",
        "ต้นทุน",
        "กำไร",
    ),
    "cash_flow": (
        "cash flow",
        "liquidity",
        "working capital",
        "สภาพคล่อง",
        "กระแสเงินสด",
        "รายรับ",
        "รายจ่าย",
        "เงินสด",
    ),
    "overdue": (
        "overdue",
        "past due",
        "collection",
        "aging",
        "due date",
        "ค้าง",
        "เกินกำหนด",
        "เลยกำหนด",
        "เร่ง",
        "หนี้",
    ),
    "material_vs_labor": (
        "material",
        "labor",
        "materials",
        "wages",
        "ค่าแรง",
        "ค่าวัสดุ",
        "วัสดุ",
        "แรงงาน",
    ),
    "pending_approval": (
        "pending approval",
        "approval queue",
        "approval",
        "approve",
        "review queue",
        "pending",
        "อนุมัติ",
        "รออนุมัติ",
        "คิว",
        "review",
    ),
    "subcontractor_performance": (
        "subcontractor",
        "contractor",
        "performer",
        "best performer",
        "performance",
        "supplier",
        "vendor performance",
        "ผู้รับเหมา",
        "ผลงาน",
        "ประสิทธิภาพ",
        "รายไหนดีกว่า",
    ),
    "duplicate_risk": (
        "duplicate",
        "double count",
        "double payment",
        "repeat receipt",
        "ซ้ำ",
        "บิลซ้ำ",
        "จ่ายซ้ำ",
        "duplicate risk",
    ),
}

ENGLISH_MONTH_LOOKUP: dict[str, int] = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}

THAI_MONTH_LOOKUP: dict[str, int] = {
    "มกราคม": 1,
    "ม.ค.": 1,
    "มค": 1,
    "กุมภาพันธ์": 2,
    "ก.พ.": 2,
    "กพ": 2,
    "มีนาคม": 3,
    "มี.ค.": 3,
    "มีค": 3,
    "เมษายน": 4,
    "เม.ย.": 4,
    "เมย": 4,
    "พฤษภาคม": 5,
    "พ.ค.": 5,
    "พค": 5,
    "มิถุนายน": 6,
    "มิ.ย.": 6,
    "มิย": 6,
    "กรกฎาคม": 7,
    "ก.ค.": 7,
    "กค": 7,
    "สิงหาคม": 8,
    "ส.ค.": 8,
    "สค": 8,
    "กันยายน": 9,
    "ก.ย.": 9,
    "กย": 9,
    "ตุลาคม": 10,
    "ต.ค.": 10,
    "ตค": 10,
    "พฤศจิกายน": 11,
    "พ.ย.": 11,
    "พย": 11,
    "ธันวาคม": 12,
    "ธ.ค.": 12,
    "ธค": 12,
}

CUSTOM_RANGE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"(?:between|from|ระหว่าง)\s*(\d{4}-\d{2}-\d{2})\s*(?:and|to|until|ถึง)\s*(\d{4}-\d{2}-\d{2})"
    ),
    re.compile(r"(\d{4}-\d{2}-\d{2})\s*(?:and|to|until|ถึง)\s*(\d{4}-\d{2}-\d{2})"),
)
QUARTER_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bq([1-4])\s*[-/]?\s*(20\d{2})\b"),
    re.compile(r"ไตรมาส\s*([1-4])\s*(?:ปี)?\s*(20\d{2})"),
)
ENGLISH_MONTH_PATTERN = re.compile(
    r"\b("
    + "|".join(sorted((re.escape(name) for name in ENGLISH_MONTH_LOOKUP), key=len, reverse=True))
    + r")\.?\s+(20\d{2})\b"
)
THAI_MONTH_PATTERN = re.compile(
    "("
    + "|".join(sorted((re.escape(name) for name in THAI_MONTH_LOOKUP), key=len, reverse=True))
    + r")\s*(20\d{2})"
)


@dataclass
class TimeScope:
    key: str
    label: str
    start: date
    end: date


@dataclass
class ChatAnalyticsSnapshot:
    projects: list[Project]
    boq_items: list[BOQItem]
    leaf_boq_items: list[BOQItem]
    installments: list[Installment]
    transactions: list[Transaction]
    input_requests: list[InputRequest]
    project_by_id: dict[UUID, Project]
    boq_item_by_id: dict[UUID, BOQItem]
    installment_by_id: dict[UUID, Installment]
    project_name: str | None


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _to_float(value: object) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _format_currency(value: float) -> str:
    return f"{value:,.2f} THB"


def _format_percent(value: float) -> str:
    return f"{value:.1f}%"


def _safe_divide(numerator: float, denominator: float) -> float:
    if not denominator:
        return 0.0
    return numerator / denominator


def _display_date(value: date | datetime | None) -> str:
    if value is None:
        return "-"
    if isinstance(value, datetime):
        return value.date().isoformat()
    return value.isoformat()


def _normalize_name(value: str | None, fallback: str = "Unknown") -> str:
    cleaned = str(value or "").strip()
    return cleaned or fallback


def _normalize_optional_name(value: str | None) -> str | None:
    cleaned = str(value or "").strip()
    return cleaned or None


def _effective_request_amount(request: InputRequest) -> float:
    if request.approved_amount is not None:
        return _to_float(request.approved_amount)
    return _to_float(request.amount)


def _detect_intent(message: str) -> str:
    normalized = f" {message.lower()} "
    scores: dict[str, int] = {intent: 0 for intent in INTENT_KEYWORDS}

    for intent, keywords in INTENT_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in normalized:
                scores[intent] += max(1, len(keyword.split()))

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    if ranked and ranked[0][1] > 0:
        return ranked[0][0]

    return "general_overview"


def _month_end(year: int, month: int) -> date:
    return date(year, month, calendar.monthrange(year, month)[1])


def _parse_iso_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _parse_custom_range_scope(message: str) -> TimeScope | None:
    for pattern in CUSTOM_RANGE_PATTERNS:
        match = pattern.search(message)
        if not match:
            continue
        start = _parse_iso_date(match.group(1))
        end = _parse_iso_date(match.group(2))
        if start is None or end is None:
            continue
        if end < start:
            start, end = end, start
        return TimeScope(
            key="custom_range",
            label=f"{start.isoformat()} to {end.isoformat()}",
            start=start,
            end=end,
        )
    return None


def _parse_quarter_scope(message: str) -> TimeScope | None:
    for pattern in QUARTER_PATTERNS:
        match = pattern.search(message)
        if not match:
            continue
        quarter = int(match.group(1))
        year = int(match.group(2))
        start_month = ((quarter - 1) * 3) + 1
        start = date(year, start_month, 1)
        end = _month_end(year, start_month + 2)
        return TimeScope(
            key=f"q{quarter}_{year}",
            label=f"Q{quarter} {year}",
            start=start,
            end=end,
        )
    return None


def _parse_named_month_scope(message: str) -> TimeScope | None:
    english_match = ENGLISH_MONTH_PATTERN.search(message)
    if english_match:
        month_value = ENGLISH_MONTH_LOOKUP.get(english_match.group(1).rstrip(".").lower())
        year = int(english_match.group(2))
        if month_value:
            start = date(year, month_value, 1)
            end = _month_end(year, month_value)
            return TimeScope(
                key=f"{year}-{month_value:02d}",
                label=f"{calendar.month_abbr[month_value]} {year}",
                start=start,
                end=end,
            )

    thai_match = THAI_MONTH_PATTERN.search(message)
    if thai_match:
        month_value = THAI_MONTH_LOOKUP.get(thai_match.group(1))
        year = int(thai_match.group(2))
        if month_value:
            start = date(year, month_value, 1)
            end = _month_end(year, month_value)
            return TimeScope(
                key=f"{year}-{month_value:02d}",
                label=f"{thai_match.group(1)} {year}",
                start=start,
                end=end,
            )

    return None


def _parse_time_scope(message: str) -> TimeScope | None:
    normalized = message.lower()
    today = _today()
    month_start = today.replace(day=1)
    quarter_start_month = ((today.month - 1) // 3) * 3 + 1
    quarter_start = date(today.year, quarter_start_month, 1)
    year_start = date(today.year, 1, 1)

    previous_month_end = month_start - timedelta(days=1)
    previous_month_start = previous_month_end.replace(day=1)

    custom_range_scope = _parse_custom_range_scope(normalized)
    if custom_range_scope is not None:
        return custom_range_scope

    quarter_scope = _parse_quarter_scope(normalized)
    if quarter_scope is not None:
        return quarter_scope

    named_month_scope = _parse_named_month_scope(normalized)
    if named_month_scope is not None:
        return named_month_scope

    if any(keyword in normalized for keyword in ("last 30 days", "past 30 days", "30 วันที่ผ่านมา", "30 วันล่าสุด")):
        return TimeScope(
            key="last_30_days",
            label="Last 30 Days",
            start=today - timedelta(days=29),
            end=today,
        )

    if any(keyword in normalized for keyword in ("this quarter", "current quarter", "ไตรมาสนี้")):
        return TimeScope(
            key="this_quarter",
            label="This Quarter",
            start=quarter_start,
            end=today,
        )

    if any(keyword in normalized for keyword in ("this month", "current month", "เดือนนี้")):
        return TimeScope(
            key="this_month",
            label="This Month",
            start=month_start,
            end=today,
        )

    if any(keyword in normalized for keyword in ("last month", "previous month", "เดือนที่แล้ว")):
        return TimeScope(
            key="last_month",
            label="Last Month",
            start=previous_month_start,
            end=previous_month_end,
        )

    if any(keyword in normalized for keyword in ("this year", "ปีนี้")):
        return TimeScope(
            key="this_year",
            label="This Year",
            start=year_start,
            end=today,
        )

    if any(keyword in normalized for keyword in ("today", "วันนี้")):
        return TimeScope(
            key="today",
            label="Today",
            start=today,
            end=today,
        )

    return None


def _value_in_scope(value: date | datetime | None, time_scope: TimeScope | None) -> bool:
    if time_scope is None:
        return True
    if value is None:
        return False
    scoped_value = value.date() if isinstance(value, datetime) else value
    return time_scope.start <= scoped_value <= time_scope.end


def _request_operational_name(request: InputRequest) -> str:
    return _normalize_name(request.requester_name or request.vendor_name)


def _request_actor_id(request: InputRequest) -> str | None:
    return _normalize_optional_name(request.subcontractor_id)


def _installment_actor_id(installment: Installment) -> str | None:
    return _normalize_optional_name(installment.subcontractor_id)


def _transaction_actor_id(
    transaction: Transaction,
    installment: Installment | None,
) -> str | None:
    return _normalize_optional_name(transaction.subcontractor_id) or (
        _installment_actor_id(installment) if installment is not None else None
    )


def _actor_group_key(actor_id: str | None, actor_name: str) -> str:
    return actor_id or f"name::{actor_name.lower()}"


def _actor_display_name(actor_id: str | None, actor_name: str | None) -> str:
    if actor_name:
        return actor_name
    if actor_id:
        return actor_id
    return "Unknown Actor"


def _request_project_name(request: InputRequest, snapshot: ChatAnalyticsSnapshot) -> str:
    project = snapshot.project_by_id.get(request.project_id)
    return project.name if project else "Unknown Project"


async def _load_snapshot(
    db: AsyncSession,
    project_id: UUID | None,
) -> ChatAnalyticsSnapshot:
    projects_query = select(Project).options(noload("*")).order_by(Project.name.asc())
    if project_id is not None:
        projects_query = projects_query.filter(Project.id == project_id)
    projects = (await db.execute(projects_query)).scalars().all()

    project_by_id = {project.id: project for project in projects}
    scoped_project_ids = set(project_by_id.keys())

    if project_id is not None and not scoped_project_ids:
        return ChatAnalyticsSnapshot(
            projects=[],
            boq_items=[],
            leaf_boq_items=[],
            installments=[],
            transactions=[],
            input_requests=[],
            project_by_id={},
            boq_item_by_id={},
            installment_by_id={},
            project_name=None,
        )

    boq_query = select(BOQItem).options(noload("*")).filter(BOQItem.valid_to.is_(None))
    if scoped_project_ids:
        boq_query = boq_query.filter(BOQItem.project_id.in_(scoped_project_ids))
    boq_items = (await db.execute(boq_query)).scalars().all()
    boq_item_by_id = {item.id: item for item in boq_items}
    parent_ids = {item.parent_id for item in boq_items if item.parent_id is not None}
    leaf_boq_items = [item for item in boq_items if item.id not in parent_ids]

    installments_query = (
        select(Installment)
        .join(BOQItem, Installment.boq_item_id == BOQItem.id)
        .options(noload("*"))
        .filter(BOQItem.valid_to.is_(None))
    )
    if scoped_project_ids:
        installments_query = installments_query.filter(BOQItem.project_id.in_(scoped_project_ids))
    installments = (await db.execute(installments_query)).scalars().all()
    installment_by_id = {item.id: item for item in installments}

    transactions_query = (
        select(Transaction)
        .join(Installment, Transaction.installment_id == Installment.id)
        .join(BOQItem, Installment.boq_item_id == BOQItem.id)
        .options(noload("*"))
        .filter(BOQItem.valid_to.is_(None))
    )
    if scoped_project_ids:
        transactions_query = transactions_query.filter(BOQItem.project_id.in_(scoped_project_ids))
    transactions = (await db.execute(transactions_query)).scalars().all()

    input_query = select(InputRequest).options(noload("*")).order_by(InputRequest.created_at.desc())
    if project_id is not None:
        input_query = input_query.filter(InputRequest.project_id == project_id)
    input_requests = (await db.execute(input_query)).scalars().all()

    project_name = projects[0].name if project_id is not None and projects else None

    return ChatAnalyticsSnapshot(
        projects=projects,
        boq_items=boq_items,
        leaf_boq_items=leaf_boq_items,
        installments=installments,
        transactions=transactions,
        input_requests=input_requests,
        project_by_id=project_by_id,
        boq_item_by_id=boq_item_by_id,
        installment_by_id=installment_by_id,
        project_name=project_name,
    )


def _build_project_rollups(
    snapshot: ChatAnalyticsSnapshot,
    time_scope: TimeScope | None,
) -> dict[UUID, dict]:
    today = _today()
    rollups: dict[UUID, dict] = {}

    for project in snapshot.projects:
        rollups[project.id] = {
            "project_id": str(project.id),
            "project_name": project.name,
            "customer_boq_total": 0.0,
            "subcontractor_boq_total": 0.0,
            "material_boq_total": 0.0,
            "labor_boq_total": 0.0,
            "transaction_cost": 0.0,
            "approved_expense_requests": 0.0,
            "approved_income_requests": 0.0,
            "approved_material_requests": 0.0,
            "approved_labor_requests": 0.0,
            "pending_request_amount": 0.0,
            "pending_request_count": 0,
            "pending_installment_amount": 0.0,
            "pending_installment_count": 0,
            "draft_request_count": 0,
            "duplicate_pending_count": 0,
            "scheduled_open_inflow": 0.0,
            "overdue_amount": 0.0,
            "overdue_count": 0,
            "oldest_overdue_date": None,
            "contingency_budget": _to_float(project.contingency_budget),
        }

    for item in snapshot.leaf_boq_items:
        project_rollup = rollups.get(item.project_id)
        if project_rollup is None:
            continue

        grand_total = _to_float(item.grand_total)
        project_rollup["material_boq_total"] += _to_float(item.total_material)
        project_rollup["labor_boq_total"] += _to_float(item.total_labor)

        if (item.boq_type or "").upper() == "SUBCONTRACTOR":
            project_rollup["subcontractor_boq_total"] += grand_total
        else:
            project_rollup["customer_boq_total"] += grand_total

    for installment in snapshot.installments:
        boq_item = snapshot.boq_item_by_id.get(installment.boq_item_id)
        if boq_item is None:
            continue
        project_rollup = rollups.get(boq_item.project_id)
        if project_rollup is None:
            continue

        amount = _to_float(installment.amount)
        status = (installment.status or "").upper()
        due_date = installment.due_date
        in_scope = _value_in_scope(due_date, time_scope)
        is_open_receivable = due_date is not None and status in OPEN_RECEIVABLE_STATUSES
        is_overdue = (
            due_date is not None
            and (bool(installment.is_overdue) or due_date < today)
            and status not in OPEN_OVERDUE_EXCLUDED_STATUSES
        )

        if status in PENDING_INSTALLMENT_STATUSES and in_scope:
            project_rollup["pending_installment_amount"] += amount
            project_rollup["pending_installment_count"] += 1

        if is_open_receivable and in_scope:
            project_rollup["scheduled_open_inflow"] += amount

        if is_overdue and in_scope:
            project_rollup["overdue_amount"] += amount
            project_rollup["overdue_count"] += 1
            oldest_date = project_rollup["oldest_overdue_date"]
            if oldest_date is None or due_date < oldest_date:
                project_rollup["oldest_overdue_date"] = due_date

    for transaction in snapshot.transactions:
        if not _value_in_scope(transaction.approved_at, time_scope):
            continue
        installment = snapshot.installment_by_id.get(transaction.installment_id)
        if installment is None:
            continue
        boq_item = snapshot.boq_item_by_id.get(installment.boq_item_id)
        if boq_item is None:
            continue
        project_rollup = rollups.get(boq_item.project_id)
        if project_rollup is None:
            continue
        project_rollup["transaction_cost"] += _to_float(transaction.base_amount)

    for request in snapshot.input_requests:
        project_rollup = rollups.get(request.project_id)
        if project_rollup is None:
            continue

        amount = _effective_request_amount(request)
        status = (request.status or "").upper()
        entry_type = (request.entry_type or "").upper()
        request_type = (request.request_type or "").strip()
        created_in_scope = _value_in_scope(request.created_at, time_scope)
        approved_in_scope = _value_in_scope(request.paid_at or request.approved_at, time_scope)

        if status in APPROVED_INPUT_STATUSES and approved_in_scope:
            if entry_type == "INCOME":
                project_rollup["approved_income_requests"] += amount
            else:
                project_rollup["approved_expense_requests"] += amount
                if request_type == "ค่าวัสดุ":
                    project_rollup["approved_material_requests"] += amount
                elif request_type == "ค่าแรง":
                    project_rollup["approved_labor_requests"] += amount

        if status == "PENDING_ADMIN" and created_in_scope:
            project_rollup["pending_request_amount"] += amount
            project_rollup["pending_request_count"] += 1
            if bool(request.is_duplicate_flag):
                project_rollup["duplicate_pending_count"] += 1

        if status == "DRAFT" and created_in_scope:
            project_rollup["draft_request_count"] += 1

    for project_rollup in rollups.values():
        budget_baseline = (
            project_rollup["subcontractor_boq_total"]
            or project_rollup["customer_boq_total"]
            or project_rollup["contingency_budget"]
        )
        actual_cost = project_rollup["transaction_cost"] + project_rollup["approved_expense_requests"]
        project_rollup["budget_baseline"] = budget_baseline
        project_rollup["actual_cost"] = actual_cost
        project_rollup["burn_ratio"] = _safe_divide(actual_cost, budget_baseline)
        project_rollup["cash_inflow_total"] = (
            project_rollup["scheduled_open_inflow"] + project_rollup["approved_income_requests"]
        )
        project_rollup["cash_outflow_total"] = actual_cost
        project_rollup["cash_position"] = (
            project_rollup["cash_inflow_total"] - project_rollup["cash_outflow_total"]
        )
        project_rollup["pending_outflow"] = (
            project_rollup["pending_request_amount"] + project_rollup["pending_installment_amount"]
        )

    return rollups


def _project_source(project_rollup: dict, *, description: str, score: float | None = None) -> dict:
    return {
        "id": project_rollup["project_id"],
        "label": project_rollup["project_name"],
        "description": description,
        "project_id": project_rollup["project_id"],
        "score": score,
    }


def _scope_text(time_scope: TimeScope | None) -> str:
    return time_scope.label if time_scope is not None else "All Time"


def _build_general_overview(
    snapshot: ChatAnalyticsSnapshot,
    project_rollups: dict[UUID, dict],
    time_scope: TimeScope | None,
) -> dict:
    total_budget = sum(item["budget_baseline"] for item in project_rollups.values())
    actual_cost = sum(item["actual_cost"] for item in project_rollups.values())
    pending_amount = sum(item["pending_outflow"] for item in project_rollups.values())
    overdue_amount = sum(item["overdue_amount"] for item in project_rollups.values())
    risk_projects = [
        item for item in project_rollups.values() if item["budget_baseline"] > 0 and item["burn_ratio"] >= 0.85
    ]
    top_risk = max(project_rollups.values(), key=lambda item: item["burn_ratio"], default=None)
    scope_label = _scope_text(time_scope)

    if total_budget <= 0 and actual_cost <= 0 and pending_amount <= 0:
        summary = f"There is not enough financial data in the current workspace to build a {scope_label.lower()} overview yet."
    elif top_risk and top_risk["budget_baseline"] > 0:
        summary = (
            f"{scope_label} overview shows {_format_currency(actual_cost)} of committed cost "
            f"against {_format_currency(total_budget)} baseline. {top_risk['project_name']} is currently "
            f"the most stretched project at {_format_percent(top_risk['burn_ratio'] * 100)} of baseline."
        )
    else:
        summary = (
            f"{scope_label} overview shows {_format_currency(actual_cost)} of committed cost "
            f"with {_format_currency(pending_amount)} still in the approval queue."
        )

    sources = [
        _project_source(
            item,
            description=(
                f"Burn ratio {_format_percent(item['burn_ratio'] * 100)} with pending outflow "
                f"{_format_currency(item['pending_outflow'])}"
            ),
            score=item["burn_ratio"],
        )
        for item in sorted(project_rollups.values(), key=lambda current: current["burn_ratio"], reverse=True)[:5]
    ]

    return {
        "intent": "general_overview",
        "summary": summary,
        "metrics": [
            {"label": "Time Scope", "value": scope_label},
            {"label": "Budget Baseline", "value": _format_currency(total_budget)},
            {"label": "Committed Cost", "value": _format_currency(actual_cost)},
            {"label": "Pending Queue", "value": _format_currency(pending_amount)},
            {"label": "Overdue Exposure", "value": _format_currency(overdue_amount)},
            {"label": "Projects At Risk", "value": str(len(risk_projects))},
        ],
        "next_actions": [
            "Review the project with the highest burn ratio before approving more spend.",
            "Check pending approvals and overdue receivables to tighten the near-term cash position.",
        ],
        "sources": sources,
        "context_item_count": (
            len(snapshot.projects)
            + len(snapshot.transactions)
            + len(snapshot.input_requests)
            + len(snapshot.installments)
        ),
    }


def _build_budget_risk(
    snapshot: ChatAnalyticsSnapshot,
    project_rollups: dict[UUID, dict],
    time_scope: TimeScope | None,
) -> dict:
    candidate_projects = [item for item in project_rollups.values() if item["budget_baseline"] > 0]
    total_budget = sum(item["budget_baseline"] for item in candidate_projects)
    total_actual = sum(item["actual_cost"] for item in candidate_projects)
    total_pending = sum(item["pending_outflow"] for item in candidate_projects)
    overall_burn = _safe_divide(total_actual, total_budget)
    ranked = sorted(candidate_projects, key=lambda item: item["burn_ratio"], reverse=True)
    top_project = ranked[0] if ranked else None
    projects_at_risk = [item for item in candidate_projects if item["burn_ratio"] >= 0.85]
    scope_label = _scope_text(time_scope)

    if not ranked:
        summary = f"There is not enough BOQ baseline data to assess {scope_label.lower()} budget risk yet."
    elif top_project["burn_ratio"] >= 1:
        summary = (
            f"{scope_label} budget risk is critical. {top_project['project_name']} has already consumed "
            f"{_format_percent(top_project['burn_ratio'] * 100)} of its baseline "
            f"({_format_currency(top_project['actual_cost'])} of {_format_currency(top_project['budget_baseline'])})."
        )
    elif top_project["burn_ratio"] >= 0.85:
        summary = (
            f"{scope_label} budget risk is elevated. {top_project['project_name']} is at "
            f"{_format_percent(top_project['burn_ratio'] * 100)} of baseline and the wider portfolio is at "
            f"{_format_percent(overall_burn * 100)}."
        )
    else:
        summary = (
            f"{scope_label} budget burn remains under control at {_format_percent(overall_burn * 100)} "
            f"of baseline, although {top_project['project_name']} is the closest project to its limit."
        )

    sources = [
        _project_source(
            item,
            description=(
                f"Actual {_format_currency(item['actual_cost'])} vs baseline {_format_currency(item['budget_baseline'])}. "
                f"Pending outflow {_format_currency(item['pending_outflow'])}."
            ),
            score=item["burn_ratio"],
        )
        for item in ranked[:5]
    ]

    next_actions = []
    if top_project is not None:
        next_actions.append(
            f"Review cost drivers and pending approvals for {top_project['project_name']} before new spend is approved."
        )
    if total_pending > 0:
        next_actions.append(
            f"Reconcile {_format_currency(total_pending)} of pending outflow against available budget headroom."
        )
    if not next_actions:
        next_actions.append("Continue monitoring burn ratio as more actual-cost data lands in transactions.")

    return {
        "intent": "budget_risk",
        "summary": summary,
        "metrics": [
            {"label": "Time Scope", "value": scope_label},
            {"label": "Budget Baseline", "value": _format_currency(total_budget)},
            {"label": "Committed Cost", "value": _format_currency(total_actual)},
            {"label": "Portfolio Burn", "value": _format_percent(overall_burn * 100)},
            {"label": "Projects At Risk", "value": str(len(projects_at_risk))},
            {"label": "Pending Outflow", "value": _format_currency(total_pending)},
        ],
        "next_actions": next_actions,
        "sources": sources,
        "context_item_count": len(candidate_projects) + len(snapshot.transactions) + len(snapshot.input_requests),
    }


def _build_cash_flow(
    snapshot: ChatAnalyticsSnapshot,
    project_rollups: dict[UUID, dict],
    time_scope: TimeScope | None,
) -> dict:
    scheduled_inflow = sum(item["scheduled_open_inflow"] for item in project_rollups.values())
    supplemental_income = sum(item["approved_income_requests"] for item in project_rollups.values())
    committed_outflow = sum(item["cash_outflow_total"] for item in project_rollups.values())
    pending_outflow = sum(item["pending_outflow"] for item in project_rollups.values())
    overdue_inflow = sum(item["overdue_amount"] for item in project_rollups.values())
    net_position = scheduled_inflow + supplemental_income - committed_outflow
    stressed_projects = sorted(project_rollups.values(), key=lambda item: item["cash_position"])
    top_stress = stressed_projects[0] if stressed_projects else None
    scope_label = _scope_text(time_scope)

    if scheduled_inflow <= 0 and committed_outflow <= 0 and supplemental_income <= 0:
        summary = f"There is not enough receivable and transaction data to assess {scope_label.lower()} cash flow yet."
    elif net_position < 0:
        summary = (
            f"{scope_label} cash flow looks tight. Open inflow totals {_format_currency(scheduled_inflow + supplemental_income)} "
            f"against committed outflow of {_format_currency(committed_outflow)}, leaving a gap of "
            f"{_format_currency(abs(net_position))} before considering pending approvals."
        )
    else:
        summary = (
            f"{scope_label} cash flow is positive on the current dataset with {_format_currency(net_position)} net coverage, "
            f"but {_format_currency(pending_outflow)} still sits in the approval queue."
        )

    if top_stress is not None and top_stress["cash_position"] < 0:
        summary = f"{summary} {top_stress['project_name']} is the most stretched project from a cash perspective."

    sources = [
        _project_source(
            item,
            description=(
                f"Inflow {_format_currency(item['cash_inflow_total'])}, outflow {_format_currency(item['cash_outflow_total'])}, "
                f"pending {_format_currency(item['pending_outflow'])}."
            ),
            score=item["cash_position"],
        )
        for item in sorted(project_rollups.values(), key=lambda current: current["cash_position"])[:5]
    ]

    next_actions = [
        "Prioritise overdue collections before releasing lower-priority approvals.",
        "Use pending approval totals as the immediate pressure test for near-term liquidity.",
    ]
    if pending_outflow > 0:
        next_actions[1] = f"Reassess {_format_currency(pending_outflow)} of pending outflow before it converts into cash-out."

    return {
        "intent": "cash_flow",
        "summary": summary,
        "metrics": [
            {"label": "Time Scope", "value": scope_label},
            {"label": "Open Inflow", "value": _format_currency(scheduled_inflow)},
            {"label": "Approved Income", "value": _format_currency(supplemental_income)},
            {"label": "Committed Outflow", "value": _format_currency(committed_outflow)},
            {"label": "Pending Outflow", "value": _format_currency(pending_outflow)},
            {"label": "Net Position", "value": _format_currency(net_position)},
            {"label": "Overdue Inflow", "value": _format_currency(overdue_inflow)},
        ],
        "next_actions": next_actions,
        "sources": sources,
        "context_item_count": len(snapshot.installments) + len(snapshot.transactions) + len(snapshot.input_requests),
    }


def _build_overdue(
    snapshot: ChatAnalyticsSnapshot,
    project_rollups: dict[UUID, dict],
    time_scope: TimeScope | None,
) -> dict:
    today = _today()
    overdue_items: list[dict] = []

    for installment in snapshot.installments:
        boq_item = snapshot.boq_item_by_id.get(installment.boq_item_id)
        project = snapshot.project_by_id.get(boq_item.project_id) if boq_item else None
        if boq_item is None or project is None or installment.due_date is None:
            continue

        status = (installment.status or "").upper()
        if status in OPEN_OVERDUE_EXCLUDED_STATUSES:
            continue
        if not _value_in_scope(installment.due_date, time_scope):
            continue

        is_overdue = bool(installment.is_overdue) or installment.due_date < today
        if not is_overdue:
            continue

        overdue_items.append(
            {
                "installment_id": str(installment.id),
                "installment_no": installment.installment_no or "-",
                "project_id": str(project.id),
                "project_name": project.name,
                "due_date": installment.due_date,
                "days_overdue": max((today - installment.due_date).days, 0),
                "amount": _to_float(installment.amount),
            }
        )

    overdue_items.sort(key=lambda item: (item["days_overdue"], item["amount"]), reverse=True)
    total_amount = sum(item["amount"] for item in overdue_items)
    affected_projects = len({item["project_id"] for item in overdue_items})
    oldest_days = overdue_items[0]["days_overdue"] if overdue_items else 0
    scope_label = _scope_text(time_scope)

    if not overdue_items:
        summary = f"There are no overdue receivable items in {scope_label.lower()}."
    else:
        top_item = overdue_items[0]
        summary = (
            f"{scope_label} overdue exposure totals {_format_currency(total_amount)} across {len(overdue_items)} items. "
            f"The oldest item is installment {top_item['installment_no']} in {top_item['project_name']}, "
            f"currently {top_item['days_overdue']} days overdue."
        )

    sources = [
        {
            "id": item["installment_id"],
            "label": f"{item['project_name']} · {item['installment_no']}",
            "description": (
                f"Due {_display_date(item['due_date'])}, {item['days_overdue']} days overdue, "
                f"amount {_format_currency(item['amount'])}"
            ),
            "project_id": item["project_id"],
            "score": float(item["days_overdue"]),
        }
        for item in overdue_items[:5]
    ]

    return {
        "intent": "overdue",
        "summary": summary,
        "metrics": [
            {"label": "Time Scope", "value": scope_label},
            {"label": "Overdue Amount", "value": _format_currency(total_amount)},
            {"label": "Overdue Items", "value": str(len(overdue_items))},
            {"label": "Affected Projects", "value": str(affected_projects)},
            {"label": "Oldest Delay", "value": f"{oldest_days} days"},
        ],
        "next_actions": [
            "Escalate the oldest overdue items first because they block near-term inflow the longest.",
            "Check whether any overdue project also has high pending outflow before approving more cost.",
        ],
        "sources": sources,
        "context_item_count": len(overdue_items),
    }


def _build_material_vs_labor(
    snapshot: ChatAnalyticsSnapshot,
    project_rollups: dict[UUID, dict],
    time_scope: TimeScope | None,
) -> dict:
    boq_material = sum(item["material_boq_total"] for item in project_rollups.values())
    boq_labor = sum(item["labor_boq_total"] for item in project_rollups.values())
    approved_material = sum(item["approved_material_requests"] for item in project_rollups.values())
    approved_labor = sum(item["approved_labor_requests"] for item in project_rollups.values())
    uncategorized_expense = sum(
        max(item["approved_expense_requests"] - item["approved_material_requests"] - item["approved_labor_requests"], 0)
        for item in project_rollups.values()
    )
    total_boq_split = boq_material + boq_labor
    material_share = _safe_divide(boq_material, total_boq_split)
    labor_share = _safe_divide(boq_labor, total_boq_split)
    scope_label = _scope_text(time_scope)

    if total_boq_split <= 0 and approved_material <= 0 and approved_labor <= 0:
        summary = f"There is not enough classified material and labor data to compare the split in {scope_label.lower()}."
    else:
        summary = (
            f"BOQ baseline is weighted {_format_percent(material_share * 100)} material and "
            f"{_format_percent(labor_share * 100)} labor. In {scope_label.lower()}, approved expense requests show "
            f"{_format_currency(approved_material)} tagged as material and {_format_currency(approved_labor)} tagged as labor."
        )
        if uncategorized_expense > 0:
            summary = f"{summary} {_format_currency(uncategorized_expense)} of approved expense requests are still uncategorized."

    ranked = sorted(
        project_rollups.values(),
        key=lambda item: item["material_boq_total"] + item["labor_boq_total"],
        reverse=True,
    )
    sources = [
        _project_source(
            item,
            description=(
                f"BOQ material {_format_currency(item['material_boq_total'])}, labor {_format_currency(item['labor_boq_total'])}. "
                f"Approved requests material {_format_currency(item['approved_material_requests'])}, labor {_format_currency(item['approved_labor_requests'])}."
            ),
            score=item["material_boq_total"] + item["labor_boq_total"],
        )
        for item in ranked[:5]
    ]

    next_actions = [
        "Validate that high-value expense requests are tagged correctly as material or labor before approval.",
    ]
    if uncategorized_expense > 0:
        next_actions.append(
            f"Backfill request_type for {_format_currency(uncategorized_expense)} of approved expense requests to improve actual split reporting."
        )

    return {
        "intent": "material_vs_labor",
        "summary": summary,
        "metrics": [
            {"label": "Time Scope", "value": scope_label},
            {"label": "BOQ Material", "value": _format_currency(boq_material)},
            {"label": "BOQ Labor", "value": _format_currency(boq_labor)},
            {"label": "Material Share", "value": _format_percent(material_share * 100)},
            {"label": "Approved Material", "value": _format_currency(approved_material)},
            {"label": "Approved Labor", "value": _format_currency(approved_labor)},
            {"label": "Uncategorized", "value": _format_currency(uncategorized_expense)},
        ],
        "next_actions": next_actions,
        "sources": sources,
        "context_item_count": len(snapshot.leaf_boq_items) + len(snapshot.input_requests),
    }


def _build_pending_approval(
    snapshot: ChatAnalyticsSnapshot,
    project_rollups: dict[UUID, dict],
    time_scope: TimeScope | None,
) -> dict:
    pending_requests = [
        item
        for item in snapshot.input_requests
        if (item.status or "").upper() == "PENDING_ADMIN" and _value_in_scope(item.created_at, time_scope)
    ]
    draft_requests = [
        item
        for item in snapshot.input_requests
        if (item.status or "").upper() == "DRAFT" and _value_in_scope(item.created_at, time_scope)
    ]
    pending_installments = [
        item
        for item in snapshot.installments
        if (item.status or "").upper() in PENDING_INSTALLMENT_STATUSES
        and _value_in_scope(item.due_date, time_scope)
    ]

    total_request_amount = sum(_effective_request_amount(item) for item in pending_requests)
    total_installment_amount = sum(_to_float(item.amount) for item in pending_installments)
    total_pending_amount = total_request_amount + total_installment_amount
    duplicate_pending = sum(1 for item in pending_requests if bool(item.is_duplicate_flag))
    top_project = max(project_rollups.values(), key=lambda item: item["pending_outflow"], default=None)
    scope_label = _scope_text(time_scope)

    if total_pending_amount <= 0 and not draft_requests:
        summary = f"There are no pending approvals in {scope_label.lower()}."
    else:
        summary = (
            f"{scope_label} approval queue holds {_format_currency(total_pending_amount)} across "
            f"{len(pending_requests)} input requests and {len(pending_installments)} installments."
        )
        if top_project is not None and top_project["pending_outflow"] > 0:
            summary = (
                f"{summary} {top_project['project_name']} carries the largest pending exposure at "
                f"{_format_currency(top_project['pending_outflow'])}."
            )
        if duplicate_pending > 0:
            summary = f"{summary} {duplicate_pending} pending requests are flagged as potential duplicates."

    sources = [
        _project_source(
            item,
            description=(
                f"Pending requests {item['pending_request_count']} / {_format_currency(item['pending_request_amount'])}, "
                f"pending installments {item['pending_installment_count']} / {_format_currency(item['pending_installment_amount'])}."
            ),
            score=item["pending_outflow"],
        )
        for item in sorted(project_rollups.values(), key=lambda current: current["pending_outflow"], reverse=True)[:5]
        if item["pending_outflow"] > 0 or item["draft_request_count"] > 0
    ]

    next_actions = [
        "Clear high-value pending approvals first because they convert into committed cash-out fastest.",
    ]
    if duplicate_pending > 0:
        next_actions.append(
            f"Review the {duplicate_pending} duplicate-flagged requests before approval to avoid double counting."
        )
    if draft_requests:
        next_actions.append(
            f"Resolve {len(draft_requests)} draft requests so they do not hide work outside the formal approval queue."
        )

    return {
        "intent": "pending_approval",
        "summary": summary,
        "metrics": [
            {"label": "Time Scope", "value": scope_label},
            {"label": "Pending Requests", "value": str(len(pending_requests))},
            {"label": "Pending Request Amount", "value": _format_currency(total_request_amount)},
            {"label": "Pending Installments", "value": str(len(pending_installments))},
            {"label": "Pending Installment Amount", "value": _format_currency(total_installment_amount)},
            {"label": "Draft Requests", "value": str(len(draft_requests))},
            {"label": "Duplicate Flags", "value": str(duplicate_pending)},
        ],
        "next_actions": next_actions,
        "sources": sources,
        "context_item_count": len(pending_requests) + len(pending_installments) + len(draft_requests),
    }


def _build_subcontractor_performance(
    snapshot: ChatAnalyticsSnapshot,
    _project_rollups: dict[UUID, dict],
    time_scope: TimeScope | None,
) -> dict:
    grouped: dict[str, dict] = {}

    for request in snapshot.input_requests:
        if not _value_in_scope(request.created_at, time_scope):
            continue

        actor_id = _request_actor_id(request)
        actor_name = _request_operational_name(request)
        actor_key = _actor_group_key(actor_id, actor_name)
        entry = grouped.setdefault(
            actor_key,
            {
                "actor_id": actor_id,
                "name": _actor_display_name(actor_id, actor_name),
                "submitted_count": 0,
                "approved_count": 0,
                "paid_count": 0,
                "rejected_count": 0,
                "pending_count": 0,
                "duplicate_count": 0,
                "finance_transaction_count": 0,
                "finance_transaction_amount": 0.0,
                "pending_installment_count": 0,
                "pending_installment_amount": 0.0,
                "approved_amount": 0.0,
                "submitted_amount": 0.0,
                "project_amounts": {},
            },
        )

        if actor_id and not entry["actor_id"]:
            entry["actor_id"] = actor_id
        if actor_name and (entry["name"] == "Unknown Actor" or entry["name"] == entry["actor_id"]):
            entry["name"] = actor_name

        amount = _effective_request_amount(request)
        status = (request.status or "").upper()
        project_name = _request_project_name(request, snapshot)

        entry["submitted_count"] += 1
        entry["submitted_amount"] += amount
        entry["project_amounts"][project_name] = entry["project_amounts"].get(project_name, 0.0) + amount

        if status in APPROVED_INPUT_STATUSES:
            entry["approved_count"] += 1
            entry["approved_amount"] += amount
            if status == "PAID":
                entry["paid_count"] += 1
        elif status == "REJECTED":
            entry["rejected_count"] += 1
        elif status == "PENDING_ADMIN":
            entry["pending_count"] += 1

        if bool(request.is_duplicate_flag):
            entry["duplicate_count"] += 1

    for installment in snapshot.installments:
        if not _value_in_scope(installment.due_date, time_scope):
            continue
        actor_id = _installment_actor_id(installment)
        if actor_id is None:
            continue
        actor_key = _actor_group_key(actor_id, actor_id)
        entry = grouped.setdefault(
            actor_key,
            {
                "actor_id": actor_id,
                "name": actor_id,
                "submitted_count": 0,
                "approved_count": 0,
                "paid_count": 0,
                "rejected_count": 0,
                "pending_count": 0,
                "duplicate_count": 0,
                "finance_transaction_count": 0,
                "finance_transaction_amount": 0.0,
                "pending_installment_count": 0,
                "pending_installment_amount": 0.0,
                "approved_amount": 0.0,
                "submitted_amount": 0.0,
                "project_amounts": {},
            },
        )

        if (installment.status or "").upper() in PENDING_INSTALLMENT_STATUSES:
            entry["pending_installment_count"] += 1
            entry["pending_installment_amount"] += _to_float(installment.amount)

    for transaction in snapshot.transactions:
        if not _value_in_scope(transaction.approved_at, time_scope):
            continue
        installment = snapshot.installment_by_id.get(transaction.installment_id)
        actor_id = _transaction_actor_id(transaction, installment)
        if actor_id is None:
            continue
        actor_key = _actor_group_key(actor_id, actor_id)
        entry = grouped.setdefault(
            actor_key,
            {
                "actor_id": actor_id,
                "name": actor_id,
                "submitted_count": 0,
                "approved_count": 0,
                "paid_count": 0,
                "rejected_count": 0,
                "pending_count": 0,
                "duplicate_count": 0,
                "finance_transaction_count": 0,
                "finance_transaction_amount": 0.0,
                "pending_installment_count": 0,
                "pending_installment_amount": 0.0,
                "approved_amount": 0.0,
                "submitted_amount": 0.0,
                "project_amounts": {},
            },
        )
        entry["finance_transaction_count"] += 1
        entry["finance_transaction_amount"] += _to_float(transaction.base_amount)

    candidates = [
        item
        for item in grouped.values()
        if item["submitted_count"] > 0 or item["finance_transaction_count"] > 0
    ]
    scope_label = _scope_text(time_scope)
    has_true_actor_refs = any(item["actor_id"] for item in candidates)

    if not candidates:
        summary = (
            f"There is not enough requester-level submission data to evaluate subcontractor performance in {scope_label.lower()}."
        )
        return {
            "intent": "subcontractor_performance",
            "summary": summary,
            "metrics": [
                {"label": "Time Scope", "value": scope_label},
                {"label": "Actors Analysed", "value": "0"},
            ],
            "next_actions": [
                "Capture a dedicated subcontractor identifier in finance and input records for stronger performance analytics."
            ],
            "sources": [],
            "context_item_count": 0,
        }

    max_approved_amount = max(item["approved_amount"] for item in candidates) or 1.0

    for entry in candidates:
        submitted_count = entry["submitted_count"]
        approval_rate = _safe_divide(entry["approved_count"], submitted_count)
        duplicate_rate = _safe_divide(entry["duplicate_count"], submitted_count)
        paid_rate = _safe_divide(entry["paid_count"], max(entry["approved_count"], 1))
        volume_score = _safe_divide(entry["approved_amount"], max_approved_amount)
        finance_volume_score = _safe_divide(
            entry["finance_transaction_amount"],
            max((item["finance_transaction_amount"] for item in candidates), default=0.0) or 1.0,
        )
        pending_penalty = _safe_divide(
            entry["pending_installment_count"] + entry["pending_count"],
            max(submitted_count + entry["finance_transaction_count"], 1),
        )

        entry["approval_rate"] = approval_rate
        entry["duplicate_rate"] = duplicate_rate
        entry["paid_rate"] = paid_rate
        entry["score"] = (
            approval_rate * 0.35
            + (1 - duplicate_rate) * 0.2
            + paid_rate * 0.1
            + volume_score * 0.15
            + finance_volume_score * 0.15
            + (1 - pending_penalty) * 0.05
        )
        entry["top_project_name"] = (
            max(entry["project_amounts"], key=entry["project_amounts"].get)
            if entry["project_amounts"]
            else "-"
        )

    ranked = sorted(candidates, key=lambda item: item["score"], reverse=True)
    top_actor = ranked[0]
    if has_true_actor_refs:
        summary = (
            f"{scope_label} subcontractor-performance view points to {top_actor['name']} as the strongest actor "
            f"with approval rate {_format_percent(top_actor['approval_rate'] * 100)}, duplicate rate "
            f"{_format_percent(top_actor['duplicate_rate'] * 100)}, and finance volume "
            f"{_format_currency(top_actor['finance_transaction_amount'])}."
        )
    else:
        summary = (
            f"{scope_label} subcontractor-performance proxy points to {top_actor['name']} as the strongest operational actor "
            f"with approval rate {_format_percent(top_actor['approval_rate'] * 100)} and duplicate rate "
            f"{_format_percent(top_actor['duplicate_rate'] * 100)}. "
            f"This ranking still falls back to requester-level names because true subcontractor references are sparse."
        )

    sources = [
        {
            "id": entry["actor_id"] or f"subcontractor-{index}",
            "label": entry["name"],
            "description": (
                f"Approved {_format_currency(entry['approved_amount'])}, approval rate {_format_percent(entry['approval_rate'] * 100)}, "
                f"duplicate rate {_format_percent(entry['duplicate_rate'] * 100)}, finance volume "
                f"{_format_currency(entry['finance_transaction_amount'])}, top project {entry['top_project_name']}."
            ),
            "project_id": "",
            "score": entry["score"],
        }
        for index, entry in enumerate(ranked[:5], start=1)
    ]

    return {
        "intent": "subcontractor_performance",
        "summary": summary,
        "metrics": [
            {"label": "Time Scope", "value": scope_label},
            {"label": "Actors Analysed", "value": str(len(candidates))},
            {"label": "Top Performer", "value": top_actor["name"]},
            {"label": "Top Actor ID", "value": top_actor["actor_id"] or "-"},
            {"label": "Top Approval Rate", "value": _format_percent(top_actor["approval_rate"] * 100)},
            {"label": "Top Duplicate Rate", "value": _format_percent(top_actor["duplicate_rate"] * 100)},
            {"label": "Top Approved Amount", "value": _format_currency(top_actor["approved_amount"])},
            {"label": "Top Finance Volume", "value": _format_currency(top_actor["finance_transaction_amount"])},
        ],
        "next_actions": (
            [
                f"Review why {top_actor['name']} converts submissions cleanly and use that pattern for weaker actors.",
                "Validate actor references on new input and finance records so this ranking stays tied to the same subcontractor across workflows.",
            ]
            if has_true_actor_refs
            else [
                f"Review why {top_actor['name']} converts submissions cleanly and use that pattern for weaker actors.",
                "Backfill subcontractor_id on existing records before using this view for commercial decisions.",
            ]
        ),
        "sources": sources,
        "context_item_count": len(candidates),
    }


def _build_duplicate_risk(
    snapshot: ChatAnalyticsSnapshot,
    _project_rollups: dict[UUID, dict],
    time_scope: TimeScope | None,
) -> dict:
    scoped_requests = [
        item for item in snapshot.input_requests if _value_in_scope(item.created_at, time_scope)
    ]
    duplicate_requests = [item for item in scoped_requests if bool(item.is_duplicate_flag)]
    scope_label = _scope_text(time_scope)

    clusters: dict[str, dict] = {}
    for request in duplicate_requests:
        cluster_key = (
            str(request.duplicate_of_request_id)
            if request.duplicate_of_request_id is not None
            else f"{request.receipt_no or '-'}|{request.document_date or '-'}|{_effective_request_amount(request):.2f}"
        )
        entry = clusters.setdefault(
            cluster_key,
            {
                "count": 0,
                "amount": 0.0,
                "project_name": _request_project_name(request, snapshot),
                "receipt_no": request.receipt_no or "-",
                "request_id": str(request.id),
                "requester_name": _request_operational_name(request),
                "subcontractor_id": _request_actor_id(request),
                "project_id": str(request.project_id),
            },
        )
        entry["count"] += 1
        entry["amount"] += _effective_request_amount(request)

    ranked_clusters = sorted(
        clusters.values(),
        key=lambda item: (item["count"], item["amount"]),
        reverse=True,
    )
    duplicate_exposure = sum(_effective_request_amount(item) for item in duplicate_requests)
    duplicate_pending = sum(1 for item in duplicate_requests if (item.status or "").upper() == "PENDING_ADMIN")
    affected_projects = len({_request_project_name(item, snapshot) for item in duplicate_requests})

    if not duplicate_requests:
        summary = f"There are no duplicate-flagged requests in {scope_label.lower()}."
    else:
        top_cluster = ranked_clusters[0]
        summary = (
            f"{scope_label} duplicate risk totals {_format_currency(duplicate_exposure)} across {len(duplicate_requests)} flagged requests. "
            f"The largest cluster is receipt {top_cluster['receipt_no']} in {top_cluster['project_name']} "
            f"with {top_cluster['count']} flagged requests."
        )

    sources = [
        {
            "id": cluster["request_id"],
            "label": f"{cluster['project_name']} · {cluster['receipt_no']}",
            "description": (
                f"{cluster['count']} flagged requests from {cluster['requester_name']}"
                f"{' (' + cluster['subcontractor_id'] + ')' if cluster['subcontractor_id'] else ''}, "
                f"potential exposure {_format_currency(cluster['amount'])}."
            ),
            "project_id": cluster["project_id"],
            "score": float(cluster["count"]),
        }
        for cluster in ranked_clusters[:5]
    ]

    return {
        "intent": "duplicate_risk",
        "summary": summary,
        "metrics": [
            {"label": "Time Scope", "value": scope_label},
            {"label": "Flagged Requests", "value": str(len(duplicate_requests))},
            {"label": "Potential Exposure", "value": _format_currency(duplicate_exposure)},
            {"label": "Pending Flags", "value": str(duplicate_pending)},
            {"label": "Affected Projects", "value": str(affected_projects)},
            {"label": "Largest Cluster", "value": str(ranked_clusters[0]["count"] if ranked_clusters else 0)},
        ],
        "next_actions": [
            "Review duplicate-flagged requests before approval so they do not inflate cost or trigger double payment.",
            "Strengthen duplicate matching with vendor fuzzy-match and document-reference normalization if flagged volume stays high.",
        ],
        "sources": sources,
        "context_item_count": len(duplicate_requests),
    }


def _render_reply(summary: str, metrics: list[dict], next_actions: list[str]) -> str:
    lines = [summary]

    if metrics:
        lines.append("")
        lines.append("Key metrics:")
        for metric in metrics[:6]:
            lines.append(f"- {metric['label']}: {metric['value']}")

    if next_actions:
        lines.append("")
        lines.append("Next actions:")
        for action in next_actions[:3]:
            lines.append(f"- {action}")

    return "\n".join(lines)


async def analyze_chat_question(
    db: AsyncSession,
    *,
    question: str,
    project_id: UUID | None = None,
) -> dict:
    time_scope = _parse_time_scope(question)
    snapshot = await _load_snapshot(db, project_id)
    project_rollups = _build_project_rollups(snapshot, time_scope)
    intent = _detect_intent(question)

    builders = {
        "budget_risk": _build_budget_risk,
        "cash_flow": _build_cash_flow,
        "overdue": _build_overdue,
        "material_vs_labor": _build_material_vs_labor,
        "pending_approval": _build_pending_approval,
        "subcontractor_performance": _build_subcontractor_performance,
        "duplicate_risk": _build_duplicate_risk,
        "general_overview": _build_general_overview,
    }

    analysis = builders.get(intent, _build_general_overview)(snapshot, project_rollups, time_scope)
    analysis["reply"] = _render_reply(
        summary=analysis["summary"],
        metrics=analysis.get("metrics", []),
        next_actions=analysis.get("next_actions", []),
    )
    analysis["project_id"] = str(project_id) if project_id is not None else None
    analysis["project_name"] = snapshot.project_name
    analysis["time_scope"] = (
        {
            "key": time_scope.key,
            "label": time_scope.label,
            "start_date": time_scope.start.isoformat(),
            "end_date": time_scope.end.isoformat(),
        }
        if time_scope is not None
        else None
    )
    analysis["llm_context"] = {
        "intent": analysis["intent"],
        "summary": analysis["summary"],
        "metrics": analysis.get("metrics", []),
        "next_actions": analysis.get("next_actions", []),
        "sources": analysis.get("sources", []),
        "time_scope": analysis["time_scope"],
    }
    return analysis
