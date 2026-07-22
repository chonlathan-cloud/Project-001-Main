from __future__ import annotations

import asyncio
from copy import deepcopy
from itertools import count
import unittest
from unittest.mock import AsyncMock, patch

from app.api.deps.auth import AuthenticatedUser
from app.api.v1 import settings as settings_api
from app.schemas.profile_schema import UpdateCustomerProfileRequest
from app.services import daily_report_service, identity_service


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


class SettingsCustomerTests(unittest.TestCase):
    def setUp(self):
        self.firestore = FakeFirestore()
        self.identity_patch = patch.object(
            identity_service,
            "get_firestore_client",
            return_value=self.firestore,
        )
        self.membership_patch = patch.object(
            daily_report_service,
            "_client",
            return_value=self.firestore,
        )
        self.identity_patch.start()
        self.membership_patch.start()
        self.owner = AuthenticatedUser(
            subject="owner@example.com",
            role="owner",
            roles=("owner",),
            email="owner@example.com",
        )
        self.inspector = AuthenticatedUser(
            subject="inspector@example.com",
            role="inspector",
            roles=("inspector",),
            email="inspector@example.com",
        )

    def tearDown(self):
        self.membership_patch.stop()
        self.identity_patch.stop()

    def _create_customer(
        self,
        *,
        customer_id: str = "customer-1",
        line_uid: str = "line-user-1",
        name: str = "Riverside Client",
    ):
        return identity_service.create_customer_profile(
            customer_id=customer_id,
            email=None,
            line_uid=line_uid,
            line_picture_url="https://example.com/customer.jpg",
            name=name,
            first_name="Narin",
            nickname="Rin",
            contact_name="Narin Customer",
            phone=None,
        )

    def test_customer_directory_item_includes_active_project_memberships(self):
        customer = self._create_customer()
        daily_report_service.upsert_project_membership(
            project_id="project-1",
            principal_type="customer",
            principal_id=customer.id,
            is_active=True,
            actor_id=self.owner.email or self.owner.subject,
        )

        item = settings_api._customer_item(customer)

        self.assertEqual(item.id, "customer-1")
        self.assertEqual(item.assigned_project_ids, ["project-1"])
        self.assertEqual(item.contact_name, "Narin Customer")
        self.assertEqual(item.first_name, "Narin")
        self.assertEqual(item.nickname, "Rin")

    def test_update_customer_replaces_projects_and_preserves_line_identity(self):
        customer = self._create_customer()
        daily_report_service.upsert_project_membership(
            project_id="project-old",
            principal_type="customer",
            principal_id=customer.id,
            is_active=True,
            actor_id=self.owner.email or self.owner.subject,
        )
        request = UpdateCustomerProfileRequest(
            name="Riverside Owner Team",
            contact_name="Narin Updated",
            phone="0812345678",
            assigned_project_ids=["project-new"],
            is_active=False,
        )

        with patch.object(settings_api, "_validate_project_ids", new=AsyncMock()) as validator:
            response = asyncio.run(
                settings_api.update_customer(
                    customer.id,
                    request,
                    self.owner,
                    object(),
                )
            )

        validator.assert_awaited_once()
        self.assertEqual(response.data.name, "Riverside Owner Team")
        self.assertEqual(response.data.contact_name, "Narin Updated")
        self.assertEqual(response.data.phone, "0812345678")
        self.assertFalse(response.data.is_active)
        self.assertEqual(response.data.line_uid, "line-user-1")
        self.assertEqual(response.data.assigned_project_ids, ["project-new"])

    def test_reset_customer_line_keeps_profile_and_projects(self):
        customer = self._create_customer()
        daily_report_service.upsert_project_membership(
            project_id="project-1",
            principal_type="customer",
            principal_id=customer.id,
            is_active=True,
            actor_id=self.owner.email or self.owner.subject,
        )

        response = asyncio.run(settings_api.reset_customer_line(customer.id, self.owner))

        self.assertIsNone(response.data.line_uid)
        self.assertEqual(response.data.name, "Riverside Client")
        self.assertEqual(response.data.assigned_project_ids, ["project-1"])

    def test_inspector_customer_list_is_limited_to_assigned_projects(self):
        first = self._create_customer()
        second = self._create_customer(
            customer_id="customer-2",
            line_uid="line-user-2",
            name="Other Project Client",
        )
        for project_id, customer_id in [
            ("project-visible", first.id),
            ("project-hidden", first.id),
            ("project-hidden", second.id),
        ]:
            daily_report_service.upsert_project_membership(
                project_id=project_id,
                principal_type="customer",
                principal_id=customer_id,
                is_active=True,
                actor_id=self.owner.email or self.owner.subject,
            )
        daily_report_service.upsert_project_membership(
            project_id="project-visible",
            principal_type="admin",
            principal_id=self.inspector.email or "",
            is_active=True,
            actor_id=self.owner.email or self.owner.subject,
        )

        response = asyncio.run(settings_api.list_customers(self.inspector))

        self.assertEqual([item.id for item in response.data], ["customer-1"])
        self.assertEqual(response.data[0].assigned_project_ids, ["project-visible"])


if __name__ == "__main__":
    unittest.main()
