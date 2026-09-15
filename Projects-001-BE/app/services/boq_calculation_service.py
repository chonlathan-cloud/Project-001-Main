"""Pure Decimal calculation and completeness rules for BOQ V2."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Iterable, Literal
from uuid import UUID


MONEY_QUANTUM = Decimal("0.01")
RATE_QUANTUM = Decimal("0.0001")
ZERO_MONEY = Decimal("0.00")
CALCULATION_VERSION = "boq-v2-calc-v1"


class BOQCalculationError(ValueError):
    pass


@dataclass(frozen=True)
class CostComponentInput:
    component_id: UUID
    component_type: Literal["MATERIAL", "LABOR"]
    state: Literal["UNKNOWN", "PRICED", "NOT_APPLICABLE"]
    quantity: Decimal
    unit_rate: Decimal | None = None
    explicit_zero_reason: str | None = None


@dataclass(frozen=True)
class SellItemInput:
    item_id: UUID
    quantity: Decimal
    material_unit_rate: Decimal
    labor_unit_rate: Decimal
    included: bool = True


@dataclass(frozen=True)
class ComponentResult:
    component_id: UUID
    total: Decimal | None
    required: bool
    priced: bool


@dataclass(frozen=True)
class BOQCalculationResult:
    calculation_version: str
    net_sell_ex_vat: Decimal
    known_estimated_cost: Decimal
    forecast_cost: Decimal | None
    forecast_margin: Decimal | None
    required_count: int
    priced_count: int
    missing_component_ids: tuple[UUID, ...]
    completeness_state: Literal["COMPLETE", "INCOMPLETE"]


def _decimal(value: object, *, label: str) -> Decimal:
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise BOQCalculationError(f"{label} must be a decimal") from exc
    if not result.is_finite():
        raise BOQCalculationError(f"{label} must be finite")
    return result


def validate_quantity_or_rate(value: object, *, label: str) -> Decimal:
    result = _decimal(value, label=label)
    if result < 0:
        raise BOQCalculationError(f"{label} cannot be negative")
    normalized = result.normalize()
    scale = max(0, -normalized.as_tuple().exponent)
    integer_digits = max(1, normalized.copy_abs().adjusted() + 1)
    if scale > 4 or integer_digits > 16:
        raise BOQCalculationError(f"{label} exceeds NUMERIC(20,4)")
    return result.quantize(RATE_QUANTUM)


def money(value: object) -> Decimal:
    result = _decimal(value, label="money")
    try:
        quantized = result.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
    except InvalidOperation as exc:
        raise BOQCalculationError("money exceeds NUMERIC(20,2)") from exc
    integer_digits = max(1, quantized.copy_abs().adjusted() + 1)
    if integer_digits > 18:
        raise BOQCalculationError("money exceeds NUMERIC(20,2)")
    return quantized


def extended_amount(quantity: object, unit_rate: object) -> Decimal:
    quantity_value = validate_quantity_or_rate(quantity, label="quantity")
    rate_value = validate_quantity_or_rate(unit_rate, label="unit_rate")
    return money(quantity_value * rate_value)


def calculate_cost_component(component: CostComponentInput) -> ComponentResult:
    quantity = validate_quantity_or_rate(component.quantity, label="component quantity")
    if component.state == "NOT_APPLICABLE":
        if component.unit_rate is not None:
            raise BOQCalculationError("NOT_APPLICABLE cost cannot have a unit rate")
        return ComponentResult(component.component_id, ZERO_MONEY, False, False)
    if component.state == "UNKNOWN":
        if component.unit_rate is not None:
            raise BOQCalculationError("UNKNOWN cost cannot have a unit rate")
        return ComponentResult(component.component_id, None, True, False)
    if component.state != "PRICED" or component.unit_rate is None:
        raise BOQCalculationError("PRICED cost requires a unit rate")
    unit_rate = validate_quantity_or_rate(
        component.unit_rate, label="component unit rate"
    )
    if unit_rate == 0 and not str(component.explicit_zero_reason or "").strip():
        raise BOQCalculationError("explicit zero cost requires a reason")
    return ComponentResult(
        component.component_id,
        extended_amount(quantity, unit_rate),
        True,
        True,
    )


def calculate_boq(
    sell_items: Iterable[SellItemInput],
    cost_components: Iterable[CostComponentInput],
) -> BOQCalculationResult:
    sell_total = ZERO_MONEY
    for item in sell_items:
        if not item.included:
            continue
        quantity = validate_quantity_or_rate(item.quantity, label="sell quantity")
        material = extended_amount(quantity, item.material_unit_rate)
        labor = extended_amount(quantity, item.labor_unit_rate)
        sell_total = money(sell_total + material + labor)

    component_results = [calculate_cost_component(item) for item in cost_components]
    required = [item for item in component_results if item.required]
    priced = [item for item in required if item.priced]
    missing = tuple(
        sorted((item.component_id for item in required if not item.priced), key=str)
    )
    known_cost = money(
        sum((item.total or ZERO_MONEY for item in component_results), ZERO_MONEY)
    )
    complete = len(required) == len(priced)
    forecast_cost = known_cost if complete else None
    forecast_margin = money(sell_total - known_cost) if complete else None
    return BOQCalculationResult(
        calculation_version=CALCULATION_VERSION,
        net_sell_ex_vat=sell_total,
        known_estimated_cost=known_cost,
        forecast_cost=forecast_cost,
        forecast_margin=forecast_margin,
        required_count=len(required),
        priced_count=len(priced),
        missing_component_ids=missing,
        completeness_state="COMPLETE" if complete else "INCOMPLETE",
    )


def price_from_markup(cost: object, percent: object) -> Decimal:
    cost_value = money(cost)
    percent_value = validate_quantity_or_rate(percent, label="markup percent")
    return money(cost_value * (Decimal("1") + percent_value / Decimal("100")))


def price_from_margin(cost: object, percent: object) -> Decimal:
    cost_value = money(cost)
    percent_value = validate_quantity_or_rate(percent, label="margin percent")
    if percent_value >= 100:
        raise BOQCalculationError("margin percent must be below 100")
    return money(cost_value / (Decimal("1") - percent_value / Decimal("100")))


def apply_adjustment(
    base: object,
    *,
    adjustment_type: Literal["FIXED", "PERCENT"],
    direction: Literal["DISCOUNT", "SURCHARGE"],
    value: object,
) -> Decimal:
    base_value = money(base)
    adjustment = (
        money(value)
        if adjustment_type == "FIXED"
        else money(base_value * validate_quantity_or_rate(value, label="percent") / 100)
    )
    result = (
        base_value - adjustment if direction == "DISCOUNT" else base_value + adjustment
    )
    if result < 0:
        raise BOQCalculationError("adjustment cannot make the total negative")
    return money(result)


def effective_component_quantity(
    scope_quantity: object,
    *,
    quantity_basis: Literal["INHERITED", "OVERRIDDEN"],
    overridden_quantity: object | None = None,
) -> Decimal:
    if quantity_basis == "INHERITED":
        if overridden_quantity is not None:
            raise BOQCalculationError(
                "INHERITED component cannot carry an overridden quantity"
            )
        return validate_quantity_or_rate(scope_quantity, label="scope quantity")
    if quantity_basis != "OVERRIDDEN" or overridden_quantity is None:
        raise BOQCalculationError(
            "OVERRIDDEN component requires an explicit component quantity"
        )
    return validate_quantity_or_rate(
        overridden_quantity, label="overridden component quantity"
    )


def margin_percent(net_sell_ex_vat: object, forecast_cost: object) -> Decimal | None:
    sell = money(net_sell_ex_vat)
    if sell == ZERO_MONEY:
        return None
    cost = money(forecast_cost)
    return ((sell - cost) / sell * Decimal("100")).quantize(
        RATE_QUANTUM, rounding=ROUND_HALF_UP
    )


def vat_amount(net_ex_vat: object, percent: object) -> Decimal:
    return money(
        money(net_ex_vat)
        * validate_quantity_or_rate(percent, label="VAT percent")
        / Decimal("100")
    )


def signed_change_order_amount(
    direction: Literal["ADD", "DEDUCT"], magnitude: object
) -> Decimal:
    value = money(magnitude)
    if value < ZERO_MONEY:
        raise BOQCalculationError("change-order magnitude cannot be negative")
    if direction == "ADD":
        return value
    if direction == "DEDUCT":
        return -value
    raise BOQCalculationError("change-order direction must be ADD or DEDUCT")


def allocate_payment_percentages(
    total: object,
    percentages: Iterable[object],
) -> tuple[Decimal, ...]:
    total_value = money(total)
    percentage_values = [
        validate_quantity_or_rate(item, label="payment percentage")
        for item in percentages
    ]
    if not percentage_values or sum(percentage_values) != Decimal("100.0000"):
        raise BOQCalculationError("payment percentages must total 100")
    allocated: list[Decimal] = []
    for percentage in percentage_values[:-1]:
        allocated.append(money(total_value * percentage / Decimal("100")))
    allocated.append(money(total_value - sum(allocated, ZERO_MONEY)))
    return tuple(allocated)
