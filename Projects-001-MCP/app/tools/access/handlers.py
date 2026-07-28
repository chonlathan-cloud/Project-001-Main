"""Foundation current-access tool."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from app.policy.models import AccessContext
from app.schemas.common import Freshness, SourceReference, ToolResponse
from app.tools.discovery.handlers import READ_ONLY_ANNOTATIONS
from app.tools.registry import DomainName, ToolRegistry
from app.tools.runtime import ToolPayload, ToolRuntime


def register_access_tools(
    mcp: FastMCP,
    runtime: ToolRuntime,
    registry: ToolRegistry,
) -> None:
    @mcp.tool(
        description="Show your effective Product MCP role, permissions and project scope.",
        annotations=READ_ONLY_ANNOTATIONS,
        structured_output=True,
    )
    async def get_current_access() -> ToolResponse:
        async def operation(access: AccessContext) -> ToolPayload:
            all_projects = access.role == "owner" or access.all_projects_read
            return ToolPayload(
                data={
                    "role": access.role,
                    "permissions": sorted(access.permissions),
                    "project_scope": {
                        "all_projects": all_projects,
                        "assigned_project_ids": (
                            [] if all_projects else sorted(access.assigned_project_ids)
                        ),
                    },
                    "external_mcp_enabled": access.external_mcp_enabled,
                    "authorization_revision": access.authorization_revision,
                    "resolved_at": access.resolved_at.isoformat(),
                },
                sources=[
                    SourceReference(
                        domain=DomainName.USERS_ACCESS.value,
                        record_id="current-user-access",
                        source_system="product_backend_authorization",
                        version=access.contract_version,
                        last_updated_at=access.resolved_at,
                    )
                ],
                freshness=Freshness(source_read_at=access.resolved_at, cache_status="bypass"),
            )

        return await runtime.execute(registry.tool("get_current_access"), operation)
