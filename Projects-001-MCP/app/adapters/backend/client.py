"""Bounded client for curated Product Backend MCP read contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Protocol

import httpx
from pydantic import BaseModel, ConfigDict, TypeAdapter, ValidationError

from app.config.settings import Settings
from app.policy.client import CloudRunIdentityTokenProvider, ServiceIdentityTokenProvider
from app.policy.models import AccessContext
from app.server.request_context import current_request_id

MAX_BACKEND_RESPONSE_BYTES = 5 * 1024 * 1024
JSON_OBJECT = TypeAdapter(dict[str, Any])


class BackendReadOperation(StrEnum):
    SEARCH = "search"
    FETCH = "fetch"
    LIST_PROJECTS = "list_projects"
    GET_PROJECT = "get_project"
    GET_PROJECT_SUMMARY = "get_project_summary"
    GET_BOQ_CURRENT = "get_boq_current"
    LIST_BOQ_VERSIONS = "list_boq_versions"
    GET_BOQ_VERSION = "get_boq_version"
    COMPARE_BOQ_VERSIONS = "compare_boq_versions"
    LIST_PROJECT_ACCESS = "list_project_access"
    GET_USER_ACCESS = "get_user_access"
    GET_PROJECT_FINANCIAL_SUMMARY = "get_project_financial_summary"
    SEARCH_FINANCIAL_RECORDS = "search_financial_records"
    GET_PAYMENT = "get_payment"
    GET_PAYMENT_DOCUMENT_STATUS = "get_payment_document_status"
    SEARCH_DOCUMENTS = "search_documents"
    GET_DOCUMENT_METADATA = "get_document_metadata"
    READ_DOCUMENT_CONTENT = "read_document_content"
    GET_REPORT_SHARE_STATUS = "get_report_share_status"


ENDPOINTS = {
    BackendReadOperation.SEARCH: "/api/v1/internal/mcp/search",
    BackendReadOperation.FETCH: "/api/v1/internal/mcp/fetch",
    BackendReadOperation.LIST_PROJECTS: "/api/v1/internal/mcp/projects:list",
    BackendReadOperation.GET_PROJECT: "/api/v1/internal/mcp/projects:get",
    BackendReadOperation.GET_PROJECT_SUMMARY: "/api/v1/internal/mcp/projects:summary",
    BackendReadOperation.GET_BOQ_CURRENT: "/api/v1/internal/mcp/boq:current",
    BackendReadOperation.LIST_BOQ_VERSIONS: "/api/v1/internal/mcp/boq/versions:list",
    BackendReadOperation.GET_BOQ_VERSION: "/api/v1/internal/mcp/boq/versions:get",
    BackendReadOperation.COMPARE_BOQ_VERSIONS: "/api/v1/internal/mcp/boq/versions:compare",
    BackendReadOperation.LIST_PROJECT_ACCESS: "/api/v1/internal/mcp/project-access:list",
    BackendReadOperation.GET_USER_ACCESS: "/api/v1/internal/mcp/user-access:get",
    BackendReadOperation.GET_PROJECT_FINANCIAL_SUMMARY: (
        "/api/v1/internal/mcp/finance/projects:summary"
    ),
    BackendReadOperation.SEARCH_FINANCIAL_RECORDS: "/api/v1/internal/mcp/finance/records:search",
    BackendReadOperation.GET_PAYMENT: "/api/v1/internal/mcp/payments:get",
    BackendReadOperation.GET_PAYMENT_DOCUMENT_STATUS: (
        "/api/v1/internal/mcp/payments/document-status:get"
    ),
    BackendReadOperation.SEARCH_DOCUMENTS: "/api/v1/internal/mcp/documents:search",
    BackendReadOperation.GET_DOCUMENT_METADATA: "/api/v1/internal/mcp/documents/metadata:get",
    BackendReadOperation.READ_DOCUMENT_CONTENT: "/api/v1/internal/mcp/documents/content:read",
    BackendReadOperation.GET_REPORT_SHARE_STATUS: (
        "/api/v1/internal/mcp/daily-reports/share-status:get"
    ),
}


class BackendReadError(RuntimeError):
    pass


class BackendNotFoundOrForbidden(BackendReadError):
    pass


class BackendInvalidInput(BackendReadError):
    pass


class BackendRateLimited(BackendReadError):
    pass


class BackendReadEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    data: dict[str, Any]


class BackendReadClientProtocol(Protocol):
    async def read(
        self,
        operation: BackendReadOperation,
        access: AccessContext,
        payload: dict[str, Any],
    ) -> dict[str, Any]: ...


class BackendReadClient:
    def __init__(
        self,
        settings: Settings,
        *,
        token_provider: ServiceIdentityTokenProvider | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._settings = settings
        self._token_provider = token_provider or CloudRunIdentityTokenProvider()
        self._transport = transport

    async def read(
        self,
        operation: BackendReadOperation,
        access: AccessContext,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        body = {
            **payload,
            "contract_version": "1.0",
            "subject": access.subject,
            "issuer": access.issuer,
            "client_id": access.client_id,
            "environment": access.environment.value,
        }
        try:
            service_token = await self._token_provider.get_token(self._settings.backend_audience)
            async with httpx.AsyncClient(
                base_url=self._settings.canonical_backend_url,
                timeout=self._settings.backend_timeout_seconds,
                follow_redirects=False,
                transport=self._transport,
            ) as client:
                response = await client.post(
                    ENDPOINTS[operation],
                    headers={
                        "Authorization": f"Bearer {service_token}",
                        "X-Request-ID": current_request_id(),
                        "X-MCP-Contract-Version": "1.0",
                    },
                    json=JSON_OBJECT.dump_python(body, mode="json"),
                )
        except (httpx.HTTPError, KeyError) as exc:
            raise BackendReadError("Backend read contract is unavailable.") from exc

        if response.status_code in {403, 404}:
            raise BackendNotFoundOrForbidden
        if response.status_code in {400, 422}:
            raise BackendInvalidInput
        if response.status_code == 429:
            raise BackendRateLimited
        if response.status_code != 200:
            raise BackendReadError("Backend read contract is unavailable.")
        if len(response.content) > MAX_BACKEND_RESPONSE_BYTES:
            raise BackendReadError("Backend read response exceeded the allowed size.")
        try:
            envelope = BackendReadEnvelope.model_validate(response.json())
        except (ValidationError, ValueError, TypeError) as exc:
            raise BackendReadError("Backend read contract returned an invalid envelope.") from exc
        if envelope.status != "success":
            raise BackendReadError("Backend read contract did not succeed.")
        return envelope.data
