"""
Aggregation service for the Insight Warehouse page.

This service normalizes data from multiple source tables into one warehouse row
shape so the frontend can filter, search, sort, and paginate without knowing
the original source table details.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import csv
import io
import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.insight_schema import (
    InsightWarehouseExportQuery,
    InsightWarehouseFilterSet,
    InsightWarehouseFlag,
    InsightWarehouseNavigationTarget,
    InsightWarehousePageInfo,
    InsightWarehouseRow,
    InsightWarehouseRowsQuery,
    InsightWarehouseRowsResponse,
    InsightWarehouseSummaryCard,
    InsightWarehouseSummaryResponse,
)
from app.services.chat_analytics_service import (
    ChatAnalyticsSnapshot,
    _effective_request_amount,
    _load_snapshot,
    _normalize_name,
    _normalize_optional_name,
    _today,
)

INSTALLMENT_OUTFLOW_STATUSES = {"LOCKED", "PENDING", "PENDING_ADMIN", "ADVANCE", "APPROVED", "PAID"}
INSTALLMENT_INFLOW_STATUSES = {"BILLING", "RE-BILLING", "ACCEPT"}
INSTALLMENT_CLOSED_OVERDUE_STATUSES = {"APPROVED", "PAID", "ACCEPT"}
LARGE_AMOUNT_THRESHOLD = 100000.0


@dataclass
class WarehouseRecord:
    row: InsightWarehouseRow
    search_text: str


def _to_float(value: object) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _to_date(value: date | datetime | None) -> date | None:
    if value is None:
        return None
    return value.date() if isinstance(value, datetime) else value


def _latest_timestamp(*values: date | datetime | None) -> datetime | None:
    candidates: list[datetime] = []
    for value in values:
        if value is None:
            continue
        if isinstance(value, datetime):
            candidates.append(
                value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
            )
        else:
            candidates.append(datetime.combine(value, datetime.min.time(), tzinfo=timezone.utc))
    return max(candidates, default=None)


def _combine_text_parts(*values: object) -> str:
    parts: list[str] = []
    for value in values:
        cleaned = str(value or "").strip()
        if cleaned:
            parts.append(cleaned)
    return " | ".join(parts)


def _make_flags(
    *,
    duplicate: bool = False,
    overdue: bool = False,
    low_confidence: bool = False,
    flow_direction: str | None = None,
) -> list[InsightWarehouseFlag]:
    flags: list[InsightWarehouseFlag] = []
    if duplicate:
        flags.append(InsightWarehouseFlag(key="duplicate", label="Duplicate", tone="warning"))
    if overdue:
        flags.append(InsightWarehouseFlag(key="overdue", label="Overdue", tone="danger"))
    if low_confidence:
        flags.append(
            InsightWarehouseFlag(
                key="ocr_low_confidence",
                label="OCR Check",
                tone="warning",
            )
        )
    if flow_direction == "INFLOW":
        flags.append(InsightWarehouseFlag(key="inflow", label="Cash In", tone="positive"))
    elif flow_direction == "OUTFLOW":
        flags.append(InsightWarehouseFlag(key="outflow", label="Cash Out", tone="neutral"))
    return flags


def _row_search_text(row: InsightWarehouseRow) -> str:
    return " ".join(
        part.lower()
        for part in [
            row.source_type,
            row.project_name,
            row.actor_id,
            row.actor_name,
            row.reference_no,
            row.title,
            row.description,
            row.entry_type,
            row.flow_direction,
            row.request_type,
            row.status,
            *(row.tags or []),
        ]
        if part
    )


def _normalize_input_request_rows(snapshot: ChatAnalyticsSnapshot) -> list[WarehouseRecord]:
    records: list[WarehouseRecord] = []
    for request in snapshot.input_requests:
        project = snapshot.project_by_id.get(request.project_id)
        project_name = project.name if project else "Unknown Project"
        actor_id = _normalize_optional_name(request.subcontractor_id)
        actor_name = _normalize_name(request.requester_name or request.vendor_name, fallback="Unknown Requester")
        amount = _effective_request_amount(request)
        entry_type = (request.entry_type or "").upper() or None
        flow_direction = "INFLOW" if entry_type == "INCOME" else "OUTFLOW"
        is_duplicate = bool(request.is_duplicate_flag)
        title = request.request_type or f"{entry_type or 'REQUEST'} Request"
        description = _combine_text_parts(request.work_type, request.vendor_name, request.note)

        row = InsightWarehouseRow(
            id=f"INPUT_REQUEST:{request.id}",
            source_type="INPUT_REQUEST",
            source_id=str(request.id),
            project_id=request.project_id,
            project_name=project_name,
            actor_id=actor_id,
            actor_name=actor_name,
            reference_no=request.receipt_no or str(request.id),
            title=title,
            description=description or None,
            entry_type=entry_type,
            flow_direction=flow_direction,
            request_type=request.request_type,
            status=(request.status or "PENDING_ADMIN").upper(),
            amount=amount,
            currency="THB",
            event_date=request.request_date,
            due_date=None,
            approved_at=request.approved_at,
            paid_at=request.paid_at,
            created_at=request.created_at,
            updated_at=request.updated_at,
            is_duplicate_flag=is_duplicate,
            is_overdue=False,
            tags=[
                item
                for item in [
                    request.work_type,
                    request.request_type,
                    request.vendor_name,
                    request.payment_reference,
                ]
                if item
            ],
            flags=_make_flags(
                duplicate=is_duplicate,
                low_confidence=bool(request.ocr_low_confidence_fields),
                flow_direction=flow_direction,
            ),
            navigation_target=InsightWarehouseNavigationTarget(
                label="Open in Approval",
                path=(
                    f"/approval?request_id={request.id}&project_id={request.project_id}"
                ),
            ),
        )
        records.append(WarehouseRecord(row=row, search_text=_row_search_text(row)))
    return records


def _installment_direction_and_entry_type(status: str) -> tuple[str, str]:
    normalized_status = (status or "").upper()
    if normalized_status in INSTALLMENT_INFLOW_STATUSES:
        return "INFLOW", "INCOME"
    return "OUTFLOW", "EXPENSE"


def _normalize_installment_rows(snapshot: ChatAnalyticsSnapshot) -> list[WarehouseRecord]:
    records: list[WarehouseRecord] = []
    today = _today()

    for installment in snapshot.installments:
        boq_item = snapshot.boq_item_by_id.get(installment.boq_item_id)
        project = snapshot.project_by_id.get(boq_item.project_id) if boq_item else None
        project_id = project.id if project else None
        project_name = project.name if project else "Unknown Project"
        actor_id = _normalize_optional_name(installment.subcontractor_id)
        actor_name = actor_id or "System"
        status = (installment.status or "LOCKED").upper()
        flow_direction, entry_type = _installment_direction_and_entry_type(status)
        is_overdue = bool(installment.due_date) and status not in INSTALLMENT_CLOSED_OVERDUE_STATUSES and (
            bool(installment.is_overdue) or installment.due_date < today
        )
        title = installment.expense_category or f"Installment {installment.installment_no or '-'}"
        description = _combine_text_parts(
            installment.expense_type,
            installment.cost_type,
            boq_item.description if boq_item else None,
        )

        row = InsightWarehouseRow(
            id=f"INSTALLMENT:{installment.id}",
            source_type="INSTALLMENT",
            source_id=str(installment.id),
            project_id=project_id,
            project_name=project_name,
            actor_id=actor_id,
            actor_name=actor_name,
            reference_no=installment.installment_no or str(installment.id),
            title=title,
            description=description or None,
            entry_type=entry_type,
            flow_direction=flow_direction,
            request_type=installment.expense_type,
            status=status,
            amount=_to_float(installment.amount),
            currency="THB",
            event_date=installment.due_date,
            due_date=installment.due_date,
            approved_at=None,
            paid_at=None,
            created_at=None,
            updated_at=None,
            is_duplicate_flag=False,
            is_overdue=is_overdue,
            tags=[
                item
                for item in [
                    installment.expense_category,
                    installment.expense_type,
                    installment.cost_type,
                    boq_item.description if boq_item else None,
                ]
                if item
            ],
            flags=_make_flags(overdue=is_overdue, flow_direction=flow_direction),
            navigation_target=InsightWarehouseNavigationTarget(
                label="Open Project",
                path=(
                    f"/project/detail/{project_id}?source=installment&installment_id={installment.id}"
                    if project_id
                    else "/project/detail"
                ),
            ),
        )
        records.append(WarehouseRecord(row=row, search_text=_row_search_text(row)))
    return records


def _normalize_transaction_rows(snapshot: ChatAnalyticsSnapshot) -> list[WarehouseRecord]:
    records: list[WarehouseRecord] = []
    for transaction in snapshot.transactions:
        installment = snapshot.installment_by_id.get(transaction.installment_id)
        boq_item = (
            snapshot.boq_item_by_id.get(installment.boq_item_id)
            if installment is not None
            else None
        )
        project = snapshot.project_by_id.get(boq_item.project_id) if boq_item else None
        project_id = project.id if project else None
        project_name = project.name if project else "Unknown Project"
        actor_id = _normalize_optional_name(transaction.subcontractor_id) or (
            _normalize_optional_name(installment.subcontractor_id) if installment is not None else None
        )
        actor_name = actor_id or "System"
        amount = _to_float(transaction.net_payable) or _to_float(transaction.base_amount)
        title = installment.expense_category if installment is not None and installment.expense_category else "Recorded Payment"
        description = _combine_text_parts(
            installment.installment_no if installment is not None else None,
            installment.expense_type if installment is not None else None,
            boq_item.description if boq_item else None,
            f"Base {_to_float(transaction.base_amount):,.2f} THB",
            f"Net {_to_float(transaction.net_payable):,.2f} THB",
        )

        row = InsightWarehouseRow(
            id=f"TRANSACTION:{transaction.id}",
            source_type="TRANSACTION",
            source_id=str(transaction.id),
            project_id=project_id,
            project_name=project_name,
            actor_id=actor_id,
            actor_name=actor_name,
            reference_no=installment.installment_no if installment is not None else str(transaction.id),
            title=title,
            description=description or None,
            entry_type="EXPENSE",
            flow_direction="OUTFLOW",
            request_type=installment.expense_type if installment is not None else None,
            status="PAID",
            amount=amount,
            currency="THB",
            event_date=_to_date(transaction.approved_at),
            due_date=installment.due_date if installment is not None else None,
            approved_at=transaction.approved_at,
            paid_at=transaction.approved_at,
            created_at=transaction.approved_at,
            updated_at=None,
            is_duplicate_flag=False,
            is_overdue=False,
            tags=[
                item
                for item in [
                    installment.expense_category if installment is not None else None,
                    installment.expense_type if installment is not None else None,
                    boq_item.description if boq_item else None,
                ]
                if item
            ],
            flags=_make_flags(flow_direction="OUTFLOW"),
            navigation_target=InsightWarehouseNavigationTarget(
                label="Open Project",
                path=(
                    f"/project/detail/{project_id}?source=transaction&transaction_id={transaction.id}"
                    if project_id
                    else "/project/detail"
                ),
            ),
        )
        records.append(WarehouseRecord(row=row, search_text=_row_search_text(row)))
    return records


def _build_records(snapshot: ChatAnalyticsSnapshot) -> list[WarehouseRecord]:
    return [
        *_normalize_input_request_rows(snapshot),
        *_normalize_installment_rows(snapshot),
        *_normalize_transaction_rows(snapshot),
    ]


def _matches_quick_view(row: InsightWarehouseRow, quick_view: str | None) -> bool:
    if not quick_view or quick_view == "all_records":
        return True
    if quick_view == "pending_approval":
        return row.status in {"DRAFT", "PENDING", "PENDING_ADMIN", "ADVANCE", "LOCKED"}
    if quick_view == "overdue":
        return row.is_overdue
    if quick_view == "duplicate_risk":
        return row.is_duplicate_flag
    if quick_view == "paid_recently":
        return row.status == "PAID" or row.paid_at is not None
    if quick_view == "large_amount":
        return (row.amount or 0) >= LARGE_AMOUNT_THRESHOLD
    return True


def _matches_filters(row: InsightWarehouseRow, filters: InsightWarehouseFilterSet) -> bool:
    if filters.project_id is not None and row.project_id != filters.project_id:
        return False
    if filters.source_types and row.source_type not in filters.source_types:
        return False
    if filters.statuses and row.status not in filters.statuses:
        return False
    if filters.entry_types and (row.entry_type or "") not in filters.entry_types:
        return False
    if filters.flow_directions and row.flow_direction not in filters.flow_directions:
        return False
    if filters.duplicate_only and not row.is_duplicate_flag:
        return False
    if filters.overdue_only and not row.is_overdue:
        return False
    if not _matches_quick_view(row, filters.quick_view):
        return False

    selected_date = {
        "event_date": row.event_date,
        "due_date": row.due_date,
        "approved_at": _to_date(row.approved_at),
        "paid_at": _to_date(row.paid_at),
        "created_at": _to_date(row.created_at),
    }.get(filters.date_field)

    if filters.date_from and (selected_date is None or selected_date < filters.date_from):
        return False
    if filters.date_to and (selected_date is None or selected_date > filters.date_to):
        return False

    amount = row.amount or 0.0
    if filters.amount_min is not None and amount < filters.amount_min:
        return False
    if filters.amount_max is not None and amount > filters.amount_max:
        return False
    return True


def _apply_search(records: list[WarehouseRecord], query_text: str | None) -> list[WarehouseRecord]:
    if not query_text:
        return records
    normalized_query = query_text.strip().lower()
    if not normalized_query:
        return records
    return [record for record in records if normalized_query in record.search_text]


def _sort_value(row: InsightWarehouseRow, sort_by: str) -> tuple[int, object]:
    value = {
        "event_date": row.event_date,
        "due_date": row.due_date,
        "amount": row.amount,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "status": row.status,
        "project_name": row.project_name,
        "actor_name": row.actor_name,
    }.get(sort_by)

    if value is None:
        return (1, "")
    if isinstance(value, str):
        return (0, value.lower())
    return (0, value)


def _last_updated_at(rows: list[InsightWarehouseRow]) -> datetime | None:
    timestamps = [
        _latest_timestamp(
            row.updated_at,
            row.created_at,
            row.paid_at,
            row.approved_at,
            row.event_date,
            row.due_date,
        )
        for row in rows
    ]
    return max((item for item in timestamps if item is not None), default=None)


def _paginate_rows(rows: list[InsightWarehouseRow], page: int, page_size: int) -> tuple[list[InsightWarehouseRow], InsightWarehousePageInfo]:
    total_items = len(rows)
    total_pages = (total_items + page_size - 1) // page_size if total_items else 0
    start_index = (page - 1) * page_size
    end_index = start_index + page_size
    sliced_rows = rows[start_index:end_index]
    page_info = InsightWarehousePageInfo(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1 and total_pages > 0,
    )
    return sliced_rows, page_info


async def _collect_sorted_rows(
    db: AsyncSession,
    filters: InsightWarehouseFilterSet,
    *,
    sort_by: str = "event_date",
    sort_order: str = "desc",
) -> list[InsightWarehouseRow]:
    snapshot = await _load_snapshot(db, filters.project_id)
    records = _build_records(snapshot)
    filtered_records = [
        record for record in _apply_search(records, filters.q) if _matches_filters(record.row, filters)
    ]
    return [
        record.row
        for record in sorted(
            filtered_records,
            key=lambda record: _sort_value(record.row, sort_by),
            reverse=sort_order == "desc",
        )
    ]


async def list_insight_warehouse_rows(
    db: AsyncSession,
    query: InsightWarehouseRowsQuery,
) -> InsightWarehouseRowsResponse:
    sorted_rows = await _collect_sorted_rows(
        db,
        query,
        sort_by=query.sort_by,
        sort_order=query.sort_order,
    )

    paged_rows, page_info = _paginate_rows(sorted_rows, query.page, query.page_size)
    last_updated_at = _last_updated_at(sorted_rows)

    empty_state_message = None
    if not sorted_rows:
        empty_state_message = "No warehouse records matched the current filters."

    return InsightWarehouseRowsResponse(
        items=paged_rows,
        page_info=page_info,
        applied_filters=query,
        last_updated_at=last_updated_at,
        empty_state_message=empty_state_message,
    )


async def get_insight_warehouse_summary(
    db: AsyncSession,
    filters: InsightWarehouseFilterSet,
) -> InsightWarehouseSummaryResponse:
    filtered_rows = await _collect_sorted_rows(db, filters)

    pending_rows = [
        row for row in filtered_rows if row.status in {"DRAFT", "PENDING", "PENDING_ADMIN", "ADVANCE", "LOCKED"}
    ]
    overdue_rows = [row for row in filtered_rows if row.is_overdue]
    duplicate_rows = [row for row in filtered_rows if row.is_duplicate_flag]
    inflow_rows = [row for row in filtered_rows if row.flow_direction == "INFLOW"]
    outflow_rows = [row for row in filtered_rows if row.flow_direction == "OUTFLOW"]

    return InsightWarehouseSummaryResponse(
        cards=[
            InsightWarehouseSummaryCard(
                key="records",
                label="Total Records",
                count=len(filtered_rows),
                tone="neutral",
                description="All warehouse rows after the current filters are applied.",
            ),
            InsightWarehouseSummaryCard(
                key="pending",
                label="Pending Queue",
                count=len(pending_rows),
                amount=round(sum(row.amount or 0.0 for row in pending_rows), 2),
                tone="warning",
                description="Items still waiting for review, approval, or payment.",
            ),
            InsightWarehouseSummaryCard(
                key="overdue",
                label="Overdue Exposure",
                count=len(overdue_rows),
                amount=round(sum(row.amount or 0.0 for row in overdue_rows), 2),
                tone="danger",
                description="Rows with overdue receivable risk.",
            ),
            InsightWarehouseSummaryCard(
                key="duplicate",
                label="Duplicate Flags",
                count=len(duplicate_rows),
                tone="warning",
                description="Records flagged as possible duplicates.",
            ),
            InsightWarehouseSummaryCard(
                key="inflow",
                label="Cash In",
                amount=round(sum(row.amount or 0.0 for row in inflow_rows), 2),
                tone="positive",
                description="Filtered inflow total within the warehouse view.",
            ),
            InsightWarehouseSummaryCard(
                key="outflow",
                label="Cash Out",
                amount=round(sum(row.amount or 0.0 for row in outflow_rows), 2),
                tone="neutral",
                description="Filtered outflow total within the warehouse view.",
            ),
        ],
        applied_filters=filters,
        last_updated_at=_last_updated_at(filtered_rows),
    )


def _csv_row(row: InsightWarehouseRow) -> list[str]:
    return [
        row.id,
        row.source_type,
        row.source_id,
        str(row.project_id or ""),
        row.project_name or "",
        row.actor_id or "",
        row.actor_name or "",
        row.reference_no or "",
        row.title,
        row.description or "",
        row.entry_type or "",
        row.flow_direction,
        row.request_type or "",
        row.status,
        "" if row.amount is None else f"{row.amount:.2f}",
        row.currency or "THB",
        row.event_date.isoformat() if row.event_date else "",
        row.due_date.isoformat() if row.due_date else "",
        row.approved_at.isoformat() if row.approved_at else "",
        row.paid_at.isoformat() if row.paid_at else "",
        row.created_at.isoformat() if row.created_at else "",
        row.updated_at.isoformat() if row.updated_at else "",
        "true" if row.is_duplicate_flag else "false",
        "true" if row.is_overdue else "false",
        ", ".join(row.tags or []),
        ", ".join(flag.label for flag in row.flags),
        row.navigation_target.path if row.navigation_target else "",
    ]


async def export_insight_warehouse_csv(
    db: AsyncSession,
    query: InsightWarehouseExportQuery,
    *,
    sort_by: str = "event_date",
    sort_order: str = "desc",
) -> tuple[str, str]:
    rows = await _collect_sorted_rows(
        db,
        query,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "id",
            "source_type",
            "source_id",
            "project_id",
            "project_name",
            "actor_id",
            "actor_name",
            "reference_no",
            "title",
            "description",
            "entry_type",
            "flow_direction",
            "request_type",
            "status",
            "amount",
            "currency",
            "event_date",
            "due_date",
            "approved_at",
            "paid_at",
            "created_at",
            "updated_at",
            "is_duplicate_flag",
            "is_overdue",
            "tags",
            "flags",
            "navigation_path",
        ]
    )
    for row in rows:
        writer.writerow(_csv_row(row))

    today = _today().isoformat()
    file_name = f"insight-warehouse-{today}.csv"
    return file_name, buffer.getvalue()


async def export_insight_warehouse_json(
    db: AsyncSession,
    query: InsightWarehouseExportQuery,
    *,
    sort_by: str = "event_date",
    sort_order: str = "desc",
) -> tuple[str, str]:
    rows = await _collect_sorted_rows(
        db,
        query,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    file_name = f"insight-warehouse-{_today().isoformat()}.json"
    payload = {
        "status": "success",
        "data": {
            "items": [row.model_dump(mode="json") for row in rows],
            "count": len(rows),
        },
    }
    return file_name, json.dumps(payload, ensure_ascii=False, indent=2)
