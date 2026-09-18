from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import HTTPException, status

from app.api.v1.projects import (
    get_sync_boq_batch_job_retired,
    preview_boq_tabs_retired,
    sync_boq_batch_retired,
    sync_boq_retired,
)
from app.schemas.project_budget_schema import (
    CostCompleteness,
    ProjectBudgetReadContext,
    ProjectBudgetSnapshot,
)
from app.services.project_budget_service import active_budget_amount
from app.services.mcp_read_service import _v2_line_id, _v2_version_id


def _context(*, source_kind: str, status: str) -> ProjectBudgetReadContext:
    is_v2 = source_kind == "V2"
    snapshot = ProjectBudgetSnapshot(
        source_kind=source_kind,
        status=status,
        project_id=uuid4(),
        baseline_id=uuid4() if is_v2 else None,
        baseline_version=3 if is_v2 else None,
        main_revision_id=uuid4() if is_v2 else None,
        accepted_change_order_ids=[uuid4()] if is_v2 else [],
        cost_plan_version=7 if is_v2 else None,
        calculation_version="boq-v2-calc-v1" if is_v2 else "legacy-scd2-v1",
        activated_at="2026-09-18T00:00:00Z" if is_v2 else None,
        net_sell_ex_vat="1250000.00" if is_v2 else "100.00",
        original_estimated_cost="900000.00" if is_v2 and status == "READY" else None,
        agreed_cost=None,
        forecast_cost="950000.00" if is_v2 and status == "READY" else None,
        forecast_margin="300000.00" if is_v2 and status == "READY" else None,
        cost_completeness=CostCompleteness(
            state=(
                "COMPLETE"
                if is_v2 and status == "READY"
                else "INCOMPLETE"
                if is_v2
                else "LEGACY_UNVERIFIED"
            ),
            required_count=2 if is_v2 else 0,
            priced_count=2 if is_v2 and status == "READY" else 1 if is_v2 else 0,
            missing_component_ids=[uuid4()] if is_v2 and status != "READY" else [],
        ),
        forecast_basis=(
            "ESTIMATED"
            if is_v2 and status == "READY"
            else "NONE"
            if is_v2
            else "LEGACY_SYNC"
        ),
        as_of="2026-09-18T00:00:00Z",
    )
    return ProjectBudgetReadContext(
        snapshot=snapshot,
        legacy_project_list_budget="111.00",
        legacy_dashboard_budget="222.00",
        legacy_fund_forecast_base="333.00",
        legacy_chat_budget="444.00",
        legacy_mcp_customer_budget="555.00",
    )


def test_v2_current_budget_consumers_share_sell_snapshot_and_funds_margin() -> None:
    context = _context(source_kind="V2", status="READY")
    for consumer in ("PROJECT_LIST", "DASHBOARD", "CHAT", "MCP"):
        assert active_budget_amount(context, consumer=consumer) == "1250000.00"
    assert active_budget_amount(context, consumer="FUNDS") == "300000.00"


def test_v2_unknown_cost_keeps_sell_budget_but_withholds_funds_margin() -> None:
    context = _context(source_kind="V2", status="UNKNOWN_COST")
    assert active_budget_amount(context, consumer="PROJECT_LIST") == "1250000.00"
    assert active_budget_amount(context, consumer="FUNDS") is None


def test_legacy_consumer_specific_compatibility_remains_locked() -> None:
    context = _context(source_kind="LEGACY", status="READY")
    assert active_budget_amount(context, consumer="PROJECT_LIST") == "111.00"
    assert active_budget_amount(context, consumer="DASHBOARD") == "222.00"
    assert active_budget_amount(context, consumer="FUNDS") == "333.00"
    assert active_budget_amount(context, consumer="CHAT") == "444.00"
    assert active_budget_amount(context, consumer="MCP") == "555.00"


@pytest.mark.parametrize(
    ("endpoint", "args"),
    [
        (sync_boq_retired, ()),
        (preview_boq_tabs_retired, ()),
        (sync_boq_batch_retired, ()),
        (get_sync_boq_batch_job_retired, ("retired-job",)),
    ],
)
def test_legacy_sync_routes_return_actionable_410(endpoint, args) -> None:
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(endpoint(*args, _user=object()))
    assert exc_info.value.status_code == status.HTTP_410_GONE
    assert exc_info.value.detail["code"] == "BOQ_SYNC_RETIRED"
    assert "boq-workspace" in exc_info.value.detail["replacement"]


def test_sync_implementations_are_removed_from_runtime_package() -> None:
    services = Path(__file__).resolve().parents[2] / "app" / "services"
    assert not (services / "boq_sync_service.py").exists()
    assert not (services / "boq_sync_job_service.py").exists()


def test_v2_mcp_references_are_stable_and_source_scoped() -> None:
    baseline_id = uuid4()
    document_id = uuid4()
    logical_id = uuid4()

    assert _v2_version_id(baseline_id) == f"boqv2_{baseline_id.hex}"
    assert _v2_line_id(document_id, logical_id) == (
        f"boqlv2_{document_id.hex}_{logical_id.hex}"
    )
