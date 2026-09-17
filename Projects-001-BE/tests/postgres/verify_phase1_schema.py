"""Verify the additive BOQ V2 schema and migration defaults."""

from __future__ import annotations

import asyncio
import os
from urllib.parse import urlparse

import asyncpg


EXPECTED_REVISION = "20260917_0002"
EXPECTED_V2_TABLES = {
    "boq_v2_audit_events",
    "boq_v2_baseline_change_orders",
    "boq_v2_command_idempotency",
    "boq_v2_cost_components",
    "boq_v2_cost_plans",
    "boq_v2_documents",
    "boq_v2_project_baselines",
    "boq_v2_project_budget_sources",
    "boq_v2_revisions",
    "boq_v2_scope_nodes",
    "boq_v2_document_sequences",
    "boq_v2_change_order_deductions",
    "boq_v2_revision_snapshots",
    "boq_v2_acceptances",
    "boq_v2_export_artifacts",
}
EXPECTED_CONSTRAINTS = {
    "ck_boq_v2_active_baseline_identity",
    "ck_boq_v2_baseline_effective_range",
    "ck_boq_v2_complete_cost_plan_values",
    "ck_boq_v2_cost_explicit_zero_reason",
    "ck_boq_v2_cost_state_values",
    "ck_boq_v2_document_alternative_group",
    "ck_boq_v2_document_direction",
    "uq_boq_v2_command_idempotency",
    "uq_boq_v2_scope_revision_logical",
    "uq_boq_v2_document_number",
    "uq_boq_v2_snapshot_revision_version_purpose",
    "uq_boq_v2_acceptance_revision",
    "ck_boq_v2_internal_export_xlsx_only",
}
EXPECTED_INDEXES = {
    "uq_boq_v2_active_project_baseline",
    "uq_boq_v2_current_cost_plan",
    "uq_boq_v2_scope_root_position",
}


def _safe_url() -> str:
    value = os.environ.get("PHASE1_DATABASE_URL", "").strip()
    if not value:
        raise SystemExit("PHASE1_DATABASE_URL is required; backend .env is not allowed")
    parsed = urlparse(value)
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise SystemExit("Refusing non-loopback Phase 1 database")
    if not parsed.path.lstrip("/").endswith("_test"):
        raise SystemExit("Refusing database whose name does not end with _test")
    return value.replace("postgresql+asyncpg://", "postgresql://", 1)


async def main() -> None:
    connection = await asyncpg.connect(_safe_url())
    try:
        revision = await connection.fetchval("SELECT version_num FROM alembic_version")
        tables = {
            row["tablename"]
            for row in await connection.fetch(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            )
        }
        constraints = {
            row["conname"]
            for row in await connection.fetch(
                """
                SELECT con.conname
                FROM pg_constraint con
                JOIN pg_class rel ON rel.oid = con.conrelid
                JOIN pg_namespace ns ON ns.oid = rel.relnamespace
                WHERE ns.nspname = 'public' AND rel.relname LIKE 'boq_v2_%'
                """
            )
        }
        indexes = {
            row["indexname"]
            for row in await connection.fetch(
                """
                SELECT indexname FROM pg_indexes
                WHERE schemaname = 'public' AND tablename LIKE 'boq_v2_%'
                """
            )
        }
        active_sources = await connection.fetchval(
            "SELECT count(*) FROM boq_v2_project_budget_sources WHERE source_kind = 'V2'"
        )
        source_rows = await connection.fetchval(
            "SELECT count(*) FROM boq_v2_project_budget_sources"
        )

        assert revision == EXPECTED_REVISION, revision
        assert {
            name for name in tables if name.startswith("boq_v2_")
        } == EXPECTED_V2_TABLES
        assert EXPECTED_CONSTRAINTS <= constraints, EXPECTED_CONSTRAINTS - constraints
        assert EXPECTED_INDEXES <= indexes, EXPECTED_INDEXES - indexes
        assert source_rows == 0, "Migration must not backfill source selection"
        assert active_sources == 0, "Migration must not activate V2"

        transaction = connection.transaction()
        await transaction.start()
        try:
            await connection.execute(
                """
                INSERT INTO projects (id, name, project_type, status)
                VALUES ('72000000-0000-4000-8000-000000000001', 'Constraint check',
                        'CONSTRUCTION', 'ACTIVE')
                """
            )
            await connection.execute(
                """
                INSERT INTO boq_v2_documents
                    (id, project_id, document_number, document_kind, created_by)
                VALUES
                    ('72000000-0000-4000-8000-000000000002',
                     '72000000-0000-4000-8000-000000000001',
                     'TEST-72000002', 'MAIN', 'phase1-test')
                """
            )
            invalid_direction_rejected = False
            try:
                async with connection.transaction():
                    await connection.execute(
                        """
                        INSERT INTO boq_v2_documents
                            (id, project_id, document_number, document_kind, direction, created_by)
                        VALUES
                            ('72000000-0000-4000-8000-000000000003',
                             '72000000-0000-4000-8000-000000000001',
                             'TEST-72000003', 'MAIN', 'DEDUCT', 'phase1-test')
                        """
                    )
            except asyncpg.CheckViolationError:
                invalid_direction_rejected = True
            assert invalid_direction_rejected
            invalid_alternative_rejected = False
            try:
                async with connection.transaction():
                    await connection.execute(
                        """
                        INSERT INTO boq_v2_documents
                            (id, project_id, document_number, document_kind, created_by)
                        VALUES
                            ('72000000-0000-4000-8000-000000000004',
                             '72000000-0000-4000-8000-000000000001',
                             'TEST-72000004', 'ALTERNATIVE', 'phase1-test')
                        """
                    )
            except asyncpg.CheckViolationError:
                invalid_alternative_rejected = True
            assert invalid_alternative_rejected
        finally:
            await transaction.rollback()
    finally:
        await connection.close()

    print(
        f"BOQ V2 schema verified through Phase 3: revision={revision}, "
        f"v2_tables={len(EXPECTED_V2_TABLES)}, source_rows=0"
    )


if __name__ == "__main__":
    asyncio.run(main())
