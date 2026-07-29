"""Core Pilot discovery, Project/BOQ, and access tools."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime
from typing import Annotated, Any
from uuid import UUID

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from app.adapters.backend.client import (
    BackendInvalidInput,
    BackendNotFoundOrForbidden,
    BackendRateLimited,
    BackendReadClientProtocol,
    BackendReadOperation,
)
from app.policy.models import AccessContext
from app.schemas.common import (
    Freshness,
    Pagination,
    SourceReference,
    ToolResponse,
    WarningItem,
)
from app.tools.discovery.handlers import READ_ONLY_ANNOTATIONS
from app.tools.registry import DomainName, ToolRegistry
from app.tools.runtime import (
    InvalidToolInput,
    NotFoundOrForbidden,
    ToolPayload,
    ToolRateLimited,
    ToolRuntime,
)

Cursor = Annotated[str | None, Field(max_length=1024)]
ProjectLimit = Annotated[int, Field(ge=1, le=100)]
SearchLimit = Annotated[int, Field(ge=1, le=50)]
Version = Annotated[str, Field(min_length=1, max_length=128)]


def _search_definition(
    registry: ToolRegistry,
    domains: list[DomainName] | None,
):
    definition = registry.tool("search")
    if DomainName.FINANCE_PAYMENTS in set(domains or []):
        return replace(
            definition,
            domain=DomainName.FINANCE_PAYMENTS,
            required_permissions=definition.required_permissions
            | frozenset({"financial_data_read"}),
            sensitive=True,
        )
    return definition


def _fetch_definition(
    registry: ToolRegistry,
    reference: str,
):
    definition = registry.tool("fetch")
    domain_name, record_type, opaque_id = reference.split(":", 2)
    project_id = None
    if domain_name == DomainName.FINANCE_PAYMENTS.value:
        definition = replace(
            definition,
            domain=DomainName.FINANCE_PAYMENTS,
            required_permissions=definition.required_permissions
            | frozenset({"financial_data_read"}),
            sensitive=True,
        )
    elif domain_name == DomainName.USERS_ACCESS.value:
        definition = replace(
            definition,
            domain=DomainName.USERS_ACCESS,
            sensitive=True,
        )
    elif domain_name == DomainName.GCS_FILES.value and record_type == "document":
        definition = replace(definition, domain=DomainName.GCS_FILES)
        parts = opaque_id.split(".", 2)
        if len(parts) == 3:
            try:
                project_id = str(UUID(parts[1]))
            except ValueError:
                pass
    return definition, project_id


async def _read(
    client: BackendReadClientProtocol,
    operation: BackendReadOperation,
    access: AccessContext,
    payload: dict[str, Any],
) -> dict[str, Any]:
    try:
        return await client.read(operation, access, payload)
    except BackendNotFoundOrForbidden as exc:
        raise NotFoundOrForbidden from exc
    except BackendInvalidInput as exc:
        raise InvalidToolInput from exc
    except BackendRateLimited as exc:
        raise ToolRateLimited from exc


def _payload(
    data: dict[str, Any],
    *,
    domain: DomainName,
    record_id: str,
    version: str | None = None,
    result_count: int | None = None,
) -> ToolPayload:
    data = dict(data)
    source_read_at = data.pop("source_read_at", None)
    returned_count = data.get("returned_count")
    next_cursor = data.get("next_cursor")
    partial = bool(data.get("truncated", False))
    warnings = (
        [
            WarningItem(
                code="PARTIAL_RESULT",
                message="The bounded result was truncated; narrow the request before reading more.",
            )
        ]
        if partial
        else []
    )
    return ToolPayload(
        data=data,
        sources=[
            SourceReference(
                domain=domain.value,
                record_id=record_id,
                source_system="product_backend",
                version=version,
                last_updated_at=source_read_at,
                product_url=data.get("product_url"),
            )
        ],
        pagination=(
            Pagination(returned_count=int(returned_count or 0), next_cursor=next_cursor)
            if returned_count is not None
            else None
        ),
        freshness=(
            Freshness(source_read_at=source_read_at, cache_status="bypass")
            if source_read_at is not None
            else None
        ),
        warnings=warnings,
        partial=partial,
        result_count=(
            result_count
            if result_count is not None
            else int(returned_count)
            if returned_count is not None
            else 1
        ),
    )


def register_core_tools(
    mcp: FastMCP,
    runtime: ToolRuntime,
    registry: ToolRegistry,
    backend: BackendReadClientProtocol,
) -> None:
    @mcp.tool(
        description="Search authorized Product records using bounded federated retrieval.",
        annotations=READ_ONLY_ANNOTATIONS,
        structured_output=True,
    )
    async def search(
        query: Annotated[str, Field(min_length=1, max_length=500)],
        domains: Annotated[list[DomainName] | None, Field(max_length=10)] = None,
        project_id: UUID | None = None,
        record_types: Annotated[list[str] | None, Field(max_length=20)] = None,
        date_from: date | None = None,
        date_to: date | None = None,
        cursor: Cursor = None,
        limit: SearchLimit = 20,
    ) -> ToolResponse:
        async def operation(access: AccessContext) -> ToolPayload:
            data = await _read(
                backend,
                BackendReadOperation.SEARCH,
                access,
                {
                    "query": query,
                    "domains": [item.value for item in domains or []],
                    "project_id": project_id,
                    "record_types": record_types or [],
                    "date_from": date_from,
                    "date_to": date_to,
                    "cursor": cursor,
                    "limit": limit,
                },
            )
            return _payload(
                data,
                domain=DomainName.SYSTEM_CATALOG,
                record_id="federated-search",
            )

        return await runtime.execute(
            _search_definition(registry, domains),
            operation,
            project_id=str(project_id) if project_id else None,
            target_record_ids=[str(project_id)] if project_id else None,
        )

    @mcp.tool(
        description="Fetch one authorized Product record from a stable search reference.",
        annotations=READ_ONLY_ANNOTATIONS,
        structured_output=True,
    )
    async def fetch(
        reference: Annotated[
            str,
            Field(
                min_length=5,
                max_length=512,
                pattern=r"^[a-z_]+:[a-z_]+:[A-Za-z0-9._~-]+$",
            ),
        ],
        version: Annotated[str | None, Field(min_length=1, max_length=128)] = None,
        as_of: datetime | None = None,
        max_content_chars: Annotated[int, Field(ge=1, le=20000)] = 4000,
    ) -> ToolResponse:
        async def operation(access: AccessContext) -> ToolPayload:
            if version is not None and as_of is not None:
                raise InvalidToolInput
            data = await _read(
                backend,
                BackendReadOperation.FETCH,
                access,
                {
                    "reference": reference,
                    "version": version,
                    "as_of": as_of,
                    "max_content_chars": max_content_chars,
                },
            )
            domain_name = reference.split(":", 1)[0]
            try:
                domain = DomainName(domain_name)
            except ValueError:
                domain = DomainName.SYSTEM_CATALOG
            version_data = data.get("version") or {}
            return _payload(
                data,
                domain=domain,
                record_id=reference,
                version=version_data.get("version_id"),
            )

        definition, project_id = _fetch_definition(registry, reference)
        return await runtime.execute(
            definition,
            operation,
            project_id=project_id,
            target_record_ids=[reference],
        )

    @mcp.tool(
        description="List only projects visible in the current Product access scope.",
        annotations=READ_ONLY_ANNOTATIONS,
        structured_output=True,
    )
    async def list_projects(
        status: Annotated[list[str] | None, Field(max_length=10)] = None,
        cursor: Cursor = None,
        limit: ProjectLimit = 20,
    ) -> ToolResponse:
        async def operation(access: AccessContext) -> ToolPayload:
            data = await _read(
                backend,
                BackendReadOperation.LIST_PROJECTS,
                access,
                {"statuses": status or [], "cursor": cursor, "limit": limit},
            )
            return _payload(
                data,
                domain=DomainName.PROJECTS_BOQ,
                record_id="authorized-project-list",
            )

        return await runtime.execute(registry.tool("list_projects"), operation)

    @mcp.tool(
        description="Get an authorized project's canonical details and Product citation URL.",
        annotations=READ_ONLY_ANNOTATIONS,
        structured_output=True,
    )
    async def get_project(project_id: UUID) -> ToolResponse:
        async def operation(access: AccessContext) -> ToolPayload:
            data = await _read(
                backend,
                BackendReadOperation.GET_PROJECT,
                access,
                {"project_id": project_id},
            )
            return _payload(
                data,
                domain=DomainName.PROJECTS_BOQ,
                record_id=str(project_id),
            )

        return await runtime.execute(
            registry.tool("get_project"),
            operation,
            project_id=str(project_id),
            target_record_ids=[str(project_id)],
        )

    @mcp.tool(
        description="Get a bounded project and BOQ summary, optionally at a point in time.",
        annotations=READ_ONLY_ANNOTATIONS,
        structured_output=True,
    )
    async def get_project_summary(
        project_id: UUID,
        as_of: datetime | None = None,
    ) -> ToolResponse:
        async def operation(access: AccessContext) -> ToolPayload:
            data = await _read(
                backend,
                BackendReadOperation.GET_PROJECT_SUMMARY,
                access,
                {"project_id": project_id, "as_of": as_of},
            )
            version_data = data.get("boq", {}).get("version") or {}
            return _payload(
                data,
                domain=DomainName.PROJECTS_BOQ,
                record_id=str(project_id),
                version=version_data.get("version_id"),
            )

        return await runtime.execute(
            registry.tool("get_project_summary"),
            operation,
            project_id=str(project_id),
            target_record_ids=[str(project_id)],
        )

    @mcp.tool(
        description="Get the current authorized BOQ snapshot with exact monetary values.",
        annotations=READ_ONLY_ANNOTATIONS,
        structured_output=True,
    )
    async def get_boq_current(project_id: UUID) -> ToolResponse:
        async def operation(access: AccessContext) -> ToolPayload:
            data = await _read(
                backend,
                BackendReadOperation.GET_BOQ_CURRENT,
                access,
                {"project_id": project_id},
            )
            version_data = data.get("version") or {}
            return _payload(
                data,
                domain=DomainName.PROJECTS_BOQ,
                record_id=str(project_id),
                version=version_data.get("version_id"),
                result_count=int(data.get("returned_count", 0)),
            )

        return await runtime.execute(
            registry.tool("get_boq_current"),
            operation,
            project_id=str(project_id),
            target_record_ids=[str(project_id)],
        )

    @mcp.tool(
        description="List deterministic Product-owned BOQ version manifests for a project.",
        annotations=READ_ONLY_ANNOTATIONS,
        structured_output=True,
    )
    async def list_boq_versions(
        project_id: UUID,
        cursor: Cursor = None,
        limit: ProjectLimit = 20,
    ) -> ToolResponse:
        async def operation(access: AccessContext) -> ToolPayload:
            data = await _read(
                backend,
                BackendReadOperation.LIST_BOQ_VERSIONS,
                access,
                {"project_id": project_id, "cursor": cursor, "limit": limit},
            )
            return _payload(
                data,
                domain=DomainName.PROJECTS_BOQ,
                record_id=f"{project_id}-versions",
            )

        return await runtime.execute(
            registry.tool("list_boq_versions"),
            operation,
            project_id=str(project_id),
            target_record_ids=[str(project_id)],
        )

    @mcp.tool(
        description="Get one BOQ snapshot by stable version identifier/number or point in time.",
        annotations=READ_ONLY_ANNOTATIONS,
        structured_output=True,
    )
    async def get_boq_version(
        project_id: UUID,
        version: Annotated[str | None, Field(min_length=1, max_length=128)] = None,
        as_of: datetime | None = None,
    ) -> ToolResponse:
        async def operation(access: AccessContext) -> ToolPayload:
            if (version is None) == (as_of is None):
                raise InvalidToolInput
            data = await _read(
                backend,
                BackendReadOperation.GET_BOQ_VERSION,
                access,
                {"project_id": project_id, "version": version, "as_of": as_of},
            )
            version_data = data.get("version") or {}
            return _payload(
                data,
                domain=DomainName.PROJECTS_BOQ,
                record_id=str(project_id),
                version=version_data.get("version_id"),
                result_count=int(data.get("returned_count", 0)),
            )

        return await runtime.execute(
            registry.tool("get_boq_version"),
            operation,
            project_id=str(project_id),
            target_record_ids=[
                str(project_id),
                version or (as_of.isoformat() if as_of else ""),
            ],
        )

    @mcp.tool(
        description="Compare two authorized BOQ snapshots by stable line identity.",
        annotations=READ_ONLY_ANNOTATIONS,
        structured_output=True,
    )
    async def compare_boq_versions(
        project_id: UUID,
        version_a: Version,
        version_b: Version,
    ) -> ToolResponse:
        async def operation(access: AccessContext) -> ToolPayload:
            data = await _read(
                backend,
                BackendReadOperation.COMPARE_BOQ_VERSIONS,
                access,
                {
                    "project_id": project_id,
                    "version_a": version_a,
                    "version_b": version_b,
                },
            )
            return _payload(
                data,
                domain=DomainName.PROJECTS_BOQ,
                record_id=str(project_id),
                version=f"{version_a}..{version_b}",
                result_count=(
                    len(data.get("added", []))
                    + len(data.get("removed", []))
                    + len(data.get("changed", []))
                ),
            )

        return await runtime.execute(
            registry.tool("compare_boq_versions"),
            operation,
            project_id=str(project_id),
            target_record_ids=[str(project_id), version_a, version_b],
        )

    @mcp.tool(
        description="List minimized user access facts for one authorized project.",
        annotations=READ_ONLY_ANNOTATIONS,
        structured_output=True,
    )
    async def list_project_access(
        project_id: UUID,
        cursor: Cursor = None,
        limit: ProjectLimit = 20,
    ) -> ToolResponse:
        async def operation(access: AccessContext) -> ToolPayload:
            data = await _read(
                backend,
                BackendReadOperation.LIST_PROJECT_ACCESS,
                access,
                {"project_id": project_id, "cursor": cursor, "limit": limit},
            )
            return _payload(
                data,
                domain=DomainName.USERS_ACCESS,
                record_id=str(project_id),
            )

        return await runtime.execute(
            registry.tool("list_project_access"),
            operation,
            project_id=str(project_id),
            target_record_ids=[str(project_id)],
        )

    @mcp.tool(
        description="Get minimized Product access facts for an opaque user identifier.",
        annotations=READ_ONLY_ANNOTATIONS,
        structured_output=True,
    )
    async def get_user_access(
        user_id: Annotated[
            str,
            Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._~-]+$"),
        ],
    ) -> ToolResponse:
        async def operation(access: AccessContext) -> ToolPayload:
            data = await _read(
                backend,
                BackendReadOperation.GET_USER_ACCESS,
                access,
                {"user_id": user_id},
            )
            return _payload(
                data,
                domain=DomainName.USERS_ACCESS,
                record_id=user_id,
            )

        return await runtime.execute(
            registry.tool("get_user_access"),
            operation,
            target_record_ids=[user_id],
        )
