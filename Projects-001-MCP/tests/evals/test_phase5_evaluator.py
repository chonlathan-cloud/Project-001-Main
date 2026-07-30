from __future__ import annotations

from tests.evals.phase5_evaluator import evaluate_phase5


def test_phase5_operations_chat_and_admin_gate_is_exact() -> None:
    report = evaluate_phase5()

    assert report["evaluated_case_count"] == 1
    assert report["passed_count"] == 1
    assert report["score_percent"] == 100.0
    assert report["tool_inventory_complete"] is True
    assert report["no_out_of_scope_visibility"] is True
    assert report["operational_queries_safe"] is True
    assert report["internal_chat_consistent"] is True
    assert report["admin_matrix_score_percent"] == 100.0
    assert report["revocation_passed"] is True
    assert report["gate_passed"] is True
