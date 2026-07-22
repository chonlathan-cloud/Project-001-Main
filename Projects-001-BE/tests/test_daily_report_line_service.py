from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from app.services import daily_report_line_service


class FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class FakeAsyncClient:
    def __init__(self, *, response: FakeResponse):
        self.response = response
        self.get_calls: list[tuple[str, dict]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def get(self, url: str, *, headers: dict):
        self.get_calls.append((url, headers))
        return self.response


class DailyReportLineServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_customer_webhook_fetches_and_records_group_name(self):
        client = FakeAsyncClient(
            response=FakeResponse(
                {
                    "groupId": "Cgroup1234567890",
                    "groupName": "โครงการบ้านคุณสมชาย",
                }
            )
        )
        record_candidate = Mock()
        update_display_name = Mock()
        settings = SimpleNamespace(line_customer_channel_access_token="test-token")

        with (
            patch.object(daily_report_line_service, "get_settings", return_value=settings),
            patch.object(
                daily_report_line_service.daily_report_service,
                "get_line_destination_candidate",
                return_value=None,
            ),
            patch.object(
                daily_report_line_service.daily_report_service,
                "record_line_destination_candidate",
                record_candidate,
            ),
            patch.object(
                daily_report_line_service.daily_report_service,
                "update_line_destination_candidate_display_name",
                update_display_name,
            ),
            patch.object(
                daily_report_line_service.httpx,
                "AsyncClient",
                return_value=client,
            ),
        ):
            result = await daily_report_line_service.handle_customer_webhook(
                {
                    "events": [
                        {
                            "type": "message",
                            "source": {
                                "type": "group",
                                "groupId": "Cgroup1234567890",
                            },
                        }
                    ]
                }
            )

        self.assertEqual(result, {"events": 1, "discovered": 1, "replies_sent": 0})
        self.assertEqual(len(client.get_calls), 1)
        self.assertTrue(client.get_calls[0][0].endswith("/Cgroup1234567890/summary"))
        record_candidate.assert_called_once()
        self.assertEqual(
            update_display_name.call_args.kwargs["display_name"],
            "โครงการบ้านคุณสมชาย",
        )
        self.assertEqual(update_display_name.call_args.kwargs["display_name_status"], "AVAILABLE")

    async def test_recent_group_name_skips_summary_lookup(self):
        settings = SimpleNamespace(line_customer_channel_access_token="test-token")
        record_candidate = Mock()
        existing_candidate = {
            "display_name": "กลุ่มเดิม",
            "display_name_checked_at": datetime.now(UTC),
        }

        with (
            patch.object(daily_report_line_service, "get_settings", return_value=settings),
            patch.object(
                daily_report_line_service.daily_report_service,
                "get_line_destination_candidate",
                return_value=existing_candidate,
            ),
            patch.object(
                daily_report_line_service.daily_report_service,
                "record_line_destination_candidate",
                record_candidate,
            ),
            patch.object(daily_report_line_service.httpx, "AsyncClient") as async_client,
        ):
            result = await daily_report_line_service.handle_customer_webhook(
                {
                    "events": [
                        {
                            "type": "message",
                            "source": {
                                "type": "group",
                                "groupId": "Cgroup1234567890",
                            },
                        }
                    ]
                }
            )

        self.assertEqual(result["discovered"], 1)
        async_client.assert_not_called()
        record_candidate.assert_called_once()

    async def test_candidate_list_backfills_missing_group_name(self):
        client = FakeAsyncClient(
            response=FakeResponse(
                {
                    "groupId": "Cgroup1234567890",
                    "groupName": "โครงการบ้านคุณสมชาย",
                }
            )
        )
        settings = SimpleNamespace(line_customer_channel_access_token="test-token")
        update_display_name = Mock()
        refreshed_candidates = [
            {
                "line_target_id": "Cgroup1234567890",
                "target_type": "group",
                "display_name": "โครงการบ้านคุณสมชาย",
            }
        ]

        with (
            patch.object(daily_report_line_service, "get_settings", return_value=settings),
            patch.object(
                daily_report_line_service.daily_report_service,
                "update_line_destination_candidate_display_name",
                update_display_name,
            ),
            patch.object(
                daily_report_line_service.daily_report_service,
                "list_line_destination_candidates",
                return_value=refreshed_candidates,
            ),
            patch.object(
                daily_report_line_service.httpx,
                "AsyncClient",
                return_value=client,
            ),
        ):
            result = await daily_report_line_service.refresh_line_destination_candidate_names(
                [{"line_target_id": "Cgroup1234567890", "target_type": "group"}]
            )

        self.assertEqual(result, refreshed_candidates)
        self.assertEqual(
            update_display_name.call_args.kwargs["display_name"],
            "โครงการบ้านคุณสมชาย",
        )


if __name__ == "__main__":
    unittest.main()
