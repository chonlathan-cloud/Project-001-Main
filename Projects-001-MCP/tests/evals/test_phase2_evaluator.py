from __future__ import annotations

from tests.evals.phase2_evaluator import evaluate_phase2


def test_phase2_core_golden_gate_is_at_least_95_percent() -> None:
    report = evaluate_phase2()

    assert report["evaluated_case_count"] == 6
    assert report["passed_count"] == 6
    assert report["score_percent"] == 100.0
    assert report["boq_fixture_exact"] is True
    assert report["gate_passed"] is True
