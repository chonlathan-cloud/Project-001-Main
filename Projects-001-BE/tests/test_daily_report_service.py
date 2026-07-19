from __future__ import annotations

from copy import deepcopy
from datetime import date
from itertools import count
import unittest
from unittest.mock import patch

from app.services import daily_report_service


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

    def _submitted_source(self):
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


if __name__ == "__main__":
    unittest.main()
