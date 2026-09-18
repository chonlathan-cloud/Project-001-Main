"""Bounded, version-aware Core Pilot reads for the Product MCP."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.core.config import Settings, get_settings
from app.models.boq import BOQItem, Project
from app.models.boq_v2 import (
    BOQV2BaselineChangeOrder,
    BOQV2Document,
    BOQV2ProjectBaseline,
    BOQV2Revision,
    BOQV2ScopeNode,
)
from app.schemas.mcp_schema import (
    McpAccessContext,
    McpBOQCompareRequest,
    McpBOQVersionRequest,
    McpBOQVersionsRequest,
    McpFetchRequest,
    McpPrincipalRequest,
    McpProjectAccessRequest,
    McpProjectListRequest,
    McpProjectRequest,
    McpProjectSummaryRequest,
    McpSearchRequest,
    McpUserAccessRequest,
)
from app.services import daily_report_service
from app.services.identity_service import (
    get_admin,
    get_customer,
    get_subcontractor,
    list_admins,
    list_customers,
    list_subcontractors,
)
from app.services.mcp_access_service import resolve_mcp_access
from app.services.project_budget_service import (
    active_budget_amount,
    load_project_budget_context,
    load_project_budget_contexts,
)

MAX_BOQ_LINES = 500


class McpNotFoundOrForbidden(RuntimeError):
    pass


class McpInvalidInput(RuntimeError):
    pass


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _decimal_string(value: object, places: str = "0.01") -> str:
    amount = Decimal(str(value or 0)).quantize(Decimal(places), rounding=ROUND_HALF_UP)
    return format(amount, "f")


def _money(value: object) -> dict[str, str]:
    return {"amount": _decimal_string(value), "currency": "THB"}


def _encode_cursor(scope: str, offset: int, settings: Settings) -> str:
    payload = json.dumps(
        {"v": 1, "scope": scope, "offset": offset},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    signature = hmac.new(
        settings.effective_mcp_cursor_secret.encode(),
        b"projects-001-mcp-cursor-v1\0" + payload,
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(payload + b"." + signature).decode().rstrip("=")


def _decode_cursor(cursor: str | None, scope: str, settings: Settings) -> int:
    if not cursor:
        return 0
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        decoded = base64.urlsafe_b64decode(padded)
        payload, signature = decoded.rsplit(b".", 1)
        expected = hmac.new(
            settings.effective_mcp_cursor_secret.encode(),
            b"projects-001-mcp-cursor-v1\0" + payload,
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("signature")
        data = json.loads(payload)
        if data != {"v": 1, "scope": scope, "offset": int(data["offset"])}:
            raise ValueError("scope")
        offset = int(data["offset"])
        if offset < 0 or offset > 1_000_000:
            raise ValueError("offset")
        return offset
    except Exception as exc:
        raise McpInvalidInput("Invalid or expired cursor.") from exc


def _authorize(
    request: McpPrincipalRequest,
    *,
    project_id: str | None = None,
    required_permissions: frozenset[str] = frozenset(),
    settings: Settings | None = None,
    access_context: Any | None = None,
) -> McpAccessContext:
    access = access_context or resolve_mcp_access(request, settings=settings)
    if (
        not access.active
        or (access_context is None and not access.external_mcp_enabled)
        or access.role not in {"owner", "admin"}
        or (access.role == "admin" and "mcp_access" not in access.permissions)
    ):
        raise McpNotFoundOrForbidden
    if access.role != "owner" and not required_permissions.issubset(
        set(access.permissions)
    ):
        raise McpNotFoundOrForbidden
    if (
        project_id
        and access.role != "owner"
        and not access.all_projects_read
        and project_id not in access.assigned_project_ids
    ):
        raise McpNotFoundOrForbidden
    return access


def _project_scope(access: McpAccessContext) -> set[str] | None:
    if access.role == "owner" or access.all_projects_read:
        return None
    return set(access.assigned_project_ids)


def _valid_project_ids(values: list[str] | set[str]) -> list[str]:
    normalized: set[str] = set()
    for value in values:
        try:
            normalized.add(str(UUID(str(value))))
        except (TypeError, ValueError, AttributeError):
            continue
    return sorted(normalized)


def _project_url(project_id: UUID | str, settings: Settings) -> str:
    return f"{settings.frontend_base_url}/project/detail/{project_id}"


def _project_item(
    project: Project,
    settings: Settings,
    total_budget: object = 0,
    *,
    budget_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "project_id": str(project.id),
        "name": project.name,
        "project_type": project.project_type,
        "status": project.status,
        "contingency_budget": _money(project.contingency_budget),
        "current_boq_budget": _money(total_budget),
        "budget_snapshot": budget_snapshot,
        "product_url": _project_url(project.id, settings),
    }


async def list_projects(
    db: AsyncSession,
    request: McpProjectListRequest,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    app_settings = settings or get_settings()
    access = _authorize(request, settings=app_settings)
    offset = _decode_cursor(request.cursor, "projects", app_settings)
    statement = (
        select(Project)
        .options(noload("*"))
        .order_by(Project.name, Project.id)
    )
    scope = _project_scope(access)
    if scope is not None:
        if not scope:
            return {
                "items": [],
                "returned_count": 0,
                "next_cursor": None,
                "source_read_at": _utc_now(),
            }
        statement = statement.where(Project.id.in_([UUID(item) for item in scope]))
    statuses = {item.strip().upper() for item in request.statuses if item.strip()}
    if statuses:
        statement = statement.where(func.upper(Project.status).in_(statuses))
    projects = list(
        (
            await db.execute(statement.offset(offset).limit(request.limit + 1))
        ).scalars().all()
    )
    has_more = len(projects) > request.limit
    page = projects[: request.limit]
    contexts = await load_project_budget_contexts(db, [project.id for project in page])
    return {
        "items": [
            _project_item(
                project,
                app_settings,
                (
                    active_budget_amount(contexts[project.id], consumer="MCP")
                    if project.id in contexts
                    else 0
                ),
                budget_snapshot=(
                    contexts[project.id].snapshot.model_dump(mode="json")
                    if project.id in contexts
                    else None
                ),
            )
            for project in page
        ],
        "returned_count": len(page),
        "next_cursor": (
            _encode_cursor("projects", offset + len(page), app_settings) if has_more else None
        ),
        "source_read_at": _utc_now(),
    }


async def _load_project(db: AsyncSession, project_id: UUID) -> Project:
    project = (
        await db.execute(
            select(Project).options(noload("*")).where(Project.id == project_id)
        )
    ).scalar_one_or_none()
    if project is None:
        raise McpNotFoundOrForbidden
    return project


async def _current_customer_budget(db: AsyncSession, project_id: UUID) -> Decimal:
    context = await load_project_budget_context(db, project_id)
    return Decimal(
        active_budget_amount(context, consumer="MCP")
        if context is not None
        else "0.00"
    )


async def get_project(
    db: AsyncSession,
    request: McpProjectRequest,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    app_settings = settings or get_settings()
    _authorize(request, project_id=str(request.project_id), settings=app_settings)
    project = await _load_project(db, request.project_id)
    budget_context = await load_project_budget_context(db, request.project_id)
    current_customer_budget = Decimal(
        active_budget_amount(budget_context, consumer="MCP")
        if budget_context is not None
        else "0.00"
    )
    return {
        **_project_item(
            project,
            app_settings,
            current_customer_budget,
            budget_snapshot=(
                budget_context.snapshot.model_dump(mode="json")
                if budget_context is not None
                else None
            ),
        ),
        "overhead_percent": _decimal_string(project.overhead_percent),
        "profit_percent": _decimal_string(project.profit_percent),
        "vat_percent": _decimal_string(project.vat_percent),
        "source_read_at": _utc_now(),
    }


def _version_id(project_id: UUID | str, created_at: datetime) -> str:
    digest = hashlib.sha256(
        f"{project_id}|{_as_utc(created_at).isoformat()}".encode()
    ).hexdigest()[:16]
    project_part = str(project_id).replace("-", "")
    return f"boqv_{project_part}_{digest}"


def build_boq_manifests(project_id: UUID | str, boundaries: list[datetime | None]) -> list[dict[str, Any]]:
    normalized = sorted({_as_utc(item) for item in boundaries if item is not None})
    if any(item is None for item in boundaries):
        normalized.insert(0, datetime(1970, 1, 1, tzinfo=UTC))
    manifests: list[dict[str, Any]] = []
    for index, created_at in enumerate(normalized):
        valid_to = normalized[index + 1] if index + 1 < len(normalized) else None
        manifests.append(
            {
                "version_id": _version_id(project_id, created_at),
                "version_number": index + 1,
                "valid_from": created_at,
                "valid_to": valid_to,
                "is_current": valid_to is None,
            }
        )
    return manifests


async def _boq_manifests(db: AsyncSession, project_id: UUID) -> list[dict[str, Any]]:
    boundaries = list(
        (
            await db.execute(
                select(BOQItem.valid_from)
                .where(BOQItem.project_id == project_id)
                .distinct()
            )
        ).scalars().all()
    )
    return build_boq_manifests(project_id, boundaries)


async def _snapshot_rows(
    db: AsyncSession,
    project_id: UUID,
    *,
    as_of: datetime | None,
) -> list[BOQItem]:
    statement = (
        select(BOQItem)
        .options(noload("*"))
        .where(BOQItem.project_id == project_id)
        .order_by(
            BOQItem.boq_type,
            BOQItem.sheet_name,
            BOQItem.wbs_level,
            BOQItem.item_no,
            BOQItem.id,
        )
    )
    if as_of is None:
        statement = statement.where(BOQItem.valid_to.is_(None))
    else:
        boundary = _as_utc(as_of)
        statement = statement.where(
            or_(BOQItem.valid_from.is_(None), BOQItem.valid_from <= boundary),
            or_(BOQItem.valid_to.is_(None), BOQItem.valid_to > boundary),
        )
    return list((await db.execute(statement)).scalars().all())


def _stable_line_ids(items: list[BOQItem]) -> dict[str, str]:
    item_by_id = {str(item.id): item for item in items}
    memo: dict[str, str] = {}

    def line_path(item: BOQItem) -> str:
        item_id = str(item.id)
        if item_id in memo:
            return memo[item_id]
        own = str(item.item_no or "").strip() or f"level-{item.wbs_level}"
        parent = item_by_id.get(str(item.parent_id)) if item.parent_id else None
        path = f"{line_path(parent)}/{own}" if parent is not None else own
        memo[item_id] = path
        return path

    base_values = [
        "|".join(
            [
                str(item.boq_type or "").strip().upper(),
                str(item.sheet_name or "").strip().lower(),
                line_path(item).lower(),
            ]
        )
        for item in items
    ]
    counts = Counter(base_values)
    seen: Counter[str] = Counter()
    result: dict[str, str] = {}
    for item, base in zip(items, base_values, strict=True):
        seen[base] += 1
        disambiguated = f"{base}|{seen[base]}" if counts[base] > 1 else base
        result[str(item.id)] = "boql_" + hashlib.sha256(disambiguated.encode()).hexdigest()[:24]
    return result


def _boq_line_reference(project_id: UUID | str, line_id: str) -> str:
    return f"projects_boq:boq_line:{project_id}.{line_id}"


def _serialize_boq_line(
    item: BOQItem,
    stable_ids: dict[str, str],
) -> dict[str, Any]:
    return {
        "line_id": stable_ids[str(item.id)],
        "parent_line_id": stable_ids.get(str(item.parent_id)) if item.parent_id else None,
        "boq_type": item.boq_type,
        "sheet_name": item.sheet_name,
        "wbs_level": item.wbs_level,
        "item_no": item.item_no,
        "description": item.description,
        "quantity": _decimal_string(item.qty, "0.0001"),
        "unit": item.unit,
        "material_unit_price": _money(item.material_unit_price),
        "labor_unit_price": _money(item.labor_unit_price),
        "total_material": _money(item.total_material),
        "total_labor": _money(item.total_labor),
        "grand_total": _money(item.grand_total),
    }


def serialize_boq_snapshot(
    project_id: UUID | str,
    project_name: str,
    manifest: dict[str, Any] | None,
    items: list[BOQItem],
    settings: Settings,
) -> dict[str, Any]:
    stable_ids = _stable_line_ids(items)
    serialized = [_serialize_boq_line(item, stable_ids) for item in items[:MAX_BOQ_LINES]]
    return {
        "project_id": str(project_id),
        "project_name": project_name,
        "version": manifest,
        "lines": serialized,
        "line_count": len(items),
        "returned_count": len(serialized),
        "truncated": len(items) > MAX_BOQ_LINES,
        "product_url": _project_url(project_id, settings),
        "source_read_at": _utc_now(),
        "source_kind": "LEGACY",
    }


def _v2_version_id(baseline_id: UUID | str) -> str:
    return f"boqv2_{str(baseline_id).replace('-', '')}"


def _v2_line_id(document_id: UUID | str, logical_id: UUID | str) -> str:
    return (
        "boqlv2_"
        f"{str(document_id).replace('-', '')}_"
        f"{str(logical_id).replace('-', '')}"
    )


async def _v2_boq_manifests(
    db: AsyncSession,
    project_id: UUID,
) -> list[dict[str, Any]]:
    baselines = list(
        (
            await db.execute(
                select(BOQV2ProjectBaseline)
                .options(noload("*"))
                .where(BOQV2ProjectBaseline.project_id == project_id)
                .order_by(BOQV2ProjectBaseline.version, BOQV2ProjectBaseline.id)
            )
        )
        .scalars()
        .all()
    )
    return [
        {
            "version_id": _v2_version_id(baseline.id),
            "version_number": baseline.version,
            "source_kind": "V2",
            "baseline_id": str(baseline.id),
            "main_revision_id": str(baseline.main_revision_id),
            "cost_plan_id": str(baseline.cost_plan_id) if baseline.cost_plan_id else None,
            "calculation_version": baseline.calculation_version,
            "valid_from": baseline.effective_from,
            "valid_to": baseline.effective_to,
            "is_current": baseline.is_active,
        }
        for baseline in baselines
    ]


async def _v2_snapshot(
    db: AsyncSession,
    project: Project,
    manifest: dict[str, Any],
    settings: Settings,
    *,
    budget_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    baseline_id = UUID(str(manifest["baseline_id"]))
    baseline = (
        await db.execute(
            select(BOQV2ProjectBaseline)
            .options(noload("*"))
            .where(BOQV2ProjectBaseline.id == baseline_id)
        )
    ).scalar_one_or_none()
    if baseline is None or baseline.project_id != project.id:
        raise McpNotFoundOrForbidden

    change_orders = list(
        (
            await db.execute(
                select(BOQV2BaselineChangeOrder)
                .options(noload("*"))
                .where(BOQV2BaselineChangeOrder.baseline_id == baseline.id)
                .order_by(BOQV2BaselineChangeOrder.position)
            )
        )
        .scalars()
        .all()
    )
    revision_ids = [baseline.main_revision_id, *[row.revision_id for row in change_orders]]
    revision_rows = (
        await db.execute(
            select(BOQV2Revision, BOQV2Document)
            .join(BOQV2Document, BOQV2Document.id == BOQV2Revision.document_id)
            .where(BOQV2Revision.id.in_(revision_ids))
        )
    ).all()
    revision_by_id = {revision.id: (revision, document) for revision, document in revision_rows}
    nodes = list(
        (
            await db.execute(
                select(BOQV2ScopeNode)
                .options(noload("*"))
                .where(BOQV2ScopeNode.revision_id.in_(revision_ids))
                .order_by(
                    BOQV2ScopeNode.revision_id,
                    BOQV2ScopeNode.position,
                    BOQV2ScopeNode.id,
                )
            )
        )
        .scalars()
        .all()
    )
    nodes_by_revision: dict[UUID, list[BOQV2ScopeNode]] = {}
    for node in nodes:
        nodes_by_revision.setdefault(node.revision_id, []).append(node)

    lines: list[dict[str, Any]] = []
    for revision_id in revision_ids:
        revision_context = revision_by_id.get(revision_id)
        if revision_context is None:
            continue
        _revision, document = revision_context
        revision_nodes = nodes_by_revision.get(revision_id, [])
        logical_by_row = {node.id: node.logical_id for node in revision_nodes}
        boq_type = (
            "V2_MAIN"
            if document.document_kind in {"MAIN", "ALTERNATIVE"}
            else f"V2_CHANGE_ORDER_{document.direction}"
        )
        for node in revision_nodes[:MAX_BOQ_LINES - len(lines)]:
            line_id = _v2_line_id(document.id, node.logical_id)
            parent_logical_id = logical_by_row.get(node.parent_id)
            lines.append(
                {
                    "line_id": line_id,
                    "parent_line_id": (
                        _v2_line_id(document.id, parent_logical_id)
                        if parent_logical_id is not None
                        else None
                    ),
                    "boq_type": boq_type,
                    "sheet_name": document.document_number,
                    "wbs_level": node.node_kind,
                    "item_no": node.item_code,
                    "description": node.description,
                    "quantity": (
                        _decimal_string(node.quantity, "0.0001")
                        if node.quantity is not None
                        else None
                    ),
                    "unit": node.unit,
                    "material_unit_price": _money(node.sell_material_unit_rate),
                    "labor_unit_price": _money(node.sell_labor_unit_rate),
                    "total_material": None,
                    "total_labor": None,
                    "grand_total": _money(node.sell_total),
                    "document_id": str(document.id),
                    "revision_id": str(revision_id),
                    "logical_id": str(node.logical_id),
                    "node_kind": node.node_kind,
                    "inclusion_state": node.inclusion_state,
                }
            )
        if len(lines) >= MAX_BOQ_LINES:
            break
    return {
        "project_id": str(project.id),
        "project_name": project.name,
        "source_kind": "V2",
        "budget_snapshot": budget_snapshot,
        "version": manifest,
        "lines": lines,
        "line_count": len(nodes),
        "returned_count": len(lines),
        "truncated": len(nodes) > MAX_BOQ_LINES,
        "product_url": _project_url(project.id, settings),
        "source_read_at": _utc_now(),
    }


async def get_boq_current(
    db: AsyncSession,
    request: McpProjectRequest,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    app_settings = settings or get_settings()
    _authorize(request, project_id=str(request.project_id), settings=app_settings)
    project = await _load_project(db, request.project_id)
    context = await load_project_budget_context(db, request.project_id)
    if context is not None and context.snapshot.source_kind == "V2":
        if context.snapshot.baseline_id is None:
            return {
                "project_id": str(project.id),
                "project_name": project.name,
                "source_kind": "V2",
                "budget_snapshot": context.snapshot.model_dump(mode="json"),
                "version": None,
                "lines": [],
                "line_count": 0,
                "returned_count": 0,
                "truncated": False,
                "product_url": _project_url(project.id, app_settings),
                "source_read_at": _utc_now(),
            }
        manifests = await _v2_boq_manifests(db, request.project_id)
        manifest = next(
            (
                item
                for item in manifests
                if item["baseline_id"] == str(context.snapshot.baseline_id)
            ),
            None,
        )
        if manifest is None:
            raise McpNotFoundOrForbidden
        return await _v2_snapshot(
            db,
            project,
            manifest,
            app_settings,
            budget_snapshot=context.snapshot.model_dump(mode="json"),
        )
    manifests = await _boq_manifests(db, request.project_id)
    rows = await _snapshot_rows(db, request.project_id, as_of=None)
    return serialize_boq_snapshot(
        request.project_id,
        project.name,
        manifests[-1] if manifests else None,
        rows,
        app_settings,
    )


async def list_boq_versions(
    db: AsyncSession,
    request: McpBOQVersionsRequest,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    app_settings = settings or get_settings()
    _authorize(request, project_id=str(request.project_id), settings=app_settings)
    await _load_project(db, request.project_id)
    offset = _decode_cursor(request.cursor, f"boq-versions:{request.project_id}", app_settings)
    legacy_manifests = [
        {**item, "source_kind": "LEGACY"}
        for item in await _boq_manifests(db, request.project_id)
    ]
    v2_manifests = await _v2_boq_manifests(db, request.project_id)
    manifests = sorted(
        [*legacy_manifests, *v2_manifests],
        key=lambda item: (_as_utc(item["valid_from"]), item["version_id"]),
        reverse=True,
    )
    page = manifests[offset : offset + request.limit]
    has_more = offset + len(page) < len(manifests)
    return {
        "project_id": str(request.project_id),
        "items": page,
        "returned_count": len(page),
        "next_cursor": (
            _encode_cursor(
                f"boq-versions:{request.project_id}",
                offset + len(page),
                app_settings,
            )
            if has_more
            else None
        ),
        "source_read_at": _utc_now(),
    }


def _select_manifest(
    manifests: list[dict[str, Any]],
    *,
    version: str | None = None,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    if version is not None:
        normalized = version.strip().lower().removeprefix("v")
        for item in manifests:
            if item["version_id"] == version or str(item["version_number"]) == normalized:
                return item
    elif as_of is not None:
        boundary = _as_utc(as_of)
        eligible = [item for item in manifests if item["valid_from"] <= boundary]
        if eligible:
            return eligible[-1]
    raise McpNotFoundOrForbidden


async def get_boq_version(
    db: AsyncSession,
    request: McpBOQVersionRequest,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    app_settings = settings or get_settings()
    _authorize(request, project_id=str(request.project_id), settings=app_settings)
    project = await _load_project(db, request.project_id)
    v2_manifests = await _v2_boq_manifests(db, request.project_id)
    if request.version is not None and request.version.startswith("boqv2_"):
        manifest = _select_manifest(v2_manifests, version=request.version)
        context = await load_project_budget_context(
            db,
            request.project_id,
            as_of=manifest["valid_from"],
        )
        return await _v2_snapshot(
            db,
            project,
            manifest,
            app_settings,
            budget_snapshot=(
                context.snapshot.model_dump(mode="json") if context else None
            ),
        )
    if request.as_of is not None:
        context = await load_project_budget_context(
            db,
            request.project_id,
            as_of=request.as_of,
        )
        if context is not None and context.snapshot.source_kind == "V2":
            manifest = _select_manifest(v2_manifests, as_of=request.as_of)
            return await _v2_snapshot(
                db,
                project,
                manifest,
                app_settings,
                budget_snapshot=context.snapshot.model_dump(mode="json"),
            )
    manifests = await _boq_manifests(db, request.project_id)
    manifest = _select_manifest(manifests, version=request.version, as_of=request.as_of)
    rows = await _snapshot_rows(db, request.project_id, as_of=manifest["valid_from"])
    return serialize_boq_snapshot(
        request.project_id,
        project.name,
        manifest,
        rows,
        app_settings,
    )


def compare_boq_snapshots(
    snapshot_a: dict[str, Any],
    snapshot_b: dict[str, Any],
) -> dict[str, Any]:
    lines_a = {item["line_id"]: item for item in snapshot_a["lines"]}
    lines_b = {item["line_id"]: item for item in snapshot_b["lines"]}
    comparable_fields = (
        "parent_line_id",
        "boq_type",
        "sheet_name",
        "wbs_level",
        "item_no",
        "description",
        "quantity",
        "unit",
        "material_unit_price",
        "labor_unit_price",
        "total_material",
        "total_labor",
        "grand_total",
    )
    added = [lines_b[key] for key in sorted(lines_b.keys() - lines_a.keys())]
    removed = [lines_a[key] for key in sorted(lines_a.keys() - lines_b.keys())]
    changed: list[dict[str, Any]] = []
    for key in sorted(lines_a.keys() & lines_b.keys()):
        fields = [name for name in comparable_fields if lines_a[key][name] != lines_b[key][name]]
        if fields:
            changed.append(
                {"line_id": key, "changed_fields": fields, "before": lines_a[key], "after": lines_b[key]}
            )
    return {
        "version_a": snapshot_a["version"],
        "version_b": snapshot_b["version"],
        "added": added,
        "removed": removed,
        "changed": changed,
        "unchanged_count": len(lines_a.keys() & lines_b.keys()) - len(changed),
        "truncated": bool(snapshot_a.get("truncated") or snapshot_b.get("truncated")),
    }


async def compare_boq_versions(
    db: AsyncSession,
    request: McpBOQCompareRequest,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    app_settings = settings or get_settings()
    _authorize(request, project_id=str(request.project_id), settings=app_settings)
    project = await _load_project(db, request.project_id)
    legacy_manifests = await _boq_manifests(db, request.project_id)
    v2_manifests = await _v2_boq_manifests(db, request.project_id)

    async def load_selected(version: str) -> dict[str, Any]:
        if version.startswith("boqv2_"):
            selected = _select_manifest(v2_manifests, version=version)
            return await _v2_snapshot(db, project, selected, app_settings)
        selected = _select_manifest(legacy_manifests, version=version)
        rows = await _snapshot_rows(
            db, request.project_id, as_of=selected["valid_from"]
        )
        return serialize_boq_snapshot(
            request.project_id, project.name, selected, rows, app_settings
        )

    snapshot_a = await load_selected(request.version_a)
    snapshot_b = await load_selected(request.version_b)
    result = compare_boq_snapshots(snapshot_a, snapshot_b)
    result.update(
        {
            "project_id": str(request.project_id),
            "project_name": project.name,
            "product_url": _project_url(request.project_id, app_settings),
            "source_read_at": _utc_now(),
        }
    )
    return result


async def get_project_summary(
    db: AsyncSession,
    request: McpProjectSummaryRequest,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    app_settings = settings or get_settings()
    _authorize(request, project_id=str(request.project_id), settings=app_settings)
    project = await _load_project(db, request.project_id)
    context = await load_project_budget_context(
        db,
        request.project_id,
        as_of=request.as_of,
    )
    if context is not None and context.snapshot.source_kind == "V2":
        snapshot = context.snapshot
        current_budget = active_budget_amount(context, consumer="MCP")
        return {
            "project": _project_item(
                project,
                app_settings,
                current_budget,
                budget_snapshot=snapshot.model_dump(mode="json"),
            ),
            "boq": {
                "version": {
                    "version_id": (
                        _v2_version_id(snapshot.baseline_id)
                        if snapshot.baseline_id
                        else None
                    ),
                    "version_number": snapshot.baseline_version,
                    "source_kind": "V2",
                    "baseline_id": (
                        str(snapshot.baseline_id) if snapshot.baseline_id else None
                    ),
                },
                "line_count": None,
                "customer_budget": _money(current_budget),
                "subcontractor_budget": (
                    _money(snapshot.forecast_cost)
                    if snapshot.forecast_cost is not None
                    else None
                ),
                "gross_margin": (
                    _money(snapshot.forecast_margin)
                    if snapshot.forecast_margin is not None
                    else None
                ),
                "status": snapshot.status,
                "cost_completeness": snapshot.cost_completeness.model_dump(mode="json"),
            },
            "calculation_method": "active_project_budget_snapshot_v2",
            "source_read_at": _utc_now(),
        }
    manifests = await _boq_manifests(db, request.project_id)
    manifest = (
        _select_manifest(manifests, as_of=request.as_of)
        if request.as_of is not None
        else manifests[-1]
        if manifests
        else None
    )
    rows = await _snapshot_rows(
        db,
        request.project_id,
        as_of=manifest["valid_from"] if manifest and request.as_of is not None else None,
    )
    customer_total = sum(
        Decimal(str(item.grand_total or 0))
        for item in rows
        if item.parent_id is None and item.boq_type == "CUSTOMER"
    )
    subcontractor_total = sum(
        Decimal(str(item.grand_total or 0))
        for item in rows
        if item.parent_id is None and item.boq_type == "SUBCONTRACTOR"
    )
    return {
        "project": _project_item(
            project,
            app_settings,
            customer_total,
            budget_snapshot=(
                context.snapshot.model_dump(mode="json") if context else None
            ),
        ),
        "boq": {
            "version": manifest,
            "line_count": len(rows),
            "customer_budget": _money(customer_total),
            "subcontractor_budget": _money(subcontractor_total),
            "gross_margin": _money(customer_total - subcontractor_total),
        },
        "calculation_method": "current_or_selected_scd2_snapshot_root_line_sum_v1",
        "source_read_at": _utc_now(),
    }


async def list_project_access(
    request: McpProjectAccessRequest,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    app_settings = settings or get_settings()
    _authorize(request, project_id=str(request.project_id), settings=app_settings)
    offset = _decode_cursor(request.cursor, f"project-access:{request.project_id}", app_settings)
    members: list[dict[str, Any]] = []
    for entry in list_admins():
        assigned = daily_report_service.list_membership_project_ids(
            principal_type="admin", principal_id=entry.email
        )
        if entry.role != "owner" and not entry.mcp_all_projects_read and str(request.project_id) not in assigned:
            continue
        members.append(
            {
                "user_id": f"admin.{entry.id}",
                "principal_type": "admin",
                "display_name": entry.display_name,
                "role": entry.role,
                "roles": entry.roles,
                "active": entry.is_active,
                "external_mcp_enabled": (
                    entry.external_mcp_enabled
                    and entry.role in app_settings.mcp_allowed_roles
                ),
                "access_basis": (
                    "owner" if entry.role == "owner" else "all_projects" if entry.mcp_all_projects_read else "assigned"
                ),
            }
        )
    for entry in list_customers():
        assigned = daily_report_service.list_membership_project_ids(
            principal_type="customer", principal_id=entry.id
        )
        if str(request.project_id) not in assigned:
            continue
        members.append(
            {
                "user_id": f"customer.{entry.id}",
                "principal_type": "customer",
                "display_name": entry.contact_name or entry.name,
                "role": "customer",
                "roles": ["customer"],
                "active": entry.is_active,
                "external_mcp_enabled": False,
                "access_basis": "assigned",
            }
        )
    for entry in list_subcontractors():
        assigned = set(entry.assigned_project_ids)
        assigned.update(
            daily_report_service.list_membership_project_ids(
                principal_type="subcontractor", principal_id=entry.id
            )
        )
        if str(request.project_id) not in assigned:
            continue
        members.append(
            {
                "user_id": f"subcontractor.{entry.id}",
                "principal_type": "subcontractor",
                "display_name": entry.contact_name or entry.name,
                "role": "subcontractor",
                "roles": ["subcontractor"],
                "active": entry.is_active,
                "external_mcp_enabled": False,
                "access_basis": "assigned",
            }
        )
    members.sort(key=lambda item: (str(item["display_name"] or "").lower(), item["user_id"]))
    page = members[offset : offset + request.limit]
    has_more = offset + len(page) < len(members)
    return {
        "project_id": str(request.project_id),
        "items": page,
        "returned_count": len(page),
        "next_cursor": (
            _encode_cursor(
                f"project-access:{request.project_id}", offset + len(page), app_settings
            )
            if has_more
            else None
        ),
        "source_read_at": _utc_now(),
    }


async def get_user_access(
    request: McpUserAccessRequest,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    app_settings = settings or get_settings()
    caller = _authorize(request, settings=app_settings)
    principal_type, separator, raw_user_id = request.user_id.partition(".")
    if not separator or principal_type not in {"admin", "customer", "subcontractor"}:
        principal_type = "admin"
        raw_user_id = request.user_id
    if caller.role != "owner" and request.user_id not in {
        caller.user_id,
        f"admin.{caller.user_id}",
    }:
        raise McpNotFoundOrForbidden
    try:
        if principal_type == "admin":
            entry = get_admin(raw_user_id)
            assigned = daily_report_service.list_membership_project_ids(
                principal_type="admin", principal_id=entry.email
            )
            assigned = _valid_project_ids(assigned)
            all_projects_read = entry.role == "owner" or entry.mcp_all_projects_read
            return {
                "user_id": f"admin.{entry.id}",
                "principal_type": "admin",
                "display_name": entry.display_name,
                "role": entry.role,
                "roles": entry.roles,
                "active": entry.is_active,
                "external_mcp_enabled": (
                    entry.external_mcp_enabled
                    and entry.role in app_settings.mcp_allowed_roles
                ),
                "permissions": entry.mcp_permissions,
                "all_projects_read": all_projects_read,
                "assigned_project_ids": [] if all_projects_read else assigned,
                "authorization_updated_at": entry.updated_at,
                "source_read_at": _utc_now(),
            }
        if principal_type == "customer":
            entry = get_customer(raw_user_id)
            assigned = daily_report_service.list_membership_project_ids(
                principal_type="customer", principal_id=entry.id
            )
            assigned = _valid_project_ids(assigned)
            display_name = entry.contact_name or entry.name
        else:
            entry = get_subcontractor(raw_user_id)
            assigned_set = set(entry.assigned_project_ids)
            assigned_set.update(
                daily_report_service.list_membership_project_ids(
                    principal_type="subcontractor", principal_id=entry.id
                )
            )
            assigned = _valid_project_ids(assigned_set)
            display_name = entry.contact_name or entry.name
    except HTTPException as exc:
        if exc.status_code == status.HTTP_404_NOT_FOUND:
            raise McpNotFoundOrForbidden from exc
        raise
    return {
        "user_id": f"{principal_type}.{entry.id}",
        "principal_type": principal_type,
        "display_name": display_name,
        "role": principal_type,
        "roles": [principal_type],
        "active": entry.is_active,
        "external_mcp_enabled": False,
        "permissions": [],
        "all_projects_read": False,
        "assigned_project_ids": assigned,
        "authorization_updated_at": entry.updated_at,
        "source_read_at": _utc_now(),
    }


async def search(
    db: AsyncSession,
    request: McpSearchRequest,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    app_settings = settings or get_settings()
    access = _authorize(
        request,
        project_id=str(request.project_id) if request.project_id else None,
        settings=app_settings,
    )
    offset = _decode_cursor(request.cursor, "federated-search", app_settings)
    allowed_scope = _project_scope(access)
    if request.project_id:
        allowed_scope = {str(request.project_id)}
    normalized_query = request.query.strip().lower()
    domains = set(request.domains) if request.domains else {"projects_boq"}
    record_types = set(request.record_types)
    hits: list[dict[str, Any]] = []
    if "projects_boq" in domains:
        project_statement = select(Project).options(noload("*")).where(
            or_(
                func.lower(Project.name).contains(normalized_query, autoescape=True),
                func.lower(Project.status).contains(normalized_query, autoescape=True),
                func.lower(Project.project_type).contains(normalized_query, autoescape=True),
            )
        ).order_by(Project.name, Project.id)
        if allowed_scope is not None:
            if allowed_scope:
                project_statement = project_statement.where(
                    Project.id.in_([UUID(item) for item in allowed_scope])
                )
            else:
                project_statement = project_statement.where(False)
        if not record_types or "project" in record_types:
            projects = list((await db.execute(project_statement.limit(100))).scalars().all())
            hits.extend(
                {
                    "reference": f"projects_boq:project:{project.id}",
                    "domain": "projects_boq",
                    "record_type": "project",
                    "title": project.name,
                    "snippet": f"{project.project_type} · {project.status}",
                    "project_id": str(project.id),
                    "product_url": _project_url(project.id, app_settings),
                }
                for project in projects
            )

        if not record_types or "boq_line" in record_types:
            project_ids_statement = select(Project.id)
            if allowed_scope is not None:
                if allowed_scope:
                    project_ids_statement = project_ids_statement.where(
                        Project.id.in_([UUID(item) for item in allowed_scope])
                    )
                else:
                    project_ids_statement = project_ids_statement.where(False)
            searchable_project_ids = list(
                (await db.execute(project_ids_statement)).scalars().all()
            )
            budget_contexts = await load_project_budget_contexts(
                db, searchable_project_ids
            )
            legacy_project_ids = [
                project_id
                for project_id in searchable_project_ids
                if budget_contexts.get(project_id) is None
                or budget_contexts[project_id].snapshot.source_kind == "LEGACY"
            ]
            v2_revision_to_project: dict[UUID, UUID] = {}
            for project_id, context in budget_contexts.items():
                snapshot = context.snapshot
                if snapshot.source_kind != "V2" or snapshot.main_revision_id is None:
                    continue
                v2_revision_to_project[snapshot.main_revision_id] = project_id
                for revision_id in snapshot.accepted_change_order_ids:
                    v2_revision_to_project[revision_id] = project_id

            boq_statement = (
                select(BOQItem, Project.name)
                .join(Project, Project.id == BOQItem.project_id)
                .options(noload("*"))
                .where(
                    BOQItem.valid_to.is_(None),
                    BOQItem.project_id.in_(legacy_project_ids),
                    or_(
                        func.lower(func.coalesce(BOQItem.description, "")).contains(
                            normalized_query,
                            autoescape=True,
                        ),
                        func.lower(func.coalesce(BOQItem.item_no, "")).contains(
                            normalized_query,
                            autoescape=True,
                        ),
                    ),
                )
                .order_by(Project.name, BOQItem.boq_type, BOQItem.sheet_name, BOQItem.id)
            )
            boq_rows = (await db.execute(boq_statement.limit(100))).all()
            matched_legacy_project_ids = {
                item.project_id for item, _name in boq_rows
            }
            all_legacy_rows = list(
                (
                    await db.execute(
                        select(BOQItem)
                        .options(noload("*"))
                        .where(
                            BOQItem.project_id.in_(matched_legacy_project_ids),
                            BOQItem.valid_to.is_(None),
                        )
                    )
                )
                .scalars()
                .all()
            )
            legacy_rows_by_project: dict[UUID, list[BOQItem]] = {}
            for row in all_legacy_rows:
                legacy_rows_by_project.setdefault(row.project_id, []).append(row)
            stable_ids_by_project: dict[str, dict[str, str]] = {}
            for project_id, current_rows in legacy_rows_by_project.items():
                stable_ids_by_project[str(project_id)] = _stable_line_ids(current_rows)
            hits.extend(
                {
                    "reference": _boq_line_reference(
                        item.project_id,
                        stable_ids_by_project[str(item.project_id)][str(item.id)],
                    ),
                    "domain": "projects_boq",
                    "record_type": "boq_line",
                    "title": item.description or item.item_no or "BOQ line",
                    "snippet": f"{project_name} · {item.boq_type} · {item.sheet_name or 'unspecified sheet'}",
                    "project_id": str(item.project_id),
                    "product_url": _project_url(item.project_id, app_settings),
                }
                for item, project_name in boq_rows
            )
            active_v2_revision_ids = list(v2_revision_to_project)
            if active_v2_revision_ids:
                v2_rows = (
                    await db.execute(
                        select(BOQV2ScopeNode, BOQV2Document, Project.name)
                        .join(
                            BOQV2Revision,
                            BOQV2Revision.id == BOQV2ScopeNode.revision_id,
                        )
                        .join(
                            BOQV2Document,
                            BOQV2Document.id == BOQV2Revision.document_id,
                        )
                        .join(Project, Project.id == BOQV2ScopeNode.project_id)
                        .where(
                            BOQV2ScopeNode.revision_id.in_(active_v2_revision_ids),
                            or_(
                                func.lower(
                                    func.coalesce(BOQV2ScopeNode.description, "")
                                ).contains(normalized_query, autoescape=True),
                                func.lower(
                                    func.coalesce(BOQV2ScopeNode.item_code, "")
                                ).contains(normalized_query, autoescape=True),
                            ),
                        )
                        .order_by(Project.name, BOQV2Document.document_number, BOQV2ScopeNode.id)
                        .limit(100)
                    )
                ).all()
                hits.extend(
                    {
                        "reference": _boq_line_reference(
                            node.project_id,
                            _v2_line_id(document.id, node.logical_id),
                        ),
                        "domain": "projects_boq",
                        "record_type": "boq_line",
                        "title": node.description or node.item_code or "BOQ line",
                        "snippet": f"{project_name} · Native BOQ · {document.document_number}",
                        "project_id": str(node.project_id),
                        "source_kind": "V2",
                        "product_url": _project_url(node.project_id, app_settings),
                    }
                    for node, document, project_name in v2_rows
                )
    if domains.intersection({"finance_payments", "gcs_files"}):
        from app.services.mcp_finance_document_service import search_phase3_hits

        hits.extend(
            await search_phase3_hits(
                db,
                request,
                settings=app_settings,
            )
        )
    if domains.intersection({"inspection", "daily_reports"}):
        from app.services.mcp_project_operations_service import search_phase4_hits

        hits.extend(
            await search_phase4_hits(
                db,
                request,
                settings=app_settings,
            )
        )
    hits.sort(key=lambda item: (item["title"].lower(), item["reference"]))
    page = hits[offset : offset + request.limit]
    has_more = offset + len(page) < len(hits)
    return {
        "query": request.query,
        "items": page,
        "returned_count": len(page),
        "next_cursor": (
            _encode_cursor("federated-search", offset + len(page), app_settings)
            if has_more
            else None
        ),
        "source_read_at": _utc_now(),
    }


async def fetch(
    db: AsyncSession,
    request: McpFetchRequest,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    parts = request.reference.split(":", 2)
    if len(parts) != 3:
        raise McpInvalidInput("Invalid reference.")
    domain, record_type, opaque_id = parts
    principal = request.model_dump(
        include={"contract_version", "subject", "issuer", "client_id", "environment"}
    )
    if domain == "projects_boq" and record_type == "project":
        try:
            project_id = UUID(opaque_id)
        except ValueError as exc:
            raise McpInvalidInput("Invalid project reference.") from exc
        if request.version or request.as_of:
            return await get_boq_version(
                db,
                McpBOQVersionRequest(
                    **principal,
                    project_id=project_id,
                    version=request.version,
                    as_of=request.as_of,
                ),
                settings=settings,
            )
        return await get_project(
            db,
            McpProjectRequest(**principal, project_id=project_id),
            settings=settings,
        )
    if domain == "projects_boq" and record_type == "boq_line":
        project_part, separator, line_id = opaque_id.partition(".")
        if not separator or not line_id.startswith(("boql_", "boqlv2_")):
            raise McpInvalidInput("Invalid BOQ line reference.")
        try:
            project_id = UUID(project_part)
        except ValueError as exc:
            raise McpInvalidInput("Invalid BOQ line reference.") from exc
        if request.version is not None or request.as_of is not None:
            snapshot = await get_boq_version(
                db,
                McpBOQVersionRequest(
                    **principal,
                    project_id=project_id,
                    version=request.version,
                    as_of=request.as_of,
                ),
                settings=settings,
            )
        else:
            snapshot = await get_boq_current(
                db,
                McpProjectRequest(**principal, project_id=project_id),
                settings=settings,
            )
        item = next(
            (row for row in snapshot.get("lines", []) if row.get("line_id") == line_id),
            None,
        )
        if item is None:
            raise McpNotFoundOrForbidden
        return {
            "reference": request.reference,
            "project_id": str(project_id),
            "project_name": snapshot["project_name"],
            "source_kind": snapshot.get("source_kind", "LEGACY"),
            "version": snapshot.get("version"),
            "line": item,
            "product_url": snapshot["product_url"],
            "source_read_at": _utc_now(),
        }
    if domain == "users_access" and record_type == "user" and not request.version and not request.as_of:
        return await get_user_access(
            McpUserAccessRequest(**principal, user_id=opaque_id),
            settings=settings,
        )
    if domain in {"finance_payments", "gcs_files"}:
        from app.services.mcp_finance_document_service import fetch_phase3

        result = await fetch_phase3(
            db,
            request,
            settings=settings or get_settings(),
        )
        if result is not None:
            return result
    if domain in {"inspection", "daily_reports"}:
        from app.services.mcp_project_operations_service import fetch_phase4

        result = await fetch_phase4(
            db,
            request,
            settings=settings or get_settings(),
        )
        if result is not None:
            return result
    raise McpNotFoundOrForbidden
