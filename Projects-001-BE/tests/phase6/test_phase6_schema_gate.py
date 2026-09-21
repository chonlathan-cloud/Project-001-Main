from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import pytest

from scripts.phase6_schema_gate import evaluate_profile, load_profile, observe
from scripts.schema_preflight import validate_target


def _profile() -> dict[str, object]:
    return {
        "profile_version": 1,
        "approval_status": "APPROVED",
        "target_database": "project-001",
        "postgresql_major": 18,
        "vector_version": "0.8.1",
        "fingerprint_sha256": "abc123",
        "table_count": 15,
        "boq_v2_table_count": 0,
        "alembic_revisions": [],
        "budget_source_table_exists": False,
        "budget_source_rows": None,
        "approval": {
            "approver": "owner@example.test",
            "approved_at": "2026-09-21T00:00:00Z",
            "evidence_reference": "phase6-review-1",
        },
    }


def _observed() -> dict[str, object]:
    return {
        "database": "project-001",
        "postgresql_major": 18,
        "vector_version": "0.8.1",
        "fingerprint_sha256": "abc123",
        "table_count": 15,
        "boq_v2_table_count": 0,
        "alembic_revisions": [],
        "budget_source_table_exists": False,
        "budget_source_rows": None,
        "schema_stable_during_gate": True,
    }


def test_approved_exact_profile_passes() -> None:
    assert evaluate_profile(_profile(), _observed()) == []


def test_proposed_or_incomplete_approval_fails_closed() -> None:
    profile = _profile()
    profile["approval_status"] = "PROPOSED"
    profile["approval"] = {
        "approver": None,
        "approved_at": None,
        "evidence_reference": None,
    }

    fields = {item["field"] for item in evaluate_profile(profile, _observed())}

    assert fields == {
        "approval_status",
        "approval.approver",
        "approval.approved_at",
        "approval.evidence_reference",
    }


def test_unknown_drift_and_schema_race_fail_closed() -> None:
    observed = _observed()
    observed["fingerprint_sha256"] = "unexpected"
    observed["schema_stable_during_gate"] = False
    observed["boq_v2_table_count"] = 1

    fields = {item["field"] for item in evaluate_profile(_profile(), observed)}

    assert fields == {
        "fingerprint_sha256",
        "boq_v2_table_count",
        "schema_stable_during_gate",
    }


def test_profile_loader_rejects_missing_contract_fields(tmp_path: Path) -> None:
    path = tmp_path / "profile.json"
    path.write_text(json.dumps({"profile_version": 1}), encoding="utf-8")

    with pytest.raises(ValueError, match="missing fields"):
        load_profile(path)


def test_schema_gate_observes_isolated_postgresql_when_configured() -> None:
    raw_url = os.environ.get("PHASE6_DATABASE_URL", "").strip()
    if not raw_url:
        pytest.skip("PHASE6_DATABASE_URL is not configured")
    database_url, masked_target = validate_target(
        raw_url, allow_nonlocal_readonly=False
    )

    observed = asyncio.run(observe(database_url, masked_target))

    assert observed["database"] == "projects001_phase6_test"
    assert observed["postgresql_major"] == 18
    assert observed["vector_version"] == "0.8.1"
    assert observed["boq_v2_table_count"] == 22
    assert observed["alembic_revisions"] == ["20260917_0003"]
    assert observed["budget_source_table_exists"] is True
    assert isinstance(observed["budget_source_rows"], int)
    assert observed["budget_source_rows"] >= 0
    assert observed["schema_stable_during_gate"] is True

    profile = _profile()
    profile.update(
        {
            "target_database": observed["database"],
            "postgresql_major": observed["postgresql_major"],
            "vector_version": observed["vector_version"],
            "fingerprint_sha256": observed["fingerprint_sha256"],
            "table_count": observed["table_count"],
            "boq_v2_table_count": observed["boq_v2_table_count"],
            "alembic_revisions": observed["alembic_revisions"],
            "budget_source_table_exists": observed[
                "budget_source_table_exists"
            ],
            "budget_source_rows": observed["budget_source_rows"],
        }
    )
    assert evaluate_profile(profile, observed) == []
