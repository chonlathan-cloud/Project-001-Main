from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.boq_margin_service import projected_boq_totals
from scripts.schema_preflight import validate_target


BACKEND_DIR = Path(__file__).resolve().parents[2]
REPOSITORY_DIR = BACKEND_DIR.parent
FIXTURE_PATH = (
    BACKEND_DIR / "tests/fixtures/boq_v2_phase0/legacy_budget_consumers.json"
)
SNAPSHOT_SCHEMA_PATH = (
    REPOSITORY_DIR
    / "docs/FeedbackV2/phase0/contracts/project-budget-snapshot.schema.json"
)


def _root(boq_type: str, total: Decimal) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        parent_id=None,
        boq_type=boq_type,
        item_no="1",
        description="Golden root",
        total_material=total,
        total_labor=Decimal("0.00"),
        grand_total=total,
    )


def _current_projection(scenario: dict[str, object]) -> dict[str, object]:
    values = scenario["inputs"]
    customer = Decimal(values["customer_root_total"])
    subcontractor = Decimal(values["subcontractor_root_total"])
    contingency = Decimal(values["contingency_budget"])
    items = []
    if customer:
        items.append(_root("CUSTOMER", customer))
    if subcontractor:
        items.append(_root("SUBCONTRACTOR", subcontractor))
    totals = projected_boq_totals(items)

    project_list = (
        totals.customer_total + totals.subcontractor_total
        if values["project_list_has_grouped_boq_row"]
        else contingency
    )
    dashboard = totals.customer_total or totals.subcontractor_total or contingency
    chat = totals.subcontractor_total or totals.customer_total or contingency
    if totals.customer_total:
        frontend_total = totals.customer_total
        frontend_source = "Customer BOQ"
    elif totals.subcontractor_total:
        frontend_total = totals.subcontractor_total
        frontend_source = "Subcontractor BOQ"
    else:
        frontend_total = contingency
        frontend_source = "Project budget"

    def money(value: object) -> str:
        return f"{Decimal(value):.2f}"

    return {
        "project_list_total_budget": money(project_list),
        "project_detail_customer_total_budget": money(totals.customer_total),
        "project_detail_subcontractor_total_budget": money(
            totals.subcontractor_total
        ),
        "project_detail_total_variance": money(totals.margin),
        "project_detail_margin_percent": (
            money((totals.margin / totals.customer_total) * Decimal("100"))
            if totals.customer_total
            else None
        ),
        "fund_forecast_base": money(totals.margin),
        "dashboard_total_budget": money(dashboard),
        "chat_display_budget": money(chat),
        "mcp_current_boq_budget": {
            "amount": money(totals.customer_total),
            "currency": "THB",
        },
        "frontend_card_total_budget": money(frontend_total),
        "frontend_card_budget_source": frontend_source,
    }


def test_legacy_budget_golden_fixture_matches_current_projection_rules() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert fixture["contract_version"] == 1
    assert len(fixture["scenarios"]) >= 3
    for scenario in fixture["scenarios"]:
        assert _current_projection(scenario) == scenario["expected"]


def test_project_budget_snapshot_schema_locks_required_fields() -> None:
    schema = json.loads(SNAPSHOT_SCHEMA_PATH.read_text(encoding="utf-8"))
    required = set(schema["required"])
    assert required == set(schema["properties"])
    assert schema["additionalProperties"] is False
    assert set(schema["properties"]["source_kind"]["enum"]) == {"LEGACY", "V2"}
    assert "UNKNOWN_COST" in schema["properties"]["status"]["enum"]
    assert schema["$defs"]["nullableMoney"]["anyOf"][0]["pattern"].endswith(
        "[0-9]{2}$"
    )


def test_schema_preflight_accepts_only_safe_local_test_target_by_default() -> None:
    value = "postgresql+asyncpg://phase0:phase0@127.0.0.1:55432/example_test"
    normalized, masked = validate_target(value, allow_nonlocal_readonly=False)
    assert normalized.startswith("postgresql://")
    assert masked == "127.0.0.1:55432/example_test"
    assert "phase0" not in masked

    with pytest.raises(ValueError, match="does not end with _test"):
        validate_target(
            "postgresql+asyncpg://user:secret@127.0.0.1:5432/project001",
            allow_nonlocal_readonly=False,
        )
    with pytest.raises(ValueError, match="non-loopback"):
        validate_target(
            "postgresql+asyncpg://user:secret@db.example.com:5432/project001_test",
            allow_nonlocal_readonly=False,
        )


def test_phase1_registers_v2_tables_without_public_snapshot_route() -> None:
    import app.models  # noqa: F401
    from app.core.database import Base

    assert len(
        [name for name in Base.metadata.tables if name.startswith("boq_v2_")]
    ) == 10
    project_router = (BACKEND_DIR / "app/api/v1/projects.py").read_text(
        encoding="utf-8"
    )
    assert "ProjectBudgetSnapshot" not in project_router
