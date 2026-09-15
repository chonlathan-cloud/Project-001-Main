from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.project_budget_schema import (
    CostCompleteness,
    ProjectBudgetReadContext,
    ProjectBudgetSnapshot,
)
from app.services.fund_service import FundDomainError, _assert_outward_budget_ready
from app.services.project_budget_service import (
    budget_source_fingerprint,
    legacy_budget_facts_from_items,
)


def _item(*, boq_type: str, total: str, parent_id=None):
    return SimpleNamespace(
        id=uuid4(),
        parent_id=parent_id,
        boq_type=boq_type,
        item_no="1",
        description="Budget row",
        grand_total=Decimal(total),
        total_material=Decimal(total),
        total_labor=Decimal("0.00"),
    )


def _snapshot(*, source="V2", status="UNKNOWN_COST", baseline_version=1):
    is_legacy = source == "LEGACY"
    return ProjectBudgetSnapshot(
        source_kind=source,
        status=status,
        project_id=uuid4(),
        baseline_id=uuid4() if source == "V2" else None,
        baseline_version=baseline_version if source == "V2" else None,
        main_revision_id=uuid4() if source == "V2" else None,
        accepted_change_order_ids=[],
        cost_plan_version=1 if source == "V2" else None,
        calculation_version="boq-v2-calc-v1" if source == "V2" else "legacy-scd2-v1",
        activated_at="2026-09-15T00:00:00Z" if source == "V2" else None,
        net_sell_ex_vat="100.00",
        forecast_cost=None if status == "UNKNOWN_COST" or is_legacy else "60.00",
        forecast_margin=None if status == "UNKNOWN_COST" or is_legacy else "40.00",
        cost_completeness=CostCompleteness(
            state=(
                "LEGACY_UNVERIFIED"
                if is_legacy
                else "INCOMPLETE"
                if status == "UNKNOWN_COST"
                else "COMPLETE"
            ),
            required_count=0 if is_legacy else 2,
            priced_count=0 if is_legacy else 1 if status == "UNKNOWN_COST" else 2,
            missing_component_ids=(
                [uuid4()] if status == "UNKNOWN_COST" and not is_legacy else []
            ),
        ),
        forecast_basis=(
            "LEGACY_SYNC"
            if is_legacy
            else "NONE"
            if status == "UNKNOWN_COST"
            else "ESTIMATED"
        ),
        as_of="2026-09-15T00:00:00Z",
    )


def _context(snapshot: ProjectBudgetSnapshot) -> ProjectBudgetReadContext:
    return ProjectBudgetReadContext(
        snapshot=snapshot,
        legacy_project_list_budget="100.00",
        legacy_dashboard_budget="100.00",
        legacy_fund_forecast_base="40.00",
        legacy_chat_budget="60.00",
        legacy_mcp_customer_budget="100.00",
    )


def test_legacy_consumer_projections_remain_intentionally_distinct() -> None:
    customer_root = _item(boq_type="CUSTOMER", total="100.00")
    customer_leaf = _item(
        boq_type="CUSTOMER", total="80.00", parent_id=customer_root.id
    )
    subcontractor_root = _item(boq_type="SUBCONTRACTOR", total="60.00")
    subcontractor_leaf = _item(
        boq_type="SUBCONTRACTOR", total="50.00", parent_id=subcontractor_root.id
    )
    facts = legacy_budget_facts_from_items(
        project_id=uuid4(),
        contingency_budget="25.00",
        items=[customer_root, customer_leaf, subcontractor_root, subcontractor_leaf],
    )
    assert facts.project_list_budget == Decimal("160.00")
    assert facts.dashboard_budget == Decimal("100.00")
    assert facts.chat_budget == Decimal("50.00")
    assert facts.mcp_customer_budget == Decimal("100.00")
    assert facts.fund_forecast_base == Decimal("40.00")


def test_legacy_type_normalization_remains_consumer_specific() -> None:
    nonstandard = _item(boq_type=" SUBCONTRACTOR ", total="25.00")
    facts = legacy_budget_facts_from_items(
        project_id=uuid4(), contingency_budget="10.00", items=[nonstandard]
    )
    assert facts.project_list_budget == Decimal("25.00")
    assert facts.dashboard_budget == Decimal("25.00")
    assert facts.chat_budget == Decimal("25.00")
    assert facts.mcp_customer_budget == Decimal("0.00")


def test_snapshot_money_is_fixed_scale_and_unknown_margin_is_null() -> None:
    with pytest.raises(ValidationError):
        ProjectBudgetSnapshot.model_validate(
            {
                **_snapshot(status="READY").model_dump(mode="json"),
                "net_sell_ex_vat": "100",
            }
        )
    with pytest.raises(ValidationError, match="unknown cost"):
        ProjectBudgetSnapshot.model_validate(
            {**_snapshot().model_dump(mode="json"), "forecast_margin": "1.00"}
        )


def test_source_fingerprint_changes_when_lineage_changes_at_equal_amount() -> None:
    first = _snapshot(status="READY", baseline_version=1)
    second = first.model_copy(update={"baseline_version": 2})
    assert budget_source_fingerprint(first) != budget_source_fingerprint(second)


def test_unknown_v2_cost_blocks_only_new_outward_budget_check() -> None:
    with pytest.raises(FundDomainError) as exc_info:
        _assert_outward_budget_ready(_context(_snapshot()))
    assert exc_info.value.code == "BOQ_BUDGET_NOT_READY"
    _assert_outward_budget_ready(_context(_snapshot(status="READY")))
    legacy = _snapshot(source="LEGACY", status="READY", baseline_version=None)
    _assert_outward_budget_ready(_context(legacy))
