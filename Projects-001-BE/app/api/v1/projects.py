"""
Router 2 & 3: Project List, Project Detail, BOQ Tree, BOQ Sync.
"""

import re
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.core.database import get_db
from app.models.boq import BOQItem, Project
from app.models.finance import Installment  # noqa: F401
from app.models.finance import Transaction
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
    ProjectListResponse,
    SheetTabsRequest,
    SheetTabsResponse,
    SyncBOQRequest,
    SyncBOQBatchRequest,
    SyncBOQBatchJobResponse,
    SyncBOQBatchResponse,
    SyncBOQResponse,
    UpdateProjectRequest,
)
from app.schemas.responses import StandardResponse
from app.services.boq_sync_job_service import (
    create_boq_sync_job,
    get_boq_sync_job,
    run_boq_sync_job,
    serialize_boq_sync_job,
)
from app.services.boq_sync_service import fetch_google_sheet_tabs, sync_boq_sheet

router = APIRouter(prefix="/projects", tags=["Projects & BOQ"])

MATCH_STATUS_MATCHED = "MATCHED"
MATCH_STATUS_CUSTOMER_ONLY = "CUSTOMER_ONLY"
MATCH_STATUS_SUBCONTRACTOR_ONLY = "SUBCONTRACTOR_ONLY"


def _to_project_list_item(project: Project, *, total_budget: float | None = None) -> ProjectItem:
    return ProjectItem(
        id=project.id,
        name=project.name,
        project_type=project.project_type,
        status=project.status,
        total_budget=float(
            total_budget if total_budget is not None else (project.contingency_budget or 0)
        ),
        progress_percent=0.0,  # TODO: calculate from installments
    )


def _to_project_detail(project: Project) -> ProjectDetailResponse:
    return ProjectDetailResponse(
        project_id=project.id,
        name=project.name,
        project_type=project.project_type,
        overhead_percent=float(project.overhead_percent or 0),
        profit_percent=float(project.profit_percent or 0),
        vat_percent=float(project.vat_percent or 0),
        contingency_budget=float(project.contingency_budget or 0),
        status=project.status,
    )


def _to_float(value: Any) -> float:
    return float(value or 0)


def _normalize_compare_text(value: Any) -> str:
    cleaned = re.sub(r"\s+", " ", str(value or "").strip().lower())
    return cleaned


def _build_boq_tree_payload(items: list[BOQItem], parent_id: UUID | None = None) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    for item in items:
        if item.parent_id != parent_id:
            continue

        children = _build_boq_tree_payload(items, parent_id=item.id)
        nodes.append(
            {
                "sheet_name": item.sheet_name,
                "boq_type": item.boq_type,
                "wbs_level": item.wbs_level,
                "description": item.description,
                "item_no": item.item_no,
                "qty": _to_float(item.qty) if item.qty is not None else None,
                "unit": item.unit,
                "total_budget": _to_float(item.grand_total),
                "actual_spent": None,
                "variance": None,
                "material_budget": _to_float(item.total_material),
                "labor_budget": _to_float(item.total_labor),
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

            customer_total_budget = _to_float(customer_node.get("total_budget")) if customer_node else 0.0
            subcontractor_total_budget = (
                _to_float(subcontractor_node.get("total_budget")) if subcontractor_node else 0.0
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
                    "customer_material_budget": (
                        _to_float(customer_node.get("material_budget")) if customer_node else 0.0
                    ),
                    "subcontractor_material_budget": (
                        _to_float(subcontractor_node.get("material_budget")) if subcontractor_node else 0.0
                    ),
                    "customer_labor_budget": (
                        _to_float(customer_node.get("labor_budget")) if customer_node else 0.0
                    ),
                    "subcontractor_labor_budget": (
                        _to_float(subcontractor_node.get("labor_budget")) if subcontractor_node else 0.0
                    ),
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
    pending_installments = [
        item
        for item in installments
        if str(item.status or "").upper() in {"PENDING", "PENDING_ADMIN", "ADVANCE"}
    ]
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
    paid_input_requests = [
        item for item in input_requests if str(item.status or "").upper() == "PAID"
    ]

    return [
        {
            "key": "approved_transactions",
            "label": "Approved Transactions",
            "amount": sum(_to_float(item.net_payable or item.base_amount) for item in transactions),
            "count": len(transactions),
            "tone": "positive",
        },
        {
            "key": "pending_installments",
            "label": "Pending Installments",
            "amount": sum(_to_float(item.amount) for item in pending_installments),
            "count": len(pending_installments),
            "tone": "warning",
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
                _to_float(item.approved_amount if item.approved_amount is not None else item.amount)
                for item in paid_input_requests
            ),
            "count": len(paid_input_requests),
            "tone": "positive",
        },
    ]


# ---------------------------------------------------------------------------
# Router 2: GET /api/v1/projects
# ---------------------------------------------------------------------------
@router.get("", response_model=StandardResponse[list[ProjectItem]])
async def list_projects(db: AsyncSession = Depends(get_db)):
    """Return all projects with basic info and progress."""
    try:
        result = await db.execute(select(Project).options(noload("*")))
        projects = result.scalars().all()
        project_ids = [project.id for project in projects]
        budget_by_project_id: dict[UUID, float] = {}

        if project_ids:
            budget_result = await db.execute(
                select(
                    BOQItem.project_id,
                    func.coalesce(func.sum(BOQItem.grand_total), 0),
                )
                .filter(BOQItem.project_id.in_(project_ids))
                .filter(BOQItem.valid_to.is_(None))
                .filter(BOQItem.parent_id.is_(None))
                .group_by(BOQItem.project_id)
            )
            budget_by_project_id = {
                project_id: float(total_budget or 0)
                for project_id, total_budget in budget_result.all()
            }

        items = [
            _to_project_list_item(
                project,
                total_budget=budget_by_project_id.get(project.id, float(project.contingency_budget or 0)),
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
):
    """Create a new project before connecting BOQ sources."""
    try:
        project = Project(
            name=request.name.strip(),
            project_type=request.project_type.strip(),
            overhead_percent=Decimal(str(request.overhead_percent)),
            profit_percent=Decimal(str(request.profit_percent)),
            vat_percent=Decimal(str(request.vat_percent)),
            contingency_budget=Decimal(str(request.contingency_budget)),
            status=request.status.strip().upper(),
        )
        db.add(project)
        await db.commit()
        await db.refresh(project)

        return StandardResponse(data=_to_project_detail(project))

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

        return StandardResponse(data=_to_project_detail(project))

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

        return StandardResponse(data=_to_project_detail(project))

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

        customer_total_budget = sum(
            _to_float(node.get("total_budget")) for node in customer_tree
        )
        subcontractor_total_budget = sum(
            _to_float(node.get("total_budget")) for node in subcontractor_tree
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
            )
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch BOQ: {exc}",
        ) from exc


# ---------------------------------------------------------------------------
# Router 2: POST /api/v1/boq/sync  (uses AI to parse Google Sheet)
# ---------------------------------------------------------------------------
@router.post("/boq/sync", response_model=StandardResponse[SyncBOQResponse])
async def sync_boq(
    request: SyncBOQRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Sync BOQ from a Google Sheet URL.
    Flow: Fetch one tab → Gemini parses WBS → Save to DB (SCD Type 2).
    """
    try:
        result = await db.execute(
            select(Project).options(noload("*")).filter_by(id=request.project_id)
        )
        project = result.scalar_one_or_none()

        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {request.project_id} not found.",
            )

        data = await sync_boq_sheet(
            session=db,
            project=project,
            boq_type=request.boq_type,
            sheet_url=request.sheet_url,
            sheet_name=request.sheet_name,
        )
        return StandardResponse(data=SyncBOQResponse(**data))

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync BOQ: {exc}",
        ) from exc


@router.post("/boq/tabs", response_model=StandardResponse[SheetTabsResponse])
async def preview_boq_tabs(request: SheetTabsRequest):
    """Preview workbook tabs so the frontend can batch select syncable BOQ tabs."""
    try:
        tabs = await fetch_google_sheet_tabs(request.sheet_url)
        return StandardResponse(
            data=SheetTabsResponse(
                sheet_url=request.sheet_url,
                tabs=tabs,
            )
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to preview Google Sheet tabs: {exc}",
        ) from exc


@router.post("/boq/sync-batch", response_model=StandardResponse[SyncBOQBatchJobResponse])
async def sync_boq_batch(
    request: SyncBOQBatchRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Queue a background job that syncs multiple BOQ tabs from the same workbook."""
    try:
        result = await db.execute(
            select(Project).options(noload("*")).filter_by(id=request.project_id)
        )
        project = result.scalar_one_or_none()

        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {request.project_id} not found.",
            )

        job = await create_boq_sync_job(
            project_id=project.id,
            project_name=project.name,
            boq_type=request.boq_type,
            sheet_url=request.sheet_url,
            sheet_names=request.sheet_names,
        )
        background_tasks.add_task(run_boq_sync_job, job["job_id"])
        return StandardResponse(data=serialize_boq_sync_job(job))

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync BOQ tabs: {exc}",
        ) from exc


@router.get("/boq/sync-jobs/{job_id}", response_model=StandardResponse[SyncBOQBatchJobResponse])
async def get_sync_boq_batch_job(job_id: str):
    """Return current status and per-tab progress for a queued BOQ batch sync job."""
    try:
        job = await get_boq_sync_job(job_id)
        return StandardResponse(data=serialize_boq_sync_job(job))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch BOQ sync job {job_id}: {exc}",
        ) from exc
