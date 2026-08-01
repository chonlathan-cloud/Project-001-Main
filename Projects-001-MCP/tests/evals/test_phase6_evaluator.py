from __future__ import annotations

from tests.evals.phase6_evaluator import evaluate_phase6


def test_phase6_repository_gate_does_not_claim_live_beta_release() -> None:
    report = evaluate_phase6()

    assert all(report["previous_repository_gates"].values())
    assert report["plugin_repository_ready"] is True
    assert report["plugin_connection_bound"] is False
    assert report["beta_profile_ready"] is True
    assert report["deployment_policy_ready"] is True
    assert report["documentation_ready"] is True
    assert report["phase5_evidence_pending_rows"] == 7
    assert report["repository_gate_passed"] is True
    assert report["live_release_gate_passed"] is None
    assert report["live_release_status"] == "not_evaluated"
