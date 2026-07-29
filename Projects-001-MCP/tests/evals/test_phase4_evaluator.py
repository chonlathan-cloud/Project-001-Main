from __future__ import annotations

from tests.evals.phase4_evaluator import evaluate_phase4


def test_phase4_project_operations_and_audit_gate_is_exact() -> None:
    report = evaluate_phase4()

    assert report["evaluated_case_count"] == 6
    assert report["passed_count"] == 6
    assert report["score_percent"] == 100.0
    assert report["inspection_fixture_safe"] is True
    assert report["daily_report_fixture_safe"] is True
    assert report["dashboard_fixture_exact"] is True
    assert report["audit_fixture_safe"] is True
    assert report["no_silent_conflict_merge"] is True
    assert report["operations_p95_target_seconds"] <= 15
    assert report["gate_passed"] is True
