from __future__ import annotations

import unittest

from fastapi import HTTPException

from app.api.deps.auth import AuthenticatedUser
from app.api.v1.input_requests import _validate_entry_type_for_user


class InputRequestAccessRuleTests(unittest.TestCase):
    def test_subcontractor_can_submit_expense(self):
        user = AuthenticatedUser(
            subject="line-user",
            role="subcontractor",
            roles=("subcontractor",),
            subcontractor_id="sub-001",
        )

        _validate_entry_type_for_user(user=user, entry_type="EXPENSE")

    def test_subcontractor_cannot_submit_income(self):
        user = AuthenticatedUser(
            subject="line-user",
            role="subcontractor",
            roles=("subcontractor",),
            subcontractor_id="sub-001",
        )

        with self.assertRaises(HTTPException) as context:
            _validate_entry_type_for_user(user=user, entry_type="INCOME")

        self.assertEqual(context.exception.status_code, 403)
        self.assertIn("รายจ่าย", context.exception.detail)

    def test_internal_roles_can_submit_income(self):
        for role in ("owner", "admin", "inspector"):
            with self.subTest(role=role):
                user = AuthenticatedUser(
                    subject=f"{role}-user",
                    role=role,
                    roles=(role,),
                )

                _validate_entry_type_for_user(user=user, entry_type="INCOME")


if __name__ == "__main__":
    unittest.main()
