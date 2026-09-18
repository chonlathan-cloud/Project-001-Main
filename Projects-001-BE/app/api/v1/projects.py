"""Project CRUD, legacy BOQ history, and retired sync compatibility routes."""

import re
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.api.deps.auth import AuthenticatedUser, require_admin_user, require_owner_user
from app.core.database import get_db
from app.models.boq import BOQItem, Project
from app.models.finance import Installment  # noqa: F401
from app.models.finance import Transaction
from app.models.funds import FundBucket
from app.models.input_request import InputRequest
from app.schemas.boq_schema import (
    BOQCompareNode,
    BOQCompareSummary,
    BOQWbsSummaryItem,
    BOQTreeNode,
    BOQTreeResponse,
    CreateProjectRequest,
    ProjectExecutionSummaryItem,
    ProjectDetailResponse,
    ProjectItem,
    UpdateProjectRequest,
)
from app.schemas.responses import StandardResponse
from app.services.project_budget_service import (
    active_budget_amount,
    legacy_budget_facts_from_items,
    load_project_budget_contexts,
)

router = APIRouter(prefix="/projects", tags=["Projects & BOQ"])

MATCH_STATUS_MATCHED = "MATCHED"
MATCH_STATUS_CUSTOMER_ONLY = "CUSTOMER_ONLY"
MATCH_STATUS_SUBCONTRACTOR_ONLY = "SUBCONTRACTOR_ONLY"
RESERVED_OPERATIONS_NAMES = {
    "company operations",
    "company operations / ค่าใช้จ่ายส่วนกลาง",
    "โครงการบริษัท",
}


def _to_project_list_item(
    project: Project,
    *,
    total_budget: float | None = None,
    budget_snapshot=None,
    execution: dict[str, float] | None = None,
) -> ProjectItem:
    execution = execution or {}
    normalized_budget = float(
        total_budget if total_budget is not None else (project.contingency_budget or 0)
    )
    spent = float(execution.get("spent", 0.0))
    return ProjectItem(
        id=project.id,
        name=project.name,
        project_type=project.project_type,
        system_key=project.system_key,
        status=project.status,
        total_budget=normalized_budget,
        progress_percent=(spent / normalized_budget * 100) if normalized_budget else 0.0,
        spent=spent,
        pending_amount=float(execution.get("pending_amount", 0.0)),
        paid_amount=float(execution.get("paid_amount", 0.0)),
        budget_snapshot=budget_snapshot,
    )


def _to_project_detail(
    project: Project,
    *,
    total_budget: float | None = None,
    budget_snapshot=None,
) -> ProjectDetailResponse:
    return ProjectDetailResponse(
        project_id=project.id,
        name=project.name,
        project_type=project.project_type,
        system_key=project.system_key,
        overhead_percent=float(project.overhead_percent or 0),
        profit_percent=float(project.profit_percent or 0),
        vat_percent=float(project.vat_percent or 0),
        contingency_budget=float(project.contingency_budget or 0),
        status=project.status,
        total_budget=float(
            total_budget if total_budget is not None else (project.contingency_budget or 0)
        ),
        budget_snapshot=budget_snapshot,
    )


async def _project_detail_with_budget(
    db: AsyncSession,
    project: Project,
) -> ProjectDetailResponse:
    budget_context = (
        await load_project_budget_contexts(db, [project.id])
    ).get(project.id)
    return _to_project_detail(
        project,
        total_budget=(
            active_budget_amount(budget_context, consumer="PROJECT_LIST")
            if budget_context is not None
            else project.contingency_budget
        ),
        budget_snapshot=(
            budget_context.snapshot if budget_context is not None else None
        ),
    )


def _to_float(value: Any) -> float:
    return float(value or 0)


def _normalize_compare_text(value: Any) -> str:
    cleaned = re.sub(r"\s+", " ", str(value or "").strip().lower())
    return cleaned


def _has_budget_amount(material: Any, labor: Any, total: Any) -> bool:
    return any(
        abs(_to_float(value)) > 0.00001
        for value in (material, labor, total)
    )


def _is_total_like_node(node: dict[str, Any]) -> bool:
    description = _normalize_compare_text(node.get("description"))
    item_no = _normalize_compare_text(node.get("item_no"))
    text = f"{item_no} {description}".strip()
    return text.startswith("total") or " total " in f" {text} " or text.startswith("รวม")


def _budget_value(node: dict[str, Any], key: str, fallback_key: str) -> float:
    if node.get(key) is not None:
        return _to_float(node.get(key))
    return _to_float(node.get(fallback_key))


def _rollup_budget_from_children(children: list[dict[str, Any]]) -> dict[str, float]:
    total_children = [
        child
        for child in children
        if _is_total_like_node(child)
        and _has_budget_amount(
            child.get("display_material_budget"),
            child.get("display_labor_budget"),
            child.get("display_total_budget"),
        )
    ]
    source_children = total_children or children

    return {
        "material": sum(
            _budget_value(child, "display_material_budget", "material_budget")
            for child in source_children
        ),
        "labor": sum(
            _budget_value(child, "display_labor_budget", "labor_budget")
            for child in source_children
        ),
        "total": sum(
            _budget_value(child, "display_total_budget", "total_budget")
            for child in source_children
        ),
    }


def _build_boq_tree_payload(items: list[BOQItem], parent_id: UUID | None = None) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    for item in items:
        if item.parent_id != parent_id:
            continue

        children = _build_boq_tree_payload(items, parent_id=item.id)
        own_material_budget = _to_float(item.total_material)
        own_labor_budget = _to_float(item.total_labor)
        own_total_budget = _to_float(item.grand_total)
        rollup_budget = _rollup_budget_from_children(children)
        has_own_budget = _has_budget_amount(
            own_material_budget,
            own_labor_budget,
            own_total_budget,
        )
        display_material_budget = (
            own_material_budget if has_own_budget else rollup_budget["material"]
        )
        display_labor_budget = own_labor_budget if has_own_budget else rollup_budget["labor"]
        display_total_budget = own_total_budget if has_own_budget else rollup_budget["total"]

        nodes.append(
            {
                "sheet_name": item.sheet_name,
                "boq_type": item.boq_type,
                "wbs_level": item.wbs_level,
                "description": item.description,
                "item_no": item.item_no,
                "qty": _to_float(item.qty) if item.qty is not None else None,
                "unit": item.unit,
                "total_budget": own_total_budget,
                "own_total_budget": own_total_budget,
                "rollup_total_budget": rollup_budget["total"],
                "display_total_budget": display_total_budget,
                "actual_spent": None,
                "variance": None,
                "material_budget": own_material_budget,
                "labor_budget": own_labor_budget,
                "own_material_budget": own_material_budget,
                "own_labor_budget": own_labor_budget,
                "rollup_material_budget": rollup_budget["material"],
                "rollup_labor_budget": rollup_budget["labor"],
                "display_material_budget": display_material_budget,
                "display_labor_budget": display_labor_budget,
                "customer_price": None,
                "subcontractor_price": None,
                "margin_per_unit": None,
                "children": children,
            }
        )
    return nodes


def _compare_base_key(node: dict[str, Any]) -> str:
    return "|".join(
        [
            _normalize_compare_text(node.get("sheet_name")),
            str(node.get("wbs_level") or ""),
            _normalize_compare_text(node.get("item_no")),
            _normalize_compare_text(node.get("description")),
        ]
    )


def _group_nodes_by_base_key(nodes: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for node in nodes:
        base_key = _compare_base_key(node)
        grouped.setdefault(base_key, []).append(node)
    return grouped


def _ordered_base_keys(
    customer_nodes: list[dict[str, Any]],
    subcontractor_nodes: list[dict[str, Any]],
) -> list[str]:
    ordered_keys: list[str] = []
    seen: set[str] = set()

    for node in [*customer_nodes, *subcontractor_nodes]:
        base_key = _compare_base_key(node)
        if base_key in seen:
            continue
        seen.add(base_key)
        ordered_keys.append(base_key)

    return ordered_keys


def _build_compare_tree(
    customer_nodes: list[dict[str, Any]],
    subcontractor_nodes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    compare_nodes: list[dict[str, Any]] = []
    customer_groups = _group_nodes_by_base_key(customer_nodes)
    subcontractor_groups = _group_nodes_by_base_key(subcontractor_nodes)

    for base_key in _ordered_base_keys(customer_nodes, subcontractor_nodes):
        customer_group = customer_groups.get(base_key, [])
        subcontractor_group = subcontractor_groups.get(base_key, [])
        pair_count = max(len(customer_group), len(subcontractor_group))

        for index in range(pair_count):
            customer_node = customer_group[index] if index < len(customer_group) else None
            subcontractor_node = (
                subcontractor_group[index] if index < len(subcontractor_group) else None
            )

            if customer_node and subcontractor_node:
                match_status = MATCH_STATUS_MATCHED
            elif customer_node:
                match_status = MATCH_STATUS_CUSTOMER_ONLY
            else:
                match_status = MATCH_STATUS_SUBCONTRACTOR_ONLY

            customer_total_budget = (
                _budget_value(customer_node, "display_total_budget", "total_budget")
                if customer_node
                else 0.0
            )
            subcontractor_total_budget = (
                _budget_value(subcontractor_node, "display_total_budget", "total_budget")
                if subcontractor_node
                else 0.0
            )
            customer_material_budget = (
                _budget_value(customer_node, "display_material_budget", "material_budget")
                if customer_node
                else 0.0
            )
            subcontractor_material_budget = (
                _budget_value(
                    subcontractor_node,
                    "display_material_budget",
                    "material_budget",
                )
                if subcontractor_node
                else 0.0
            )
            customer_labor_budget = (
                _budget_value(customer_node, "display_labor_budget", "labor_budget")
                if customer_node
                else 0.0
            )
            subcontractor_labor_budget = (
                _budget_value(subcontractor_node, "display_labor_budget", "labor_budget")
                if subcontractor_node
                else 0.0
            )
            variance = customer_total_budget - subcontractor_total_budget
            margin_percent = (
                (variance / customer_total_budget) * 100 if customer_total_budget else None
            )

            compare_nodes.append(
                {
                    "key": f"{base_key}#{index}",
                    "sheet_name": (
                        customer_node.get("sheet_name")
                        if customer_node
                        else subcontractor_node.get("sheet_name") if subcontractor_node else None
                    ),
                    "wbs_level": (
                        customer_node.get("wbs_level")
                        if customer_node
                        else subcontractor_node.get("wbs_level") if subcontractor_node else 1
                    ),
                    "description": (
                        customer_node.get("description")
                        if customer_node
                        else subcontractor_node.get("description") if subcontractor_node else None
                    ),
                    "item_no": (
                        customer_node.get("item_no")
                        if customer_node
                        else subcontractor_node.get("item_no") if subcontractor_node else None
                    ),
                    "unit": (
                        customer_node.get("unit")
                        if customer_node
                        else subcontractor_node.get("unit") if subcontractor_node else None
                    ),
                    "customer_qty": customer_node.get("qty") if customer_node else None,
                    "subcontractor_qty": subcontractor_node.get("qty") if subcontractor_node else None,
                    "customer_total_budget": customer_total_budget,
                    "subcontractor_total_budget": subcontractor_total_budget,
                    "customer_material_budget": customer_material_budget,
                    "subcontractor_material_budget": subcontractor_material_budget,
                    "customer_labor_budget": customer_labor_budget,
                    "subcontractor_labor_budget": subcontractor_labor_budget,
                    "variance": variance,
                    "margin_percent": margin_percent,
                    "match_status": match_status,
                    "children": _build_compare_tree(
                        customer_node.get("children", []) if customer_node else [],
                        subcontractor_node.get("children", []) if subcontractor_node else [],
                    ),
                }
            )

    return compare_nodes


def _count_compare_statuses(nodes: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        MATCH_STATUS_MATCHED: 0,
        MATCH_STATUS_CUSTOMER_ONLY: 0,
        MATCH_STATUS_SUBCONTRACTOR_ONLY: 0,
    }

    for node in nodes:
        status = str(node.get("match_status") or MATCH_STATUS_MATCHED)
        counts[status] = counts.get(status, 0) + 1
        child_counts = _count_compare_statuses(node.get("children", []))
        for key, value in child_counts.items():
            counts[key] = counts.get(key, 0) + value

    return counts


def _to_wbs_summary_item(node: dict[str, Any]) -> dict[str, Any]:
    return {
        "key": str(node.get("key") or ""),
        "label": str(node.get("description") or node.get("item_no") or "-"),
        "sheet_name": node.get("sheet_name"),
        "customer_total_budget": _to_float(node.get("customer_total_budget")),
        "subcontractor_total_budget": _to_float(
            node.get("subcontractor_total_budget")
        ),
        "variance": _to_float(node.get("variance")),
        "margin_percent": node.get("margin_percent"),
        "customer_material_budget": _to_float(
            node.get("customer_material_budget")
        ),
        "subcontractor_material_budget": _to_float(
            node.get("subcontractor_material_budget")
        ),
        "customer_labor_budget": _to_float(node.get("customer_labor_budget")),
        "subcontractor_labor_budget": _to_float(
            node.get("subcontractor_labor_budget")
        ),
        "match_status": str(node.get("match_status") or MATCH_STATUS_MATCHED),
    }


def _execution_summary_items(
    installments: list[Installment],
    transactions: list[Transaction],
    input_requests: list[InputRequest],
) -> list[dict[str, Any]]:
    overdue_installments = [
        item
        for item in installments
        if bool(item.is_overdue)
        and str(item.status or "").upper() not in {"APPROVED", "PAID", "ACCEPT"}
    ]

    pending_input_requests = [
        item
        for item in input_requests
        if str(item.status or "").upper() == "PENDING_ADMIN"
    ]
    approved_input_requests = [
        item for item in input_requests if str(item.status or "").upper() == "APPROVED"
    ]
    rejected_input_requests = [
        item for item in input_requests if str(item.status or "").upper() == "REJECTED"
    ]
    paid_input_requests = [
        item for item in input_requests if str(item.status or "").upper() == "PAID"
    ]

    def _input_request_approved_amount(item: InputRequest) -> float:
        return _to_float(
            item.approved_amount if item.approved_amount is not None else item.amount
        )

    return [
        {
            "key": "approved_transactions",
            "label": "Approved Transactions",
            "amount": sum(
                _to_float(item.net_payable or item.base_amount)
                for item in transactions
            ),
            "count": len(transactions),
            "tone": "positive",
        },
        {
            "key": "approved_input_requests",
            "label": "Approved Input Requests",
            "amount": sum(
                _input_request_approved_amount(item) for item in approved_input_requests
            ),
            "count": len(approved_input_requests),
            "tone": "positive",
        },
        {
            "key": "rejected_input_requests",
            "label": "Rejected Input Requests",
            "amount": sum(_to_float(item.amount) for item in rejected_input_requests),
            "count": len(rejected_input_requests),
            "tone": "danger",
        },
        {
            "key": "overdue_installments",
            "label": "Overdue Installments",
            "amount": sum(_to_float(item.amount) for item in overdue_installments),
            "count": len(overdue_installments),
            "tone": "danger",
        },
        {
            "key": "pending_input_requests",
            "label": "Pending Input Requests",
            "amount": sum(_to_float(item.amount) for item in pending_input_requests),
            "count": len(pending_input_requests),
            "tone": "warning",
        },
        {
            "key": "paid_input_requests",
            "label": "Paid Input Requests",
            "amount": sum(
                _input_request_approved_amount(item) for item in paid_input_requests
            ),
            "count": len(paid_input_requests),
            "tone": "positive",
        },
    ]


async def _project_execution_totals(
    db: AsyncSession,
    project_ids: list[UUID],
) -> dict[UUID, dict[str, float]]:
    """Load project-card finance totals in bounded batch queries."""

    totals = {
        project_id: {"spent": 0.0, "pending_amount": 0.0, "paid_amount": 0.0}
        for project_id in project_ids
    }
    if not project_ids:
        return totals

    transaction_rows = (
        await db.execute(
            select(
                BOQItem.project_id,
                Transaction.net_payable,
                Transaction.base_amount,
            )
            .join(Installment, Installment.boq_item_id == BOQItem.id)
            .join(Transaction, Transaction.installment_id == Installment.id)
            .where(BOQItem.project_id.in_(project_ids))
        )
    ).all()
    for project_id, net_payable, base_amount in transaction_rows:
        totals[project_id]["spent"] += _to_float(net_payable or base_amount)

    installment_rows = (
        await db.execute(
            select(
                BOQItem.project_id,
                Installment.amount,
                Installment.is_overdue,
                Installment.status,
            )
            .join(Installment, Installment.boq_item_id == BOQItem.id)
            .where(BOQItem.project_id.in_(project_ids))
        )
    ).all()
    for project_id, amount, is_overdue, installment_status in installment_rows:
        if bool(is_overdue) and str(installment_status or "").upper() not in {
            "APPROVED",
            "PAID",
            "ACCEPT",
        }:
            totals[project_id]["pending_amount"] += _to_float(amount)

    input_rows = (
        await db.execute(
            select(
                InputRequest.project_id,
                InputRequest.status,
                InputRequest.amount,
                InputRequest.approved_amount,
            ).where(InputRequest.project_id.in_(project_ids))
        )
    ).all()
    for project_id, request_status, amount, approved_amount in input_rows:
        normalized_status = str(request_status or "").upper()
        effective_amount = _to_float(
            approved_amount if approved_amount is not None else amount
        )
        if normalized_status in {"APPROVED", "PAID"}:
            totals[project_id]["spent"] += effective_amount
        if normalized_status == "PENDING_ADMIN":
            totals[project_id]["pending_amount"] += _to_float(amount)
        if normalized_status == "PAID":
            totals[project_id]["paid_amount"] += effective_amount
    return totals


# ---------------------------------------------------------------------------
# Router 2: GET /api/v1/projects
# ---------------------------------------------------------------------------
@router.get("", response_model=StandardResponse[list[ProjectItem]])
async def list_projects(
    db: AsyncSession = Depends(get_db),
    _user: AuthenticatedUser = Depends(require_admin_user),
):
    """Return all projects with basic info and progress."""
    try:
        result = await db.execute(select(Project).options(noload("*")))
        projects = result.scalars().all()
        project_ids = [project.id for project in projects]
        budget_contexts = await load_project_budget_contexts(db, project_ids)
        execution_totals = await _project_execution_totals(db, project_ids)

        items = [
            _to_project_list_item(
                project,
                total_budget=(
                    active_budget_amount(
                        budget_contexts[project.id], consumer="PROJECT_LIST"
                    )
                    if project.id in budget_contexts
                    else project.contingency_budget
                ),
                budget_snapshot=(
                    budget_contexts[project.id].snapshot
                    if project.id in budget_contexts
                    else None
                ),
                execution=execution_totals.get(project.id),
            )
            for project in projects
        ]
        return StandardResponse(data=items)

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch projects: {exc}",
        ) from exc


# ---------------------------------------------------------------------------
# Router 2: POST /api/v1/projects
# ---------------------------------------------------------------------------
@router.post("", response_model=StandardResponse[ProjectDetailResponse])
async def create_project(
    request: CreateProjectRequest,
    db: AsyncSession = Depends(get_db),
    _user: AuthenticatedUser = Depends(require_owner_user),
):
    """Create a new project before connecting BOQ sources."""
    try:
        normalized_name = request.name.strip()
        operations_name = (
            await db.execute(
                select(Project.name)
                .where(Project.system_key == "OPERATIONS")
                .limit(1)
            )
        ).scalar_one_or_none()
        reserved_names = {
            *RESERVED_OPERATIONS_NAMES,
            str(operations_name or "").strip().casefold(),
        }
        if (
            request.project_type.strip().upper() == "INTERNAL"
            and normalized_name.casefold() in reserved_names
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "DUPLICATE_OPERATIONS_PROJECT",
                    "message": "Company Operations already exists as the System Project.",
                },
            )
        project = Project(
            name=normalized_name,
            project_type=request.project_type.strip(),
            overhead_percent=Decimal(str(request.overhead_percent)),
            profit_percent=Decimal(str(request.profit_percent)),
            vat_percent=Decimal(str(request.vat_percent)),
            contingency_budget=Decimal(str(request.contingency_budget)),
            status=request.status.strip().upper(),
        )
        db.add(project)
        await db.flush()
        db.add(
            FundBucket(
                project_id=project.id,
                bucket_type="PROJECT",
                currency="THB",
                status="ACTIVE",
            )
        )
        await db.commit()
        await db.refresh(project)

        return StandardResponse(data=await _project_detail_with_budget(db, project))

    except HTTPException:
        await db.rollback()
        raise
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project: {exc}",
        ) from exc


# ---------------------------------------------------------------------------
# Router 2: PUT /api/v1/projects/{id}
# ---------------------------------------------------------------------------
@router.put("/{project_id}", response_model=StandardResponse[ProjectDetailResponse])
async def update_project(
    project_id: UUID,
    request: UpdateProjectRequest,
    db: AsyncSession = Depends(get_db),
    _user: AuthenticatedUser = Depends(require_owner_user),
):
    """Update project fields such as name or financial settings."""
    try:
        result = await db.execute(
            select(Project).options(noload("*")).filter_by(id=project_id)
        )
        project = result.scalar_one_or_none()

        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found.",
            )

        updates = request.model_dump(exclude_none=True)
        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one field is required to update a project.",
            )

        if project.system_key == "OPERATIONS":
            requested_type = str(updates.get("project_type", project.project_type)).upper()
            requested_status = str(updates.get("status", project.status)).upper()
            if requested_type != "INTERNAL" or requested_status != "ACTIVE":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "SYSTEM_PROJECT_IMMUTABLE",
                        "message": (
                            "Company Operations must remain an ACTIVE INTERNAL System Project. "
                            "Its display name may still be changed."
                        ),
                    },
                )

        for field, value in updates.items():
            if field in {"overhead_percent", "profit_percent", "vat_percent", "contingency_budget"}:
                setattr(project, field, Decimal(str(value)))
            elif isinstance(value, str):
                cleaned = value.strip()
                setattr(project, field, cleaned.upper() if field == "status" else cleaned)
            else:
                setattr(project, field, value)

        await db.commit()
        await db.refresh(project)

        return StandardResponse(data=await _project_detail_with_budget(db, project))

    except HTTPException:
        await db.rollback()
        raise
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update project: {exc}",
        ) from exc


# ---------------------------------------------------------------------------
# Router 3: GET /api/v1/projects/{id}
# ---------------------------------------------------------------------------
@router.get("/{project_id}", response_model=StandardResponse[ProjectDetailResponse])
async def get_project_detail(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: AuthenticatedUser = Depends(require_admin_user),
):
    """Return basic project information."""
    try:
        result = await db.execute(
            select(Project).options(noload("*")).filter_by(id=project_id)
        )
        project = result.scalar_one_or_none()

        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found.",
            )

        return StandardResponse(data=await _project_detail_with_budget(db, project))

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch project: {exc}",
        ) from exc


@router.get("/{project_id}/boq", response_model=StandardResponse[BOQTreeResponse])
async def get_project_boq(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: AuthenticatedUser = Depends(require_admin_user),
):
    """Return Customer, Subcontractor, and Compare BOQ trees for Project Detail."""
    try:
        proj_result = await db.execute(
            select(Project).options(noload("*")).filter_by(id=project_id)
        )
        project = proj_result.scalar_one_or_none()
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found.",
            )

        items_result = await db.execute(
            select(BOQItem)
            .options(noload("*"))
            .filter_by(project_id=project_id)
            .filter(BOQItem.valid_to.is_(None))
            .order_by(BOQItem.boq_type, BOQItem.sheet_name, BOQItem.wbs_level, BOQItem.item_no)
        )
        all_items = items_result.scalars().all()
        budget_context = (
            await load_project_budget_contexts(db, [project_id])
        ).get(project_id)

        customer_items = [item for item in all_items if item.boq_type == "CUSTOMER"]
        subcontractor_items = [
            item for item in all_items if item.boq_type == "SUBCONTRACTOR"
        ]

        customer_tree = _build_boq_tree_payload(customer_items, parent_id=None)
        subcontractor_tree = _build_boq_tree_payload(
            subcontractor_items,
            parent_id=None,
        )
        compare_tree = _build_compare_tree(customer_tree, subcontractor_tree)
        wbs_summary = [_to_wbs_summary_item(node) for node in compare_tree]

        legacy_budget = legacy_budget_facts_from_items(
            project_id=project_id,
            contingency_budget=project.contingency_budget,
            items=all_items,
        )
        customer_total_budget = float(legacy_budget.projected_customer_total)
        subcontractor_total_budget = float(
            legacy_budget.projected_subcontractor_total
        )
        total_variance = customer_total_budget - subcontractor_total_budget
        compare_counts = _count_compare_statuses(compare_tree)
        sheet_names = sorted(
            {
                str(item.sheet_name).strip()
                for item in all_items
                if str(item.sheet_name or "").strip()
            }
        )

        installments_result = await db.execute(
            select(Installment)
            .join(BOQItem, BOQItem.id == Installment.boq_item_id)
            .options(noload("*"))
            .filter(BOQItem.project_id == project_id)
        )
        project_installments = installments_result.scalars().all()

        transactions_result = await db.execute(
            select(Transaction)
            .join(Installment, Installment.id == Transaction.installment_id)
            .join(BOQItem, BOQItem.id == Installment.boq_item_id)
            .options(noload("*"))
            .filter(BOQItem.project_id == project_id)
        )
        project_transactions = transactions_result.scalars().all()

        input_requests_result = await db.execute(
            select(InputRequest)
            .options(noload("*"))
            .filter(InputRequest.project_id == project_id)
        )
        project_input_requests = input_requests_result.scalars().all()
        execution_summary = _execution_summary_items(
            project_installments,
            project_transactions,
            project_input_requests,
        )

        return StandardResponse(
            data=BOQTreeResponse(
                project_name=project.name,
                boq_tree=[
                    BOQTreeNode.model_validate(node)
                    for node in (customer_tree or subcontractor_tree)
                ],
                customer_tree=[
                    BOQTreeNode.model_validate(node) for node in customer_tree
                ],
                subcontractor_tree=[
                    BOQTreeNode.model_validate(node) for node in subcontractor_tree
                ],
                compare_tree=[
                    BOQCompareNode.model_validate(node) for node in compare_tree
                ],
                compare_summary=BOQCompareSummary(
                    customer_total_budget=customer_total_budget,
                    subcontractor_total_budget=subcontractor_total_budget,
                    total_variance=total_variance,
                    margin_percent=(
                        (total_variance / customer_total_budget) * 100
                        if customer_total_budget
                        else None
                    ),
                    matched_count=compare_counts.get(MATCH_STATUS_MATCHED, 0),
                    customer_only_count=compare_counts.get(
                        MATCH_STATUS_CUSTOMER_ONLY,
                        0,
                    ),
                    subcontractor_only_count=compare_counts.get(
                        MATCH_STATUS_SUBCONTRACTOR_ONLY,
                        0,
                    ),
                    sheet_names=sheet_names,
                ),
                wbs_summary=[
                    BOQWbsSummaryItem.model_validate(item) for item in wbs_summary
                ],
                execution_summary=[
                    ProjectExecutionSummaryItem.model_validate(item)
                    for item in execution_summary
                ],
                active_budget_snapshot=(
                    budget_context.snapshot if budget_context is not None else None
                ),
                legacy_history_only=bool(
                    budget_context is not None
                    and budget_context.snapshot.source_kind == "V2"
                ),
            )
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch BOQ: {exc}",
        ) from exc


def _raise_boq_sync_retired() -> None:
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail={
            "code": "BOQ_SYNC_RETIRED",
            "message": (
                "Google Sheets BOQ synchronization has been retired. "
                "Use the native BOQ workspace for this project."
            ),
            "replacement": "/api/v1/projects/{project_id}/boq-workspace",
        },
    )


@router.post("/boq/sync", status_code=status.HTTP_410_GONE)
async def sync_boq_retired(
    _user: AuthenticatedUser = Depends(require_owner_user),
):
    """Compatibility endpoint for clients deployed before sync retirement."""

    _raise_boq_sync_retired()


@router.post("/boq/tabs", status_code=status.HTTP_410_GONE)
async def preview_boq_tabs_retired(
    _user: AuthenticatedUser = Depends(require_owner_user),
):
    _raise_boq_sync_retired()


@router.post("/boq/sync-batch", status_code=status.HTTP_410_GONE)
async def sync_boq_batch_retired(
    _user: AuthenticatedUser = Depends(require_owner_user),
):
    _raise_boq_sync_retired()


@router.get("/boq/sync-jobs/{job_id}", status_code=status.HTTP_410_GONE)
async def get_sync_boq_batch_job_retired(
    job_id: str,
    _user: AuthenticatedUser = Depends(require_owner_user),
):
    del job_id
    _raise_boq_sync_retired()
