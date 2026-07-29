from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest

from app.api.v1.mcp_internal import router
from app.core.config import Settings
from app.schemas.mcp_schema import (
    McpDailyReportRequest,
    McpDailyReportsListRequest,
    McpDashboardSummaryRequest,
    McpInspectionRequest,
    McpProjectInsightsRequest,
)
from app.services.mcp_project_operations_service import (
    get_daily_report,
    get_inspection_item,
    get_project_insights,
)

PROJECT_ID = UUID("10000000-0000-4000-8000-000000000001")


def settings() -> Settings:
    return Settings(
        _env_file=None,
        APP_ENV="test",
        FRONTEND_BASE_URL="https://product.test",
        JWT_SECRET_KEY="unit-test-only",  # noqa: S106 - inert test fixture
        MCP_CURSOR_SECRET="cursor-test-only",  # noqa: S106 - inert test fixture
    )


def principal() -> dict[str, object]:
    return {
        "subject": "oauth-owner-001",
        "issuer": "https://issuer.test",
        "client_id": "inspector-test-client",
        "environment": "demo",
    }


def test_phase4_date_ranges_are_bounded() -> None:
    with pytest.raises(ValueError):
        McpDailyReportsListRequest(
            **principal(),
            project_id=PROJECT_ID,
            date_from="2025-01-01",
            date_to="2026-07-29",
        )
    with pytest.raises(ValueError):
        McpDashboardSummaryRequest(
            **principal(),
            date_from="2025-01-01",
            date_to="2026-07-29",
        )


def test_inspection_detail_uses_opaque_documents_and_omits_actor_and_paths() -> None:
    request = McpInspectionRequest(
        **principal(),
        project_id=PROJECT_ID,
        item_id="defect_001",
    )
    defect = {
        "id": "defect_001",
        "project_id": str(PROJECT_ID),
        "round_id": "round_001",
        "title": "Wall crack",
        "status": "OPEN",
        "severity": "MAJOR",
        "before_file_ids": ["file_before_001"],
        "after_file_ids": [],
        "storage_key": "gs://private/inspection.jpg",
    }
    events = [
        {
            "id": "event_001",
            "event_type": "CREATED",
            "actor_id": "private-user-id",
            "actor_role": "admin",
            "created_at": datetime(2026, 7, 29, tzinfo=UTC),
        }
    ]
    with (
        patch("app.services.mcp_project_operations_service._authorize"),
        patch(
            "app.services.mcp_project_operations_service._require_project",
            new=AsyncMock(),
        ),
        patch(
            "app.services.mcp_project_operations_service.inspection_service.get_defect_for_mcp",
            return_value=defect,
        ),
        patch(
            "app.services.mcp_project_operations_service.inspection_service.list_events_for_mcp",
            return_value=events,
        ),
    ):
        result = asyncio.run(get_inspection_item(object(), request, settings=settings()))

    assert result["document_ids"] == [f"inspection.{PROJECT_ID}.file_before_001"]
    serialized = str(result).lower()
    assert "storage_key" not in serialized
    assert "gs://" not in serialized
    assert "private-user-id" not in serialized


def test_daily_report_explicit_version_uses_immutable_snapshot_without_share_data() -> None:
    request = McpDailyReportRequest(
        **principal(),
        report_id="report_001",
        version="v2",
    )
    report = {
        "id": "report_001",
        "project_id": str(PROJECT_ID),
        "status": "CORRECTION_DRAFT",
        "summary": "mutable draft must not win",
        "share_token": "forbidden",
        "published_version": 2,
    }
    version = {
        "id": "report_001-v2",
        "report_id": "report_001",
        "version": 2,
        "snapshot": {
            "report_id": "report_001",
            "project_id": str(PROJECT_ID),
            "report_date": "2026-07-29",
            "summary": "immutable published summary",
            "published_media_ids": ["private-media-id"],
        },
        "published_at": datetime(2026, 7, 29, tzinfo=UTC),
    }
    with (
        patch(
            "app.services.mcp_project_operations_service._authorized_report",
            new=AsyncMock(return_value=report),
        ),
        patch(
            "app.services.mcp_project_operations_service._require_project",
            new=AsyncMock(),
        ),
        patch(
            "app.services.mcp_project_operations_service.daily_report_service."
            "get_report_version_for_mcp",
            return_value=version,
        ),
    ):
        result = asyncio.run(get_daily_report(object(), request, settings=settings()))

    assert result["summary"] == "immutable published summary"
    assert result["status"] == "PUBLISHED"
    assert result["selected_version"]["immutable"] is True
    serialized = str(result).lower()
    assert "mutable draft" not in serialized
    assert "share_token" not in serialized
    assert "forbidden" not in serialized
    assert "private-media-id" not in serialized


def test_project_insights_marks_source_outage_partial_and_keeps_sources_separate() -> None:
    request = McpProjectInsightsRequest(
        **principal(),
        project_id=PROJECT_ID,
    )
    financial = {
        "project_id": str(PROJECT_ID),
        "budget": {"amount": "160000.00", "currency": "THB"},
        "actual": {"amount": "90000.00", "currency": "THB"},
        "over_budget": False,
        "product_url": "https://product.test/project/detail/opaque",
        "source_read_at": datetime(2026, 7, 29, tzinfo=UTC),
    }
    reports = [
        {
            "id": "report_001",
            "report_date": "2026-07-29",
            "progress_percent": 62,
        }
    ]
    with (
        patch("app.services.mcp_project_operations_service._authorize"),
        patch(
            "app.services.mcp_project_operations_service.get_project_financial_summary",
            new=AsyncMock(return_value=financial),
        ),
        patch(
            "app.services.mcp_project_operations_service.inspection_service.list_defects",
            side_effect=RuntimeError("source outage"),
        ),
        patch(
            "app.services.mcp_project_operations_service.daily_report_service.list_reports_for_mcp",
            return_value=reports,
        ),
    ):
        result = asyncio.run(get_project_insights(object(), request, settings=settings()))

    assert result["partial"] is True
    assert result["source_status"] == {
        "finance": "available",
        "inspection": "unavailable",
        "daily_reports": "available",
    }
    assert result["inspection"] is None
    assert result["daily_reports"]["latest_progress_percent"] == 62
    assert result["warnings"][0]["code"] == "SOURCE_UNAVAILABLE"
    assert result["calculation_method"].startswith("independent_")


def test_phase4_backend_routes_are_service_internal() -> None:
    paths = {route.path for route in router.routes}
    assert {
        "/internal/mcp/inspection/items:list",
        "/internal/mcp/inspection/items:get",
        "/internal/mcp/daily-reports:list",
        "/internal/mcp/daily-reports:get",
        "/internal/mcp/daily-reports/versions:list",
        "/internal/mcp/daily-reports/share-status:get",
        "/internal/mcp/dashboard:summary",
        "/internal/mcp/projects/insights:get",
    }.issubset(paths)
