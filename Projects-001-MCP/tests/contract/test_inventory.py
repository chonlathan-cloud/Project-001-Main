from __future__ import annotations

import json
from pathlib import Path

from app.tools.registry import TOOLS

ROOT = Path(__file__).resolve().parents[2]


def test_all_inventory_tools_have_closed_input_schemas() -> None:
    contract = json.loads((ROOT / "contracts/tool-input-schemas-v1.json").read_text())
    schemas = contract["tools"]
    assert set(schemas) == {tool.name for tool in TOOLS}
    assert len(schemas) == 37
    for name, schema in schemas.items():
        assert schema["type"] == "object", name
        assert schema["additionalProperties"] is False, name
        assert "environment" not in schema.get("properties", {}), name


def test_forbidden_generic_tools_are_absent() -> None:
    names = {tool.name for tool in TOOLS}
    forbidden = {
        "execute_sql",
        "query_firestore_path",
        "read_gcs_path",
        "get_secret_value",
        "list_all_iam",
        "run_gcloud",
    }
    assert names.isdisjoint(forbidden)


def test_foundation_core_pilot_and_phase3_tools_are_implemented() -> None:
    assert {tool.name for tool in TOOLS if tool.implemented} == {
        "get_system_catalog",
        "describe_domain",
        "get_current_access",
        "search",
        "fetch",
        "list_projects",
        "get_project",
        "get_project_summary",
        "get_boq_current",
        "list_boq_versions",
        "get_boq_version",
        "compare_boq_versions",
        "list_project_access",
        "get_user_access",
        "get_project_financial_summary",
        "search_financial_records",
        "get_payment",
        "get_payment_document_status",
        "search_documents",
        "get_document_metadata",
        "read_document_content",
    }
