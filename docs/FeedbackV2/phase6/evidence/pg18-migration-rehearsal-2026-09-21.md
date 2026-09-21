# PostgreSQL 18 migration rehearsal — 2026-09-21

Classification: **PASS for the clean empty-database path; restored-production
clone rehearsal still required**

This rehearsal closes the database-major-version gap between the Phase 0–5
PostgreSQL 16 harness and the production PostgreSQL 18 instance. It does not
approve or simulate stamping the drifted populated production schema.

## Isolation and release identity

- Git commit under test: `8db6544`
- Container project: `projects001_phase6_pg18`
- Binding: `127.0.0.1:55435`
- Database: `projects001_phase6_test`
- Storage: `tmpfs` at the PostgreSQL 18 data root `/var/lib/postgresql`
- Image: `pgvector/pgvector:0.8.1-pg18`
- Multi-architecture pinned digest:
  `sha256:508c5290cda481d4f5f846446a26e9c1b804766828a394a5861de1b348a18b4c`
- Runtime on the validation machine: PostgreSQL `18.2`, pgvector `0.8.1`
- Production observed at preflight: PostgreSQL `18.3`, pgvector `0.8.1`

The PostgreSQL patch version differs by one patch release. The rehearsal proves
the migration chain on PostgreSQL major 18 with the exact production pgvector
extension version; the restored-clone rehearsal remains the authority for the
exact production patch and schema drift.

## Reproducible harness

- `Projects-001-BE/scripts/phase6_pg18_test_db.sh`
- `Projects-001-BE/tests/postgres/docker-compose.phase6-pg18.yml`

The wrapper reuses the existing Phase 1 controller through explicit compose
file, project, and database URL overrides. Existing Phase 1 defaults remain
unchanged. The harness refuses shared storage by using `tmpfs`, binds only to
loopback, uses non-production credentials, and names the database with `_test`.

## Migration results

Commands:

```bash
./scripts/phase6_pg18_test_db.sh up
./scripts/phase6_pg18_test_db.sh upgrade-empty
./scripts/phase6_pg18_test_db.sh current
./scripts/phase6_pg18_test_db.sh check
./scripts/phase6_pg18_test_db.sh upgrade-empty
```

Results:

- empty upgrade applied `20260915_0000` → `20260915_0001` →
  `20260917_0002` → `20260917_0003` in order;
- current revision: `20260917_0003 (head)`;
- Alembic check: `No new upgrade operations detected.`;
- second `upgrade head`: no-op;
- public tables: 38, comprising 15 legacy tables, 22 V2 tables, and
  `alembic_version`;
- V2 source rows: 0; migration did not activate V2; and
- schema fingerprint after head:
  `be513c276c384e8e02ce57430f93e6c7d836e19ea099e0c1b05f5f5b2b7b9492`.

## Invariant verifiers

The following commands passed on the same PostgreSQL 18 database. Each business
fixture verifier rolls back its transaction:

```bash
./scripts/phase6_pg18_test_db.sh verify
./scripts/phase6_pg18_test_db.sh golden
./scripts/phase6_pg18_test_db.sh finance-history
./scripts/phase6_pg18_test_db.sh funds
./scripts/phase6_pg18_test_db.sh phase5-cutover
```

Evidence:

- 22 V2 tables, zero source rows, zero Phase 4 business rows;
- all three legacy golden scenarios and 11 consumer projections each passed;
- archived BOQ finance and as-of source history remained accessible;
- Funds allowed incoming to unknown V2, rejected new outward allocation, and
  allowed a valid reversal; and
- same-project MAIN + ADD − DEDUCT cutover replaced rather than added legacy,
  while legacy finance/history IDs remained unchanged.

## Clean-commit regression

Tests ran from disposable detached worktrees at `8db6544`, excluding the nine
unrelated modifications in the primary worktree.

- Backend against PostgreSQL 18/pgvector 0.8.1: `180 passed in 8.72s`.
- Backend startup import with isolated database and V2 flag disabled: passed.
- Standalone MCP: `133 passed`; existing Starlette/httpx/anyio deprecation
  warnings remain.
- Frontend Node tests: `10 passed`, `0 failed`.
- Frontend ESLint: passed.
- Frontend Vite production build: passed; existing `>500 kB` chunk-size warning
  remains.

## Remaining production blocker

This PASS does not clear the production schema stop gate. Production is
populated, unstamped, and differs from the frozen legacy baseline. Before any
production stamp or migration, restore the fresh production backup to an
isolated target, classify the recorded drift, prove critical row/history
invariants, stamp only the approved baseline, and repeat the upgrade and smoke
sequence there. No production action occurred during this rehearsal.
