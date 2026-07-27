from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import UTC, date, datetime
from itertools import count
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlsplit

from fastapi import HTTPException

from app.services import daily_report_service
from app.services import daily_report_notification_service


class FakeSnapshot:
    def __init__(self, item_id: str, payload: dict | None):
        self.id = item_id
        self._payload = deepcopy(payload)
        self.exists = payload is not None

    def to_dict(self):
        return deepcopy(self._payload)


class FakeDocument:
    def __init__(self, store: dict[str, dict], item_id: str):
        self._store = store
        self.id = item_id

    def get(self):
        return FakeSnapshot(self.id, self._store.get(self.id))

    def set(self, payload: dict, merge: bool = False):
        if merge:
            current = deepcopy(self._store.get(self.id, {}))
            current.update(deepcopy(payload))
            self._store[self.id] = current
            return
        self._store[self.id] = deepcopy(payload)

    def create(self, payload: dict):
        if self.id in self._store:
            from google.api_core.exceptions import AlreadyExists

            raise AlreadyExists("Document already exists.")
        self._store[self.id] = deepcopy(payload)

    def delete(self):
        self._store.pop(self.id, None)


class FakeCollection:
    def __init__(self, store: dict[str, dict], id_counter):
        self._store = store
        self._id_counter = id_counter

    def document(self, item_id: str | None = None):
        return FakeDocument(self._store, item_id or f"auto-{next(self._id_counter)}")

    def stream(self):
        return [
            FakeSnapshot(item_id, payload)
            for item_id, payload in self._store.items()
        ]


class FakeFirestore:
    def __init__(self):
        self.data: dict[str, dict[str, dict]] = {}
        self._id_counter = count(1)

    def collection(self, name: str):
        return FakeCollection(self.data.setdefault(name, {}), self._id_counter)


class DailyReportServiceTests(unittest.TestCase):
    def setUp(self):
        self.firestore = FakeFirestore()
        self.client_patch = patch.object(
            daily_report_service,
            "_client",
            return_value=self.firestore,
        )
        self.client_patch.start()

    def tearDown(self):
        self.client_patch.stop()

    def test_customer_text_strips_only_known_subcontractor_labels(self):
        text = (
            "THAMES PHUBORDEE: สสสสสxcvxcv\n\n"
            "Pao: testing\n\n"
            "พื้นที่: ชั้น 2"
        )

        cleaned = daily_report_service._strip_known_source_labels(
            text,
            {"THAMES PHUBORDEE", "Pao"},
        )

        self.assertEqual(
            cleaned,
            "สสสสสxcvxcv\n\ntesting\n\nพื้นที่: ชั้น 2",
        )

    def _submitted_source(self):
        daily_report_service.update_project_settings(
            project_id="project-1",
            updates={"reporting_company_name": "RAYADEE Construction Co., Ltd."},
            actor_id="owner@example.com",
        )
        submission = daily_report_service.create_submission(
            project_id="project-1",
            project_name="Riverside Residence",
            report_date=date(2026, 7, 18),
            subcontractor_id="sub-1",
            subcontractor_name="ABC Construction",
            actor_id="sub-1",
        )
        daily_report_service.update_submission(
            submission_id=submission["id"],
            subcontractor_id="sub-1",
            actor_id="sub-1",
            updates={
                "work_summary": "Installed ceiling framing in the east wing.",
                "manpower_total": 8,
                "progress_percent": 42,
                "issues": [{"title": "Late lighting layout", "severity": "high"}],
                "tomorrow_plan": "Continue framing after MEP coordination.",
            },
        )
        media_id = daily_report_service.new_media_id()
        daily_report_service.record_media(
            media_id=media_id,
            submission_id=submission["id"],
            project_id="project-1",
            owner_id="sub-1",
            media_type="PHOTO",
            file_name="site.jpg",
            content_type="image/jpeg",
            size_bytes=1024,
            storage_key="gs://private/site.jpg",
        )
        submitted = daily_report_service.submit_submission(
            submission_id=submission["id"],
            subcontractor_id="sub-1",
            actor_id="sub-1",
        )
        return submitted

    def test_submission_publish_and_correction_preserve_versions(self):
        submitted = self._submitted_source()
        self.assertEqual(submitted["status"], "SUBMITTED")

        reports = daily_report_service.list_reports(project_ids={"project-1"})
        self.assertEqual(len(reports), 1)
        report = reports[0]
        self.assertEqual(report["status"], "PENDING_REVIEW")
        self.assertEqual(report["manpower_total"], 8)
        self.assertEqual(report["reporting_company_name"], "RAYADEE Construction Co., Ltd.")
        self.assertEqual(
            report["summary"],
            "Installed ceiling framing in the east wing.",
        )
        self.assertEqual(
            report["tomorrow_plan"],
            "Continue framing after MEP coordination.",
        )

        daily_report_service.update_report_draft(
            report_id=report["id"],
            updates={"customer_note": "Reviewed against site evidence."},
            actor_id="owner@example.com",
            actor_role="owner",
        )
        first_publication = daily_report_service.publish_report(
            report_id=report["id"],
            publication_note="Initial issue",
            actor_id="owner@example.com",
            actor_role="owner",
        )
        self.assertEqual(first_publication["published_version"], 1)
        self.assertEqual(first_publication["status"], "PUBLISHED")

        daily_report_service.start_correction(
            report_id=report["id"],
            actor_id="owner@example.com",
            actor_role="owner",
        )
        customer_snapshot = daily_report_service.get_customer_report(report["id"])
        self.assertEqual(customer_snapshot["published_version"], 1)
        self.assertEqual(customer_snapshot["status"], "PUBLISHED")
        self.assertEqual(customer_snapshot["submissions"], [])
        self.assertEqual(
            customer_snapshot["reporting_company_name"],
            "RAYADEE Construction Co., Ltd.",
        )
        daily_report_service.update_project_settings(
            project_id="project-1",
            updates={"reporting_company_name": "RAYADEE Group Co., Ltd."},
            actor_id="owner@example.com",
        )
        daily_report_service.update_report_draft(
            report_id=report["id"],
            updates={"summary": "Corrected approved progress summary."},
            actor_id="owner@example.com",
            actor_role="owner",
        )
        second_publication = daily_report_service.publish_report(
            report_id=report["id"],
            publication_note="Corrected wording",
            actor_id="owner@example.com",
            actor_role="owner",
        )
        self.assertEqual(second_publication["published_version"], 2)

        versions = daily_report_service.list_versions(report["id"])
        self.assertEqual([item["version"] for item in versions], [2, 1])
        self.assertNotEqual(
            versions[0]["snapshot"]["summary"],
            versions[1]["snapshot"]["summary"],
        )
        self.assertEqual(
            [item["snapshot"]["reporting_company_name"] for item in versions],
            ["RAYADEE Group Co., Ltd.", "RAYADEE Construction Co., Ltd."],
        )

    def test_publish_requires_project_or_staff_reporting_company(self):
        self._submitted_source()
        report = daily_report_service.list_reports(project_ids={"project-1"})[0]
        daily_report_service.update_project_settings(
            project_id="project-1",
            updates={"reporting_company_name": None},
            actor_id="owner@example.com",
        )

        with self.assertRaises(HTTPException) as error:
            daily_report_service.publish_report(
                report_id=report["id"],
                publication_note=None,
                actor_id="owner@example.com",
                actor_role="owner",
            )

        self.assertEqual(error.exception.status_code, 400)
        self.assertIn("reporting company name", error.exception.detail)

    def test_publish_migrates_untouched_legacy_subcontractor_labels(self):
        self._submitted_source()
        report = daily_report_service.list_reports(project_ids={"project-1"})[0]
        daily_report_service.update_report_draft(
            report_id=report["id"],
            updates={
                "summary": "ABC Construction: Installed ceiling framing in the east wing.",
                "tomorrow_plan": "ABC Construction: Continue framing after MEP coordination.",
            },
            actor_id="owner@example.com",
            actor_role="owner",
        )

        daily_report_service.publish_report(
            report_id=report["id"],
            publication_note=None,
            actor_id="owner@example.com",
            actor_role="owner",
        )

        snapshot = daily_report_service.list_versions(report["id"])[0]["snapshot"]
        self.assertEqual(
            snapshot["summary"],
            "Installed ceiling framing in the east wing.",
        )
        self.assertEqual(
            snapshot["tomorrow_plan"],
            "Continue framing after MEP coordination.",
        )

    def test_customer_view_hides_source_label_from_existing_published_snapshot(self):
        self._submitted_source()
        report = daily_report_service.list_reports(project_ids={"project-1"})[0]
        daily_report_service.publish_report(
            report_id=report["id"],
            publication_note=None,
            actor_id="owner@example.com",
            actor_role="owner",
        )
        version_id = f"{report['id']}-v1"
        stored_version = self.firestore.data[daily_report_service.VERSIONS_COLLECTION][version_id]
        stored_version["snapshot"]["summary"] = (
            "ABC Construction: Installed ceiling framing in the east wing."
        )

        customer_report = daily_report_service.get_customer_report(report["id"])

        self.assertEqual(
            customer_report["summary"],
            "Installed ceiling framing in the east wing.",
        )
        self.assertEqual(
            stored_version["snapshot"]["summary"],
            "ABC Construction: Installed ceiling framing in the east wing.",
        )

    def test_change_request_returns_submission_to_editable_state(self):
        submitted = self._submitted_source()
        report = daily_report_service.list_reports(project_ids={"project-1"})[0]

        daily_report_service.request_changes(
            report_id=report["id"],
            reason="Add a closer photo of the ceiling supports.",
            submission_ids=[submitted["id"]],
            actor_id="admin@example.com",
            actor_role="admin",
        )
        changed = daily_report_service.get_submission(submitted["id"])
        self.assertEqual(changed["status"], "CHANGES_REQUESTED")
        self.assertIn("closer photo", changed["change_request_reason"])

    def test_memberships_are_scoped_by_principal_and_project(self):
        daily_report_service.upsert_project_membership(
            project_id="project-1",
            principal_type="customer",
            principal_id="customer-1",
            is_active=True,
            actor_id="owner@example.com",
        )
        self.assertTrue(
            daily_report_service.has_project_membership(
                project_id="project-1",
                principal_type="customer",
                principal_id="customer-1",
            )
        )
        self.assertFalse(
            daily_report_service.has_project_membership(
                project_id="project-2",
                principal_type="customer",
                principal_id="customer-1",
            )
        )

    def test_customer_share_link_is_project_scoped_rotatable_and_revocable(self):
        runtime_settings = SimpleNamespace(
            frontend_base_url="https://app.example.test",
            customer_report_public_share_enabled=True,
        )
        with patch.object(
            daily_report_service,
            "get_settings",
            return_value=runtime_settings,
        ):
            created = daily_report_service.update_customer_share_link(
                project_id="project-1",
                enabled=True,
                rotate=False,
                actor_id="admin@example.com",
                actor_role="admin",
            )
            first_token = parse_qs(urlsplit(created["link_url"]).fragment)["access"][0]
            self.assertEqual(
                daily_report_service.resolve_customer_share_project(first_token),
                "project-1",
            )

            rotated = daily_report_service.update_customer_share_link(
                project_id="project-1",
                enabled=True,
                rotate=True,
                actor_id="owner@example.com",
                actor_role="owner",
            )
            second_token = parse_qs(urlsplit(rotated["link_url"]).fragment)["access"][0]
            self.assertNotEqual(first_token, second_token)
            with self.assertRaises(HTTPException):
                daily_report_service.resolve_customer_share_project(first_token)
            self.assertEqual(
                daily_report_service.resolve_customer_share_project(second_token),
                "project-1",
            )

            daily_report_service.update_customer_share_link(
                project_id="project-1",
                enabled=False,
                rotate=False,
                actor_id="owner@example.com",
                actor_role="owner",
            )
            with self.assertRaises(HTTPException):
                daily_report_service.resolve_customer_share_project(second_token)

    def test_public_customer_report_excludes_internal_fields(self):
        self._submitted_source()
        report = daily_report_service.list_reports(project_ids={"project-1"})[0]
        daily_report_service.publish_report(
            report_id=report["id"],
            publication_note=None,
            actor_id="admin@example.com",
            actor_role="admin",
        )

        public_report = daily_report_service.get_public_customer_report(
            project_id="project-1",
            report_id=report["id"],
        )

        self.assertNotIn("published_by", public_report)
        self.assertNotIn("delivery_status", public_report)
        self.assertNotIn("source_submission_ids", public_report)
        self.assertNotIn("uploader_name", public_report["media"][0])
        self.assertEqual(
            public_report["reporting_company_name"],
            "RAYADEE Construction Co., Ltd.",
        )
        with self.assertRaises(HTTPException):
            daily_report_service.get_public_customer_report(
                project_id="project-2",
                report_id=report["id"],
            )

    def test_line_destination_uses_discovered_group_name(self):
        daily_report_service.record_line_destination_candidate(
            line_target_id="Cgroup1234567890",
            target_type="group",
            event_type="join",
        )
        daily_report_service.update_line_destination_candidate_display_name(
            line_target_id="Cgroup1234567890",
            display_name="โครงการบ้านคุณสมชาย",
            display_name_status="AVAILABLE",
        )
        daily_report_service.record_line_destination_candidate(
            line_target_id="Cgroup1234567890",
            target_type="group",
            event_type="message",
        )

        candidate = daily_report_service.get_line_destination_candidate("Cgroup1234567890")
        self.assertEqual(candidate["display_name"], "โครงการบ้านคุณสมชาย")
        self.assertEqual(candidate["display_name_status"], "AVAILABLE")

        destination = daily_report_service.update_line_destination(
            project_id="project-1",
            line_target_id="Cgroup1234567890",
            is_active=True,
            actor_id="owner@example.com",
        )
        self.assertEqual(destination["display_name"], "โครงการบ้านคุณสมชาย")
        self.assertEqual(destination["status"], "ACTIVE")

    def test_line_destination_rejects_undiscovered_or_non_group_target(self):
        with self.assertRaises(HTTPException):
            daily_report_service.update_line_destination(
                project_id="project-1",
                line_target_id="Cnot-discovered",
                is_active=True,
                actor_id="owner@example.com",
            )

        daily_report_service.record_line_destination_candidate(
            line_target_id="Ucustomer",
            target_type="user",
            event_type="message",
        )
        with self.assertRaises(HTTPException):
            daily_report_service.update_line_destination(
                project_id="project-1",
                line_target_id="Ucustomer",
                is_active=True,
                actor_id="owner@example.com",
            )

    def test_customer_publication_pins_curated_media(self):
        self._submitted_source()
        report = daily_report_service.list_reports(project_ids={"project-1"})[0]
        source_media = daily_report_service.get_report(report["id"])["media"][0]
        daily_report_service.set_report_media_visibility(
            report_id=report["id"],
            media_id=source_media["id"],
            included=False,
            actor_id="admin@example.com",
            actor_role="admin",
        )
        supplemental = daily_report_service.record_supplemental_media(
            media_id="admin-photo-1",
            report_id=report["id"],
            project_id="project-1",
            owner_id="admin@example.com",
            uploader_name="Site Admin",
            media_type="PHOTO",
            file_name="reassurance.jpg",
            content_type="image/jpeg",
            size_bytes=512,
            storage_key="gs://private/reassurance.jpg",
        )
        self.assertEqual(supplemental["source_type"], "ADMIN_SUPPLEMENTAL")

        daily_report_service.publish_report(
            report_id=report["id"],
            publication_note=None,
            actor_id="admin@example.com",
            actor_role="admin",
        )
        version = daily_report_service.list_versions(report["id"])[0]
        self.assertEqual(version["snapshot"]["published_media_ids"], ["admin-photo-1"])
        customer_report = daily_report_service.get_customer_report(report["id"])
        self.assertEqual([item["id"] for item in customer_report["media"]], ["admin-photo-1"])

        daily_report_service.start_correction(
            report_id=report["id"],
            actor_id="admin@example.com",
            actor_role="admin",
        )
        daily_report_service.remove_supplemental_media(
            report_id=report["id"],
            media_id="admin-photo-1",
            actor_id="admin@example.com",
            actor_role="admin",
        )
        historical_customer_report = daily_report_service.get_customer_report(report["id"])
        self.assertEqual(
            [item["id"] for item in historical_customer_report["media"]],
            ["admin-photo-1"],
        )

    def test_global_staff_alert_is_visible_to_every_admin_scope(self):
        project_alert = daily_report_service.ensure_staff_notification(
            project_id="project-1",
            report_date="2026-07-20",
            notification_type="UPLOAD_FAILURE",
            title="Project failure",
            message="Project-scoped failure",
        )
        global_alert = daily_report_service.ensure_global_staff_notification(
            notification_type="SCHEDULER_FAILURE",
            title="Global failure",
            message="Global system failure",
            discriminator="2026072010",
        )

        project_one_items = daily_report_service.list_staff_notifications(
            project_ids={"project-1"}
        )
        project_two_items = daily_report_service.list_staff_notifications(
            project_ids={"project-2"}
        )

        self.assertIn(project_alert["id"], {item["id"] for item in project_one_items})
        self.assertIn(global_alert["id"], {item["id"] for item in project_one_items})
        self.assertNotIn(project_alert["id"], {item["id"] for item in project_two_items})
        self.assertIn(global_alert["id"], {item["id"] for item in project_two_items})
        self.assertEqual(global_alert["scope"], "GLOBAL")

    def test_cycle_snapshot_and_no_work_day_are_stable(self):
        defaults = daily_report_service.get_project_settings("project-1")
        self.assertEqual(defaults["timezone"], "Asia/Bangkok")
        self.assertEqual(defaults["working_days"], [1, 2, 3, 4, 5, 6])
        self.assertEqual(defaults["cycle_creation_time"], "06:00")
        self.assertEqual(defaults["first_reminder_time"], "16:00")
        self.assertEqual(defaults["overdue_grace_minutes"], 15)
        self.assertEqual(defaults["draft_time"], "18:00")

        first = daily_report_service.ensure_daily_cycle(
            project_id="project-1",
            project_name="Riverside Residence",
            report_date="2026-07-20",
            submission_due_at=datetime(2026, 7, 20, 10, 0, tzinfo=UTC),
            review_target_at=datetime(2026, 7, 20, 12, 0, tzinfo=UTC),
            expected_subcontractor_ids=["sub-1"],
        )
        second = daily_report_service.ensure_daily_cycle(
            project_id="project-1",
            project_name="Changed Project Name",
            report_date="2026-07-20",
            submission_due_at=datetime(2026, 7, 20, 11, 0, tzinfo=UTC),
            review_target_at=datetime(2026, 7, 20, 13, 0, tzinfo=UTC),
            expected_subcontractor_ids=["sub-2"],
        )
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(second["expected_subcontractor_ids"], ["sub-1"])
        self.assertEqual(second["submission_due_at"], datetime(2026, 7, 20, 10, 0, tzinfo=UTC))

        no_work = daily_report_service.set_no_work_day(
            project_id="project-1",
            report_date="2026-07-20",
            reason="วันหยุดโครงการ",
            actor_id="admin@example.com",
            actor_role="admin",
        )
        self.assertEqual(no_work["status"], "ACTIVE")
        self.assertTrue(
            daily_report_service.is_no_work_day(
                project_id="project-1",
                report_date="2026-07-20",
            )
        )
        cycle = daily_report_service.get_daily_cycle(
            project_id="project-1",
            report_date="2026-07-20",
        )
        self.assertEqual(cycle["status"], "NO_WORK")

    def test_due_scanner_sends_each_reminder_once_and_creates_overdue_alert(self):
        daily_report_service.update_project_settings(
            project_id="project-1",
            updates={"expected_subcontractor_ids": ["sub-1"]},
            actor_id="owner@example.com",
        )
        projects = [{"id": "project-1", "name": "Riverside Residence", "status": "ACTIVE"}]
        profile = SimpleNamespace(is_active=True, line_uid="U123")
        runtime_settings = SimpleNamespace(frontend_base_url="https://example.test")

        with (
            patch.object(
                daily_report_notification_service,
                "get_settings",
                return_value=runtime_settings,
            ),
            patch.object(
                daily_report_notification_service,
                "get_subcontractor",
                return_value=profile,
            ),
            patch.object(
                daily_report_notification_service,
                "_send_line_text",
                new=AsyncMock(),
            ) as send_line,
        ):
            first = asyncio.run(
                daily_report_notification_service.run_due_action_scan(
                    projects=projects,
                    fallback_project_subcontractors={},
                    now=datetime(2026, 7, 20, 9, 0, tzinfo=UTC),
                )
            )
            repeated = asyncio.run(
                daily_report_notification_service.run_due_action_scan(
                    projects=projects,
                    fallback_project_subcontractors={},
                    now=datetime(2026, 7, 20, 9, 1, tzinfo=UTC),
                )
            )
            overdue = asyncio.run(
                daily_report_notification_service.run_due_action_scan(
                    projects=projects,
                    fallback_project_subcontractors={},
                    now=datetime(2026, 7, 20, 10, 15, tzinfo=UTC),
                )
            )

        self.assertEqual(first["notifications_sent"], 1)
        self.assertEqual(repeated["notifications_sent"], 0)
        self.assertEqual(repeated["notifications_skipped"], 1)
        self.assertEqual(overdue["notifications_sent"], 1)
        self.assertEqual(overdue["overdue_alerts_created"], 1)
        self.assertEqual(send_line.await_count, 2)
        cycle = daily_report_service.get_daily_cycle(
            project_id="project-1",
            report_date="2026-07-20",
        )
        self.assertEqual(cycle["status"], "OVERDUE")
        staff_alerts = daily_report_service.list_staff_notifications(project_ids={"project-1"})
        self.assertEqual(staff_alerts[0]["notification_type"], "MISSING_SUBMISSIONS")

    def test_due_scanner_skips_no_work_dates(self):
        daily_report_service.update_project_settings(
            project_id="project-1",
            updates={"enabled": True},
            actor_id="owner@example.com",
        )
        daily_report_service.set_no_work_day(
            project_id="project-1",
            report_date="2026-07-20",
            reason="หยุดงานตามแผน",
            actor_id="admin@example.com",
            actor_role="admin",
        )
        runtime_settings = SimpleNamespace(frontend_base_url="https://example.test")
        with patch.object(
            daily_report_notification_service,
            "get_settings",
            return_value=runtime_settings,
        ):
            result = asyncio.run(
                daily_report_notification_service.run_due_action_scan(
                    projects=[{"id": "project-1", "name": "Riverside Residence"}],
                    fallback_project_subcontractors={"project-1": ["sub-1"]},
                    now=datetime(2026, 7, 20, 9, 0, tzinfo=UTC),
                )
            )
        self.assertEqual(result["cycles_ready"], 0)
        self.assertEqual(result["projects_skipped"], 1)

    def test_due_scanner_skips_unconfigured_disabled_and_completed_projects(self):
        daily_report_service.update_project_settings(
            project_id="disabled-project",
            updates={"enabled": False},
            actor_id="owner@example.com",
        )
        runtime_settings = SimpleNamespace(frontend_base_url="https://example.test")
        with patch.object(
            daily_report_notification_service,
            "get_settings",
            return_value=runtime_settings,
        ):
            result = asyncio.run(
                daily_report_notification_service.run_due_action_scan(
                    projects=[
                        {"id": "unconfigured-project", "name": "Unconfigured"},
                        {"id": "disabled-project", "name": "Disabled"},
                        {
                            "id": "completed-project",
                            "name": "Completed",
                            "status": "COMPLETED",
                        },
                    ],
                    fallback_project_subcontractors={},
                    now=datetime(2026, 7, 20, 9, 0, tzinfo=UTC),
                )
            )
        self.assertEqual(result["projects_checked"], 0)
        self.assertEqual(result["projects_skipped"], 3)
        self.assertEqual(result["cycles_ready"], 0)

    def test_draft_and_review_alerts_do_not_publish_report(self):
        self._submitted_source()
        daily_report_service.update_project_settings(
            project_id="project-1",
            updates={"expected_subcontractor_ids": ["sub-1"]},
            actor_id="owner@example.com",
        )
        runtime_settings = SimpleNamespace(frontend_base_url="https://example.test")
        projects = [{"id": "project-1", "name": "Riverside Residence"}]
        with patch.object(
            daily_report_notification_service,
            "get_settings",
            return_value=runtime_settings,
        ):
            draft_result = asyncio.run(
                daily_report_notification_service.run_due_action_scan(
                    projects=projects,
                    fallback_project_subcontractors={},
                    now=datetime(2026, 7, 18, 11, 0, tzinfo=UTC),
                )
            )
            review_result = asyncio.run(
                daily_report_notification_service.run_due_action_scan(
                    projects=projects,
                    fallback_project_subcontractors={},
                    now=datetime(2026, 7, 18, 12, 0, tzinfo=UTC),
                )
            )

        self.assertEqual(draft_result["draft_alerts_created"], 1)
        self.assertEqual(review_result["review_alerts_created"], 1)
        report = daily_report_service.list_reports(project_ids={"project-1"})[0]
        self.assertEqual(report["status"], "PENDING_REVIEW")
        self.assertIsNone(report["published_at"])
        cycle = daily_report_service.get_daily_cycle(
            project_id="project-1",
            report_date="2026-07-18",
        )
        self.assertEqual(cycle["status"], "PENDING_REVIEW")


if __name__ == "__main__":
    unittest.main()
