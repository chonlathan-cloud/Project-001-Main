from __future__ import annotations

from tests.evals.phase3_evaluator import evaluate_phase3


def test_phase3_finance_and_document_gate_is_exact() -> None:
    report = evaluate_phase3()

    assert report["evaluated_case_count"] == 5
    assert report["passed_count"] == 5
    assert report["score_percent"] == 100.0
    assert report["finance_fixture_exact"] is True
    assert report["document_gateway_safe"] is True
    assert report["sensitive_audit_fail_closed"] is True
    assert report["gate_passed"] is True
