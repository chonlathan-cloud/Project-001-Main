"""Inspection, Daily Report, Dashboard and project-insight MCP tools."""

from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from app.adapters.backend.client import BackendReadClientProtocol, BackendReadOperation
from app.policy.models import AccessContext
from app.schemas.common import ToolResponse
from app.tools.core.handlers import _payload, _read
from app.tools.discovery.handlers import READ_ONLY_ANNOTATIONS
from app.tools.registry import DomainName, ToolRegistry
from app.tools.runtime import InvalidToolInput, NotFoundOrForbidden, ToolPayload, ToolRuntime

Cursor = Annotated[str | None, Field(max_length=1024)]
ShortLimit = Annotated[int, Field(ge=1, le=50)]
Limit = Annotated[int, Field(ge=1, le=100)]
OpaqueId = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._~-]+$")]
Version = Annotated[str | None, Field(min_length=1, max_length=128)]
StatusItem = Annotated[str, Field(min_length=1, max_length=32)]
StatusList = Annotated[list[StatusItem] | None, Field(max_length=10)]


def _validate_date_range(date_from: date | None, date_to: date | None) -> None:
    if date_from and date_to:
        if date_from > date_to or (date_to - date_from).days > 366:
            raise InvalidToolInput


def _validate_requested_projects(access: AccessContext, project_ids: list[UUID]) -> None:
    if access.role == "owner" or access.all_projects_read or not project_ids:
        return
    if not {str(value) for value in project_ids}.issubset(access.assigned_project_ids):
        raise NotFoundOrForbidden


def register_project_operation_tools(
    mcp: FastMCP,
    runtime: ToolRuntime,
    registry: ToolRegistry,
    backend: BackendReadClientProtocol,
) -> None:
    @mcp.tool(
        description=(
            "List authorized inspection items with bounded status, severity and due-date filters."
        ),
        annotations=READ_ONLY_ANNOTATIONS,
        structured_output=True,
    )
    async def list_inspection_items(
        project_id: UUID,
        statuses: StatusList = None,
        severities: StatusList = None,
        due_before: date | None = None,
        overdue: bool | None = None,
        cursor: Cursor = None,
        limit: ShortLimit = 20,
    ) -> ToolResponse:
        async def operation(access: AccessContext) -> ToolPayload:
            data = await _read(
                backend,
                BackendReadOperation.LIST_INSPECTION_ITEMS,
                access,
                {
                    "project_id": project_id,
                    "statuses": statuses or [],
                    "severities": severities or [],
                    "due_before": due_before,
                    "overdue": overdue,
                    "cursor": cursor,
                    "limit": limit,
                },
            )
            return _payload(
                data,
                domain=DomainName.INSPECTION,
                record_id=str(project_id),
            )

        return await runtime.execute(
            registry.tool("list_inspection_items"),
            operation,
            project_id=str(project_id),
            target_record_ids=[str(project_id)],
        )

    @mcp.tool(
        description=(
            "Get one authorized inspection item, bounded event history and opaque document IDs."
        ),
        annotations=READ_ONLY_ANNOTATIONS,
        structured_output=True,
    )
    async def get_inspection_item(project_id: UUID, item_id: OpaqueId) -> ToolResponse:
        async def operation(access: AccessContext) -> ToolPayload:
            data = await _read(
                backend,
                BackendReadOperation.GET_INSPECTION_ITEM,
                access,
                {"project_id": project_id, "item_id": item_id},
            )
            return _payload(
                data,
                domain=DomainName.INSPECTION,
                record_id=item_id,
            )

        return await runtime.execute(
            registry.tool("get_inspection_item"),
            operation,
            project_id=str(project_id),
            target_record_ids=[item_id],
        )

    @mcp.tool(
        description=(
            "List authorized Daily Reports without share tokens, signed URLs or source submissions."
        ),
        annotations=READ_ONLY_ANNOTATIONS,
        structured_output=True,
    )
    async def list_daily_reports(
        project_id: UUID,
        date_from: date | None = None,
        date_to: date | None = None,
        statuses: StatusList = None,
        cursor: Cursor = None,
        limit: ShortLimit = 20,
    ) -> ToolResponse:
        async def operation(access: AccessContext) -> ToolPayload:
            _validate_date_range(date_from, date_to)
            data = await _read(
                backend,
                BackendReadOperation.LIST_DAILY_REPORTS,
                access,
                {
                    "project_id": project_id,
                    "date_from": date_from,
                    "date_to": date_to,
                    "statuses": statuses or [],
                    "cursor": cursor,
                    "limit": limit,
                },
            )
            return _payload(
                data,
                domain=DomainName.DAILY_REPORTS,
                record_id=str(project_id),
            )

        return await runtime.execute(
            registry.tool("list_daily_reports"),
            operation,
            project_id=str(project_id),
            target_record_ids=[str(project_id)],
        )

    @mcp.tool(
        description="Get current Daily Report content or one immutable published version.",
        annotations=READ_ONLY_ANNOTATIONS,
        structured_output=True,
    )
    async def get_daily_report(report_id: OpaqueId, version: Version = None) -> ToolResponse:
        async def operation(access: AccessContext) -> ToolPayload:
            data = await _read(
                backend,
                BackendReadOperation.GET_DAILY_REPORT,
                access,
                {"report_id": report_id, "version": version},
            )
            return _payload(
                data,
                domain=DomainName.DAILY_REPORTS,
                record_id=report_id,
                version=version,
            )

        return await runtime.execute(
            registry.tool("get_daily_report"),
            operation,
            target_record_ids=[report_id],
        )

    @mcp.tool(
        description="List immutable publication versions for one authorized Daily Report.",
        annotations=READ_ONLY_ANNOTATIONS,
        structured_output=True,
    )
    async def list_daily_report_versions(
        report_id: OpaqueId,
        cursor: Cursor = None,
        limit: Limit = 20,
    ) -> ToolResponse:
        async def operation(access: AccessContext) -> ToolPayload:
            data = await _read(
                backend,
                BackendReadOperation.LIST_DAILY_REPORT_VERSIONS,
                access,
                {"report_id": report_id, "cursor": cursor, "limit": limit},
            )
            return _payload(
                data,
                domain=DomainName.DAILY_REPORTS,
                record_id=report_id,
            )

        return await runtime.execute(
            registry.tool("list_daily_report_versions"),
            operation,
            target_record_ids=[report_id],
        )

    @mcp.tool(
        description=(
            "Get Daily Report sharing state without returning the share token or public URL."
        ),
        annotations=READ_ONLY_ANNOTATIONS,
        structured_output=True,
    )
    async def get_report_share_status(project_id: UUID) -> ToolResponse:
        async def operation(access: AccessContext) -> ToolPayload:
            data = await _read(
                backend,
                BackendReadOperation.GET_REPORT_SHARE_STATUS,
                access,
                {"project_id": project_id},
            )
            return _payload(
                data,
                domain=DomainName.DAILY_REPORTS,
                record_id=str(project_id),
            )

        return await runtime.execute(
            registry.tool("get_report_share_status"),
            operation,
            project_id=str(project_id),
            target_record_ids=[str(project_id)],
        )

    @mcp.tool(
        description="Get an exact, permission-scoped dashboard summary with calculation metadata.",
        annotations=READ_ONLY_ANNOTATIONS,
        structured_output=True,
    )
    async def get_dashboard_summary(
        project_ids: Annotated[list[UUID] | None, Field(max_length=50)] = None,
        date_from: date | None = None,
        date_to: date | None = None,
        fresh: bool = True,
    ) -> ToolResponse:
        async def operation(access: AccessContext) -> ToolPayload:
            _validate_date_range(date_from, date_to)
            _validate_requested_projects(access, project_ids or [])
            data = await _read(
                backend,
                BackendReadOperation.GET_DASHBOARD_SUMMARY,
                access,
                {
                    "project_ids": project_ids or [],
                    "date_from": date_from,
                    "date_to": date_to,
                    "fresh": fresh,
                },
            )
            return _payload(
                data,
                domain=DomainName.DASHBOARD_INSIGHTS,
                record_id="dashboard-summary",
            )

        return await runtime.execute(
            registry.tool("get_dashboard_summary"),
            operation,
            target_record_ids=[str(value) for value in project_ids or []],
        )

    @mcp.tool(
        description=(
            "Get independently sourced finance, inspection and Daily Report signals for a project."
        ),
        annotations=READ_ONLY_ANNOTATIONS,
        structured_output=True,
    )
    async def get_project_insights(
        project_id: UUID,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> ToolResponse:
        async def operation(access: AccessContext) -> ToolPayload:
            _validate_date_range(date_from, date_to)
            data = await _read(
                backend,
                BackendReadOperation.GET_PROJECT_INSIGHTS,
                access,
                {"project_id": project_id, "date_from": date_from, "date_to": date_to},
            )
            return _payload(
                data,
                domain=DomainName.DASHBOARD_INSIGHTS,
                record_id=str(project_id),
            )

        return await runtime.execute(
            registry.tool("get_project_insights"),
            operation,
            project_id=str(project_id),
            target_record_ids=[str(project_id)],
        )
