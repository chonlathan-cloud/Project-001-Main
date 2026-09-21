"""Fail-closed read-only schema gate for a Phase 6 production stamp review."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

import asyncpg

if __package__:
    from .schema_preflight import inventory, validate_target
else:
    from schema_preflight import inventory, validate_target


BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = (
    BACKEND_DIR.parent
    / "docs/FeedbackV2/phase6/evidence/production-schema-profile-2026-09-21.json"
)
REQUIRED_PROFILE_FIELDS = {
    "profile_version",
    "approval_status",
    "target_database",
    "postgresql_major",
    "vector_version",
    "fingerprint_sha256",
    "table_count",
    "boq_v2_table_count",
    "alembic_revisions",
    "budget_source_table_exists",
    "budget_source_rows",
    "approval",
}


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile",
        type=Path,
        default=DEFAULT_PROFILE,
        help="Reviewed JSON profile containing the exact expected starting state",
    )
    parser.add_argument(
        "--allow-nonlocal-readonly",
        action="store_true",
        help=(
            "Permit an authorized read-only external audit. This flag does not "
            "authorize a production stamp, migration, or any other mutation."
        ),
    )
    return parser.parse_args()


def load_profile(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("schema gate profile must be a JSON object")
    missing = sorted(REQUIRED_PROFILE_FIELDS - payload.keys())
    if missing:
        raise ValueError(f"schema gate profile is missing fields: {', '.join(missing)}")
    if payload["profile_version"] != 1:
        raise ValueError("unsupported schema gate profile_version")
    if not isinstance(payload["approval"], dict):
        raise ValueError("schema gate profile approval must be a JSON object")
    return payload


def _major_version(server_version: str) -> int | None:
    try:
        return int(server_version.split(".", 1)[0])
    except (TypeError, ValueError):
        return None


async def _operational_state(database_url: str) -> dict[str, Any]:
    connection = await asyncpg.connect(database_url)
    try:
        async with connection.transaction(isolation="repeatable_read", readonly=True):
            database = await connection.fetchval("SELECT current_database()")
            alembic_exists = await connection.fetchval(
                "SELECT to_regclass('public.alembic_version') IS NOT NULL"
            )
            if alembic_exists:
                alembic_revisions = list(
                    await connection.fetchval(
                        "SELECT COALESCE(array_agg(version_num ORDER BY version_num), "
                        "ARRAY[]::varchar[]) FROM alembic_version"
                    )
                )
            else:
                alembic_revisions = []
            source_table_exists = await connection.fetchval(
                "SELECT to_regclass('public.boq_v2_project_budget_sources') "
                "IS NOT NULL"
            )
            source_rows = None
            if source_table_exists:
                source_rows = await connection.fetchval(
                    "SELECT count(*) FROM boq_v2_project_budget_sources"
                )
    finally:
        await connection.close()
    return {
        "database": database,
        "alembic_revisions": alembic_revisions,
        "budget_source_table_exists": source_table_exists,
        "budget_source_rows": source_rows,
    }


async def observe(database_url: str, masked_target: str) -> dict[str, Any]:
    before = await inventory(database_url, masked_target)
    operational = await _operational_state(database_url)
    after = await inventory(database_url, masked_target)
    vector_version = next(
        (
            item["version"]
            for item in after["schema"]["extensions"]
            if item["name"] == "vector"
        ),
        None,
    )
    return {
        "target": masked_target,
        "database": operational["database"],
        "postgresql_major": _major_version(str(after["server_version"])),
        "vector_version": vector_version,
        "fingerprint_sha256": after["fingerprint_sha256"],
        "table_count": after["table_count"],
        "boq_v2_table_count": after["boq_v2_table_count"],
        "alembic_revisions": operational["alembic_revisions"],
        "budget_source_table_exists": operational[
            "budget_source_table_exists"
        ],
        "budget_source_rows": operational["budget_source_rows"],
        "schema_stable_during_gate": (
            before["fingerprint_sha256"] == after["fingerprint_sha256"]
        ),
    }


def evaluate_profile(
    profile: dict[str, Any], observed: dict[str, Any]
) -> list[dict[str, Any]]:
    mismatches: list[dict[str, Any]] = []

    def require(field: str, expected: Any, actual: Any) -> None:
        if actual != expected:
            mismatches.append(
                {"field": field, "expected": expected, "actual": actual}
            )

    require("approval_status", "APPROVED", profile["approval_status"])
    approval = profile["approval"]
    for field in ("approver", "approved_at", "evidence_reference"):
        value = approval.get(field)
        if not isinstance(value, str) or not value.strip():
            mismatches.append(
                {
                    "field": f"approval.{field}",
                    "expected": "non-empty string",
                    "actual": value,
                }
            )

    expected_fields = {
        "database": profile["target_database"],
        "postgresql_major": profile["postgresql_major"],
        "vector_version": profile["vector_version"],
        "fingerprint_sha256": profile["fingerprint_sha256"],
        "table_count": profile["table_count"],
        "boq_v2_table_count": profile["boq_v2_table_count"],
        "alembic_revisions": profile["alembic_revisions"],
        "budget_source_table_exists": profile["budget_source_table_exists"],
        "budget_source_rows": profile["budget_source_rows"],
        "schema_stable_during_gate": True,
    }
    for field, expected in expected_fields.items():
        require(field, expected, observed.get(field))
    return mismatches


async def main() -> int:
    args = _arguments()
    try:
        profile = load_profile(args.profile)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"invalid schema gate profile: {exc}") from exc

    raw_url = os.environ.get("PHASE6_DATABASE_URL", "").strip()
    try:
        database_url, masked_target = validate_target(
            raw_url,
            allow_nonlocal_readonly=args.allow_nonlocal_readonly,
        )
    except ValueError as exc:
        message = str(exc).replace("PHASE0_DATABASE_URL", "PHASE6_DATABASE_URL")
        raise SystemExit(message) from exc

    observed = await observe(database_url, masked_target)
    mismatches = evaluate_profile(profile, observed)
    result = {
        "result": "pass" if not mismatches else "fail",
        "profile": str(args.profile),
        "profile_status": profile["approval_status"],
        "observed": observed,
        "mismatches": mismatches,
        "mutation_authorized": False,
    }
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0 if not mismatches else 3


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
