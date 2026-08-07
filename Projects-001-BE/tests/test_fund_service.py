from __future__ import annotations

import unittest
import asyncio
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException

from app.api.deps.auth import AuthenticatedUser
from app.api.v1.funds import require_fund_owner

from app.services.fund_service import (
    _current_input_totals,
    _historical_input_totals,
    build_balance_version,
    calculate_available_values,
    is_first_day_of_month,
    money,
)


def input_request(
    *,
    status: str,
    entry_type: str,
    amount: str,
    approved_amount: str | None = None,
    request_date: date = date(2026, 8, 1),
    approved_at: datetime | None = None,
    paid_at: datetime | None = None,
):
    return SimpleNamespace(
        id=uuid4(),
        status=status,
        entry_type=entry_type,
        amount=Decimal(amount),
        approved_amount=(Decimal(approved_amount) if approved_amount is not None else None),
        request_date=request_date,
        approved_at=approved_at,
        paid_at=paid_at,
        updated_at=paid_at or approved_at,
    )


class FundFormulaTests(unittest.TestCase):
    def test_v1_formula_keeps_projected_margin_out_of_available(self):
        values = calculate_available_values(
            opening_balance="0.00",
            paid_income="900000.00",
            paid_expense="300000.00",
            approved_expense_commitment="150000.00",
            allocated_in="200000.00",
            allocated_out="250000.00",
            protected_reserve="50000.00",
        )

        self.assertEqual(values.raw_available, Decimal("350000.00"))
        self.assertEqual(values.available_to_allocate, Decimal("350000.00"))
        self.assertEqual(values.funding_deficit, Decimal("0.00"))

    def test_negative_raw_balance_becomes_deficit_and_zero_available(self):
        values = calculate_available_values(
            paid_income="10.00",
            paid_expense="12.00",
            approved_expense_commitment="3.00",
        )

        self.assertEqual(values.raw_available, Decimal("-5.00"))
        self.assertEqual(values.available_to_allocate, Decimal("0.00"))
        self.assertEqual(values.funding_deficit, Decimal("5.00"))

    def test_money_rounds_to_fixed_two_decimal_precision(self):
        self.assertEqual(money("0.005"), Decimal("0.01"))
        self.assertEqual(money("10.004"), Decimal("10.00"))

    def test_approved_amount_is_used_and_pending_is_not_a_commitment(self):
        requests = [
            input_request(
                status="APPROVED",
                entry_type="EXPENSE",
                amount="100.00",
                approved_amount="85.25",
                approved_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
            ),
            input_request(
                status="PENDING_ADMIN",
                entry_type="EXPENSE",
                amount="500.00",
            ),
        ]

        totals = _current_input_totals(
            requests,
            start_date=date(2026, 8, 1),
            today=date(2026, 8, 7),
        )

        self.assertEqual(totals["approved_expense_commitment"], Decimal("85.25"))

    def test_paid_and_approved_are_mutually_exclusive(self):
        request = input_request(
            status="PAID",
            entry_type="EXPENSE",
            amount="250.00",
            approved_amount="225.00",
            approved_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
            paid_at=datetime(2026, 8, 3, tzinfo=timezone.utc),
        )

        totals = _current_input_totals(
            [request],
            start_date=date(2026, 8, 1),
            today=date(2026, 8, 7),
        )

        self.assertEqual(totals["paid_expense"], Decimal("225.00"))
        self.assertEqual(totals["approved_expense_commitment"], Decimal("0.00"))

    def test_month_opening_reconstructs_pre_cutoff_commitment(self):
        request = input_request(
            status="PAID",
            entry_type="EXPENSE",
            amount="100.00",
            approved_at=datetime(2026, 7, 29, tzinfo=timezone.utc),
            paid_at=datetime(2026, 8, 3, tzinfo=timezone.utc),
        )

        totals = _historical_input_totals(
            [request],
            start_date=date(2026, 7, 1),
            cutoff=date(2026, 8, 1),
        )

        self.assertEqual(totals["approved_expense_commitment"], Decimal("100.00"))
        self.assertEqual(totals["paid_expense"], Decimal("0.00"))

    def test_balance_version_changes_for_offsetting_source_activity(self):
        first = build_balance_version({"raw": "100.00", "activity": ["income-1"]})
        second = build_balance_version(
            {"raw": "100.00", "activity": ["income-1", "income-2", "expense-1"]}
        )

        self.assertNotEqual(first, second)

    def test_balance_start_date_must_be_first_day(self):
        self.assertTrue(is_first_day_of_month(date(2026, 8, 1)))
        self.assertFalse(is_first_day_of_month(date(2026, 8, 2)))

    def test_admin_fund_mutation_is_structured_forbidden(self):
        admin = AuthenticatedUser(subject="admin-1", role="admin", roles=("admin",))

        with self.assertRaises(HTTPException) as context:
            asyncio.run(require_fund_owner(admin))

        self.assertEqual(context.exception.status_code, 403)
        self.assertEqual(context.exception.detail["code"], "FORBIDDEN")


if __name__ == "__main__":
    unittest.main()
