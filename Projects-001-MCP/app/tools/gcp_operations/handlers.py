"""Strictly allowlisted GCP health, status and application-error tools."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from app.adapters.backend.client import BackendReadClientProtocol, BackendReadOperation
from app.adapters.gcp.client import GcpOperationsClientProtocol, GcpOperationsInvalidInput
from app.config.settings import Settings
from app.policy.models import AccessContext
from app.schemas.common import Freshness, Pagination, SourceReference, ToolResponse, WarningItem
from app.tools.core.handlers import _payload, _read
from app.tools.discovery.handlers import READ_ONLY_ANNOTATIONS
from app.tools.registry import DomainName, ToolRegistry
from app.tools.runtime import InvalidToolInput, ToolPayload, ToolRuntime

Component = Literal["mcp", "backend", "cloud_sql", "firestore", "gcs", "oauth"]
ResourceType = Literal[
    "cloud_run",
    "cloud_sql",
    "firestore",
    "gcs",
    "logging",
    "artifact_registry",
]
ServiceAlias = Literal["frontend", "backend", "mcp"]
Severity = Literal["WARNING", "ERROR", "CRITICAL", "ALERT", "EMERGENCY"]
DataSource = Literal["backend", "cloud_sql", "firestore", "gcs", "oauth"]
Workflow = Literal["boq_sync", "receipt_ocr", "daily_report_delivery", "flowaccount_sync"]
Cursor = Annotated[str | None, Field(max_length=1024)]
ErrorLimit = Annotated[int, Field(ge=1, le=50)]
OpaqueId = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._~-]+$")]
WorkflowFilter = Annotated[
    str | None,
    Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_~-]*$"),
]


def _source_payload(data: dict, *, record_id: str, source_system: str) -> ToolPayload:
    safe = dict(data)
    source_read_at = safe.pop("source_read_at", None)
    returned_count = safe.get("returned_count")
    next_cursor = safe.get("next_cursor")
    partial = bool(safe.pop("partial", False))
    warnings = [WarningItem.model_validate(item) for item in safe.pop("warnings", [])]
    return ToolPayload(
        data=safe,
        sources=[
            SourceReference(
                domain=DomainName.GCP_OPERATIONS.value,
                record_id=record_id,
                source_system=source_system,
                last_updated_at=source_read_at,
            )
        ],
        pagination=(
            Pagination(returned_count=int(returned_count or 0), next_cursor=next_cursor)
            if returned_count is not None
            else None
        ),
        freshness=(
            Freshness(source_read_at=source_read_at, cache_status="bypass")
            if source_read_at
            else None
        ),
        warnings=warnings,
        partial=partial,
        result_count=int(returned_count) if returned_count is not None else 1,
    )


def _bounded_range(
    settings: Settings,
    *,
    date_from: datetime,
    date_to: datetime,
) -> tuple[datetime, datetime]:
    start = date_from.replace(tzinfo=UTC) if date_from.tzinfo is None else date_from.astimezone(UTC)
    end = date_to.replace(tzinfo=UTC) if date_to.tzinfo is None else date_to.astimezone(UTC)
    if (
        start > end
        or end - start > timedelta(days=settings.operational_log_read_max_days)
        or end > datetime.now(UTC) + timedelta(minutes=5)
    ):
        raise InvalidToolInput
    return start, end


def register_gcp_operation_tools(
    mcp: FastMCP,
    runtime: ToolRuntime,
    registry: ToolRegistry,
    gcp: GcpOperationsClientProtocol,
    backend: BackendReadClientProtocol,
    settings: Settings,
) -> None:
    @mcp.tool(
        description="Get bounded health for allowlisted Product components only.",
        annotations=READ_ONLY_ANNOTATIONS,
        structured_output=True,
    )
    async def get_system_health(
        components: Annotated[list[Component] | None, Field(max_length=10)] = None,
    ) -> ToolResponse:
        async def operation(_access: AccessContext) -> ToolPayload:
            try:
                data = await gcp.get_system_health(components=list(components or []))
            except GcpOperationsInvalidInput as exc:
                raise InvalidToolInput from exc
            return _source_payload(
                data,
                record_id="system-health",
                source_system="gcp_health",
            )

        return await runtime.execute(registry.tool("get_system_health"), operation)

    @mcp.tool(
        description="Summarize only the fixed Product resource aliases for this environment.",
        annotations=READ_ONLY_ANNOTATIONS,
        structured_output=True,
    )
    async def get_gcp_resource_summary(
        resource_types: Annotated[list[ResourceType] | None, Field(max_length=6)] = None,
    ) -> ToolResponse:
        async def operation(_access: AccessContext) -> ToolPayload:
            try:
                data = await gcp.get_resource_summary(resource_types=list(resource_types or []))
            except GcpOperationsInvalidInput as exc:
                raise InvalidToolInput from exc
            return _source_payload(
                data,
                record_id="resource-summary",
                source_system="gcp_resource_apis",
            )

        return await runtime.execute(registry.tool("get_gcp_resource_summary"), operation)

    @mcp.tool(
        description="Get safe readiness metadata for one exact Product Cloud Run alias.",
        annotations=READ_ONLY_ANNOTATIONS,
        structured_output=True,
    )
    async def get_cloud_run_status(service_alias: ServiceAlias) -> ToolResponse:
        async def operation(_access: AccessContext) -> ToolPayload:
            try:
                data = await gcp.get_cloud_run_status(service_alias=service_alias)
            except GcpOperationsInvalidInput as exc:
                raise InvalidToolInput from exc
            return _source_payload(
                data,
                record_id=f"cloud-run.{service_alias}",
                source_system="gcp_cloud_run",
            )

        return await runtime.execute(
            registry.tool("get_cloud_run_status"),
            operation,
            target_record_ids=[service_alias],
        )

    @mcp.tool(
        description="Search redacted application errors in the dedicated bounded operations view.",
        annotations=READ_ONLY_ANNOTATIONS,
        structured_output=True,
    )
    async def search_application_errors(
        date_from: datetime,
        date_to: datetime,
        service_alias: ServiceAlias | None = None,
        workflow: WorkflowFilter = None,
        severities: Annotated[list[Severity] | None, Field(max_length=5)] = None,
        cursor: Cursor = None,
        limit: ErrorLimit = 20,
    ) -> ToolResponse:
        async def operation(_access: AccessContext) -> ToolPayload:
            start, end = _bounded_range(settings, date_from=date_from, date_to=date_to)
            try:
                data = await gcp.search_application_errors(
                    date_from=start,
                    date_to=end,
                    service_alias=service_alias,
                    workflow=workflow,
                    severities=list(severities or []),
                    cursor=cursor,
                    limit=limit,
                )
            except GcpOperationsInvalidInput as exc:
                raise InvalidToolInput from exc
            return _source_payload(
                data,
                record_id="application-errors",
                source_system="cloud_logging_operational_view",
            )

        return await runtime.execute(
            registry.tool("search_application_errors"),
            operation,
            target_record_ids=[service_alias] if service_alias else None,
        )

    @mcp.tool(
        description="Get safe health states for named Product data sources only.",
        annotations=READ_ONLY_ANNOTATIONS,
        structured_output=True,
    )
    async def get_data_source_health(
        sources: Annotated[list[DataSource] | None, Field(max_length=5)] = None,
    ) -> ToolResponse:
        async def operation(_access: AccessContext) -> ToolPayload:
            try:
                data = await gcp.get_data_source_health(sources=list(sources or []))
            except GcpOperationsInvalidInput as exc:
                raise InvalidToolInput from exc
            return _source_payload(
                data,
                record_id="data-source-health",
                source_system="gcp_health",
            )

        return await runtime.execute(registry.tool("get_data_source_health"), operation)

    @mcp.tool(
        description="Get one authorized Product processing job without starting or mutating it.",
        annotations=READ_ONLY_ANNOTATIONS,
        structured_output=True,
    )
    async def get_processing_status(workflow: Workflow, job_id: OpaqueId) -> ToolResponse:
        async def operation(access: AccessContext) -> ToolPayload:
            data = await _read(
                backend,
                BackendReadOperation.GET_PROCESSING_STATUS,
                access,
                {"workflow": workflow, "job_id": job_id},
            )
            return _payload(
                data,
                domain=DomainName.GCP_OPERATIONS,
                record_id=f"{workflow}.{job_id}",
            )

        return await runtime.execute(
            registry.tool("get_processing_status"),
            operation,
            target_record_ids=[job_id],
        )
