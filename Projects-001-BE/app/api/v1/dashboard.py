"""
Router 1: Dashboard — Overall Overview.
GET /api/v1/dashboard/summary
"""

from collections import defaultdict
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.api.deps.auth import AuthenticatedUser, require_owner_user
from app.core.database import get_db
from app.models.finance import Installment, Transaction
from app.models.boq import BOQItem, Project
from app.models.input_request import InputRequest
from app.schemas.dashboard_schema import (
    DashboardAttentionItem,
    DashboardCashflowPoint,
    DashboardKpis,
    DashboardProjectHealthItem,
    DashboardRecentAction,
    DashboardRiskyProject,
    DashboardSummaryResponse,
    DashboardZoneStatusItem,
)
from app.schemas.responses import StandardResponse

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def _month_key(value: date | datetime) -> str:
    return value.strftime("%Y-%m")


def _month_label(value: date | datetime) -> str:
    return value.strftime("%b")


def _money(value: object) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _input_request_amount(request: InputRequest) -> float:
    if request.approved_amount is not None:
        return _money(request.approved_amount)
    return _money(request.amount)


def _cashflow_direction(entry_type: object) -> str:
    normalized = str(entry_type or "").upper()
    if normalized == "INCOME":
        return "income"
    if normalized == "EXPENSE":
        return "expense"
    return ""


def _project_health_tone(*, burn_percent: float, overdue_amount: float, pending_amount: float) -> str:
    if overdue_amount > 0 or burn_percent >= 95:
        return "danger"
    if pending_amount > 0 or burn_percent >= 80:
        return "warning"
    return "positive"


@router.get("/summary", response_model=StandardResponse[DashboardSummaryResponse])
async def get_dashboard_summary(
    db: AsyncSession = Depends(get_db),
    _user: AuthenticatedUser = Depends(require_owner_user),
):
    """
    Return aggregated KPI data, monthly cashflow, and recent actions
    using the live development dataset in Postgres.
    """
    try:
        projects = (await db.execute(select(Project).options(noload("*")))).scalars().all()
        boq_item_rows = (
            await db.execute(select(BOQItem.id, BOQItem.project_id))
        ).all()
        boq_budget_rows = (
            await db.execute(
                select(
                    BOQItem.project_id,
                    BOQItem.boq_type,
                    BOQItem.grand_total,
                )
                .filter(BOQItem.valid_to.is_(None))
                .filter(BOQItem.parent_id.is_(None))
            )
        ).all()
        installments = (
            await db.execute(select(Installment).options(noload("*")))
        ).scalars().all()
        transactions = (
            await db.execute(select(Transaction).options(noload("*")))
        ).scalars().all()
        input_requests = (
            await db.execute(select(InputRequest).options(noload("*")))
        ).scalars().all()
        installment_lookup = {
            installment.id: installment.installment_no for installment in installments
        }
        project_name_lookup = {project.id: project.name for project in projects}
        boq_project_lookup = {
            boq_item_id: project_id for boq_item_id, project_id in boq_item_rows
        }
        installment_project_lookup = {
            installment.id: boq_project_lookup.get(installment.boq_item_id)
            for installment in installments
        }
        budget_components_by_project: dict[str, dict[str, float]] = defaultdict(
            lambda: {"CUSTOMER": 0.0, "SUBCONTRACTOR": 0.0}
        )
        for project_id, boq_type, grand_total in boq_budget_rows:
            project_key = str(project_id)
            type_key = str(boq_type or "CUSTOMER").upper()
            if type_key not in {"CUSTOMER", "SUBCONTRACTOR"}:
                type_key = "CUSTOMER"
            budget_components_by_project[project_key][type_key] += _money(grand_total)

        project_budget_lookup: dict[str, float] = {}
        for project in projects:
            project_key = str(project.id)
            components = budget_components_by_project.get(project_key, {})
            project_budget_lookup[project_key] = (
                components.get("CUSTOMER", 0.0)
                or components.get("SUBCONTRACTOR", 0.0)
                or _money(project.contingency_budget)
            )

        total_budget = sum(project_budget_lookup.values())
        actual_cost = sum(_money(transaction.base_amount) for transaction in transactions)
        pending_approval_count = sum(
            1 for request in input_requests if request.status == "PENDING_ADMIN"
        )
        pending_approval_amount = sum(
            _money(request.amount)
            for request in input_requests
            if str(request.status or "").upper() == "PENDING_ADMIN"
        )
        overdue_amount = sum(
            _money(installment.amount)
            for installment in installments
            if installment.is_overdue and installment.status != "APPROVED"
        )
        total_profit_margin = (
            ((total_budget - actual_cost) / total_budget) * 100 if total_budget else 0
        )

        monthly_cashflow_map: dict[str, dict[str, float | str]] = defaultdict(
            lambda: {
                "month": "",
                "actual_income": 0.0,
                "actual_expense": 0.0,
                "committed_income": 0.0,
                "committed_expense": 0.0,
                "planned_income": 0.0,
            }
        )

        for installment in installments:
            if installment.due_date is None:
                continue
            key = _month_key(installment.due_date)
            monthly_cashflow_map[key]["month"] = _month_label(installment.due_date)
            monthly_cashflow_map[key]["planned_income"] = _money(
                monthly_cashflow_map[key]["planned_income"]
            ) + _money(installment.amount)

        for transaction in transactions:
            if transaction.approved_at is None:
                continue
            key = _month_key(transaction.approved_at)
            monthly_cashflow_map[key]["month"] = _month_label(transaction.approved_at)
            monthly_cashflow_map[key]["actual_expense"] = _money(
                monthly_cashflow_map[key]["actual_expense"]
            ) + _money(transaction.base_amount)

        for request in input_requests:
            request_status = str(request.status or "").upper()
            direction = _cashflow_direction(request.entry_type)
            if not direction:
                continue

            amount = _input_request_amount(request)
            if amount <= 0:
                continue

            if request_status == "PAID":
                event_date = request.paid_at or request.approved_at
                if event_date is None:
                    continue
                key = _month_key(event_date)
                monthly_cashflow_map[key]["month"] = _month_label(event_date)
                field = "actual_income" if direction == "income" else "actual_expense"
                monthly_cashflow_map[key][field] = _money(
                    monthly_cashflow_map[key][field]
                ) + amount
            elif request_status == "APPROVED" and request.approved_at is not None:
                key = _month_key(request.approved_at)
                monthly_cashflow_map[key]["month"] = _month_label(request.approved_at)
                field = "committed_income" if direction == "income" else "committed_expense"
                monthly_cashflow_map[key][field] = _money(
                    monthly_cashflow_map[key][field]
                ) + amount

        monthly_cashflow = [
            DashboardCashflowPoint(
                month=str(monthly_cashflow_map[key]["month"]),
                income=round(_money(monthly_cashflow_map[key]["actual_income"]), 2),
                expense=round(_money(monthly_cashflow_map[key]["actual_expense"]), 2),
                net=round(
                    _money(monthly_cashflow_map[key]["actual_income"])
                    - _money(monthly_cashflow_map[key]["actual_expense"]),
                    2,
                ),
                actual_income=round(_money(monthly_cashflow_map[key]["actual_income"]), 2),
                actual_expense=round(_money(monthly_cashflow_map[key]["actual_expense"]), 2),
                committed_income=round(_money(monthly_cashflow_map[key]["committed_income"]), 2),
                committed_expense=round(_money(monthly_cashflow_map[key]["committed_expense"]), 2),
                planned_income=round(_money(monthly_cashflow_map[key]["planned_income"]), 2),
            )
            for key in sorted(monthly_cashflow_map.keys())
        ]

        risky_project_map: dict[str, dict[str, float | int | str]] = defaultdict(
            lambda: {
                "project_id": "",
                "project_name": "",
                "overdue_amount": 0.0,
                "overdue_count": 0,
                "pending_request_amount": 0.0,
                "pending_request_count": 0,
            }
        )

        for installment in installments:
            project_id = boq_project_lookup.get(installment.boq_item_id)
            if project_id is None:
                continue

            if not (
                bool(installment.is_overdue)
                and str(installment.status or "").upper() != "APPROVED"
            ):
                continue

            project_key = str(project_id)
            risky_project_map[project_key]["project_id"] = project_key
            risky_project_map[project_key]["project_name"] = project_name_lookup.get(
                project_id, "Unknown project"
            )
            risky_project_map[project_key]["overdue_amount"] = _money(
                risky_project_map[project_key]["overdue_amount"]
            ) + _money(installment.amount)
            risky_project_map[project_key]["overdue_count"] = int(
                risky_project_map[project_key]["overdue_count"]
            ) + 1

        for request in input_requests:
            if str(request.status or "").upper() != "PENDING_ADMIN":
                continue

            project_key = str(request.project_id)
            risky_project_map[project_key]["project_id"] = project_key
            risky_project_map[project_key]["project_name"] = project_name_lookup.get(
                request.project_id, "Unknown project"
            )
            risky_project_map[project_key]["pending_request_amount"] = _money(
                risky_project_map[project_key]["pending_request_amount"]
            ) + _money(request.amount)
            risky_project_map[project_key]["pending_request_count"] = int(
                risky_project_map[project_key]["pending_request_count"]
            ) + 1

        risky_projects = sorted(
            [
                {
                    "project_id": str(item["project_id"] or ""),
                    "project_name": str(item["project_name"] or "Unknown project"),
                    "overdue_amount": round(float(item["overdue_amount"]), 2),
                    "overdue_count": int(item["overdue_count"]),
                    "pending_request_amount": round(
                        float(item["pending_request_amount"]), 2
                    ),
                    "pending_request_count": int(item["pending_request_count"]),
                    "total_risk_amount": round(
                        float(item["overdue_amount"])
                        + float(item["pending_request_amount"]),
                        2,
                    ),
                }
                for item in risky_project_map.values()
                if (
                    _money(item["overdue_amount"]) > 0
                    or _money(item["pending_request_amount"]) > 0
                )
            ],
            key=lambda item: (
                item["total_risk_amount"],
                item["overdue_amount"],
                item["pending_request_amount"],
            ),
            reverse=True,
        )[:5]
        risky_project_items = [
            DashboardRiskyProject.model_validate(item) for item in risky_projects
        ]

        actual_cost_by_project: dict[str, float] = defaultdict(float)
        for transaction in transactions:
            project_id = installment_project_lookup.get(transaction.installment_id)
            if project_id is None:
                continue
            actual_cost_by_project[str(project_id)] += _money(transaction.base_amount)

        pending_amount_by_project = {
            str(item["project_id"]): _money(item["pending_request_amount"])
            for item in risky_project_map.values()
        }
        overdue_amount_by_project = {
            str(item["project_id"]): _money(item["overdue_amount"])
            for item in risky_project_map.values()
        }

        project_health = []
        for project in projects:
            project_key = str(project.id)
            budget = project_budget_lookup.get(project_key, 0.0)
            project_actual_cost = actual_cost_by_project.get(project_key, 0.0)
            pending_amount = pending_amount_by_project.get(project_key, 0.0)
            project_overdue_amount = overdue_amount_by_project.get(project_key, 0.0)
            burn_percent = (project_actual_cost / budget) * 100 if budget else 0.0
            project_health.append(
                DashboardProjectHealthItem(
                    project_id=project_key,
                    project_name=project.name,
                    status=str(project.status or "ACTIVE"),
                    total_budget=round(budget, 2),
                    actual_cost=round(project_actual_cost, 2),
                    pending_amount=round(pending_amount, 2),
                    overdue_amount=round(project_overdue_amount, 2),
                    burn_percent=round(burn_percent, 2),
                    tone=_project_health_tone(
                        burn_percent=burn_percent,
                        overdue_amount=project_overdue_amount,
                        pending_amount=pending_amount,
                    ),
                )
            )
        project_health = sorted(
            project_health,
            key=lambda item: (item.tone == "danger", item.tone == "warning", item.burn_percent),
            reverse=True,
        )[:6]

        active_project_count = sum(
            1 for project in projects if str(project.status or "").upper() == "ACTIVE"
        )
        paid_request_amount = sum(
            _money(
                request.approved_amount
                if request.approved_amount is not None
                else request.amount
            )
            for request in input_requests
            if str(request.status or "").upper() == "PAID"
        )
        zone_status = [
            DashboardZoneStatusItem(
                key="active_projects",
                label="Active Projects",
                count=active_project_count,
                amount=round(total_budget, 2),
                tone="positive",
            ),
            DashboardZoneStatusItem(
                key="pending_approvals",
                label="Pending Approvals",
                count=pending_approval_count,
                amount=round(pending_approval_amount, 2),
                tone="warning" if pending_approval_count else "neutral",
            ),
            DashboardZoneStatusItem(
                key="overdue",
                label="Overdue Exposure",
                count=sum(1 for installment in installments if installment.is_overdue),
                amount=round(overdue_amount, 2),
                tone="danger" if overdue_amount else "neutral",
            ),
            DashboardZoneStatusItem(
                key="paid",
                label="Paid Requests",
                count=sum(1 for request in input_requests if str(request.status or "").upper() == "PAID"),
                amount=round(paid_request_amount, 2),
                tone="positive",
            ),
        ]

        attention_items = [
            item
            for item in [
                DashboardAttentionItem(
                    key="pending_approvals",
                    title="Approval queue needs review",
                    description=f"{pending_approval_count} requests are waiting for Owner action.",
                    tone="warning",
                    amount=round(pending_approval_amount, 2),
                    count=pending_approval_count,
                    path="/approval?status=PENDING_ADMIN",
                )
                if pending_approval_count
                else None,
                DashboardAttentionItem(
                    key="overdue",
                    title="Overdue exposure detected",
                    description=f"{overdue_amount:,.2f} THB is currently marked overdue.",
                    tone="danger",
                    amount=round(overdue_amount, 2),
                    path="/insights?quick_view=overdue",
                )
                if overdue_amount
                else None,
                DashboardAttentionItem(
                    key="duplicate_risk",
                    title="Duplicate receipt risk",
                    description="Some input requests have duplicate flags from receipt detection.",
                    tone="warning",
                    count=sum(1 for request in input_requests if request.is_duplicate_flag),
                    path="/insights?quick_view=duplicate_risk",
                )
                if any(request.is_duplicate_flag for request in input_requests)
                else None,
            ]
            if item is not None
        ]

        recent_transaction_actions = [
            DashboardRecentAction(
                time=transaction.approved_at.strftime("%Y-%m-%d %H:%M"),
                action=(
                    "Owner approved bill for installment "
                    f"{installment_lookup.get(transaction.installment_id, '-')}"
                ),
                tone="positive",
                source_type="transaction",
            )
            for transaction in sorted(
                transactions,
                key=lambda item: item.approved_at or datetime.min,
                reverse=True,
            )[:5]
        ]

        recent_input_actions = [
            DashboardRecentAction(
                time=request.approved_at.strftime("%Y-%m-%d %H:%M"),
                action=(
                    f"Owner approved {request.entry_type.lower()} request for "
                    f"{request.requester_name}"
                ),
                tone="positive",
                source_type="input_request",
            )
            for request in sorted(
                [item for item in input_requests if item.approved_at is not None],
                key=lambda item: item.approved_at or datetime.min,
                reverse=True,
            )[:5]
        ]

        recent_actions = sorted(
            [*recent_transaction_actions, *recent_input_actions],
            key=lambda item: item.time,
            reverse=True,
        )[:5]

        data = DashboardSummaryResponse(
            kpis=DashboardKpis(
                total_budget=round(total_budget, 2),
                actual_cost=round(actual_cost, 2),
                pending_approval_count=pending_approval_count,
                pending_approval_amount=round(pending_approval_amount, 2),
                overdue_amount=round(overdue_amount, 2),
                total_profit_margin=f"{total_profit_margin:.1f}%",
                active_project_count=active_project_count,
                cash_position=round(
                    sum(item.income for item in monthly_cashflow)
                    - sum(item.expense for item in monthly_cashflow),
                    2,
                ),
            ),
            monthly_cashflow=monthly_cashflow,
            zone_status=zone_status,
            risky_projects=risky_project_items,
            project_health=project_health,
            attention_items=attention_items,
            recent_actions=recent_actions,
        )
        return StandardResponse(data=data)

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build dashboard summary: {exc}",
        ) from exc
