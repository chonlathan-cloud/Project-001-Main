from __future__ import annotations

import unittest
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi import HTTPException

from app.api.deps.auth import AuthenticatedUser
from app.api.v1 import input_requests
from app.models.input_request import InputRequest
from app.schemas.input_schema import InputRequestMarkPaidAction


class FakeAsyncSession:
    def __init__(self):
        self.added = []
        self.committed = False
        self.rolled_back = False

    def add(self, value):
        self.added.append(value)

    async def commit(self):
        self.committed = True

    async def refresh(self, _value):
        return None

    async def flush(self):
        return None

    async def rollback(self):
        self.rolled_back = True


class FakeRowsResult:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


def approved_request(entry_type: str) -> InputRequest:
    return InputRequest(
        id=uuid4(),
        project_id=uuid4(),
        subcontractor_id="sub-001" if entry_type == "EXPENSE" else None,
        entry_type=entry_type,
        requester_name="Requester",
        request_date=date(2026, 7, 22),
        request_type="ค่าแรง" if entry_type == "EXPENSE" else None,
        amount=Decimal("1000.00"),
        approved_amount=Decimal("1000.00"),
        status="APPROVED",
        receipt_storage_key="gs://private/perm_bills/source.jpg",
        flowaccount_payment_status="NOT_READY",
    )


class InputRequestPaymentRuleTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.owner = AuthenticatedUser(
            subject="owner-user",
            role="owner",
            roles=("owner",),
        )

    async def _mark_paid(self, item: InputRequest, *, payment_date: date | None):
        db = FakeAsyncSession()
        delete_storage_key = AsyncMock()
        with (
            patch.object(
                input_requests,
                "_get_input_request_with_project",
                new=AsyncMock(return_value=(item, "Renovation The Mall")),
            ),
            patch.object(
                input_requests,
                "_next_payment_reference",
                new=AsyncMock(return_value=(1, f"{'E' if item.entry_type == 'EXPENSE' else 'IN'}00122072026")),
            ),
            patch.object(
                input_requests,
                "organize_input_receipt_in_paid_storage",
                new=AsyncMock(return_value="gs://private/perm_bills/paid/2026/07/22/ref/original.jpg"),
            ),
            patch.object(
                input_requests,
                "paid_document_storage_prefix",
                return_value="gs://private/perm_bills/paid/2026/07/22/ref",
            ),
            patch.object(
                input_requests,
                "_refresh_accounting_readiness",
                new=AsyncMock(),
            ),
            patch.object(
                input_requests,
                "_serialize_input_request",
                return_value={
                    "request_id": str(item.id),
                    "status": "PAID",
                    "internal_payment_reference": (
                        "E00122072026" if item.entry_type == "EXPENSE" else "IN00122072026"
                    ),
                },
            ),
            patch.object(
                input_requests,
                "delete_storage_key",
                new=delete_storage_key,
            ),
            patch.object(input_requests, "FlowAccountService") as flowaccount_service,
        ):
            response = await input_requests.mark_paid_admin_input_request(
                request_id=item.id,
                request=InputRequestMarkPaidAction(
                    payment_reference="BANK-OPTIONAL",
                    payment_date=payment_date,
                ),
                user=self.owner,
                db=db,
            )
        return response, db, flowaccount_service, delete_storage_key

    async def test_expense_is_paid_without_calling_flowaccount(self):
        item = approved_request("EXPENSE")

        response, db, flowaccount_service, delete_storage_key = await self._mark_paid(
            item,
            payment_date=date(2026, 7, 22),
        )

        self.assertEqual(response.data["status"], "PAID")
        self.assertEqual(item.status, "PAID")
        self.assertEqual(item.flowaccount_payment_status, "NOT_SYNCED")
        self.assertEqual(item.payment.internal_reference, "E00122072026")
        self.assertEqual(item.payment.bank_transfer_reference, "BANK-OPTIONAL")
        self.assertEqual(item.payment.payment_date, date(2026, 7, 22))
        self.assertTrue(db.committed)
        delete_storage_key.assert_awaited_once_with(
            "gs://private/perm_bills/source.jpg"
        )
        flowaccount_service.assert_not_called()

    async def test_income_is_received_without_flowaccount(self):
        item = approved_request("INCOME")

        response, db, flowaccount_service, delete_storage_key = await self._mark_paid(
            item,
            payment_date=date(2026, 7, 22),
        )

        self.assertEqual(response.data["internal_payment_reference"], "IN00122072026")
        self.assertEqual(item.flowaccount_payment_status, "NOT_REQUIRED")
        self.assertTrue(db.committed)
        delete_storage_key.assert_awaited_once_with(
            "gs://private/perm_bills/source.jpg"
        )
        flowaccount_service.assert_not_called()

    async def test_only_approved_request_can_record_payment(self):
        item = approved_request("EXPENSE")
        item.status = "PENDING_ADMIN"
        db = FakeAsyncSession()
        with patch.object(
            input_requests,
            "_get_input_request_with_project",
            new=AsyncMock(return_value=(item, "Renovation The Mall")),
        ):
            with self.assertRaises(HTTPException) as context:
                await input_requests.mark_paid_admin_input_request(
                    request_id=item.id,
                    request=InputRequestMarkPaidAction(),
                    user=self.owner,
                    db=db,
                )
        self.assertEqual(context.exception.status_code, 400)
        self.assertTrue(db.rolled_back)

    def test_reference_format_uses_type_sequence_and_business_date(self):
        payment_date = date(2026, 7, 24)
        self.assertEqual(
            input_requests._format_payment_reference("EXPENSE", 1, payment_date),
            "E00124072026",
        )
        self.assertEqual(
            input_requests._format_payment_reference("INCOME", 12, payment_date),
            "IN01224072026",
        )

    async def test_payment_confirmation_status_list_keeps_review_state_visible(self):
        payment_id = uuid4()
        request_id = uuid4()
        project_id = uuid4()
        confirmation_id = uuid4()
        submitted_at = datetime(2026, 7, 24, 8, 30, tzinfo=timezone.utc)
        confirmation = SimpleNamespace(
            id=confirmation_id,
            version=1,
            status="CHANGES_REQUESTED",
            received_date=date(2026, 7, 24),
            received_full_amount=True,
            note="ได้รับครบแล้ว",
            file_name="confirmation.jpg",
            content_type="image/jpeg",
            submitted_at=submitted_at,
            verified_at=None,
            verification_note="กรุณาถ่ายรูปใหม่ให้เห็นยอดเงิน",
        )
        payment = SimpleNamespace(
            id=payment_id,
            amount=Decimal("12500.00"),
            payment_date=date(2026, 7, 24),
            internal_reference="E00124072026",
            confirmations=[confirmation],
        )
        input_request = SimpleNamespace(
            id=request_id,
            project_id=project_id,
            requester_name="ช่างทดสอบ",
            request_type="ค่าแรง",
        )
        db = SimpleNamespace(
            execute=AsyncMock(
                return_value=FakeRowsResult(
                    [(payment, input_request, "โครงการทดสอบ")]
                )
            )
        )
        subcontractor = AuthenticatedUser(
            subject="line-user",
            role="subcontractor",
            roles=("subcontractor",),
            subcontractor_id="sub-001",
        )

        response = await input_requests.list_my_payment_confirmation_statuses(
            user=subcontractor,
            db=db,
        )

        self.assertEqual(len(response.data), 1)
        item = response.data[0]
        self.assertEqual(item.confirmation_status, "CHANGES_REQUESTED")
        self.assertTrue(item.action_required)
        self.assertEqual(item.latest_confirmation_id, confirmation_id)
        self.assertEqual(
            item.latest_verification_note,
            "กรุณาถ่ายรูปใหม่ให้เห็นยอดเงิน",
        )


if __name__ == "__main__":
    unittest.main()
