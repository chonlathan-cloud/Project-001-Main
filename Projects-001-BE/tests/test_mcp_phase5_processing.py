from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest

from app.api.v1.mcp_internal import router
from app.schemas.mcp_schema import McpProcessingStatusRequest
from app.services.mcp_processing_service import McpNotFoundOrForbidden, get_processing_status

PROJECT_ID = UUID("10000000-0000-4000-8000-000000000001")
JOB_ID = UUID("30000000-0000-4000-8000-000000000003")


def principal() -> dict[str, object]:
    return {
        "subject": "oauth-owner-001",
        "issuer": "https://issuer.test",
        "client_id": "inspector-test-client",
        "environment": "demo",
    }


def test_receipt_processing_status_is_bounded_and_authorized() -> None:
    request = McpProcessingStatusRequest(
        **principal(),
        workflow="receipt_ocr",
        job_id=str(JOB_ID),
    )
    item = SimpleNamespace(
        id=JOB_ID,
        project_id=PROJECT_ID,
        ocr_raw_json={"forbidden": "document body"},
        ocr_low_confidence_fields=["vendor", "amount"],
        updated_at=datetime(2026, 7, 30, tzinfo=UTC),
    )
    with (
        patch(
            "app.services.mcp_processing_service._input_request",
            new=AsyncMock(return_value=item),
        ),
        patch("app.services.mcp_processing_service._authorize") as authorize,
    ):
        result = asyncio.run(get_processing_status(object(), request))

    assert authorize.call_count == 2
    assert result["status"] == "READY"
    assert result["progress"] == {
        "has_existing_extraction": True,
        "low_confidence_field_count": 2,
    }
    serialized = str(result).lower()
    assert "document body" not in serialized
    assert "ocr_raw_json" not in serialized


def test_flowaccount_processing_status_omits_external_ids_and_errors() -> None:
    request = McpProcessingStatusRequest(
        **principal(),
        workflow="flowaccount_sync",
        job_id=str(JOB_ID),
    )
    item = SimpleNamespace(
        id=JOB_ID,
        project_id=PROJECT_ID,
        flowaccount_sync_status="PARTIAL_SYNC",
        flowaccount_attachment_status="SYNCED",
        flowaccount_supplier_invoice_status="NOT_READY",
        flowaccount_payment_status="NOT_READY",
        flowaccount_external_document_id="must-not-leak",
        flowaccount_sync_error="credential=must-not-leak",
        updated_at=datetime(2026, 7, 30, tzinfo=UTC),
    )
    with (
        patch(
            "app.services.mcp_processing_service._input_request",
            new=AsyncMock(return_value=item),
        ),
        patch("app.services.mcp_processing_service._authorize"),
    ):
        result = asyncio.run(get_processing_status(object(), request))

    assert result["status"] == "PARTIAL_SYNC"
    serialized = str(result).lower()
    assert "must-not-leak" not in serialized
    assert "external_document" not in serialized
    assert "sync_error" not in serialized


def test_phase5_processing_route_is_service_internal() -> None:
    assert "/internal/mcp/processing/status:get" in {route.path for route in router.routes}


def test_processing_permission_denial_stops_before_job_source_read() -> None:
    request = McpProcessingStatusRequest(
        **principal(),
        workflow="boq_sync",
        job_id="job-demo-001",
    )
    with (
        patch(
            "app.services.mcp_processing_service._authorize",
            side_effect=McpNotFoundOrForbidden,
        ),
        patch(
            "app.services.mcp_processing_service.boq_sync_job_service.get_boq_sync_job",
            new=AsyncMock(),
        ) as source_read,
    ):
        with pytest.raises(McpNotFoundOrForbidden):
            asyncio.run(get_processing_status(object(), request))

    source_read.assert_not_awaited()
