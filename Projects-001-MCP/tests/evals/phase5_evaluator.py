"""Deterministic Phase 5 operations, Internal Chat and Admin evaluation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.tools.registry import TOOLS

MCP_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_PATH = MCP_ROOT / "tests/evals/golden-evaluation-set-v1.json"
FIXTURE_PATH = MCP_ROOT / "tests/fixtures/demo-sanitized.json"

PHASE5_CASE_IDS = ("G-014",)
PHASE5_TOOLS = {
    "get_system_health",
    "get_gcp_resource_summary",
    "get_cloud_run_status",
    "search_application_errors",
    "get_data_source_health",
    "get_processing_status",
}
FORBIDDEN_ERROR_KEYS = {
    "raw_log_query",
    "token",
    "authorization",
    "signed_url",
    "storage_path",
    "prompt",
    "document_body",
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _contains_key(value: Any, forbidden: set[str]) -> bool:
    if isinstance(value, dict):
        return any(key.casefold() in forbidden for key in value) or any(
            _contains_key(item, forbidden) for item in value.values()
        )
    if isinstance(value, list):
        return any(_contains_key(item, forbidden) for item in value)
    return False


def evaluate_phase5() -> dict[str, Any]:
    golden = _load(GOLDEN_PATH)
    fixture = _load(FIXTURE_PATH)
    cases = {item["id"]: item for item in golden["cases"]}
    implemented_tools = {tool.name for tool in TOOLS if tool.implemented}
    operations = fixture["phase5_operations"]
    controls = fixture["phase5_controls"]

    tool_inventory_complete = PHASE5_TOOLS.issubset(implemented_tools)
    no_out_of_scope_visibility = (
        controls["excluded_resources_omitted"]
        and operations["allowed_cloud_run_aliases"] == ["frontend", "backend", "mcp"]
    )
    operational_queries_safe = (
        controls["operational_log_view_locked"]
        and controls["operational_query_max_days"] == 30
        and controls["operational_errors_redacted"]
        and not _contains_key(operations["error_sample"], FORBIDDEN_ERROR_KEYS)
    )
    internal_chat_consistent = (
        controls["internal_chat_metrics"] == controls["external_mcp_metrics"]
        and controls["existing_chat_history_separate"]
    )
    admin_matrix = controls["admin_allow_deny_matrix"]
    admin_passed = sum(bool(value) for value in admin_matrix.values())
    admin_score = round(admin_passed * 100 / len(admin_matrix), 2)
    revocation_passed = controls["revocation_effective_next_call"]

    results = []
    for case_id in PHASE5_CASE_IDS:
        case = cases[case_id]
        missing_tools = sorted(set(case.get("expected_tools", [])) - implemented_tools)
        results.append(
            {
                "id": case_id,
                "passed": not missing_tools and operational_queries_safe,
                "missing_tools": missing_tools,
                "facts_passed": operational_queries_safe,
            }
        )
    passed_count = sum(item["passed"] for item in results)
    score = round(passed_count * 100 / len(results), 2)
    gate_passed = (
        score == 100.0
        and tool_inventory_complete
        and no_out_of_scope_visibility
        and operational_queries_safe
        and internal_chat_consistent
        and admin_score == 100.0
        and revocation_passed
    )
    return {
        "schema_version": "1.0",
        "dataset": golden["dataset"],
        "evaluated_case_ids": list(PHASE5_CASE_IDS),
        "evaluated_case_count": len(results),
        "passed_count": passed_count,
        "score_percent": score,
        "tool_inventory_complete": tool_inventory_complete,
        "no_out_of_scope_visibility": no_out_of_scope_visibility,
        "operational_queries_safe": operational_queries_safe,
        "internal_chat_consistent": internal_chat_consistent,
        "admin_matrix_score_percent": admin_score,
        "revocation_passed": revocation_passed,
        "gate_passed": gate_passed,
        "cases": results,
    }


if __name__ == "__main__":
    print(json.dumps(evaluate_phase5(), ensure_ascii=False, indent=2))
