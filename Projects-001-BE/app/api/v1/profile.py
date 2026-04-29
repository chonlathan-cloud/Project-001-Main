"""
Authenticated profile endpoint for the Profile page.
"""

from __future__ import annotations

from collections import OrderedDict
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import AuthenticatedUser, get_current_user
from app.core.database import get_db
from app.models.boq import Project
from app.models.input_request import InputRequest
from app.schemas.responses import StandardResponse
from app.services.identity_service import get_subcontractor

router = APIRouter(prefix="/profile", tags=["Profile"])


def _money_value(value: object) -> float:
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _compact_money(value: float) -> str:
    abs_value = abs(value)
    if abs_value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if abs_value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return f"{value:.0f}"


def _month_key(value: date) -> str:
    return value.strftime("%Y-%m")


def _month_label(key: str) -> str:
    return date.fromisoformat(f"{key}-01").strftime("%b")


def _base_input_scope(user: AuthenticatedUser):
    clauses = []
    if user.role == "subcontractor":
        if not user.subcontractor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Subcontractor session does not include subcontractor_id.",
            )
        clauses.append(InputRequest.subcontractor_id == user.subcontractor_id)
    return clauses


async def _count_input_requests(
    db: AsyncSession,
    user: AuthenticatedUser,
    *,
    statuses: set[str] | None = None,
) -> int:
    query = select(func.count()).select_from(InputRequest)
    for clause in _base_input_scope(user):
        query = query.where(clause)
    if statuses:
        query = query.where(InputRequest.status.in_(statuses))
    return int((await db.execute(query)).scalar_one() or 0)


async def _sum_input_amounts(
    db: AsyncSession,
    user: AuthenticatedUser,
    *,
    statuses: set[str] | None = None,
) -> float:
    query = select(func.coalesce(func.sum(InputRequest.amount), 0)).select_from(InputRequest)
    for clause in _base_input_scope(user):
        query = query.where(clause)
    if statuses:
        query = query.where(InputRequest.status.in_(statuses))
    return _money_value((await db.execute(query)).scalar_one())


async def _active_project_count(db: AsyncSession) -> int:
    active_count = int(
        (await db.execute(
            select(func.count()).select_from(Project).where(Project.status == "ACTIVE")
        )).scalar_one()
        or 0
    )
    if active_count:
        return active_count
    return int((await db.execute(select(func.count()).select_from(Project))).scalar_one() or 0)


async def _chart_data(db: AsyncSession, user: AuthenticatedUser) -> list[dict[str, float | str]]:
    query = select(
        InputRequest.request_date,
        InputRequest.entry_type,
        InputRequest.amount,
    ).order_by(InputRequest.request_date.asc())

    for clause in _base_input_scope(user):
        query = query.where(clause)

    rows = (await db.execute(query)).all()
    grouped: OrderedDict[str, dict[str, float | str]] = OrderedDict()

    for request_date, entry_type, amount in rows:
        if request_date is None:
            continue
        key = _month_key(request_date)
        if key not in grouped:
            grouped[key] = {"name": _month_label(key), "Activity": 0, "Expenses": 0}
        grouped[key]["Activity"] = float(grouped[key]["Activity"]) + 1
        if entry_type == "EXPENSE":
            grouped[key]["Expenses"] = float(grouped[key]["Expenses"]) + _money_value(amount)

    return list(grouped.values())[-6:]


async def _build_subcontractor_profile(
    db: AsyncSession,
    user: AuthenticatedUser,
) -> dict:
    if not user.subcontractor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Subcontractor session does not include subcontractor_id.",
        )

    profile = get_subcontractor(user.subcontractor_id)
    pending_count = await _count_input_requests(db, user, statuses={"PENDING_ADMIN"})
    completed_count = await _count_input_requests(db, user, statuses={"APPROVED", "PAID"})
    all_count = await _count_input_requests(db, user)
    approved_total = await _sum_input_amounts(db, user, statuses={"APPROVED", "PAID"})

    return {
        "user": {
            "id": profile.id,
            "name": profile.name,
            "company": f"Tax ID: {profile.tax_id}" if profile.tax_id else "Subcontractor Portal",
            "role": "Subcontractor",
            "time": "Asia/Bangkok",
            "email": user.email,
            "line_uid": profile.line_uid,
        },
        "stats": [
            {
                "id": "active_projects",
                "value": str(await _active_project_count(db)),
                "label": "Active Projects",
                "subtext": "Projects available for expense/input submission",
            },
            {
                "id": "pending_approvals",
                "value": str(pending_count),
                "label": "Pending Approvals",
                "subtext": "Your submitted requests waiting for admin review",
            },
            {
                "id": "completed_tasks",
                "value": str(completed_count),
                "label": "Completed Tasks",
                "subtext": "Your approved or paid input requests",
            },
            {
                "id": "team_members",
                "value": str(all_count),
                "label": "My Requests",
                "subtext": "Total requests tied to this subcontractor account",
            },
            {
                "id": "reports_generated",
                "value": f"{profile.vat_rate * 100:.0f}%",
                "label": "VAT Rate",
                "subtext": "Financial setting stored in Firestore profile",
            },
            {
                "id": "budget_managed",
                "value": _compact_money(approved_total),
                "label": "Approved Amount",
                "subtext": "Approved or paid requests for this subcontractor",
            },
        ],
        "chartData": await _chart_data(db, user),
    }


async def _build_admin_profile(db: AsyncSession, user: AuthenticatedUser) -> dict:
    pending_count = await _count_input_requests(db, user, statuses={"PENDING_ADMIN"})
    completed_count = await _count_input_requests(db, user, statuses={"APPROVED", "PAID"})
    total_count = await _count_input_requests(db, user)
    approved_total = await _sum_input_amounts(db, user, statuses={"APPROVED", "PAID"})

    return {
        "user": {
            "name": user.display_name or user.email or "Admin",
            "company": "Manee Son Construction",
            "role": "Admin / Project Manager",
            "time": "Asia/Bangkok",
            "email": user.email,
        },
        "stats": [
            {
                "id": "active_projects",
                "value": str(await _active_project_count(db)),
                "label": "Active Projects",
                "subtext": "Projects currently available in the system",
            },
            {
                "id": "pending_approvals",
                "value": str(pending_count),
                "label": "Pending Approvals",
                "subtext": "Input requests waiting for admin review",
            },
            {
                "id": "completed_tasks",
                "value": str(completed_count),
                "label": "Completed Tasks",
                "subtext": "Approved or paid input requests",
            },
            {
                "id": "team_members",
                "value": str(total_count),
                "label": "Input Requests",
                "subtext": "Total requests captured in the input workflow",
            },
            {
                "id": "reports_generated",
                "value": str(completed_count),
                "label": "Reports Generated",
                "subtext": "Operational items ready for dashboard/reporting",
            },
            {
                "id": "budget_managed",
                "value": _compact_money(approved_total),
                "label": "Budget Managed",
                "subtext": "Approved or paid input request amount",
            },
        ],
        "chartData": await _chart_data(db, user),
    }


@router.get("/me", response_model=StandardResponse[dict])
async def get_my_profile(
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the current authenticated user's profile dashboard data."""
    if user.role == "subcontractor":
        return StandardResponse(data=await _build_subcontractor_profile(db, user))

    return StandardResponse(data=await _build_admin_profile(db, user))
