"""Sensitive, allowlisted Product Audit MCP tools."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from app.adapters.audit.client import (
    AuditReadClientProtocol,
    AuditReadInvalidInput,
    AuditReadNotFound,
)
from app.audit.models import ProductAuditEvent
from app.config.settings import Settings
from app.policy.models import AccessContext
from app.schemas.common import Freshness, Pagination, SourceReference, ToolResponse
from app.tools.discovery.handlers import READ_ONLY_ANNOTATIONS
from app.tools.registry import DomainName, ToolRegistry
from app.tools.runtime import InvalidToolInput, NotFoundOrForbidden, ToolPayload, ToolRuntime

Cursor = Annotated[str | None, Field(max_length=1024)]
AuditLimit = Annotated[int, Field(ge=1, le=50)]
ToolNames = Annotated[
    list[Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")]] | None,
    Field(max_length=20),
]
OpaqueId = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._~-]+$")]


def _audit_payload(data: dict, *, record_id: str) -> ToolPayload:
    raw = dict(data)
    source_read_at = raw.pop("source_read_at", None)
    if isinstance(raw.get("items"), list):
        raw["items"] = [
            ProductAuditEvent.model_validate(
                {
                    key: value
                    for key, value in item.items()
                    if key in ProductAuditEvent.model_fields
                }
            ).model_dump(mode="json")
            for item in raw["items"]
        ]
        raw["returned_count"] = len(raw["items"])
    else:
        raw = ProductAuditEvent.model_validate(
            {
                key: value
                for key, value in raw.items()
                if key in ProductAuditEvent.model_fields
            }
        ).model_dump(mode="json")
    returned_count = raw.get("returned_count")
    return ToolPayload(
        data=raw,
        sources=[
            SourceReference(
                domain=DomainName.HISTORY_AUDIT.value,
                record_id=record_id,
                source_system="cloud_logging",
                last_updated_at=source_read_at,
            )
        ],
        pagination=(
            Pagination(
                returned_count=int(returned_count or 0),
                next_cursor=raw.get("next_cursor"),
            )
            if returned_count is not None
            else None
        ),
        freshness=(
            Freshness(source_read_at=source_read_at, cache_status="bypass")
            if source_read_at
            else None
        ),
        result_count=int(returned_count) if returned_count is not None else 1,
    )


def register_audit_tools(
    mcp: FastMCP,
    runtime: ToolRuntime,
    registry: ToolRegistry,
    audit_reader: AuditReadClientProtocol,
    settings: Settings,
) -> None:
    @mcp.tool(
        description=(
            "Search allowlisted Product MCP audit metadata within a bounded retention window."
        ),
        annotations=READ_ONLY_ANNOTATIONS,
        structured_output=True,
    )
    async def search_audit_events(
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        tool_names: ToolNames = None,
        decisions: Annotated[
            list[Literal["allow", "deny", "error"]] | None,
            Field(max_length=4),
        ] = None,
        domain: DomainName | None = None,
        subject_id: OpaqueId | None = None,
        cursor: Cursor = None,
        limit: AuditLimit = 20,
    ) -> ToolResponse:
        async def operation(_access: AccessContext) -> ToolPayload:
            end = date_to or datetime.now(UTC)
            start = date_from or end - timedelta(days=7)
            start = start.replace(tzinfo=UTC) if start.tzinfo is None else start.astimezone(UTC)
            end = end.replace(tzinfo=UTC) if end.tzinfo is None else end.astimezone(UTC)
            if start > end or end - start > timedelta(days=settings.audit_read_max_days):
                raise InvalidToolInput
            try:
                data = await audit_reader.search(
                    date_from=start,
                    date_to=end,
                    tool_names=tool_names or [],
                    decisions=decisions or [],
                    domain=domain.value if domain else None,
                    subject_id=subject_id,
                    cursor=cursor,
                    limit=limit,
                )
            except AuditReadNotFound as exc:
                raise NotFoundOrForbidden from exc
            except AuditReadInvalidInput as exc:
                raise InvalidToolInput from exc
            return _audit_payload(data, record_id="audit-search")

        return await runtime.execute(
            registry.tool("search_audit_events"),
            operation,
            target_record_ids=[subject_id] if subject_id else None,
        )

    @mcp.tool(
        description="Get one allowlisted Product MCP audit event by opaque event ID.",
        annotations=READ_ONLY_ANNOTATIONS,
        structured_output=True,
    )
    async def get_audit_event(event_id: OpaqueId) -> ToolResponse:
        async def operation(_access: AccessContext) -> ToolPayload:
            try:
                data = await audit_reader.get(event_id=event_id)
            except AuditReadNotFound as exc:
                raise NotFoundOrForbidden from exc
            except AuditReadInvalidInput as exc:
                raise InvalidToolInput from exc
            return _audit_payload(data, record_id=event_id)

        return await runtime.execute(
            registry.tool("get_audit_event"),
            operation,
            target_record_ids=[event_id],
        )
