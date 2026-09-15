# Phase 1 validation evidence

Date: 2026-09-15 (Asia/Bangkok)
Execution scope: local repository and isolated PostgreSQL only
Production/deployment/IAM/data mutation: **not performed**

## Repository baseline

- Branch: `feature`
- Starting HEAD: `ae91252f9fa299c4ce832bfcf20c4780d071cce1`
- Phase 0 artifacts were untracked and preserved.
- Phase 1 implementation remains uncommitted.

## Isolated database

- Image: `pgvector/pgvector:pg16` pinned by digest
  `sha256:7d400e340efb42f4d8c9c12c6427adb253f726881a9985d2a471bf0eed824dff`
- Target: `127.0.0.1:55433/projects001_phase1_test`
- Storage: Docker `tmpfs`
- PostgreSQL: `16.13`
- pgvector: `0.8.2`
- Alembic head: `20260915_0001`
- Public tables at head: 26, including `alembic_version`
- `boq_v2_*` tables: 10
- V2 source-selection rows after migration: 0
- Schema fingerprint:
  `e784f8286cfedd2eff0c7bcef8b1b34b1ecc15401dcc096cdbb88d8659626946`

## Migration evidence

Both paths ran on fresh isolated `tmpfs` databases:

1. Empty database: `upgrade -> 20260915_0000 -> 20260915_0001` passed.
2. Frozen current schema: 15 legacy tables created, baseline stamped at
   `20260915_0000`, then upgraded to `20260915_0001`; passed.
3. A second `alembic upgrade head` made no changes.
4. `alembic check` reported `No new upgrade operations detected`.
5. Schema verifier found all ten expected tables, required named constraints,
   partial uniqueness indexes, no source backfill, and no V2 activation.
6. Invalid MAIN/DEDUCT document state was rejected by PostgreSQL.
7. Destructive downgrade was not run; both revisions reject it by policy.

Commands:

```bash
./Projects-001-BE/scripts/phase1_test_db.sh up
./Projects-001-BE/scripts/phase1_test_db.sh upgrade-empty
./Projects-001-BE/scripts/phase1_test_db.sh current
./Projects-001-BE/scripts/phase1_test_db.sh check
./Projects-001-BE/scripts/phase1_test_db.sh verify

./Projects-001-BE/scripts/phase1_test_db.sh down
./Projects-001-BE/scripts/phase1_test_db.sh up
./Projects-001-BE/scripts/phase1_test_db.sh upgrade-current
./Projects-001-BE/scripts/phase1_test_db.sh upgrade-empty
./Projects-001-BE/scripts/phase1_test_db.sh current
./Projects-001-BE/scripts/phase1_test_db.sh check
./Projects-001-BE/scripts/phase1_test_db.sh verify
```

## Contract and regression evidence

| Gate | Result |
| --- | --- |
| Backend complete suite | 154 passed |
| Phase 0 + Phase 1 contract subset | 23 passed |
| Ruff on changed/new Python files | passed |
| Backend startup import | passed; 185 routes; no public V2 route |
| Legacy database golden verifier | 3 scenarios × 11 projections passed |
| Historical finance verifier | archived BOQ-linked installment/transaction remained queryable; only active BOQ entered Chat budget |
| Budget as-of verifier | before V2 activation resolved LEGACY; after activation resolved V2; public legacy adapters stayed unchanged |
| Funds integration verifier | incoming allocation to unknown-cost V2 passed; new outward allocation failed closed; valid reversal passed |
| Frontend tests | 5 passed |
| Frontend lint | passed |
| Frontend build | passed with the existing >500 kB chunk warning |
| MCP contract/authorization/security | 128 passed; 1 existing Starlette/httpx deprecation warning |
| Shell syntax and Compose configuration | passed |
| Alembic metadata drift | none detected |

Primary commands:

```bash
cd Projects-001-BE
PYTHONDONTWRITEBYTECODE=1 DATABASE_URL=postgresql+asyncpg://phase1:phase1@127.0.0.1:55433/projects001_phase1_test \
  venv/bin/python -m pytest -q
PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m ruff check <changed-and-new-python-files>
PYTHONDONTWRITEBYTECODE=1 DATABASE_URL=postgresql+asyncpg://phase1:phase1@127.0.0.1:55433/projects001_phase1_test \
  venv/bin/python -c 'import main'
./scripts/phase1_test_db.sh golden
./scripts/phase1_test_db.sh finance-history
./scripts/phase1_test_db.sh funds

cd ../Projects-001-FE
npm test
npm run lint
npm run build

cd ../Projects-001-MCP
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest \
  tests/contract tests/authorization tests/security --disable-warnings
```

## Remaining release evidence

This local result does not authorize a deployment. Before release, run the
CDR-005 deployed-schema read-only preflight and approve the first stamp/upgrade
plan for that exact target. No external environment was inspected in Phase 1.
