"""Deterministic Phase 3 Finance and Document Gateway evaluation."""

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

PHASE3_CASE_IDS = ("G-006", "G-007", "G-008", "S-004", "F-002")
MONEY_PATTERN = re.compile(r"^-?\d+\.\d{2}$")
PROMPT_INJECTION_PATTERN = re.compile(
    r"ignore\s+(all\s+)?(previous|prior|system)\s+instructions?",
    re.IGNORECASE,
)
FORBIDDEN_DOCUMENT_KEYS = {
    "bucket",
    "gcs_path",
    "signed_url",
    "storage_key",
    "token",
}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _finance_fixture_is_exact(finance: dict[str, Any]) -> bool:
    money_fields = (
        "budget",
        "actual",
        "paid",
        "remaining",
        "approved_unpaid",
        "pending_requested",
    )
    if any(not MONEY_PATTERN.fullmatch(str(finance.get(field, ""))) for field in money_fields):
        return False
    return (
        Decimal(finance["remaining"])
        == Decimal(finance["budget"]) - Decimal(finance["actual"])
        and Decimal(finance["approved_unpaid"])
        == Decimal(finance["actual"]) - Decimal(finance["paid"])
    )


def _document_gateway_is_safe(fixture: dict[str, Any]) -> bool:
    documents = fixture["documents"]
    controls = fixture["phase3_controls"]
    safe = next(item for item in documents if not item["external_ai_blocked"])
    blocked = next(item for item in documents if item["external_ai_blocked"])
    serialized = json.dumps(fixture, sort_keys=True).lower()
    control_values_are_safe = all(
        controls[key]
        for key in (
            "sensitive_audit_fail_closed",
            "document_content_is_untrusted",
            "credential_redaction_enabled",
            "storage_paths_and_signed_urls_omitted",
        )
    )
    statuses_are_explicit = {
        controls["unsupported_content_status"],
        controls["large_content_status"],
        controls["unprocessed_content_status"],
    } == {"unsupported", "too_large", "unprocessed"}
    no_forbidden_keys = not any(
        f'"{key}"' in serialized for key in FORBIDDEN_DOCUMENT_KEYS
    )
    return (
        bool(PROMPT_INJECTION_PATTERN.search(safe["content"]))
        and "must never be returned" in blocked["content"].lower()
        and control_values_are_safe
        and statuses_are_explicit
        and no_forbidden_keys
    )


def evaluate_phase3() -> dict[str, Any]:
    golden = _load_json(GOLDEN_PATH)
    fixture = _load_json(FIXTURE_PATH)
    cases = {item["id"]: item for item in golden["cases"]}
    implemented_tools = {tool.name for tool in TOOLS if tool.implemented}
    finance_exact = _finance_fixture_is_exact(fixture["finance"])
    document_safe = _document_gateway_is_safe(fixture)
    fact_checks = {
        "G-006": all(
            fixture["finance"].get(key) == value
            for key, value in cases["G-006"]["expected_facts"].items()
        ),
        "G-007": finance_exact,
        "G-008": document_safe,
        "S-004": document_safe,
        "F-002": bool(fixture["phase3_controls"]["sensitive_audit_fail_closed"]),
    }

    case_results: list[dict[str, Any]] = []
    for case_id in PHASE3_CASE_IDS:
        case = cases[case_id]
        missing_tools = sorted(set(case.get("expected_tools", [])) - implemented_tools)
        facts_passed = fact_checks[case_id]
        case_results.append(
            {
                "id": case_id,
                "passed": not missing_tools and facts_passed,
                "missing_tools": missing_tools,
                "facts_passed": facts_passed,
            }
        )

    passed_count = sum(item["passed"] for item in case_results)
    score_percent = round(passed_count * 100 / len(case_results), 2)
    gate_passed = (
        score_percent == 100.0
        and finance_exact
        and document_safe
        and fixture["phase3_controls"]["sensitive_audit_fail_closed"]
    )
    return {
        "schema_version": "1.0",
        "dataset": golden["dataset"],
        "evaluated_case_ids": list(PHASE3_CASE_IDS),
        "evaluated_case_count": len(case_results),
        "passed_count": passed_count,
        "score_percent": score_percent,
        "finance_fixture_exact": finance_exact,
        "document_gateway_safe": document_safe,
        "sensitive_audit_fail_closed": fixture["phase3_controls"][
            "sensitive_audit_fail_closed"
        ],
        "gate_passed": gate_passed,
        "cases": case_results,
    }


if __name__ == "__main__":
    print(json.dumps(evaluate_phase3(), ensure_ascii=False, indent=2))
