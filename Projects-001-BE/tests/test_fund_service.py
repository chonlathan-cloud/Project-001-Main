from __future__ import annotations

import asyncio
import inspect
import unittest
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException

from app.api.deps.auth import AuthenticatedUser
from app.api.v1.funds import require_fund_owner
from app.services.boq_margin_service import projected_boq_totals
from app.services.fund_service import (
    FundDomainError,
    _ledger_totals,
    _source_fingerprint,
    _validate_active_context,
    build_balance_version,
    calculate_available_values,
    is_first_day_of_month,
    money,
)


def bucket(*, reserve: str = "0.00"):
    return SimpleNamespace(
        id=uuid4(),
        status="ACTIVE",
        balance_start_date=date(2026, 8, 1),
        protected_reserve=Decimal(reserve),
    )


def ledger_entry(
    *,
    entry_type: str,
    direction: str,
    amount: str,
    effective_date: date = date(2026, 8, 1),
):
    return SimpleNamespace(
        id=uuid4(),
        entry_type=entry_type,
        direction=direction,
        amount=Decimal(amount),
        effective_date=effective_date,
        created_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )


def boq_item(
    *,
    boq_type: str,
    grand_total: str = "0.00",
    total_material: str = "0.00",
    total_labor: str = "0.00",
    parent_id=None,
    item_no: str = "1",
    description: str = "Work",
):
    return SimpleNamespace(
        id=uuid4(),
        parent_id=parent_id,
        boq_type=boq_type,
        grand_total=Decimal(grand_total),
        total_material=Decimal(total_material),
        total_labor=Decimal(total_labor),
        item_no=item_no,
        description=description,
    )


class FundFormulaTests(unittest.TestCase):
    def test_forecast_margin_formula_uses_only_forecast_sources(self):
        values = calculate_available_values(
            forecast_base="1000000.00",
            forecast_allocated_in="200000.00",
            forecast_allocated_out="250000.00",
            forecast_reserve="50000.00",
        )

        self.assertEqual(values.raw_forecast_available, Decimal("900000.00"))
        self.assertEqual(values.available_margin_to_allocate, Decimal("900000.00"))
        self.assertEqual(values.forecast_deficit, Decimal("0.00"))

    def test_negative_raw_forecast_becomes_deficit_and_zero_available(self):
        values = calculate_available_values(
            forecast_base="100.00",
            forecast_allocated_out="125.00",
        )

        self.assertEqual(values.raw_forecast_available, Decimal("-25.00"))
        self.assertEqual(values.available_margin_to_allocate, Decimal("0.00"))
        self.assertEqual(values.forecast_deficit, Decimal("25.00"))

    def test_boq_margin_decrease_keeps_allocations_and_exposes_deficit(self):
        before = calculate_available_values(
            forecast_base="100.00",
            forecast_allocated_out="80.00",
        )
        after = calculate_available_values(
            forecast_base="50.00",
            forecast_allocated_out="80.00",
        )

        self.assertEqual(before.available_margin_to_allocate, Decimal("20.00"))
        self.assertEqual(after.raw_forecast_available, Decimal("-30.00"))
        self.assertEqual(after.available_margin_to_allocate, Decimal("0.00"))
        self.assertEqual(after.forecast_deficit, Decimal("30.00"))

    def test_actual_cashflow_statuses_cannot_enter_forecast_formula(self):
        parameters = inspect.signature(calculate_available_values).parameters

        self.assertNotIn("paid_income", parameters)
        self.assertNotIn("paid_expense", parameters)
        self.assertNotIn("approved_expense_commitment", parameters)
        with self.assertRaises(TypeError):
            calculate_available_values(forecast_base="100.00", paid_income="999.00")

    def test_allocated_in_can_be_allocated_onward(self):
        before = calculate_available_values(
            forecast_base="0.00",
            forecast_allocated_in="300.00",
        )
        after = calculate_available_values(
            forecast_base="0.00",
            forecast_allocated_in="300.00",
            forecast_allocated_out="125.00",
        )

        self.assertEqual(before.available_margin_to_allocate, Decimal("300.00"))
        self.assertEqual(after.available_margin_to_allocate, Decimal("175.00"))

    def test_money_rounds_to_fixed_two_decimal_precision(self):
        self.assertEqual(money("0.005"), Decimal("0.01"))
        self.assertEqual(money("10.004"), Decimal("10.00"))

    def test_ledger_totals_keep_opening_and_allocations_explicit(self):
        entries = [
            ledger_entry(entry_type="OPENING_BALANCE", direction="CREDIT", amount="500.00"),
            ledger_entry(entry_type="ALLOCATION", direction="CREDIT", amount="100.00"),
            ledger_entry(entry_type="ALLOCATION", direction="DEBIT", amount="75.00"),
        ]

        totals = _ledger_totals(entries, start_date=date(2026, 8, 1))

        self.assertEqual(totals["opening_forecast_balance"], Decimal("500.00"))
        self.assertEqual(totals["forecast_allocated_in"], Decimal("100.00"))
        self.assertEqual(totals["forecast_allocated_out"], Decimal("75.00"))

    def test_monthly_forecast_opening_is_previous_forecast_closing(self):
        entries = [
            ledger_entry(
                entry_type="OPENING_BALANCE",
                direction="CREDIT",
                amount="500.00",
                effective_date=date(2026, 7, 1),
            ),
            ledger_entry(
                entry_type="ALLOCATION",
                direction="DEBIT",
                amount="100.00",
                effective_date=date(2026, 7, 15),
            ),
            ledger_entry(
                entry_type="ALLOCATION",
                direction="CREDIT",
                amount="50.00",
                effective_date=date(2026, 8, 2),
            ),
        ]
        previous_month = _ledger_totals(
            entries,
            start_date=date(2026, 7, 1),
            cutoff=date(2026, 8, 1),
        )
        monthly_opening = calculate_available_values(
            forecast_base=previous_month["opening_forecast_balance"],
            forecast_allocated_in=previous_month["forecast_allocated_in"],
            forecast_allocated_out=previous_month["forecast_allocated_out"],
        )

        self.assertEqual(monthly_opening.raw_forecast_available, Decimal("400.00"))

    def test_balance_version_changes_for_boq_margin_reserve_and_ledger(self):
        base_bucket = bucket()
        values = calculate_available_values(forecast_base="100.00")
        baseline = build_balance_version(
            _source_fingerprint(
                base_bucket,
                [],
                values,
                forecast_base_type="PROJECTED_BOQ_MARGIN",
                forecast_base=Decimal("100.00"),
            )
        )
        changed_boq = build_balance_version(
            _source_fingerprint(
                base_bucket,
                [],
                calculate_available_values(forecast_base="90.00"),
                forecast_base_type="PROJECTED_BOQ_MARGIN",
                forecast_base=Decimal("90.00"),
            )
        )
        reserve_bucket = SimpleNamespace(**{**base_bucket.__dict__, "protected_reserve": Decimal("5.00")})
        changed_reserve = build_balance_version(
            _source_fingerprint(
                reserve_bucket,
                [],
                calculate_available_values(forecast_base="100.00", forecast_reserve="5.00"),
                forecast_base_type="PROJECTED_BOQ_MARGIN",
                forecast_base=Decimal("100.00"),
            )
        )
        entry = ledger_entry(entry_type="ALLOCATION", direction="DEBIT", amount="10.00")
        changed_ledger = build_balance_version(
            _source_fingerprint(
                base_bucket,
                [entry],
                calculate_available_values(forecast_base="100.00", forecast_allocated_out="10.00"),
                forecast_base_type="PROJECTED_BOQ_MARGIN",
                forecast_base=Decimal("100.00"),
            )
        )

        self.assertNotEqual(baseline, changed_boq)
        self.assertNotEqual(baseline, changed_reserve)
        self.assertNotEqual(baseline, changed_ledger)

    def test_opening_forecast_balance_changes_balance_version(self):
        operations_bucket = bucket()
        opening = ledger_entry(
            entry_type="OPENING_BALANCE",
            direction="CREDIT",
            amount="500.00",
        )
        without_opening = build_balance_version(
            _source_fingerprint(
                operations_bucket,
                [],
                calculate_available_values(),
                forecast_base_type="OPENING_FORECAST_BALANCE",
                forecast_base=Decimal("0.00"),
            )
        )
        with_opening = build_balance_version(
            _source_fingerprint(
                operations_bucket,
                [opening],
                calculate_available_values(forecast_base="500.00"),
                forecast_base_type="OPENING_FORECAST_BALANCE",
                forecast_base=Decimal("500.00"),
            )
        )

        self.assertNotEqual(without_opening, with_opening)

    def test_balance_fingerprint_does_not_lazy_load_server_updated_timestamp(self):
        class ExpiredTimestampBucket:
            id = uuid4()
            status = "ACTIVE"
            balance_start_date = date(2026, 8, 1)
            protected_reserve = Decimal("0.00")

            @property
            def updated_at(self):
                raise AssertionError("updated_at must not be lazy-loaded")

        values = calculate_available_values(forecast_base="100.00")
        fingerprint = _source_fingerprint(
            ExpiredTimestampBucket(),
            [],
            values,
            forecast_base_type="OPENING_FORECAST_BALANCE",
            forecast_base=Decimal("100.00"),
        )

        self.assertEqual(fingerprint["values"][0], "100.00")

    def test_balance_start_date_must_be_first_day(self):
        self.assertTrue(is_first_day_of_month(date(2026, 8, 1)))
        self.assertFalse(is_first_day_of_month(date(2026, 8, 2)))


class BOQMarginSourceTests(unittest.TestCase):
    def test_projected_margin_matches_customer_less_subcontractor(self):
        customer = boq_item(boq_type="CUSTOMER", grand_total="1000.00")
        subcontractor = boq_item(boq_type="SUBCONTRACTOR", grand_total="625.50")

        totals = projected_boq_totals([customer, subcontractor])

        self.assertEqual(totals.customer_total, Decimal("1000.00"))
        self.assertEqual(totals.subcontractor_total, Decimal("625.50"))
        self.assertEqual(totals.margin, Decimal("374.50"))

    def test_projected_margin_uses_boq_comparison_display_rollup(self):
        root = boq_item(boq_type="CUSTOMER", description="Section")
        detail = boq_item(
            boq_type="CUSTOMER",
            grand_total="100.00",
            parent_id=root.id,
            description="Detail",
        )
        total = boq_item(
            boq_type="CUSTOMER",
            grand_total="100.00",
            parent_id=root.id,
            item_no="Total",
            description="Total section",
        )

        totals = projected_boq_totals([root, detail, total])

        self.assertEqual(totals.customer_total, Decimal("100.00"))


class FundAuthorizationTests(unittest.TestCase):
    def test_setup_operations_can_receive_but_not_allocate_out(self):
        operations_bucket = SimpleNamespace(bucket_type="OPERATIONS", status="SETUP")
        operations_project = SimpleNamespace(id=uuid4(), status="ACTIVE")

        _validate_active_context((operations_bucket, operations_project), target=True)
        with self.assertRaises(FundDomainError) as context:
            _validate_active_context((operations_bucket, operations_project), target=False)

        self.assertEqual(context.exception.code, "SOURCE_BUCKET_INACTIVE")

    def test_admin_fund_mutation_is_structured_forbidden(self):
        admin = AuthenticatedUser(subject="admin-1", role="admin", roles=("admin",))

        with self.assertRaises(HTTPException) as context:
            asyncio.run(require_fund_owner(admin))

        self.assertEqual(context.exception.status_code, 403)
        self.assertEqual(context.exception.detail["code"], "FORBIDDEN")


if __name__ == "__main__":
    unittest.main()
