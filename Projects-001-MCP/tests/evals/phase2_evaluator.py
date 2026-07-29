"""Deterministic Phase 2 Golden and exact BOQ fixture evaluation."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

MCP_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_PATH = MCP_ROOT / "tests/evals/golden-evaluation-set-v1.json"
FIXTURE_PATH = MCP_ROOT / "tests/fixtures/demo-sanitized.json"
TOOL_SCHEMA_PATH = MCP_ROOT / "contracts/tool-input-schemas-v1.json"

PHASE2_CORE_CASE_IDS = (
    "G-001-th",
    "G-001-en",
    "G-003",
    "G-004",
    "G-005",
    "G-009",
)
MONEY_PATTERN = re.compile(r"^-?\d+\.\d{2}$")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _version_diff(
    version_a: dict[str, Any],
    version_b: dict[str, Any],
) -> dict[str, list[str]]:
    lines_a = {item["line_id"]: item for item in version_a["lines"]}
    lines_b = {item["line_id"]: item for item in version_b["lines"]}
    shared = lines_a.keys() & lines_b.keys()
    return {
        "added": sorted(lines_b.keys() - lines_a.keys()),
        "removed": sorted(lines_a.keys() - lines_b.keys()),
        "changed": sorted(key for key in shared if lines_a[key] != lines_b[key]),
    }


def _boq_fixture_is_exact(versions: list[dict[str, Any]]) -> bool:
    if not versions or sum(item["valid_to"] is None for item in versions) != 1:
        return False
    ordered = sorted(versions, key=lambda item: item["version_number"])
    if len({item["version_id"] for item in ordered}) != len(ordered):
        return False
    if len({item["version_number"] for item in ordered}) != len(ordered):
        return False
    for current, following in zip(ordered, ordered[1:], strict=False):
        if current["valid_to"] != following["valid_from"]:
            return False
    for version in ordered:
        lines = version["lines"]
        if len({item["line_id"] for item in lines}) != len(lines):
            return False
        if any(not MONEY_PATTERN.fullmatch(item["amount"]) for item in lines):
            return False
    return True


def evaluate_phase2() -> dict[str, Any]:
    golden = _load_json(GOLDEN_PATH)
    fixture = _load_json(FIXTURE_PATH)
    tool_contract = _load_json(TOOL_SCHEMA_PATH)
    implemented_tools = set(tool_contract["tools"])
    cases = {item["id"]: item for item in golden["cases"]}
    versions = fixture["boq_versions"]
    versions_by_id = {item["version_id"]: item for item in versions}
    current = next(item for item in versions if item["valid_to"] is None)
    as_of = _timestamp("2026-06-15T00:00:00Z")
    as_of_version = max(
        (item for item in versions if _timestamp(item["valid_from"]) <= as_of),
        key=lambda item: _timestamp(item["valid_from"]),
    )
    diff = _version_diff(versions_by_id["boq-v3"], versions_by_id["boq-v4"])

    fact_checks = {
        "G-003": current["version_id"] == cases["G-003"]["expected_facts"]["version_id"],
        "G-004": diff == cases["G-004"]["expected_facts"],
        "G-005": (
            as_of_version["version_id"]
            == cases["G-005"]["expected_facts"]["version_id"]
        ),
    }
    case_results: list[dict[str, Any]] = []
    for case_id in PHASE2_CORE_CASE_IDS:
        case = cases[case_id]
        missing_tools = sorted(set(case.get("expected_tools", [])) - implemented_tools)
        facts_passed = fact_checks.get(case_id, True)
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
    boq_fixture_exact = _boq_fixture_is_exact(versions)
    return {
        "schema_version": "1.0",
        "dataset": golden["dataset"],
        "evaluated_case_ids": list(PHASE2_CORE_CASE_IDS),
        "evaluated_case_count": len(case_results),
        "passed_count": passed_count,
        "score_percent": score_percent,
        "release_threshold_percent": 95.0,
        "boq_fixture_exact": boq_fixture_exact,
        "gate_passed": score_percent >= 95.0 and boq_fixture_exact,
        "cases": case_results,
    }


if __name__ == "__main__":
    print(json.dumps(evaluate_phase2(), ensure_ascii=False, indent=2))
