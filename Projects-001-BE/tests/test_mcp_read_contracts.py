from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest

from app.core.config import Settings
from app.models.boq import BOQItem
from app.schemas.mcp_schema import (
    McpProjectAccessRequest,
    McpProjectRequest,
    McpSearchRequest,
    McpUserAccessRequest,
)
from app.services.mcp_read_service import (
    McpInvalidInput,
    _boq_line_reference,
    _decode_cursor,
    _encode_cursor,
    build_boq_manifests,
    compare_boq_snapshots,
    get_project,
    get_user_access,
    list_project_access,
    serialize_boq_snapshot,
)

PROJECT_ID = UUID("10000000-0000-4000-8000-000000000001")


def settings() -> Settings:
    return Settings(
        _env_file=None,
        APP_ENV="test",
        FRONTEND_BASE_URL="https://product.test",
        JWT_SECRET_KEY="unit-test-only",
        MCP_CURSOR_SECRET="cursor-test-only",
    )


def line(
    line_id: str,
    *,
    item_no: str,
    description: str,
    amount: str,
) -> BOQItem:
    return BOQItem(
        id=UUID(line_id),
        project_id=PROJECT_ID,
        boq_type="CUSTOMER",
        sheet_name="Main",
        wbs_level=1,
        parent_id=None,
        item_no=item_no,
        description=description,
        qty=Decimal("1"),
        unit="LS",
        material_unit_price=Decimal(amount),
        labor_unit_price=Decimal("0"),
        total_material=Decimal(amount),
        total_labor=Decimal("0"),
        grand_total=Decimal(amount),
    )


def test_cursor_is_scope_bound_and_tamper_evident() -> None:
    encoded = _encode_cursor("projects", 20, settings())
    assert _decode_cursor(encoded, "projects", settings()) == 20
    with pytest.raises(McpInvalidInput):
        _decode_cursor(encoded, "boq-versions", settings())
    replacement = "A" if encoded[-1] != "A" else "B"
    with pytest.raises(McpInvalidInput):
        _decode_cursor(f"{encoded[:-1]}{replacement}", "projects", settings())


def test_boq_manifest_is_stable_and_preserves_legacy_boundary() -> None:
    first = datetime(2026, 6, 1, tzinfo=UTC)
    second = datetime(2026, 7, 1, tzinfo=UTC)
    manifests = build_boq_manifests(PROJECT_ID, [second, None, first, second])

    assert [item["version_number"] for item in manifests] == [1, 2, 3]
    assert manifests[0]["valid_from"] == datetime(1970, 1, 1, tzinfo=UTC)
    assert manifests[-1]["is_current"] is True
    assert build_boq_manifests(PROJECT_ID, [second, None, first, second]) == manifests


def test_boq_snapshot_uses_exact_money_and_stable_line_identity() -> None:
    v3_lines = [
        line(
            "30000000-0000-4000-8000-000000000001",
            item_no="1",
            description="Foundation",
            amount="100000.00",
        ),
        line(
            "30000000-0000-4000-8000-000000000002",
            item_no="2",
            description="Roof",
            amount="50000.00",
        ),
    ]
    v4_lines = [
        line(
            "40000000-0000-4000-8000-000000000001",
            item_no="1",
            description="Foundation reinforced",
            amount="120000.00",
        ),
        line(
            "40000000-0000-4000-8000-000000000002",
            item_no="3",
            description="Walls",
            amount="40000.00",
        ),
    ]
    manifest_v3 = {
        "version_id": "boq-v3",
        "version_number": 3,
        "valid_from": datetime(2026, 6, 1, tzinfo=UTC),
        "valid_to": datetime(2026, 7, 1, tzinfo=UTC),
        "is_current": False,
    }
    manifest_v4 = {
        "version_id": "boq-v4",
        "version_number": 4,
        "valid_from": datetime(2026, 7, 1, tzinfo=UTC),
        "valid_to": None,
        "is_current": True,
    }
    snapshot_v3 = serialize_boq_snapshot(
        PROJECT_ID, "Demo Riverside", manifest_v3, v3_lines, settings()
    )
    snapshot_v4 = serialize_boq_snapshot(
        PROJECT_ID, "Demo Riverside", manifest_v4, v4_lines, settings()
    )
    comparison = compare_boq_snapshots(snapshot_v3, snapshot_v4)

    assert snapshot_v4["lines"][0]["grand_total"] == {
        "amount": "120000.00",
        "currency": "THB",
    }
    assert snapshot_v3["lines"][0]["line_id"] == snapshot_v4["lines"][0]["line_id"]
    assert [item["description"] for item in comparison["added"]] == ["Walls"]
    assert [item["description"] for item in comparison["removed"]] == ["Roof"]
    assert comparison["changed"][0]["changed_fields"] == [
        "description",
        "material_unit_price",
        "total_material",
        "grand_total",
    ]


def test_boq_line_reference_is_stable_across_scd2_row_ids() -> None:
    old_row = line(
        "30000000-0000-4000-8000-000000000001",
        item_no="1",
        description="Foundation",
        amount="100000.00",
    )
    new_row = line(
        "40000000-0000-4000-8000-000000000001",
        item_no="1",
        description="Foundation reinforced",
        amount="120000.00",
    )
    old_snapshot = serialize_boq_snapshot(PROJECT_ID, "Demo", None, [old_row], settings())
    new_snapshot = serialize_boq_snapshot(PROJECT_ID, "Demo", None, [new_row], settings())

    old_line_id = old_snapshot["lines"][0]["line_id"]
    new_line_id = new_snapshot["lines"][0]["line_id"]
    assert old_line_id == new_line_id
    assert _boq_line_reference(PROJECT_ID, old_line_id) == (
        f"projects_boq:boq_line:{PROJECT_ID}.{old_line_id}"
    )


def test_project_detail_uses_current_customer_budget() -> None:
    principal = {
        "subject": "oauth-owner-001",
        "issuer": "https://issuer.test",
        "client_id": "inspector-test-client",
        "environment": "demo",
    }
    project = SimpleNamespace(
        id=PROJECT_ID,
        name="Demo Riverside",
        project_type="residential",
        status="ACTIVE",
        contingency_budget=Decimal("5000.00"),
        overhead_percent=Decimal("5.00"),
        profit_percent=Decimal("10.00"),
        vat_percent=Decimal("7.00"),
    )
    with (
        patch("app.services.mcp_read_service._authorize"),
        patch(
            "app.services.mcp_read_service._load_project",
            new=AsyncMock(return_value=project),
        ),
        patch(
            "app.services.mcp_read_service._current_customer_budget",
            new=AsyncMock(return_value=Decimal("150000.00")),
        ),
    ):
        result = asyncio.run(
            get_project(
                object(),
                McpProjectRequest(**principal, project_id=PROJECT_ID),
                settings=settings(),
            )
        )

    assert result["current_boq_budget"] == {
        "amount": "150000.00",
        "currency": "THB",
    }


def test_comparison_reports_when_bounded_snapshots_are_partial() -> None:
    comparison = compare_boq_snapshots(
        {"lines": [], "version": None, "truncated": True},
        {"lines": [], "version": None, "truncated": False},
    )

    assert comparison["truncated"] is True


def test_search_date_range_is_bounded() -> None:
    principal = {
        "subject": "oauth-user-001",
        "issuer": "https://issuer.test",
        "client_id": "inspector-test-client",
        "environment": "demo",
        "query": "foundation",
    }
    with pytest.raises(ValueError):
        McpSearchRequest(
            **principal,
            date_from="2025-01-01",
            date_to="2026-07-01",
        )


def test_project_access_includes_minimized_product_principal_types() -> None:
    principal = {
        "subject": "oauth-owner-001",
        "issuer": "https://issuer.test",
        "client_id": "inspector-test-client",
        "environment": "demo",
    }
    owner = SimpleNamespace(role="owner", user_id="owner-001")
    admin = SimpleNamespace(
        id="owner-001",
        email="owner@example.com",
        display_name="Project Owner",
        role="owner",
        roles=["owner"],
        mcp_all_projects_read=False,
        is_active=True,
        external_mcp_enabled=True,
    )
    customer = SimpleNamespace(
        id="customer-001",
        name="Riverside Customer",
        contact_name="Narin",
        is_active=True,
    )
    subcontractor = SimpleNamespace(
        id="subcontractor-001",
        name="Build Team",
        contact_name=None,
        assigned_project_ids=[str(PROJECT_ID)],
        is_active=True,
    )

    def memberships(*, principal_type: str, principal_id: str) -> list[str]:
        if principal_type == "customer" and principal_id == customer.id:
            return [str(PROJECT_ID)]
        return []

    with (
        patch("app.services.mcp_read_service._authorize", return_value=owner),
        patch("app.services.mcp_read_service.list_admins", return_value=[admin]),
        patch("app.services.mcp_read_service.list_customers", return_value=[customer]),
        patch(
            "app.services.mcp_read_service.list_subcontractors",
            return_value=[subcontractor],
        ),
        patch(
            "app.services.mcp_read_service.daily_report_service.list_membership_project_ids",
            side_effect=memberships,
        ),
    ):
        result = asyncio.run(
            list_project_access(
                McpProjectAccessRequest(**principal, project_id=PROJECT_ID),
                settings=settings(),
            )
        )

    assert {item["principal_type"] for item in result["items"]} == {
        "admin",
        "customer",
        "subcontractor",
    }
    assert all("email" not in item and "phone" not in item for item in result["items"])


def test_owner_can_read_minimized_typed_customer_access() -> None:
    principal = {
        "subject": "oauth-owner-001",
        "issuer": "https://issuer.test",
        "client_id": "inspector-test-client",
        "environment": "demo",
    }
    owner = SimpleNamespace(role="owner", user_id="owner-001")
    customer = SimpleNamespace(
        id="customer-001",
        name="Riverside Customer",
        contact_name="Narin",
        is_active=True,
        updated_at=datetime(2026, 7, 1, tzinfo=UTC),
    )
    with (
        patch("app.services.mcp_read_service._authorize", return_value=owner),
        patch("app.services.mcp_read_service.get_customer", return_value=customer),
        patch(
            "app.services.mcp_read_service.daily_report_service.list_membership_project_ids",
            return_value=[str(PROJECT_ID)],
        ),
    ):
        result = asyncio.run(
            get_user_access(
                McpUserAccessRequest(**principal, user_id="customer.customer-001"),
                settings=settings(),
            )
        )

    assert result["user_id"] == "customer.customer-001"
    assert result["principal_type"] == "customer"
    assert result["assigned_project_ids"] == [str(PROJECT_ID)]
    assert "email" not in result and "phone" not in result
