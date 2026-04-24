"""
Insight Warehouse API contract.

This router intentionally starts with contract-first placeholder responses so
frontend and backend can align on a stable warehouse shape before the
cross-source aggregation service is implemented.
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.core.database import get_db
from app.models.boq import Project
from app.schemas.insight_schema import (
    InsightWarehouseColumnDefinition,
    InsightWarehouseExportQuery,
    InsightWarehouseFilterOptionItem,
    InsightWarehouseFilterSet,
    InsightWarehouseFiltersResponse,
    InsightWarehouseQuickView,
    InsightWarehouseRowsQuery,
    InsightWarehouseRowsResponse,
    InsightWarehouseSummaryResponse,
)
from app.schemas.responses import StandardResponse
from app.services.insight_warehouse_service import (
    export_insight_warehouse_csv,
    export_insight_warehouse_json,
    get_insight_warehouse_summary as build_insight_warehouse_summary,
    list_insight_warehouse_rows as build_insight_warehouse_rows,
)

router = APIRouter(prefix="/insights", tags=["Insight Warehouse"])

SOURCE_TYPE_OPTIONS = [
    InsightWarehouseFilterOptionItem(value="INPUT_REQUEST", label="Input Requests"),
    InsightWarehouseFilterOptionItem(value="INSTALLMENT", label="Installments"),
    InsightWarehouseFilterOptionItem(value="TRANSACTION", label="Transactions"),
]

STATUS_OPTIONS = [
    InsightWarehouseFilterOptionItem(value="DRAFT", label="Draft"),
    InsightWarehouseFilterOptionItem(value="LOCKED", label="Locked"),
    InsightWarehouseFilterOptionItem(value="PENDING", label="Pending"),
    InsightWarehouseFilterOptionItem(value="PENDING_ADMIN", label="Pending Admin"),
    InsightWarehouseFilterOptionItem(value="ADVANCE", label="Advance"),
    InsightWarehouseFilterOptionItem(value="APPROVED", label="Approved"),
    InsightWarehouseFilterOptionItem(value="PAID", label="Paid"),
    InsightWarehouseFilterOptionItem(value="REJECTED", label="Rejected"),
    InsightWarehouseFilterOptionItem(value="BILLING", label="Billing"),
    InsightWarehouseFilterOptionItem(value="RE-BILLING", label="Re-Billing"),
    InsightWarehouseFilterOptionItem(value="ACCEPT", label="Accept"),
]

ENTRY_TYPE_OPTIONS = [
    InsightWarehouseFilterOptionItem(value="EXPENSE", label="Expense"),
    InsightWarehouseFilterOptionItem(value="INCOME", label="Income"),
]

FLOW_DIRECTION_OPTIONS = [
    InsightWarehouseFilterOptionItem(value="OUTFLOW", label="Cash Out"),
    InsightWarehouseFilterOptionItem(value="INFLOW", label="Cash In"),
    InsightWarehouseFilterOptionItem(value="NEUTRAL", label="Neutral"),
]

DATE_FIELD_OPTIONS = [
    InsightWarehouseFilterOptionItem(value="event_date", label="Event Date"),
    InsightWarehouseFilterOptionItem(value="due_date", label="Due Date"),
    InsightWarehouseFilterOptionItem(value="approved_at", label="Approved At"),
    InsightWarehouseFilterOptionItem(value="paid_at", label="Paid At"),
    InsightWarehouseFilterOptionItem(value="created_at", label="Created At"),
]

SORT_FIELD_OPTIONS = [
    InsightWarehouseFilterOptionItem(value="event_date", label="Event Date"),
    InsightWarehouseFilterOptionItem(value="due_date", label="Due Date"),
    InsightWarehouseFilterOptionItem(value="amount", label="Amount"),
    InsightWarehouseFilterOptionItem(value="created_at", label="Created At"),
    InsightWarehouseFilterOptionItem(value="updated_at", label="Updated At"),
    InsightWarehouseFilterOptionItem(value="status", label="Status"),
    InsightWarehouseFilterOptionItem(value="project_name", label="Project"),
    InsightWarehouseFilterOptionItem(value="actor_name", label="Actor"),
]

QUICK_VIEW_OPTIONS = [
    InsightWarehouseQuickView(
        key="all_records",
        label="All Records",
        description="Show every supported record in one warehouse table.",
    ),
    InsightWarehouseQuickView(
        key="pending_approval",
        label="Pending Approval",
        description="Focus on items still waiting for review or action.",
    ),
    InsightWarehouseQuickView(
        key="overdue",
        label="Overdue",
        description="Surface customer-side items that are already overdue.",
    ),
    InsightWarehouseQuickView(
        key="duplicate_risk",
        label="Duplicate Risk",
        description="Highlight records flagged as possible duplicates.",
    ),
    InsightWarehouseQuickView(
        key="paid_recently",
        label="Paid Recently",
        description="Review recently completed payment activity.",
    ),
    InsightWarehouseQuickView(
        key="large_amount",
        label="Large Amount",
        description="Spot high-value items first.",
    ),
]

COLUMN_OPTIONS = [
    InsightWarehouseColumnDefinition(key="source_type", label="Source", data_type="text"),
    InsightWarehouseColumnDefinition(key="reference_no", label="Reference", data_type="text"),
    InsightWarehouseColumnDefinition(key="project_name", label="Project", data_type="text"),
    InsightWarehouseColumnDefinition(key="actor_name", label="Actor", data_type="text"),
    InsightWarehouseColumnDefinition(key="status", label="Status", data_type="status"),
    InsightWarehouseColumnDefinition(key="amount", label="Amount", data_type="currency"),
    InsightWarehouseColumnDefinition(key="event_date", label="Event Date", data_type="date"),
    InsightWarehouseColumnDefinition(key="due_date", label="Due Date", data_type="date"),
    InsightWarehouseColumnDefinition(key="flags", label="Flags", data_type="flag", sortable=False),
]


def _build_filter_set(
    *,
    q: str | None,
    quick_view: str | None,
    project_id: UUID | None,
    source_types: list[str] | None,
    statuses: list[str] | None,
    entry_types: list[str] | None,
    flow_directions: list[str] | None,
    duplicate_only: bool,
    overdue_only: bool,
    date_field: str,
    date_from: date | None,
    date_to: date | None,
    amount_min: float | None,
    amount_max: float | None,
) -> InsightWarehouseFilterSet:
    return InsightWarehouseFilterSet(
        q=q,
        quick_view=quick_view,
        project_id=project_id,
        source_types=source_types or [],
        statuses=statuses or [],
        entry_types=entry_types or [],
        flow_directions=flow_directions or [],
        duplicate_only=duplicate_only,
        overdue_only=overdue_only,
        date_field=date_field,
        date_from=date_from,
        date_to=date_to,
        amount_min=amount_min,
        amount_max=amount_max,
    )


def _build_rows_query(
    *,
    q: str | None,
    quick_view: str | None,
    project_id: UUID | None,
    source_types: list[str] | None,
    statuses: list[str] | None,
    entry_types: list[str] | None,
    flow_directions: list[str] | None,
    duplicate_only: bool,
    overdue_only: bool,
    date_field: str,
    date_from: date | None,
    date_to: date | None,
    amount_min: float | None,
    amount_max: float | None,
    sort_by: str,
    sort_order: str,
    page: int,
    page_size: int,
) -> InsightWarehouseRowsQuery:
    return InsightWarehouseRowsQuery(
        q=q,
        quick_view=quick_view,
        project_id=project_id,
        source_types=source_types or [],
        statuses=statuses or [],
        entry_types=entry_types or [],
        flow_directions=flow_directions or [],
        duplicate_only=duplicate_only,
        overdue_only=overdue_only,
        date_field=date_field,
        date_from=date_from,
        date_to=date_to,
        amount_min=amount_min,
        amount_max=amount_max,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )


@router.get("/rows", response_model=StandardResponse[InsightWarehouseRowsResponse])
async def list_insight_warehouse_rows(
    q: str | None = Query(default=None, description="Global search across reference, project, actor, and note fields."),
    quick_view: str | None = Query(default=None, description="Optional preset warehouse view key."),
    project_id: UUID | None = Query(default=None),
    source_types: list[str] | None = Query(default=None),
    statuses: list[str] | None = Query(default=None),
    entry_types: list[str] | None = Query(default=None),
    flow_directions: list[str] | None = Query(default=None),
    duplicate_only: bool = Query(default=False),
    overdue_only: bool = Query(default=False),
    date_field: str = Query(default="event_date"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    amount_min: float | None = Query(default=None, ge=0),
    amount_max: float | None = Query(default=None, ge=0),
    sort_by: str = Query(default="event_date"),
    sort_order: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """
    Contract-first warehouse row endpoint.

    Returns the normalized row shape, paging envelope, and applied filters.
    The aggregation service will populate `items` in the next implementation step.
    """
    try:
        query = _build_rows_query(
            q=q,
            quick_view=quick_view,
            project_id=project_id,
            source_types=source_types,
            statuses=statuses,
            entry_types=entry_types,
            flow_directions=flow_directions,
            duplicate_only=duplicate_only,
            overdue_only=overdue_only,
            date_field=date_field,
            date_from=date_from,
            date_to=date_to,
            amount_min=amount_min,
            amount_max=amount_max,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
        )

        response = await build_insight_warehouse_rows(db, query)
        return StandardResponse(data=response)

    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.errors(),
        ) from exc


@router.get("/summary", response_model=StandardResponse[InsightWarehouseSummaryResponse])
async def get_insight_warehouse_summary(
    q: str | None = Query(default=None),
    quick_view: str | None = Query(default=None),
    project_id: UUID | None = Query(default=None),
    source_types: list[str] | None = Query(default=None),
    statuses: list[str] | None = Query(default=None),
    entry_types: list[str] | None = Query(default=None),
    flow_directions: list[str] | None = Query(default=None),
    duplicate_only: bool = Query(default=False),
    overdue_only: bool = Query(default=False),
    date_field: str = Query(default="event_date"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    amount_min: float | None = Query(default=None, ge=0),
    amount_max: float | None = Query(default=None, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    Contract-first summary endpoint for the warehouse header cards.
    """
    try:
        filters = _build_filter_set(
            q=q,
            quick_view=quick_view,
            project_id=project_id,
            source_types=source_types,
            statuses=statuses,
            entry_types=entry_types,
            flow_directions=flow_directions,
            duplicate_only=duplicate_only,
            overdue_only=overdue_only,
            date_field=date_field,
            date_from=date_from,
            date_to=date_to,
            amount_min=amount_min,
            amount_max=amount_max,
        )

        response = await build_insight_warehouse_summary(db, filters)
        return StandardResponse(data=response)

    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.errors(),
        ) from exc


@router.get("/export")
async def export_insight_warehouse(
    q: str | None = Query(default=None),
    quick_view: str | None = Query(default=None),
    project_id: UUID | None = Query(default=None),
    source_types: list[str] | None = Query(default=None),
    statuses: list[str] | None = Query(default=None),
    entry_types: list[str] | None = Query(default=None),
    flow_directions: list[str] | None = Query(default=None),
    duplicate_only: bool = Query(default=False),
    overdue_only: bool = Query(default=False),
    date_field: str = Query(default="event_date"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    amount_min: float | None = Query(default=None, ge=0),
    amount_max: float | None = Query(default=None, ge=0),
    format: str = Query(default="csv"),
    sort_by: str = Query(default="event_date"),
    sort_order: str = Query(default="desc"),
    db: AsyncSession = Depends(get_db),
):
    """
    Export the current warehouse view as CSV.
    """
    try:
        export_query = InsightWarehouseExportQuery(
            q=q,
            quick_view=quick_view,
            project_id=project_id,
            source_types=source_types or [],
            statuses=statuses or [],
            entry_types=entry_types or [],
            flow_directions=flow_directions or [],
            duplicate_only=duplicate_only,
            overdue_only=overdue_only,
            date_field=date_field,
            date_from=date_from,
            date_to=date_to,
            amount_min=amount_min,
            amount_max=amount_max,
            format=format,
        )

        if export_query.format == "json":
            file_name, file_content = await export_insight_warehouse_json(
                db,
                export_query,
                sort_by=sort_by,
                sort_order=sort_order,
            )
            media_type = "application/json; charset=utf-8"
        else:
            file_name, file_content = await export_insight_warehouse_csv(
                db,
                export_query,
                sort_by=sort_by,
                sort_order=sort_order,
            )
            media_type = "text/csv; charset=utf-8"
        return StreamingResponse(
            iter([file_content]),
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{file_name}"',
            },
        )

    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.errors(),
        ) from exc


@router.get("/filters", response_model=StandardResponse[InsightWarehouseFiltersResponse])
async def get_insight_warehouse_filters(db: AsyncSession = Depends(get_db)):
    """
    Return selectable metadata for the Insight Warehouse page:
    projects, quick views, filters, and default table columns.
    """
    try:
        project_result = await db.execute(select(Project).options(noload("*")).order_by(Project.name))
        projects = project_result.scalars().all()

        response = InsightWarehouseFiltersResponse(
            projects=[
                InsightWarehouseFilterOptionItem(value=str(project.id), label=project.name)
                for project in projects
            ],
            source_types=SOURCE_TYPE_OPTIONS,
            statuses=STATUS_OPTIONS,
            entry_types=ENTRY_TYPE_OPTIONS,
            flow_directions=FLOW_DIRECTION_OPTIONS,
            quick_views=QUICK_VIEW_OPTIONS,
            columns=COLUMN_OPTIONS,
            date_fields=DATE_FIELD_OPTIONS,
            sort_fields=SORT_FIELD_OPTIONS,
            export_formats=[
                InsightWarehouseFilterOptionItem(value="csv", label="CSV"),
                InsightWarehouseFilterOptionItem(value="json", label="JSON"),
            ],
            last_updated_at=None,
        )
        return StandardResponse(data=response)

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load Insight Warehouse filters: {exc}",
        ) from exc
