"""Foundation discovery tools."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from app.policy.models import AccessContext
from app.schemas.common import Freshness, SourceReference, ToolResponse
from app.tools.registry import DomainName, ToolRegistry
from app.tools.runtime import NotFoundOrForbidden, ToolPayload, ToolRuntime

READ_ONLY_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)


def register_discovery_tools(
    mcp: FastMCP,
    runtime: ToolRuntime,
    registry: ToolRegistry,
) -> None:
    @mcp.tool(
        description="List Product MCP domains and currently available tools in your access scope.",
        annotations=READ_ONLY_ANNOTATIONS,
        structured_output=True,
    )
    async def get_system_catalog() -> ToolResponse:
        async def operation(access: AccessContext) -> ToolPayload:
            return ToolPayload(
                data={
                    "catalog_version": "1.0",
                    "data_mode": "read_only",
                    "domains": registry.visible_domain_items(access),
                },
                sources=[
                    SourceReference(
                        domain=DomainName.SYSTEM_CATALOG.value,
                        record_id="product-mcp-registry-v1",
                        source_system="mcp_registry",
                        version="1.0",
                    )
                ],
                freshness=Freshness(source_read_at=access.resolved_at, cache_status="bypass"),
                result_count=len(registry.visible_domain_items(access)),
            )

        return await runtime.execute(registry.tool("get_system_catalog"), operation)

    @mcp.tool(
        description="Describe one Product MCP domain if it is visible in your access scope.",
        annotations=READ_ONLY_ANNOTATIONS,
        structured_output=True,
    )
    async def describe_domain(domain: DomainName) -> ToolResponse:
        async def operation(access: AccessContext) -> ToolPayload:
            definition = registry.domains[domain]
            if not registry.domain_visible(definition, access):
                raise NotFoundOrForbidden
            return ToolPayload(
                data=registry.domain_item(definition, access),
                sources=[
                    SourceReference(
                        domain=DomainName.SYSTEM_CATALOG.value,
                        record_id=f"domain-{domain.value}",
                        source_system="mcp_registry",
                        version="1.0",
                    )
                ],
                freshness=Freshness(source_read_at=access.resolved_at, cache_status="bypass"),
            )

        return await runtime.execute(registry.tool("describe_domain"), operation)
