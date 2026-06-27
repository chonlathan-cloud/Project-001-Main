from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.models.input_request import InputRequest
from app.services.flowaccount_service import FlowAccountError, FlowAccountService


class CapturingFlowAccountService(FlowAccountService):
    def __init__(self):
        super().__init__(
            SimpleNamespace(
                flowaccount_base_url="https://flowaccount.test",
                flowaccount_default_payment_method="transfer",
                flowaccount_default_bank_account_id="123",
            )
        )
        self.last_payment_payload = None

    async def _request(self, method: str, path: str, **kwargs):
        self.last_payment_payload = kwargs.get("json")
        return {"data": {"ok": True}}


def make_input_request(wht_rate: Decimal) -> InputRequest:
    return InputRequest(
        entry_type="EXPENSE",
        requester_name="Requester",
        request_date=date(2026, 6, 26),
        request_type="ค่าใช้จ่ายทั่วไป",
        vendor_name="Vendor",
        document_date=date(2026, 6, 26),
        accounting_vat_mode="vat_exclusive",
        accounting_wht_rate=wht_rate,
        amount=Decimal("3414.75"),
        approved_amount=Decimal("3414.75"),
        payment_reference="TEST-001",
    )


class FlowAccountPaymentPayloadTest(unittest.IsolatedAsyncioTestCase):
    async def test_payment_payload_sends_zero_withheld_percentage_as_integer(self):
        service = CapturingFlowAccountService()

        await service.create_expense_payment(
            make_input_request(Decimal("0.00")),
            expense_id="EXP2026060001",
            payment_date=date(2026, 6, 26),
        )

        self.assertEqual(service.last_payment_payload["withheldPercentage"], 0)
        self.assertIs(type(service.last_payment_payload["withheldPercentage"]), int)

    async def test_payment_payload_sends_labor_withheld_percentage_as_integer(self):
        service = CapturingFlowAccountService()

        await service.create_expense_payment(
            make_input_request(Decimal("3.00")),
            expense_id="EXP2026060001",
            payment_date=date(2026, 6, 26),
        )

        self.assertEqual(service.last_payment_payload["withheldPercentage"], 3)
        self.assertIs(type(service.last_payment_payload["withheldPercentage"]), int)

    async def test_payment_payload_rejects_fractional_withheld_percentage(self):
        service = CapturingFlowAccountService()

        with self.assertRaisesRegex(FlowAccountError, "whole number"):
            await service.create_expense_payment(
                make_input_request(Decimal("1.50")),
                expense_id="EXP2026060001",
                payment_date=date(2026, 6, 26),
            )


if __name__ == "__main__":
    unittest.main()
