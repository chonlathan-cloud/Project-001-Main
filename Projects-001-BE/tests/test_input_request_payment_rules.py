from __future__ import annotations

import unittest
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi import HTTPException

from app.api.deps.auth import AuthenticatedUser
from app.api.v1 import input_requests
from app.schemas.input_schema import InputRequestMarkPaidAction


class FakeAsyncSession:
    def __init__(self):
        self.committed = False
        self.rolled_back = False

    async def commit(self):
        self.committed = True

    async def refresh(self, _value):
        return None

    async def flush(self):
        return None

    async def rollback(self):
        self.rolled_back = True


class InputRequestPaymentRuleTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.owner = AuthenticatedUser(
            subject="owner-user",
            role="owner",
            roles=("owner",),
        )

    async def test_income_is_marked_received_without_flowaccount_payment(self):
        income_request = SimpleNamespace(
            id=uuid4(),
            entry_type="INCOME",
            status="APPROVED",
            payment_reference=None,
            review_note=None,
            paid_at=None,
            reviewed_at=None,
        )
        db = FakeAsyncSession()
        selected_date = date(2026, 7, 22)

        with (
            patch.object(
                input_requests,
                "_get_input_request_with_project",
                new=AsyncMock(return_value=(income_request, "Renovation The Mall")),
            ),
            patch.object(input_requests, "is_flowaccount_configured", return_value=True),
            patch.object(
                input_requests,
                "_serialize_input_request",
                return_value={"request_id": str(income_request.id), "status": "PAID"},
            ),
            patch.object(input_requests, "FlowAccountService") as flowaccount_service,
        ):
            response = await input_requests.mark_paid_admin_input_request(
                request_id=income_request.id,
                request=InputRequestMarkPaidAction(
                    payment_reference="RECEIVE-001",
                    payment_date=selected_date,
                ),
                _user=self.owner,
                db=db,
            )

        self.assertEqual(response.data["status"], "PAID")
        self.assertEqual(income_request.status, "PAID")
        self.assertEqual(income_request.payment_reference, "RECEIVE-001")
        self.assertEqual(
            income_request.paid_at.astimezone(input_requests.THAILAND_TIMEZONE).date(),
            selected_date,
        )
        self.assertTrue(db.committed)
        flowaccount_service.assert_not_called()

    async def test_expense_still_syncs_flowaccount_payment_before_paid(self):
        expense_request = SimpleNamespace(
            id=uuid4(),
            entry_type="EXPENSE",
            status="APPROVED",
            payment_reference=None,
            review_note=None,
            paid_at=None,
            reviewed_at=None,
            flowaccount_expense_id="expense-001",
            flowaccount_payment_status="NOT_READY",
            flowaccount_payment_error=None,
            flowaccount_payment_synced_at=None,
        )
        db = FakeAsyncSession()
        payment_service = SimpleNamespace(create_expense_payment=AsyncMock())
        readiness = SimpleNamespace(
            can_mark_paid=True,
            missing_fields=[],
            errors=[],
        )

        with (
            patch.object(
                input_requests,
                "_get_input_request_with_project",
                new=AsyncMock(return_value=(expense_request, "Renovation The Mall")),
            ),
            patch.object(input_requests, "is_flowaccount_configured", return_value=True),
            patch.object(
                input_requests,
                "_refresh_accounting_readiness",
                new=AsyncMock(return_value=readiness),
            ),
            patch.object(
                input_requests,
                "_serialize_input_request",
                return_value={"request_id": str(expense_request.id), "status": "PAID"},
            ),
            patch.object(
                input_requests,
                "FlowAccountService",
                return_value=payment_service,
            ),
        ):
            response = await input_requests.mark_paid_admin_input_request(
                request_id=expense_request.id,
                request=InputRequestMarkPaidAction(
                    payment_reference="PAY-001",
                    payment_date=date(2026, 7, 22),
                ),
                _user=self.owner,
                db=db,
            )

        self.assertEqual(response.data["status"], "PAID")
        self.assertEqual(expense_request.status, "PAID")
        self.assertEqual(expense_request.flowaccount_payment_status, "PAYMENT_SYNCED")
        payment_service.create_expense_payment.assert_awaited_once_with(
            expense_request,
            expense_id="expense-001",
            payment_date=date(2026, 7, 22),
        )
        self.assertTrue(db.committed)

    async def test_income_requires_received_date(self):
        income_request = SimpleNamespace(
            id=uuid4(),
            entry_type="INCOME",
            status="APPROVED",
            payment_reference=None,
            review_note=None,
            paid_at=None,
            reviewed_at=None,
        )
        db = FakeAsyncSession()

        with patch.object(
            input_requests,
            "_get_input_request_with_project",
            new=AsyncMock(return_value=(income_request, "Renovation The Mall")),
        ):
            with self.assertRaises(HTTPException) as context:
                await input_requests.mark_paid_admin_input_request(
                    request_id=income_request.id,
                    request=InputRequestMarkPaidAction(
                        payment_reference="RECEIVE-002",
                        payment_date=None,
                    ),
                    _user=self.owner,
                    db=db,
                )

        self.assertEqual(context.exception.status_code, 400)
        self.assertIn("payment_date", context.exception.detail)
        self.assertTrue(db.rolled_back)

    def test_expense_keeps_action_completion_timestamp(self):
        completed_at = datetime(2026, 7, 23, 8, 30, tzinfo=timezone.utc)

        result = input_requests._payment_completion_timestamp(
            entry_type="EXPENSE",
            payment_date=date(2026, 7, 22),
            completed_at=completed_at,
        )

        self.assertIs(result, completed_at)


if __name__ == "__main__":
    unittest.main()
