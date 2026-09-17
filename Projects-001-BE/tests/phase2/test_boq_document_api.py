from __future__ import annotations

import asyncio
import os
from uuid import UUID, uuid4

import asyncpg
import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from main import app


pytestmark = pytest.mark.skipif(
    not os.getenv("PHASE2_DATABASE_URL"),
    reason="PHASE2_DATABASE_URL isolated PostgreSQL target is required",
)


OWNER_HEADERS = {"X-Debug-Admin-Role": "owner"}
ADMIN_HEADERS = {"X-Debug-Admin-Role": "admin"}


def _idempotency(prefix: str) -> str:
    return f"phase2-{prefix}-{uuid4()}"


def _draft_node(node: dict[str, object]) -> dict[str, object]:
    components = []
    for component in node.get("components", []):
        components.append(
            {
                "id": component["id"],
                "component_type": component["component_type"],
                "quantity_basis": component["quantity_basis"],
                "quantity": (
                    component["quantity"]
                    if component["quantity_basis"] == "OVERRIDDEN"
                    else None
                ),
                "unit": component["unit"],
                "specification": component["specification"],
                "cost_state": component["cost_state"],
                "unit_rate": component["unit_rate"],
                "explicit_zero_reason": component["explicit_zero_reason"],
            }
        )
    return {
        "id": node["id"],
        "logical_id": node["logical_id"],
        "parent_logical_id": node["parent_logical_id"],
        "node_kind": node["node_kind"],
        "inclusion_state": node["inclusion_state"],
        "position": node["position"],
        "item_code": node["item_code"],
        "description": node["description"],
        "specification": node["specification"],
        "quantity": node["quantity"],
        "unit": node["unit"],
        "sell_material_unit_rate": node["sell_material_unit_rate"],
        "sell_labor_unit_rate": node["sell_labor_unit_rate"],
        "components": components,
    }


def test_native_boq_rollout_flag_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "boq_v2_enabled", False)
    with TestClient(app) as client:
        response = client.get(
            f"/api/v1/projects/{uuid4()}/boq-workspace",
            headers=OWNER_HEADERS,
        )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "BOQ_V2_ROLLOUT_DISABLED"


def test_native_boq_phase2_create_save_reload_copy_reorder_and_roles() -> None:
    with TestClient(app) as client:
        project_response = client.post(
            "/api/v1/projects",
            headers=OWNER_HEADERS,
            json={
                "name": f"Phase 2 Integration {uuid4()}",
                "project_type": "COMMERCIAL",
                "overhead_percent": 0,
                "profit_percent": 0,
                "vat_percent": 7,
                "contingency_budget": 25000,
                "status": "ACTIVE",
            },
        )
        assert project_response.status_code == 200, project_response.text
        project_id = project_response.json()["data"]["project_id"]

        empty_workspace = client.get(
            f"/api/v1/projects/{project_id}/boq-workspace",
            headers=ADMIN_HEADERS,
        )
        assert empty_workspace.status_code == 200, empty_workspace.text
        assert empty_workspace.json()["data"] == {
            **empty_workspace.json()["data"],
            "active_source_kind": "LEGACY",
            "legacy_available": False,
            "legacy_row_count": 0,
            "can_edit": False,
        }

        admin_create = client.post(
            f"/api/v1/projects/{project_id}/boq/documents",
            headers={**ADMIN_HEADERS, "Idempotency-Key": _idempotency("admin")},
            json={},
        )
        assert admin_create.status_code == 403

        create_key = _idempotency("create")
        create_response = client.post(
            f"/api/v1/projects/{project_id}/boq/documents",
            headers={**OWNER_HEADERS, "Idempotency-Key": create_key},
            json={},
        )
        assert create_response.status_code == 201, create_response.text
        created = create_response.json()["data"]
        revision_id = created["revision_id"]
        assert created["status"] == "DRAFT"
        assert created["version"] == 1
        assert created["nodes"] == []

        duplicate_create = client.post(
            f"/api/v1/projects/{project_id}/boq/documents",
            headers={**OWNER_HEADERS, "Idempotency-Key": create_key},
            json={},
        )
        assert duplicate_create.status_code == 201
        assert duplicate_create.json()["data"]["revision_id"] == revision_id

        section_id = str(uuid4())
        category_id = str(uuid4())
        priced_item_id = str(uuid4())
        free_item_id = str(uuid4())
        orphan_response = client.patch(
            f"/api/v1/boq/revisions/{revision_id}",
            headers={**OWNER_HEADERS, "Idempotency-Key": _idempotency("orphan")},
            json={
                "expected_version": 1,
                "nodes": [
                    {
                        "logical_id": priced_item_id,
                        "parent_logical_id": str(uuid4()),
                        "node_kind": "ITEM",
                        "position": 0,
                    }
                ],
            },
        )
        assert orphan_response.status_code == 422
        assert orphan_response.json()["detail"]["code"] == "ORPHAN_SCOPE_NODE"

        first_save_payload = {
            "expected_version": 1,
            "nodes": [
                {
                    "logical_id": section_id,
                    "parent_logical_id": None,
                    "node_kind": "SECTION",
                    "inclusion_state": "REQUIRED",
                    "position": 0,
                    "description": "งานระบบ",
                },
                {
                    "logical_id": category_id,
                    "parent_logical_id": section_id,
                    "node_kind": "CATEGORY",
                    "inclusion_state": "REQUIRED",
                    "position": 0,
                    "description": "ระบบปรับอากาศ",
                },
                {
                    "logical_id": priced_item_id,
                    "parent_logical_id": category_id,
                    "node_kind": "ITEM",
                    "inclusion_state": "REQUIRED",
                    "position": 0,
                    "item_code": "AC-001",
                    "description": "เครื่องปรับอากาศ",
                    "quantity": "10.0000",
                    "unit": "ชุด",
                    "sell_material_unit_rate": "700.0000",
                    "sell_labor_unit_rate": "0.0000",
                    "components": [
                        {
                            "component_type": "MATERIAL",
                            "quantity_basis": "INHERITED",
                            "cost_state": "PRICED",
                            "unit_rate": "500.0000",
                        },
                        {
                            "component_type": "LABOR",
                            "quantity_basis": "INHERITED",
                            "cost_state": "NOT_APPLICABLE",
                        },
                    ],
                },
                {
                    "logical_id": free_item_id,
                    "parent_logical_id": category_id,
                    "node_kind": "ITEM",
                    "inclusion_state": "REQUIRED",
                    "position": 1,
                    "item_code": "AC-FOC",
                    "description": "งานบริการฟรีสำหรับลูกค้า",
                    "quantity": "1.0000",
                    "unit": "งาน",
                    "sell_material_unit_rate": "0.0000",
                    "sell_labor_unit_rate": "0.0000",
                    "components": [
                        {
                            "component_type": "MATERIAL",
                            "quantity_basis": "INHERITED",
                            "cost_state": "UNKNOWN",
                        },
                        {
                            "component_type": "LABOR",
                            "quantity_basis": "INHERITED",
                            "cost_state": "NOT_APPLICABLE",
                        },
                    ],
                },
            ],
        }
        first_save_key = _idempotency("save")
        first_save = client.patch(
            f"/api/v1/boq/revisions/{revision_id}",
            headers={**OWNER_HEADERS, "Idempotency-Key": first_save_key},
            json=first_save_payload,
        )
        assert first_save.status_code == 200, first_save.text
        saved = first_save.json()["data"]
        assert saved["version"] == 2
        assert saved["net_sell_ex_vat"] == "7000.00"
        assert saved["known_estimated_cost"] == "5000.00"
        assert saved["forecast_cost"] is None
        assert saved["forecast_margin"] is None
        assert saved["completeness"]["state"] == "INCOMPLETE"
        assert saved["completeness"]["required_count"] == 2
        assert saved["completeness"]["priced_count"] == 1
        saved_by_kind = {node["node_kind"]: node for node in saved["nodes"]}
        assert saved_by_kind["SECTION"]["sell_total"] == "7000.00"
        assert saved_by_kind["CATEGORY"]["sell_total"] == "7000.00"

        idempotent_save = client.patch(
            f"/api/v1/boq/revisions/{revision_id}",
            headers={**OWNER_HEADERS, "Idempotency-Key": first_save_key},
            json=first_save_payload,
        )
        assert idempotent_save.status_code == 200
        assert idempotent_save.json()["data"]["version"] == 2

        conflicting_retry = client.patch(
            f"/api/v1/boq/revisions/{revision_id}",
            headers={**OWNER_HEADERS, "Idempotency-Key": first_save_key},
            json={**first_save_payload, "nodes": first_save_payload["nodes"][:-1]},
        )
        assert conflicting_retry.status_code == 409
        assert conflicting_retry.json()["detail"]["code"] == "IDEMPOTENCY_CONFLICT"

        stale_save = client.patch(
            f"/api/v1/boq/revisions/{revision_id}",
            headers={**OWNER_HEADERS, "Idempotency-Key": _idempotency("stale")},
            json=first_save_payload,
        )
        assert stale_save.status_code == 409
        assert stale_save.json()["detail"]["code"] == "STALE_BOQ_VERSION"
        assert stale_save.json()["detail"]["current_version"] == 2

        admin_save = client.patch(
            f"/api/v1/boq/revisions/{revision_id}",
            headers={**ADMIN_HEADERS, "Idempotency-Key": _idempotency("admin-save")},
            json={"expected_version": 2, "nodes": []},
        )
        assert admin_save.status_code == 403

        saved_nodes = [_draft_node(node) for node in saved["nodes"]]
        by_logical = {node["logical_id"]: node for node in saved_nodes}
        priced_free = by_logical[free_item_id]
        free_material = next(
            item
            for item in priced_free["components"]
            if item["component_type"] == "MATERIAL"
        )
        free_material.update(
            {
                "cost_state": "PRICED",
                "unit_rate": "0.0000",
                "explicit_zero_reason": "บริการรับประกันโดยไม่มีต้นทุนเพิ่ม",
            }
        )
        by_logical[priced_item_id]["position"] = 1
        priced_free["position"] = 0
        second_save = client.patch(
            f"/api/v1/boq/revisions/{revision_id}",
            headers={**OWNER_HEADERS, "Idempotency-Key": _idempotency("reorder")},
            json={"expected_version": 2, "nodes": list(by_logical.values())},
        )
        assert second_save.status_code == 200, second_save.text
        reordered = second_save.json()["data"]
        assert reordered["version"] == 3
        assert reordered["forecast_cost"] == "5000.00"
        assert reordered["forecast_margin"] == "2000.00"
        assert reordered["completeness"]["state"] == "COMPLETE"

        reloaded = client.get(
            f"/api/v1/boq/revisions/{revision_id}", headers=ADMIN_HEADERS
        )
        assert reloaded.status_code == 200
        reloaded_nodes = reloaded.json()["data"]["nodes"]
        reloaded_items = [node for node in reloaded_nodes if node["node_kind"] == "ITEM"]
        assert [node["logical_id"] for node in reloaded_items] == [
            free_item_id,
            priced_item_id,
        ]
        assert {node["logical_id"]: node["id"] for node in reloaded_nodes} == {
            node["logical_id"]: node["id"] for node in saved["nodes"]
        }

        copy_response = client.post(
            f"/api/v1/projects/{project_id}/boq/revisions/{revision_id}/copy",
            headers={**OWNER_HEADERS, "Idempotency-Key": _idempotency("copy")},
        )
        assert copy_response.status_code == 201, copy_response.text
        copied = copy_response.json()["data"]
        assert copied["revision_id"] != revision_id
        assert copied["predecessor_revision_id"] == revision_id
        assert copied["version"] == 1
        assert copied["net_sell_ex_vat"] == "7000.00"
        assert {node["logical_id"] for node in copied["nodes"]} == {
            node["logical_id"] for node in reloaded_nodes
        }
        assert {node["id"] for node in copied["nodes"]}.isdisjoint(
            {node["id"] for node in reloaded_nodes}
        )

        final_workspace = client.get(
            f"/api/v1/projects/{project_id}/boq-workspace",
            headers=OWNER_HEADERS,
        )
        assert final_workspace.status_code == 200
        workspace = final_workspace.json()["data"]
        assert workspace["can_edit"] is True
        assert workspace["active_source_kind"] == "LEGACY"
        assert len(workspace["revisions"]) == 2

        async def operational_rows() -> tuple[int, int]:
            database_url = os.environ["PHASE2_DATABASE_URL"].replace(
                "postgresql+asyncpg://", "postgresql://", 1
            )
            connection = await asyncpg.connect(database_url)
            try:
                source_count = await connection.fetchval(
                    "SELECT count(*) FROM boq_v2_project_budget_sources "
                    "WHERE project_id = $1",
                    UUID(project_id),
                )
                baseline_count = await connection.fetchval(
                    "SELECT count(*) FROM boq_v2_project_baselines "
                    "WHERE project_id = $1",
                    UUID(project_id),
                )
                return int(source_count), int(baseline_count)
            finally:
                await connection.close()

        assert asyncio.run(operational_rows()) == (0, 0)
