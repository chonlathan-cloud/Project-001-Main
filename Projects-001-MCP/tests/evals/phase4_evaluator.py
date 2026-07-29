"""Deterministic Phase 4 Project Operations and Product Audit evaluation."""

from __future__ import annotations

import json
import re
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.tools.registry import TOOLS

MCP_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_PATH = MCP_ROOT / "tests/evals/golden-evaluation-set-v1.json"
FIXTURE_PATH = MCP_ROOT / "tests/fixtures/demo-sanitized.json"

PHASE4_CASE_IDS = ("G-010", "G-011", "G-012", "G-013", "G-015", "C-001")
MONEY_PATTERN = re.compile(r"^-?\d+\.\d{2}$")
FORBIDDEN_AUDIT_KEYS = {"document_body", "prompt", "response_body", "content"}
FORBIDDEN_DAILY_KEYS = {"share_token", "share_url", "signed_url", "storage_key"}


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


def evaluate_phase4() -> dict[str, Any]:
    golden = _load(GOLDEN_PATH)
    fixture = _load(FIXTURE_PATH)
    cases = {item["id"]: item for item in golden["cases"]}
    implemented_tools = {tool.name for tool in TOOLS if tool.implemented}
    controls = fixture["phase4_controls"]

    inspection_safe = any(
        item["status"] != "RESOLVED" and item["overdue"]
        for item in fixture["inspection_items"]
    )
    daily_safe = (
        all(
            version["immutable"]
            for report in fixture["daily_reports"]
            for version in report["versions"]
        )
        and not _contains_key(fixture["daily_reports"], FORBIDDEN_DAILY_KEYS)
        and controls["daily_report_share_tokens_omitted"]
    )
    totals = fixture["dashboard"]["totals"]
    dashboard_exact = (
        all(MONEY_PATTERN.fullmatch(value["amount"]) for value in totals.values())
        and Decimal(totals["remaining"]["amount"])
        == Decimal(totals["budget"]["amount"]) - Decimal(totals["actual"]["amount"])
        and bool(fixture["dashboard"]["calculation_method"])
        and len(fixture["dashboard"]["sources"]) >= 3
    )
    audit_safe = (
        not _contains_key(fixture["audit_events"], FORBIDDEN_AUDIT_KEYS)
        and controls["audit_body_and_prompt_omitted"]
        and controls["audit_read_requires_permission"]
        and controls["sensitive_audit_read_fails_closed"]
    )
    no_silent_merge = (
        controls["partial_source_failures_are_explicit"]
        and controls["backend_is_primary_for_business_calculations"]
        and controls["cross_domain_sources_remain_distinct"]
    )
    fact_checks = {
        "G-010": inspection_safe,
        "G-011": daily_safe,
        "G-012": dashboard_exact,
        "G-013": audit_safe,
        "G-015": no_silent_merge,
        "C-001": controls["source_inconsistency_warning"] == "SOURCE_INCONSISTENCY"
        and controls["backend_is_primary_for_business_calculations"],
    }

    results = []
    for case_id in PHASE4_CASE_IDS:
        case = cases[case_id]
        missing_tools = sorted(set(case.get("expected_tools", [])) - implemented_tools)
        results.append(
            {
                "id": case_id,
                "passed": not missing_tools and fact_checks[case_id],
                "missing_tools": missing_tools,
                "facts_passed": fact_checks[case_id],
            }
        )
    passed_count = sum(item["passed"] for item in results)
    score = round(passed_count * 100 / len(results), 2)
    gate_passed = (
        score == 100.0
        and inspection_safe
        and daily_safe
        and dashboard_exact
        and audit_safe
        and no_silent_merge
        and controls["operations_p95_target_seconds"] <= 15
    )
    return {
        "schema_version": "1.0",
        "dataset": golden["dataset"],
        "evaluated_case_ids": list(PHASE4_CASE_IDS),
        "evaluated_case_count": len(results),
        "passed_count": passed_count,
        "score_percent": score,
        "inspection_fixture_safe": inspection_safe,
        "daily_report_fixture_safe": daily_safe,
        "dashboard_fixture_exact": dashboard_exact,
        "audit_fixture_safe": audit_safe,
        "no_silent_conflict_merge": no_silent_merge,
        "operations_p95_target_seconds": controls["operations_p95_target_seconds"],
        "gate_passed": gate_passed,
        "cases": results,
    }


if __name__ == "__main__":
    print(json.dumps(evaluate_phase4(), ensure_ascii=False, indent=2))
