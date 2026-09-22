from __future__ import annotations

import os
from io import BytesIO
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import get_settings
from app.core.database import engine
from main import app


pytestmark = pytest.mark.skipif(
    not os.getenv("PHASE3_DATABASE_URL"),
    reason="PHASE3_DATABASE_URL isolated PostgreSQL target is required",
)
OWNER = {"X-Debug-Admin-Role": "owner"}
ADMIN = {"X-Debug-Admin-Role": "admin"}


def _key(label: str) -> str:
    return f"phase7-{label}-{uuid4()}"


def _photo() -> bytes:
    output = BytesIO()
    Image.new("RGB", (720, 480), "#c2a878").save(output, format="PNG")
    return output.getvalue()


def _project(client: TestClient) -> str:
    response = client.post(
        "/api/v1/projects",
        headers=OWNER,
        json={
            "name": f"Phase 7 composer {uuid4()}",
            "project_type": "COMMERCIAL",
            "overhead_percent": 0,
            "profit_percent": 0,
            "vat_percent": 7,
            "contingency_budget": 0,
            "status": "ACTIVE",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]["project_id"]


def test_composer_snapshot_center_and_media_ownership(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(get_settings(), "boq_v2_enabled", True)
    stored: dict[str, bytes] = {}

    async def fake_upload(**kwargs):
        key = f"gs://private-test/boq_quotation_media/{kwargs['media_id']}.jpg"
        stored[key] = kwargs["file_bytes"]
        return key

    async def fake_download(storage_key: str):
        return stored[storage_key]

    async def fake_signed(*, storage_key: str, expires_in_minutes: int):
        assert storage_key in stored
        return f"https://storage.example.invalid/{storage_key.rsplit('/', 1)[-1]}?ttl={expires_in_minutes}"

    monkeypatch.setattr(
        "app.services.boq_quotation_media_service.upload_boq_quotation_media",
        fake_upload,
    )
    monkeypatch.setattr(
        "app.services.boq_quotation_media_service.download_storage_key_bytes",
        fake_download,
    )
    monkeypatch.setattr(
        "app.services.boq_quotation_media_service.generate_signed_url_for_storage_key",
        fake_signed,
    )

    with TestClient(app) as client:
        project_id = _project(client)
        created = client.post(
            f"/api/v1/projects/{project_id}/boq/documents",
            headers={**OWNER, "Idempotency-Key": _key("create")},
            json={},
        )
        assert created.status_code == 201, created.text
        draft = created.json()["data"]
        assert [
            item["section_type"] for item in draft["quotation"]["document_sections"]
        ] == [
            "SUMMARY",
            "DETAILED_BOQ",
            "VISUAL",
            "PAYMENT_TERMS",
            "TERMS",
            "ACCEPTANCE",
        ]

        admin_upload = client.post(
            f"/api/v1/boq/revisions/{draft['revision_id']}/media",
            headers=ADMIN,
            data={"expected_version": draft["version"]},
            files={"file": ("site.png", _photo(), "image/png")},
        )
        assert admin_upload.status_code == 403

        invalid_type = client.post(
            f"/api/v1/boq/revisions/{draft['revision_id']}/media",
            headers=OWNER,
            data={"expected_version": draft["version"]},
            files={"file": ("site.txt", _photo(), "text/plain")},
        )
        assert invalid_type.status_code == 415

        corrupt = client.post(
            f"/api/v1/boq/revisions/{draft['revision_id']}/media",
            headers=OWNER,
            data={"expected_version": draft["version"]},
            files={"file": ("site.png", b"not-an-image", "image/png")},
        )
        assert corrupt.status_code == 422

        uploaded = client.post(
            f"/api/v1/boq/revisions/{draft['revision_id']}/media",
            headers=OWNER,
            data={"expected_version": draft["version"]},
            files={"file": ("site.png", _photo(), "image/png")},
        )
        assert uploaded.status_code == 201, uploaded.text
        media = uploaded.json()["data"]
        assert media["content_type"] == "image/jpeg"
        assert media["revision_version"] == draft["version"] + 1
        assert media["preview_url"].startswith("https://storage.example.invalid/")

        stale_save = client.patch(
            f"/api/v1/boq/revisions/{draft['revision_id']}",
            headers={**OWNER, "Idempotency-Key": _key("stale-save")},
            json={"expected_version": draft["version"], "nodes": []},
        )
        assert stale_save.status_code == 409
        assert stale_save.json()["detail"]["code"] == "STALE_BOQ_VERSION"

        other_project_id = _project(client)
        other_created = client.post(
            f"/api/v1/projects/{other_project_id}/boq/documents",
            headers={**OWNER, "Idempotency-Key": _key("other-create")},
            json={},
        ).json()["data"]
        other_sections = other_created["quotation"]["document_sections"]
        for section in other_sections:
            section.pop("id", None)
            if section["section_type"] == "VISUAL":
                section["enabled"] = True
        substituted = client.patch(
            f"/api/v1/boq/revisions/{other_created['revision_id']}",
            headers={**OWNER, "Idempotency-Key": _key("cross-project")},
            json={
                "expected_version": other_created["version"],
                "nodes": [],
                "quotation": {
                    "document_sections": other_sections,
                    "visual_pages": [
                        {
                            "position": 0,
                            "layout": "SINGLE",
                            "entries": [{"media_id": media["id"], "position": 0}],
                        }
                    ],
                },
            },
        )
        assert substituted.status_code == 422
        assert substituted.json()["detail"]["code"] == "QUOTATION_MEDIA_NOT_OWNED"

        current = client.get(
            f"/api/v1/boq/revisions/{draft['revision_id']}", headers=ADMIN
        ).json()["data"]
        sections = current["quotation"]["document_sections"]
        for section in sections:
            if section["section_type"] in {"VISUAL", "ACCEPTANCE"}:
                section["enabled"] = True
            section.pop("id", None)
        logical_id = str(uuid4())
        quotation = {
            "title": "งานปรับปรุง / Renovation",
            "customer_name": "บริษัท ลูกค้าทดสอบ จำกัด",
            "customer_address": "Bangkok",
            "customer_tax_id": "0105559999999",
            "customer_contact": "Demo contact",
            "quotation_date": "2026-09-22",
            "valid_until": "2026-10-22",
            "currency": "THB",
            "vat_rate": "7.0000",
            "discount_type": "NONE",
            "discount_value": "0.0000",
            "payment_schedule": [{"label": "ชำระเต็มจำนวน", "percentage": "100.0000"}],
            "commercial_terms": ["ยืนราคา 30 วัน"],
            "document_pages": ["BOQ", "PAYMENT_TERMS", "COMMERCIAL_TERMS"],
            "document_schema_version": "boq-v2-document-snapshot-v2",
            "document_sections": sections,
            "visual_pages": [
                {
                    "position": 0,
                    "layout": "SINGLE",
                    "title_th": "รูปหน้างาน",
                    "title_en": "Site condition",
                    "entries": [
                        {
                            "media_id": media["id"],
                            "position": 0,
                            "scope_logical_id": logical_id,
                            "caption_th": "ก่อนเริ่มงาน",
                            "caption_en": "Before construction",
                        }
                    ],
                }
            ],
        }
        saved = client.patch(
            f"/api/v1/boq/revisions/{draft['revision_id']}",
            headers={**OWNER, "Idempotency-Key": _key("save")},
            json={
                "expected_version": current["version"],
                "quotation": quotation,
                "nodes": [
                    {
                        "logical_id": logical_id,
                        "parent_logical_id": None,
                        "node_kind": "ITEM",
                        "inclusion_state": "REQUIRED",
                        "position": 0,
                        "item_code": "P7-001",
                        "description": "งานพื้น",
                        "specification": "SPC",
                        "quantity": "10.0000",
                        "unit": "m²",
                        "sell_material_unit_rate": "100.0000",
                        "sell_labor_unit_rate": "20.0000",
                        "components": [
                            {
                                "component_type": "MATERIAL",
                                "cost_state": "PRICED",
                                "unit_rate": "70.0000",
                            },
                            {
                                "component_type": "LABOR",
                                "cost_state": "PRICED",
                                "unit_rate": "10.0000",
                            },
                        ],
                    }
                ],
            },
        )
        assert saved.status_code == 200, saved.text
        saved_data = saved.json()["data"]
        assert len(saved_data["quotation"]["visual_pages"]) == 1

        in_use = client.request(
            "DELETE",
            f"/api/v1/boq/revisions/{draft['revision_id']}/media/{media['id']}",
            headers=OWNER,
            json={"expected_version": saved_data["version"]},
        )
        assert in_use.status_code == 409
        assert in_use.json()["detail"]["code"] == "QUOTATION_MEDIA_IN_USE"

        preview = client.post(
            f"/api/v1/boq/revisions/{draft['revision_id']}/preview-snapshots",
            headers={**OWNER, "Idempotency-Key": _key("preview")},
            json={"expected_version": saved_data["version"]},
        )
        assert preview.status_code == 201, preview.text
        document = preview.json()["data"]["document"]
        assert document["schema_version"] == "boq-v2-document-snapshot-v2"
        assert document["composition"]["media_assets"][0]["sha256"] == media["sha256"]
        assert "storage_key" not in document["composition"]["media_assets"][0]

        listing = client.get("/api/v1/boq/quotations?search=Phase%207", headers=ADMIN)
        assert listing.status_code == 200, listing.text
        assert listing.json()["data"]["total"] >= 1
        assert any(
            item["revision_id"] == draft["revision_id"]
            for item in listing.json()["data"]["items"]
        )
        client.portal.call(engine.dispose)
