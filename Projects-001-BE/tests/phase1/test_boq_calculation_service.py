from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from app.services.boq_calculation_service import (
    BOQCalculationError,
    CostComponentInput,
    SellItemInput,
    allocate_payment_percentages,
    apply_adjustment,
    calculate_boq,
    effective_component_quantity,
    extended_amount,
    margin_percent,
    money,
    price_from_margin,
    price_from_markup,
    signed_change_order_amount,
    vat_amount,
)


def _component(state: str, rate: str | None, *, reason: str | None = None):
    return CostComponentInput(
        component_id=uuid4(),
        component_type="MATERIAL",
        state=state,
        quantity=Decimal("1.0000"),
        unit_rate=Decimal(rate) if rate is not None else None,
        explicit_zero_reason=reason,
    )


def test_half_up_calculation_and_unknown_completeness() -> None:
    missing = _component("UNKNOWN", None)
    result = calculate_boq(
        [
            SellItemInput(
                item_id=uuid4(),
                quantity=Decimal("1.0000"),
                material_unit_rate=Decimal("0.0050"),
                labor_unit_rate=Decimal("0.0000"),
            ),
            SellItemInput(
                item_id=uuid4(),
                quantity=Decimal("999.0000"),
                material_unit_rate=Decimal("999.0000"),
                labor_unit_rate=Decimal("999.0000"),
                included=False,
            ),
        ],
        [
            missing,
            _component("PRICED", "0.0000", reason="included at no charge"),
            _component("NOT_APPLICABLE", None),
        ],
    )

    assert extended_amount("1.0000", "0.0050") == Decimal("0.01")
    assert result.net_sell_ex_vat == Decimal("0.01")
    assert result.known_estimated_cost == Decimal("0.00")
    assert result.required_count == 2
    assert result.priced_count == 1
    assert result.missing_component_ids == (missing.component_id,)
    assert result.forecast_cost is None
    assert result.forecast_margin is None
    assert result.completeness_state == "INCOMPLETE"


def test_explicit_zero_and_state_contracts() -> None:
    with pytest.raises(BOQCalculationError, match="requires a reason"):
        calculate_boq([], [_component("PRICED", "0.0000")])
    with pytest.raises(BOQCalculationError, match="cannot have a unit rate"):
        calculate_boq([], [_component("UNKNOWN", "1.0000")])
    with pytest.raises(BOQCalculationError, match="cannot have a unit rate"):
        calculate_boq([], [_component("NOT_APPLICABLE", "1.0000")])


def test_complete_free_customer_line_still_requires_internal_cost() -> None:
    result = calculate_boq(
        [
            SellItemInput(
                item_id=uuid4(),
                quantity=Decimal("2.0000"),
                material_unit_rate=Decimal("0.0000"),
                labor_unit_rate=Decimal("0.0000"),
            )
        ],
        [_component("PRICED", "5.0000")],
    )
    assert result.net_sell_ex_vat == Decimal("0.00")
    assert result.forecast_cost == Decimal("5.00")
    assert result.forecast_margin == Decimal("-5.00")


def test_pricing_adjustment_vat_margin_and_payment_rules() -> None:
    assert price_from_markup("100.00", "20.0000") == Decimal("120.00")
    assert price_from_margin("100.00", "20.0000") == Decimal("125.00")
    assert apply_adjustment(
        "100.00", adjustment_type="PERCENT", direction="DISCOUNT", value="7.5000"
    ) == Decimal("92.50")
    assert apply_adjustment(
        "100.00", adjustment_type="FIXED", direction="SURCHARGE", value="7.505"
    ) == Decimal("107.51")
    assert vat_amount("100.00", "7.0000") == Decimal("7.00")
    assert margin_percent("125.00", "100.00") == Decimal("20.0000")
    assert margin_percent("0.00", "100.00") is None
    assert signed_change_order_amount("ADD", "10") == Decimal("10.00")
    assert signed_change_order_amount("DEDUCT", "10") == Decimal("-10.00")
    assert allocate_payment_percentages("7752.15", ["30", "30", "30", "10"]) == (
        Decimal("2325.65"),
        Decimal("2325.65"),
        Decimal("2325.65"),
        Decimal("775.20"),
    )


def test_inherited_and_overridden_quantity_semantics() -> None:
    assert effective_component_quantity(
        "3.5000", quantity_basis="INHERITED"
    ) == Decimal("3.5000")
    assert effective_component_quantity(
        "9.0000", quantity_basis="OVERRIDDEN", overridden_quantity="2.0000"
    ) == Decimal("2.0000")
    with pytest.raises(BOQCalculationError, match="requires an explicit"):
        effective_component_quantity("9.0000", quantity_basis="OVERRIDDEN")


def test_numeric_overflow_is_rejected_before_persistence() -> None:
    assert money("999999999999999999.99") == Decimal("999999999999999999.99")
    with pytest.raises(BOQCalculationError, match=r"NUMERIC\(20,2\)"):
        money("9999999999999999999.99")
    with pytest.raises(BOQCalculationError, match=r"NUMERIC\(20,4\)"):
        extended_amount("10000000000000000.0000", "1.0000")
