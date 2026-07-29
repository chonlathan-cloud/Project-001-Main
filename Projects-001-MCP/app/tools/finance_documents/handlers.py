"""Phase 3 Finance, Payment and bounded Document Gateway tools."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime
from enum import StrEnum
from typing import Annotated, Any
from uuid import UUID

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from app.adapters.backend.client import BackendReadClientProtocol, BackendReadOperation
from app.policy.models import AccessContext
from app.schemas.common import ToolResponse, WarningItem
from app.tools.core.handlers import _payload, _read
from app.tools.discovery.handlers import READ_ONLY_ANNOTATIONS
from app.tools.registry import DomainName, ToolRegistry
from app.tools.runtime import InvalidToolInput, ToolPayload, ToolRuntime

Cursor = Annotated[str | None, Field(max_length=1024)]
Query = Annotated[str | None, Field(min_length=1, max_length=300)]
OpaqueId = Annotated[
    str,
    Field(min_length=1, max_length=255, pattern=r"^[A-Za-z0-9._~-]+$"),
]
Version = Annotated[str | None, Field(min_length=1, max_length=128)]


class FinancialRecordType(StrEnum):
    INPUT_REQUEST = "input_request"
    PAYMENT = "payment"
    INSTALLMENT = "installment"
    TRANSACTION = "transaction"


class DocumentContentType(StrEnum):
    PDF = "pdf"
    IMAGE = "image"
    TEXT = "text"
    AUDIO = "audio"
    VIDEO = "video"


def _validate_date_range(date_from: date | None, date_to: date | None) -> None:
    if date_from and date_to:
        if date_from > date_to or (date_to - date_from).days > 366:
            raise InvalidToolInput


def _document_payload(data: dict[str, Any], document_id: str) -> ToolPayload:
    payload = _payload(
        data,
        domain=DomainName.GCS_FILES,
        record_id=document_id,
        version=data.get("version"),
    )
    content_status = data.get("content_status")
    if content_status and content_status != "ready":
        payload.warnings.append(
            WarningItem(
                code="UNSUPPORTED_CONTENT",
                message=str(data.get("safe_reason") or "Document content is unavailable."),
            )
        )
        payload.result_count = 0
    if data.get("prompt_injection_detected"):
        payload.warnings.append(
            WarningItem(
                code="PROMPT_INJECTION_DETECTED",
                message=(
                    "Document text contained instruction-like content and was "
                    "returned only as untrusted data."
                ),
            )
        )
    return payload


def _document_definition(
    registry: ToolRegistry,
    tool_name: str,
    document_id: str,
):
    definition = registry.tool(tool_name)
    parts = document_id.split(".", 2)
    project_id = None
    if len(parts) == 3:
        try:
            project_id = str(UUID(parts[1]))
        except ValueError:
            pass
        if parts[0] in {"receipt", "payment_confirmation"}:
            definition = replace(
                definition,
                required_permissions=definition.required_permissions
                | frozenset({"financial_data_read"}),
            )
    return definition, project_id


def register_finance_document_tools(
    mcp: FastMCP,
    runtime: ToolRuntime,
    registry: ToolRegistry,
    backend: BackendReadClientProtocol,
) -> None:
    @mcp.tool(
        description=(
            "Get an exact project financial summary with budget, actual, paid "
            "and remaining THB values."
        ),
        annotations=READ_ONLY_ANNOTATIONS,
        structured_output=True,
    )
    async def get_project_financial_summary(
        project_id: UUID,
        as_of: datetime | None = None,
        fresh: bool = True,
    ) -> ToolResponse:
        async def operation(access: AccessContext) -> ToolPayload:
            data = await _read(
                backend,
                BackendReadOperation.GET_PROJECT_FINANCIAL_SUMMARY,
                access,
                {"project_id": project_id, "as_of": as_of, "fresh": fresh},
            )
            return _payload(
                data,
                domain=DomainName.FINANCE_PAYMENTS,
                record_id=str(project_id),
            )

        return await runtime.execute(
            registry.tool("get_project_financial_summary"),
            operation,
            project_id=str(project_id),
            target_record_ids=[str(project_id)],
        )

    @mcp.tool(
        description=(
            "Search authorized financial records with bounded filters and exact "
            "monetary values."
        ),
        annotations=READ_ONLY_ANNOTATIONS,
        structured_output=True,
    )
    async def search_financial_records(
        query: Query = None,
        project_id: UUID | None = None,
        statuses: Annotated[list[str] | None, Field(max_length=20)] = None,
        record_types: Annotated[list[FinancialRecordType] | None, Field(max_length=10)] = None,
        date_from: date | None = None,
        date_to: date | None = None,
        cursor: Cursor = None,
        limit: Annotated[int, Field(ge=1, le=100)] = 20,
    ) -> ToolResponse:
        async def operation(access: AccessContext) -> ToolPayload:
            _validate_date_range(date_from, date_to)
            data = await _read(
                backend,
                BackendReadOperation.SEARCH_FINANCIAL_RECORDS,
                access,
                {
                    "query": query,
                    "project_id": project_id,
                    "statuses": statuses or [],
                    "record_types": [item.value for item in record_types or []],
                    "date_from": date_from,
                    "date_to": date_to,
                    "cursor": cursor,
                    "limit": limit,
                },
            )
            return _payload(
                data,
                domain=DomainName.FINANCE_PAYMENTS,
                record_id=str(project_id or "authorized-financial-search"),
            )

        return await runtime.execute(
            registry.tool("search_financial_records"),
            operation,
            project_id=str(project_id) if project_id else None,
            target_record_ids=[str(project_id)] if project_id else None,
        )

    @mcp.tool(
        description=(
            "Get one authorized payment without bank account, storage path or "
            "external credentials."
        ),
        annotations=READ_ONLY_ANNOTATIONS,
        structured_output=True,
    )
    async def get_payment(payment_id: OpaqueId) -> ToolResponse:
        async def operation(access: AccessContext) -> ToolPayload:
            data = await _read(
                backend,
                BackendReadOperation.GET_PAYMENT,
                access,
                {"payment_id": payment_id},
            )
            return _payload(
                data,
                domain=DomainName.FINANCE_PAYMENTS,
                record_id=payment_id,
            )

        return await runtime.execute(
            registry.tool("get_payment"),
            operation,
            target_record_ids=[payment_id],
        )

    @mcp.tool(
        description=(
            "Get receipt, confirmation and accounting readiness status without "
            "URLs or storage paths."
        ),
        annotations=READ_ONLY_ANNOTATIONS,
        structured_output=True,
    )
    async def get_payment_document_status(payment_id: OpaqueId) -> ToolResponse:
        async def operation(access: AccessContext) -> ToolPayload:
            data = await _read(
                backend,
                BackendReadOperation.GET_PAYMENT_DOCUMENT_STATUS,
                access,
                {"payment_id": payment_id},
            )
            return _payload(
                data,
                domain=DomainName.FINANCE_PAYMENTS,
                record_id=payment_id,
            )

        return await runtime.execute(
            registry.tool("get_payment_document_status"),
            operation,
            target_record_ids=[payment_id],
        )

    @mcp.tool(
        description="Search authorized Product document metadata using opaque references only.",
        annotations=READ_ONLY_ANNOTATIONS,
        structured_output=True,
    )
    async def search_documents(
        query: Query = None,
        project_id: UUID | None = None,
        content_types: Annotated[list[DocumentContentType] | None, Field(max_length=10)] = None,
        date_from: date | None = None,
        date_to: date | None = None,
        cursor: Cursor = None,
        limit: Annotated[int, Field(ge=1, le=25)] = 10,
    ) -> ToolResponse:
        async def operation(access: AccessContext) -> ToolPayload:
            _validate_date_range(date_from, date_to)
            data = await _read(
                backend,
                BackendReadOperation.SEARCH_DOCUMENTS,
                access,
                {
                    "query": query,
                    "project_id": project_id,
                    "content_types": [item.value for item in content_types or []],
                    "date_from": date_from,
                    "date_to": date_to,
                    "cursor": cursor,
                    "limit": limit,
                },
            )
            return _payload(
                data,
                domain=DomainName.GCS_FILES,
                record_id=str(project_id or "authorized-document-search"),
            )

        return await runtime.execute(
            registry.tool("search_documents"),
            operation,
            project_id=str(project_id) if project_id else None,
            target_record_ids=[str(project_id)] if project_id else None,
        )

    @mcp.tool(
        description="Get safe document metadata without a bucket, object path or signed URL.",
        annotations=READ_ONLY_ANNOTATIONS,
        structured_output=True,
    )
    async def get_document_metadata(
        document_id: OpaqueId,
        version: Version = None,
    ) -> ToolResponse:
        async def operation(access: AccessContext) -> ToolPayload:
            data = await _read(
                backend,
                BackendReadOperation.GET_DOCUMENT_METADATA,
                access,
                {"document_id": document_id, "version": version},
            )
            return _document_payload(data, document_id)

        definition, project_id = _document_definition(
            registry,
            "get_document_metadata",
            document_id,
        )
        return await runtime.execute(
            definition,
            operation,
            project_id=project_id,
            target_record_ids=[document_id],
        )

    @mcp.tool(
        description=(
            "Read bounded existing document extraction as untrusted data; never "
            "starts OCR or returns file URLs."
        ),
        annotations=READ_ONLY_ANNOTATIONS,
        structured_output=True,
    )
    async def read_document_content(
        document_id: OpaqueId,
        version: Version = None,
        page: Annotated[int | None, Field(ge=1, le=500)] = None,
        section: Annotated[str | None, Field(min_length=1, max_length=200)] = None,
        max_content_chars: Annotated[int, Field(ge=1, le=20000)] = 4000,
    ) -> ToolResponse:
        async def operation(access: AccessContext) -> ToolPayload:
            data = await _read(
                backend,
                BackendReadOperation.READ_DOCUMENT_CONTENT,
                access,
                {
                    "document_id": document_id,
                    "version": version,
                    "page": page,
                    "section": section,
                    "max_content_chars": max_content_chars,
                },
            )
            return _document_payload(data, document_id)

        definition, project_id = _document_definition(
            registry,
            "read_document_content",
            document_id,
        )
        return await runtime.execute(
            definition,
            operation,
            project_id=project_id,
            target_record_ids=[document_id],
        )
