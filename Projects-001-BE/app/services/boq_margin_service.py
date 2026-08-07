"""Shared BOQ forecast totals used by comparison and margin allocation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Iterable


ZERO = Decimal("0")


@dataclass(frozen=True)
class ProjectedBOQTotals:
    customer_total: Decimal
    subcontractor_total: Decimal

    @property
    def margin(self) -> Decimal:
        return self.customer_total - self.subcontractor_total


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value or 0))


def _normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _is_total_like(item: Any) -> bool:
    text = f"{_normalize_text(item.item_no)} {_normalize_text(item.description)}".strip()
    return text.startswith("total") or " total " in f" {text} " or text.startswith("รวม")


def _own_amounts(item: Any) -> tuple[Decimal, Decimal, Decimal]:
    return (
        _decimal(item.total_material),
        _decimal(item.total_labor),
        _decimal(item.grand_total),
    )


def _has_amount(amounts: tuple[Decimal, Decimal, Decimal]) -> bool:
    return any(value != ZERO for value in amounts)


def _totals_for_type(items: list[Any]) -> Decimal:
    children_by_parent: dict[Any, list[Any]] = {}
    for item in items:
        children_by_parent.setdefault(item.parent_id, []).append(item)

    memo: dict[Any, tuple[Decimal, Decimal, Decimal]] = {}

    def display_amounts(item: Any) -> tuple[Decimal, Decimal, Decimal]:
        if item.id in memo:
            return memo[item.id]

        children = children_by_parent.get(item.id, [])
        child_amounts = [(child, display_amounts(child)) for child in children]
        total_children = [
            amounts
            for child, amounts in child_amounts
            if _is_total_like(child) and _has_amount(amounts)
        ]
        rollup_sources = total_children or [amounts for _, amounts in child_amounts]
        rollup = tuple(
            sum((amounts[index] for amounts in rollup_sources), ZERO)
            for index in range(3)
        )
        own = _own_amounts(item)
        displayed = own if _has_amount(own) else rollup
        memo[item.id] = displayed
        return displayed

    return sum(
        (display_amounts(item)[2] for item in children_by_parent.get(None, [])),
        ZERO,
    )


def projected_boq_totals(items: Iterable[Any]) -> ProjectedBOQTotals:
    """Match the BOQ Comparison root display-total rollup using Decimal values."""

    current_items = list(items)
    customer_items = [
        item for item in current_items if str(item.boq_type or "").upper() == "CUSTOMER"
    ]
    subcontractor_items = [
        item
        for item in current_items
        if str(item.boq_type or "").upper() == "SUBCONTRACTOR"
    ]
    return ProjectedBOQTotals(
        customer_total=_totals_for_type(customer_items),
        subcontractor_total=_totals_for_type(subcontractor_items),
    )
