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
) -> McpAccessContext:
    access = resolve_mcp_access(request, settings=settings)
    if (
        not access.active
        or not access.external_mcp_enabled
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


def _project_item(project: Project, settings: Settings, total_budget: object = 0) -> dict[str, Any]:
    return {
        "project_id": str(project.id),
        "name": project.name,
        "project_type": project.project_type,
        "status": project.status,
        "contingency_budget": _money(project.contingency_budget),
        "current_boq_budget": _money(total_budget),
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
    budget = (
        select(
            BOQItem.project_id.label("project_id"),
            func.coalesce(func.sum(BOQItem.grand_total), 0).label("total_budget"),
        )
        .where(
            BOQItem.valid_to.is_(None),
            BOQItem.parent_id.is_(None),
            func.upper(func.trim(BOQItem.boq_type)) == "CUSTOMER",
        )
        .group_by(BOQItem.project_id)
        .subquery()
    )
    statement = (
        select(Project, func.coalesce(budget.c.total_budget, 0))
        .outerjoin(budget, budget.c.project_id == Project.id)
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
    rows = (await db.execute(statement.offset(offset).limit(request.limit + 1))).all()
    has_more = len(rows) > request.limit
    page = rows[: request.limit]
    return {
        "items": [_project_item(project, app_settings, total) for project, total in page],
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
    value = (
        await db.execute(
            select(func.coalesce(func.sum(BOQItem.grand_total), 0)).where(
                BOQItem.project_id == project_id,
                BOQItem.valid_to.is_(None),
                BOQItem.parent_id.is_(None),
                func.upper(func.trim(BOQItem.boq_type)) == "CUSTOMER",
            )
        )
    ).scalar_one()
    return Decimal(str(value or 0))


async def get_project(
    db: AsyncSession,
    request: McpProjectRequest,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    app_settings = settings or get_settings()
    _authorize(request, project_id=str(request.project_id), settings=app_settings)
    project = await _load_project(db, request.project_id)
    current_customer_budget = await _current_customer_budget(db, request.project_id)
    return {
        **_project_item(project, app_settings, current_customer_budget),
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
    manifests = list(reversed(await _boq_manifests(db, request.project_id)))
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
    manifests = await _boq_manifests(db, request.project_id)
    manifest_a = _select_manifest(manifests, version=request.version_a)
    manifest_b = _select_manifest(manifests, version=request.version_b)
    rows_a = await _snapshot_rows(db, request.project_id, as_of=manifest_a["valid_from"])
    rows_b = await _snapshot_rows(db, request.project_id, as_of=manifest_b["valid_from"])
    snapshot_a = serialize_boq_snapshot(
        request.project_id, project.name, manifest_a, rows_a, app_settings
    )
    snapshot_b = serialize_boq_snapshot(
        request.project_id, project.name, manifest_b, rows_b, app_settings
    )
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
        "project": _project_item(project, app_settings, customer_total),
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
            boq_statement = (
                select(BOQItem, Project.name)
                .join(Project, Project.id == BOQItem.project_id)
                .options(noload("*"))
                .where(
                    BOQItem.valid_to.is_(None),
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
            if allowed_scope is not None:
                if allowed_scope:
                    boq_statement = boq_statement.where(
                        BOQItem.project_id.in_([UUID(item) for item in allowed_scope])
                    )
                else:
                    boq_statement = boq_statement.where(False)
            boq_rows = (await db.execute(boq_statement.limit(100))).all()
            stable_ids_by_project: dict[str, dict[str, str]] = {}
            for project_id in {str(item.project_id) for item, _name in boq_rows}:
                current_rows = await _snapshot_rows(db, UUID(project_id), as_of=None)
                stable_ids_by_project[project_id] = _stable_line_ids(current_rows)
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
        if not separator or not line_id.startswith("boql_"):
            raise McpInvalidInput("Invalid BOQ line reference.")
        try:
            project_id = UUID(project_part)
        except ValueError as exc:
            raise McpInvalidInput("Invalid BOQ line reference.") from exc
        app_settings = settings or get_settings()
        _authorize(request, project_id=str(project_id), settings=app_settings)
        project = await _load_project(db, project_id)
        manifests = await _boq_manifests(db, project_id)
        if request.version is not None or request.as_of is not None:
            manifest = _select_manifest(
                manifests,
                version=request.version,
                as_of=request.as_of,
            )
            rows = await _snapshot_rows(db, project_id, as_of=manifest["valid_from"])
        else:
            manifest = manifests[-1] if manifests else None
            rows = await _snapshot_rows(db, project_id, as_of=None)
        stable_ids = _stable_line_ids(rows)
        item = next(
            (
                row
                for row in rows
                if stable_ids.get(str(row.id)) == line_id
            ),
            None,
        )
        if item is None:
            raise McpNotFoundOrForbidden
        return {
            "reference": request.reference,
            "project_id": str(project_id),
            "project_name": project.name,
            "version": manifest,
            "line": _serialize_boq_line(item, stable_ids),
            "product_url": _project_url(project_id, app_settings),
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
