from __future__ import annotations

import asyncio
import logging
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api.v1.auth import LineLoginRequest, line_login, router as auth_router
from app.api.v1.auth import submit_access_request
from app.api.v1.daily_reports import (
    _inspect_upload_with_limit,
    _media_type_and_limit,
    _validate_media_signature,
)
from app.core.rate_limit import FixedWindowRateLimiter, daily_report_rate_limit_rules
from app.core.rate_limit import RateLimitMiddleware, RateLimitRule
from app.core.observability import JsonLogFormatter
from app.core.security import issue_access_request_token, verify_access_request_token


class FakeUpload:
    def __init__(self, chunks: list[bytes]):
        self._chunks = list(chunks)
        self.seek_position = None

    async def read(self, _size: int) -> bytes:
        return self._chunks.pop(0) if self._chunks else b""

    async def seek(self, position: int) -> None:
        self.seek_position = position


class Phase8SecurityTests(unittest.TestCase):
    def test_rejected_line_subcontractor_can_start_a_new_access_request(self):
        rejected_request = SimpleNamespace(
            id="line-request-1",
            status="rejected",
            company_name="Previous Company",
            contact_name="Previous Contact",
            phone="0812345678",
            tax_id="1234567890123",
            bank_account={"bank_name": "Test Bank"},
            rejection_reason="Please correct the submitted details",
        )

        with (
            patch(
                "app.api.v1.auth._fetch_line_profile",
                new=AsyncMock(
                    return_value={
                        "userId": "U-rejected",
                        "displayName": "LINE User",
                    }
                ),
            ),
            patch("app.api.v1.auth.get_subcontractor_by_line_uid", return_value=None),
            patch(
                "app.api.v1.auth.get_access_request_by_identity",
                return_value=rejected_request,
            ),
            patch("app.api.v1.auth.issue_access_request_token", return_value="proof-token"),
        ):
            response = asyncio.run(
                line_login(
                    LineLoginRequest(
                        line_access_token="line-access-token",
                        portal="subcontractor",
                    )
                )
            )

        self.assertEqual(response.data["status"], "REQUIRE_SIGNUP")
        self.assertTrue(response.data["resubmission"])
        self.assertEqual(response.data["registration_token"], "proof-token")
        self.assertEqual(response.data["company_name"], "Previous Company")

    def test_access_request_token_proves_verified_line_identity(self):
        token = issue_access_request_token(
            provider="line",
            line_uid="U-verified",
            portal="subcontractor",
        )

        payload = verify_access_request_token(token)

        self.assertEqual(payload["provider"], "line")
        self.assertEqual(payload["line_uid"], "U-verified")
        self.assertEqual(payload["portal"], "subcontractor")

    def test_access_request_token_rejects_tampering(self):
        token = issue_access_request_token(provider="google", email="owner@example.com")
        encoded_header, encoded_payload, signature = token.split(".", 2)
        tampered_payload = f"{encoded_payload[:-1]}{'A' if encoded_payload[-1] != 'A' else 'B'}"

        with self.assertRaises(HTTPException) as context:
            verify_access_request_token(
                f"{encoded_header}.{tampered_payload}.{signature}"
            )

        self.assertEqual(context.exception.status_code, 401)

    def test_access_request_token_rejects_expired_proof(self):
        token = issue_access_request_token(
            provider="line",
            line_uid="U-expired",
            expires_minutes=0,
        )

        with self.assertRaises(HTTPException) as context:
            verify_access_request_token(token)

        self.assertEqual(context.exception.status_code, 401)

    def test_access_request_rejects_uid_that_does_not_match_verified_login(self):
        token = issue_access_request_token(provider="line", line_uid="U-verified")

        with self.assertRaises(HTTPException) as context:
            asyncio.run(
                submit_access_request(
                    provider="line",
                    registration_token=token,
                    email=None,
                    line_uid="U-attacker-supplied",
                    picture_url=None,
                    display_name="Test",
                    requested_account_type="subcontractor",
                    company_name="Test",
                    first_name=None,
                    nickname=None,
                    contact_name=None,
                    phone=None,
                    tax_id=None,
                    bank_name=None,
                    account_no=None,
                    account_name=None,
                    kyc_image=None,
                )
            )

        self.assertEqual(context.exception.status_code, 401)

    def test_access_request_accepts_identity_that_matches_verified_login(self):
        token = issue_access_request_token(provider="line", line_uid="U-verified")
        stored_request = SimpleNamespace(
            id="request-1",
            provider="line",
            email=None,
            line_uid="U-verified",
            display_name="Test",
            company_name="Test",
            contact_name=None,
            status="pending",
            rejection_reason=None,
        )

        with patch(
            "app.api.v1.auth.upsert_access_request",
            return_value=stored_request,
        ) as upsert:
            response = asyncio.run(
                submit_access_request(
                    provider="line",
                    registration_token=token,
                    email=None,
                    line_uid="U-verified",
                    picture_url=None,
                    display_name="Test",
                    requested_account_type="subcontractor",
                    company_name="Test",
                    first_name=None,
                    nickname=None,
                    contact_name=None,
                    phone=None,
                    tax_id=None,
                    bank_name=None,
                    account_no=None,
                    account_name=None,
                    kyc_image=None,
                )
            )

        self.assertEqual(response.data.status, "PENDING_APPROVAL")
        self.assertEqual(upsert.call_args.kwargs["line_uid"], "U-verified")

    def test_customer_access_request_stores_first_name_and_nickname(self):
        token = issue_access_request_token(
            provider="line",
            line_uid="U-customer",
            portal="customer",
        )
        stored_request = SimpleNamespace(
            id="request-customer",
            provider="line",
            email=None,
            line_uid="U-customer",
            display_name="LINE Display",
            company_name=None,
            contact_name="สมชาย",
            status="pending",
            rejection_reason=None,
        )

        with patch(
            "app.api.v1.auth.upsert_access_request",
            return_value=stored_request,
        ) as upsert:
            response = asyncio.run(
                submit_access_request(
                    provider="line",
                    registration_token=token,
                    email=None,
                    line_uid="U-customer",
                    picture_url=None,
                    display_name="LINE Display",
                    requested_account_type="customer",
                    company_name=None,
                    first_name="สมชาย",
                    nickname="ชาย",
                    contact_name="สมชาย",
                    phone=None,
                    tax_id=None,
                    bank_name=None,
                    account_no=None,
                    account_name=None,
                    kyc_image=None,
                )
            )

        self.assertEqual(response.data.status, "PENDING_APPROVAL")
        self.assertEqual(upsert.call_args.kwargs["first_name"], "สมชาย")
        self.assertEqual(upsert.call_args.kwargs["nickname"], "ชาย")
        self.assertEqual(upsert.call_args.kwargs["contact_name"], "สมชาย")
        self.assertIsNone(upsert.call_args.kwargs["company_name"])

    def test_customer_access_request_requires_first_name_and_nickname(self):
        token = issue_access_request_token(
            provider="line",
            line_uid="U-customer",
            portal="customer",
        )

        with self.assertRaises(HTTPException) as context:
            asyncio.run(
                submit_access_request(
                    provider="line",
                    registration_token=token,
                    email=None,
                    line_uid="U-customer",
                    picture_url=None,
                    display_name="LINE Display",
                    requested_account_type="customer",
                    company_name=None,
                    first_name="",
                    nickname="",
                    contact_name=None,
                    phone=None,
                    tax_id=None,
                    bank_name=None,
                    account_no=None,
                    account_name=None,
                    kyc_image=None,
                )
            )

        self.assertEqual(context.exception.status_code, 400)
        self.assertIn("ชื่อจริง", context.exception.detail)

    def test_legacy_raw_line_uid_signup_route_is_removed(self):
        route_paths = {route.path for route in auth_router.routes}
        self.assertNotIn("/auth/sign-up", route_paths)

    def test_structured_formatter_drops_non_allowlisted_private_fields(self):
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="safe event",
            args=(),
            exc_info=None,
        )
        record.event = "safe_event"
        record.line_access_token = "must-not-appear"
        rendered = JsonLogFormatter().format(record)
        self.assertIn("safe_event", rendered)
        self.assertNotIn("must-not-appear", rendered)
        self.assertNotIn("line_access_token", rendered)

    def test_fixed_window_rate_limit_rejects_after_limit(self):
        limiter = FixedWindowRateLimiter()
        first = limiter.consume(
            rule_name="authentication",
            client_key="ip:test",
            limit=2,
            now=120.0,
        )
        second = limiter.consume(
            rule_name="authentication",
            client_key="ip:test",
            limit=2,
            now=121.0,
        )
        third = limiter.consume(
            rule_name="authentication",
            client_key="ip:test",
            limit=2,
            now=122.0,
        )
        next_window = limiter.consume(
            rule_name="authentication",
            client_key="ip:test",
            limit=2,
            now=180.0,
        )

        self.assertTrue(first.allowed)
        self.assertTrue(second.allowed)
        self.assertFalse(third.allowed)
        self.assertEqual(third.remaining, 0)
        self.assertTrue(next_window.allowed)

    def test_daily_report_rules_cover_required_high_risk_endpoints(self):
        settings = SimpleNamespace(
            rate_limit_auth_per_minute=20,
            rate_limit_upload_per_minute=30,
            rate_limit_question_per_minute=10,
            rate_limit_webhook_per_minute=180,
        )
        rules = {rule.name: rule for rule in daily_report_rate_limit_rules(settings)}

        self.assertTrue(
            rules["authentication"].path_pattern.fullmatch(
                "/api/v1/auth/line-login"
            )
        )
        self.assertTrue(
            rules["daily_report_upload"].path_pattern.fullmatch(
                "/api/v1/daily-reports/me/submissions/submission-1/media"
            )
        )
        self.assertTrue(
            rules["daily_report_question"].path_pattern.fullmatch(
                "/api/v1/daily-reports/customer/reports/report-1/questions"
            )
        )
        self.assertTrue(
            rules["line_customer_webhook"].path_pattern.fullmatch(
                "/api/v1/daily-reports/line/customer/webhook"
            )
        )

    def test_rate_limit_middleware_returns_retry_headers(self):
        app = FastAPI()
        app.add_middleware(
            RateLimitMiddleware,
            enabled=True,
            rules=[
                RateLimitRule.create(
                    name="test",
                    method="POST",
                    path_pattern=r"/limited",
                    requests_per_minute=2,
                )
            ],
        )

        @app.post("/limited")
        async def limited():
            return {"ok": True}

        with TestClient(app) as client:
            self.assertEqual(client.post("/limited").status_code, 200)
            second = client.post("/limited")
            rejected = client.post("/limited")

        self.assertEqual(second.headers["X-RateLimit-Remaining"], "0")
        self.assertEqual(rejected.status_code, 429)
        self.assertIn("Retry-After", rejected.headers)

    def test_upload_reader_rejects_oversized_body_before_full_read(self):
        upload = FakeUpload([b"a" * 6, b"b" * 6])
        with self.assertRaises(HTTPException) as context:
            asyncio.run(_inspect_upload_with_limit(upload, 10))
        self.assertEqual(context.exception.status_code, 413)

    def test_upload_inspection_rewinds_without_buffering_complete_file(self):
        upload = FakeUpload([b"\xff\xd8\xffabc", b"def"])
        size_bytes, prefix = asyncio.run(_inspect_upload_with_limit(upload, 20))
        self.assertEqual(size_bytes, 9)
        self.assertEqual(prefix, b"\xff\xd8\xffabcdef")
        self.assertEqual(upload.seek_position, 0)

    def test_media_validation_accepts_jpeg_and_rejects_spoofed_png(self):
        media_type, _max_bytes = _media_type_and_limit("image/jpeg")
        self.assertEqual(media_type, "PHOTO")
        _validate_media_signature(b"\xff\xd8\xff\xdbvalid", "image/jpeg")
        with self.assertRaises(HTTPException) as context:
            _validate_media_signature(b"not-a-png", "image/png")
        self.assertEqual(context.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
