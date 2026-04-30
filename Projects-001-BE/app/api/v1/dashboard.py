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

from app.core.database import get_db
from app.models.finance import Installment, Transaction
from app.models.boq import BOQItem, Project
from app.models.input_request import InputRequest
from app.schemas.responses import StandardResponse

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def _month_key(value: date | datetime) -> str:
    return value.strftime("%Y-%m")


def _month_label(value: date | datetime) -> str:
    return value.strftime("%b")


@router.get("/summary", response_model=StandardResponse[dict])
async def get_dashboard_summary(db: AsyncSession = Depends(get_db)):
    """
    Return aggregated KPI data, monthly cashflow, and recent actions
    using the live development dataset in Postgres.
    """
    try:
        projects = (await db.execute(select(Project).options(noload("*")))).scalars().all()
        boq_item_rows = (
            await db.execute(select(BOQItem.id, BOQItem.project_id))
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

        total_budget = sum(float(project.contingency_budget or 0) for project in projects)
        actual_cost = sum(float(transaction.base_amount or 0) for transaction in transactions)
        pending_approval_count = sum(
            1 for request in input_requests if request.status == "PENDING_ADMIN"
        )
        overdue_amount = sum(
            float(installment.amount or 0)
            for installment in installments
            if installment.is_overdue and installment.status != "APPROVED"
        )
        total_profit_margin = (
            ((total_budget - actual_cost) / total_budget) * 100 if total_budget else 0
        )

        monthly_cashflow_map: dict[str, dict[str, float | str]] = defaultdict(
            lambda: {"month": "", "income": 0.0, "expense": 0.0}
        )

        for installment in installments:
            if installment.due_date is None:
                continue
            key = _month_key(installment.due_date)
            monthly_cashflow_map[key]["month"] = _month_label(installment.due_date)
            monthly_cashflow_map[key]["income"] = float(
                monthly_cashflow_map[key]["income"]
            ) + float(installment.amount or 0)

        for transaction in transactions:
            if transaction.approved_at is None:
                continue
            key = _month_key(transaction.approved_at)
            monthly_cashflow_map[key]["month"] = _month_label(transaction.approved_at)
            monthly_cashflow_map[key]["expense"] = float(
                monthly_cashflow_map[key]["expense"]
            ) + float(transaction.base_amount or 0)

        monthly_cashflow = [
            monthly_cashflow_map[key] for key in sorted(monthly_cashflow_map.keys())
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
            risky_project_map[project_key]["overdue_amount"] = float(
                risky_project_map[project_key]["overdue_amount"]
            ) + float(installment.amount or 0)
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
            risky_project_map[project_key]["pending_request_amount"] = float(
                risky_project_map[project_key]["pending_request_amount"]
            ) + float(request.amount or 0)
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
                    float(item["overdue_amount"]) > 0
                    or float(item["pending_request_amount"]) > 0
                )
            ],
            key=lambda item: (
                item["total_risk_amount"],
                item["overdue_amount"],
                item["pending_request_amount"],
            ),
            reverse=True,
        )[:5]

        recent_transaction_actions = [
            {
                "time": transaction.approved_at.strftime("%Y-%m-%d %H:%M"),
                "action": (
                    "Admin approved bill for installment "
                    f"{installment_lookup.get(transaction.installment_id, '-')}"
                ),
            }
            for transaction in sorted(
                transactions,
                key=lambda item: item.approved_at or datetime.min,
                reverse=True,
            )[:5]
        ]

        recent_input_actions = [
            {
                "time": request.approved_at.strftime("%Y-%m-%d %H:%M"),
                "action": (
                    f"Admin approved {request.entry_type.lower()} request for "
                    f"{request.requester_name}"
                ),
            }
            for request in sorted(
                [item for item in input_requests if item.approved_at is not None],
                key=lambda item: item.approved_at or datetime.min,
                reverse=True,
            )[:5]
        ]

        recent_actions = sorted(
            [*recent_transaction_actions, *recent_input_actions],
            key=lambda item: item["time"],
            reverse=True,
        )[:5]

        data = {
            "kpis": {
                "total_budget": round(total_budget, 2),
                "actual_cost": round(actual_cost, 2),
                "pending_approval_count": pending_approval_count,
                "overdue_amount": round(overdue_amount, 2),
                "total_profit_margin": f"{total_profit_margin:.1f}%",
            },
            "monthly_cashflow": monthly_cashflow,
            "risky_projects": risky_projects,
            "recent_actions": recent_actions,
        }
        return StandardResponse(data=data)

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build dashboard summary: {exc}",
        ) from exc
