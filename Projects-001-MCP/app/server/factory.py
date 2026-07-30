"""Product MCP server and ASGI application factory."""

from __future__ import annotations

import logging
from typing import cast

from mcp.server.auth.provider import TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import AnyHttpUrl
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

from app import __version__
from app.adapters.audit.client import AuditReadClientProtocol, GoogleCloudAuditReadClient
from app.adapters.backend.client import BackendReadClient, BackendReadClientProtocol
from app.adapters.gcp.client import GcpOperationsClientProtocol, GoogleCloudOperationsClient
from app.audit.emitter import AuditEmitter, StructuredAuditEmitter
from app.auth.oidc import OidcJwtTokenVerifier
from app.config.settings import Settings
from app.policy.client import BackendPolicyClient, PolicyClient
from app.server.request_context import RequestIdMiddleware
from app.server.strict_fastmcp import ClosedInputFastMCP
from app.tools.access.handlers import register_access_tools
from app.tools.audit.handlers import register_audit_tools
from app.tools.core.handlers import register_core_tools
from app.tools.discovery.handlers import register_discovery_tools
from app.tools.finance_documents.handlers import register_finance_document_tools
from app.tools.gcp_operations.handlers import register_gcp_operation_tools
from app.tools.project_operations.handlers import register_project_operation_tools
from app.tools.registry import ToolRegistry
from app.tools.runtime import ToolRuntime


def create_mcp_server(
    settings: Settings,
    *,
    token_verifier: TokenVerifier | None = None,
    policy_client: PolicyClient | None = None,
    audit_emitter: AuditEmitter | None = None,
    backend_read_client: BackendReadClientProtocol | None = None,
    audit_read_client: AuditReadClientProtocol | None = None,
    gcp_operations_client: GcpOperationsClientProtocol | None = None,
) -> FastMCP:
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
    verifier = token_verifier or OidcJwtTokenVerifier(settings)
    policy = policy_client or BackendPolicyClient(settings)
    audit = audit_emitter or StructuredAuditEmitter(settings)
    backend = backend_read_client or BackendReadClient(settings)
    audit_reader = audit_read_client or GoogleCloudAuditReadClient(settings)
    gcp_operations = gcp_operations_client or GoogleCloudOperationsClient(settings)

    mcp = ClosedInputFastMCP(
        name="Projects-001 Product MCP",
        instructions=(
            "Read-only access to authorized Projects-001 business and operational data. "
            "Use discovery before bounded detail reads. Never request or reveal secrets."
        ),
        token_verifier=verifier,
        auth=AuthSettings(
            issuer_url=cast(AnyHttpUrl, settings.oauth_issuer),
            resource_server_url=cast(AnyHttpUrl, settings.resource_url),
            required_scopes=settings.oauth_required_scopes,
        ),
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
        log_level=settings.log_level.upper(),
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=settings.allowed_host_patterns,
            allowed_origins=settings.allowed_origins,
        ),
    )

    registry = ToolRegistry()
    runtime = ToolRuntime(settings, policy, audit)
    register_discovery_tools(mcp, runtime, registry)
    register_access_tools(mcp, runtime, registry)
    register_core_tools(mcp, runtime, registry, backend)
    register_finance_document_tools(mcp, runtime, registry, backend)
    register_project_operation_tools(mcp, runtime, registry, backend)
    register_audit_tools(mcp, runtime, registry, audit_reader, settings)
    register_gcp_operation_tools(mcp, runtime, registry, gcp_operations, backend, settings)

    @mcp.custom_route("/health", methods=["GET"], include_in_schema=False)
    async def health(_request: Request) -> JSONResponse:
        return JSONResponse(
            {
                "status": "ok",
                "service": settings.service_name,
                "version": __version__,
                "environment": settings.environment.value,
            },
            headers={"Cache-Control": "no-store"},
        )

    return mcp


def create_app(
    settings: Settings,
    *,
    token_verifier: TokenVerifier | None = None,
    policy_client: PolicyClient | None = None,
    audit_emitter: AuditEmitter | None = None,
    backend_read_client: BackendReadClientProtocol | None = None,
    audit_read_client: AuditReadClientProtocol | None = None,
    gcp_operations_client: GcpOperationsClientProtocol | None = None,
) -> ASGIApp:
    mcp = create_mcp_server(
        settings,
        token_verifier=token_verifier,
        policy_client=policy_client,
        audit_emitter=audit_emitter,
        backend_read_client=backend_read_client,
        audit_read_client=audit_read_client,
        gcp_operations_client=gcp_operations_client,
    )
    return RequestIdMiddleware(mcp.streamable_http_app())
