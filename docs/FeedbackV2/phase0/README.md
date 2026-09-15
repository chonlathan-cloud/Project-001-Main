# BOQ V2 Phase 0 — Baseline and contract lock

Status: **LOCKED for Phase 1 implementation**
Recorded: 2026-09-14 (Asia/Bangkok)

This directory is the Phase 0 implementation input for `ModifyV2-plan.md`. It
records what exists, what Phase 1 may add, and the compatibility boundary that
must remain stable. It does not introduce BOQ V2 tables, routes, writes, feature
flags, or production changes.

## Verified repository baseline

| Check | Evidence |
| --- | --- |
| Working branch | `feature` |
| Current commit at audit | `ae91252f9fa299c4ce832bfcf20c4780d071cce1` |
| Plan baseline | `8f53197c6cf369b60a5cb2d6771a9bcc7b6b4020` |
| Relationship | Plan baseline is an ancestor of the audited commit; current commit is one commit ahead |
| Source/config/test delta | None. The only `baseline..HEAD` path is `docs/FeedbackV2/ModifyV2-plan.md` |
| Worktree before Phase 0 | Clean |
| Tracking state | `feature...origin/feature [ahead 29]` |
| Local/remote main observation | Local `main` and `origin/main` resolve to the audited commit; the plan's earlier statement that `main` differed is stale |

The implementation baseline is therefore the current `feature` commit, without
checking out or rebasing another branch. Re-run the commands in
`Validation and evidence` before starting Phase 1 because branch state can
change after this record is written.

## Phase 0 outputs

- `dependency-map.md` — verified current readers, writers, callers, and drift.
- `contracts/CDR-001-calculation-and-completeness.md` — money, rounding, and
  unknown-cost rules.
- `contracts/CDR-002-scope-identity-and-lifecycle.md` — stable identity,
  revisions, alternatives, change orders, and immutable states.
- `contracts/CDR-003-permissions-concurrency-idempotency.md` — authorization,
  serialization, optimistic concurrency, and retry contracts.
- `contracts/CDR-004-project-budget-snapshot.md` and
  `contracts/project-budget-snapshot.schema.json` — canonical internal budget
  response and legacy compatibility behavior.
- `contracts/CDR-005-migration-and-test-safety.md` — Alembic adoption boundary,
  schema preflight, isolated database, and rollback rules.
- Backend golden fixture under
  `Projects-001-BE/tests/fixtures/boq_v2_phase0/`.
- Isolated PostgreSQL 16 + pgvector harness under
  `Projects-001-BE/tests/postgres/` and `Projects-001-BE/scripts/`.

## Instructions and source documents read

- Root `AGENTS.md`; the only other discovered `AGENTS.md` is inside
  `Projects-001-FE/node_modules/recharts/` and does not govern project source.
  No applicable `AGENTS.override.md` exists.
- `Design/DESIGN.md`, `Design/FLOW.md`, `Design/FLOW_ADMIN.md`,
  `Design/FLOW_ADMIN_SYNC.md`, `Design/FLOW_SUBCONTRATOR.md`, and
  `Design/FLOW_SUBCONTRATOR_STITCH.md`.
- `Design/S-BOQ/BOQ_HIERARCHY_CONTRACT.md`, `Datastucture.json`, `S-BOQ.json`,
  `ST-DATA.json`, and `sn-customer-hierarchy.contract.json`.
- `docs/00_INSTRUCTION.md`, `docs/01_Business_Requirements.md`,
  `docs/02_HLD_Architecture.md`, `docs/03_TDD_API_DB_Spec.md`, and
  `docs/04_LLD_Implementation.md`.
- The complete `docs/FeedbackV2/ModifyV2-plan.md`, including every §12 path and
  its direct callers/importers.

## Locked implementation boundary

Phase 1 is limited to the additive domain foundation and read compatibility:

1. Alembic setup and additive BOQ V2 schema.
2. Entities, indexes, invariants, audit/version command primitives, and tests.
3. A shared budget selector/service whose default for every existing project is
   `LEGACY`.
4. Additive readiness/status handling and source-aware Funds fingerprinting.
5. Separation of active-budget reads from historical finance joins.

Phase 1 must not expose V2 write routes, switch a project to V2, retire sync,
change existing public numeric response shapes, or implement editor, offers,
catalog, quotation exports, or public V2 behavior. Offers, catalog, and exports
remain later-phase work even when Phase 1 creates only the minimum lineage
primitives needed by its own schema.

## Executed Phase 0 sequence

1. Verified branch, commit ancestry, worktree, instruction scope, referenced
   documents, §12 files, and direct callers.
2. Recorded dependency drift and locked calculation, completeness, lifecycle,
   permission, concurrency, idempotency, migration, and budget-read contracts.
3. Captured consumer-specific legacy goldens before adding a shared budget
   service.
4. Built and exercised an ephemeral PostgreSQL 16 + pgvector baseline from
   current registered ORM metadata; captured and re-compared its fingerprint.
5. Ran focused backend, frontend, and MCP regressions; recorded warnings and
   unavailable checks; removed the isolated container.

## Known repository differences from the plan

1. The hierarchy contract in `Design/S-BOQ/BOQ_HIERARCHY_CONTRACT.md` describes
   fields and integrations not present in the ORM, API schema, persistence path,
   or frontend sanitizer. Only a SQL migration and an unused helper exist.
2. Existing budget consumers do not share one formula. Project list can sum both
   CUSTOMER and SUBCONTRACTOR roots; Dashboard prefers CUSTOMER then
   SUBCONTRACTOR then contingency; Funds uses CUSTOMER minus SUBCONTRACTOR;
   Chat prefers SUBCONTRACTOR then CUSTOMER then contingency; MCP uses CUSTOMER
   roots only; frontend project cards make an additional per-project BOQ request.
3. Chat filters `BOQItem.valid_to IS NULL` while joining installments and
   transactions. That can hide finance linked to historical BOQ rows. Insight
   Warehouse consumes that snapshot rather than ingesting a BOQ budget directly.
4. The repository has automated tests. The frontend test command discovers only
   two configured files (five baseline tests), so it is not a broad frontend
   suite.
5. There is no Alembic revision history or migration ledger. Existing SQL
   scripts include data-mutating operations and are not safe to replay as a test
   migration chain.
6. Existing sync endpoints, frontend polling/drawer behavior, MCP `boq_sync`, and
   the in-memory sync job store are active and protected until the later cutover
   phase.

These are compatibility facts, not authorization to fix them during Phase 0.

## Resolved implementation decisions

- Phase 1 will introduce Alembic; Phase 0 only defines its safety contract.
- Phase 1 covers the core additive foundation only. Offers, catalog, and exports
  are deferred to their planned phases.
- `ProjectBudgetSnapshot` is the canonical internal contract, but Phase 1 must
  adapt it back to existing public legacy outputs. Public consumers remain
  byte/shape compatible until each consumer explicitly supports readiness and
  nullable values.

No additional business decision was made in Phase 0.

## Unresolved decisions and blockers

There is no unresolved business decision blocking Phase 1 within the locked
core-foundation scope. Two boundaries remain explicit:

- A read-only fingerprint of each deployed target schema is required before any
  release migration or first Alembic stamp. It requires separate environment
  access/authority and was intentionally not performed in Phase 0.
- Stitch authentication is unavailable. It does not block the backend-only
  Phase 1 foundation, but Phase 2 UI implementation must stop until the latest
  design can be fetched.

## Validation and evidence

Run from repository root unless a command changes directory:

```bash
git branch --show-current
git rev-parse HEAD
git merge-base --is-ancestor 8f53197c6cf369b60a5cb2d6771a9bcc7b6b4020 HEAD
git diff --name-status 8f53197c6cf369b60a5cb2d6771a9bcc7b6b4020..HEAD
git status --short --branch

cd Projects-001-BE
./scripts/phase0_test_db.sh up
./scripts/phase0_test_db.sh bootstrap
./scripts/phase0_test_db.sh verify
./scripts/phase0_test_db.sh fingerprint
PYTHONDONTWRITEBYTECODE=1 DATABASE_URL=postgresql+asyncpg://phase0:phase0@127.0.0.1:55432/projects001_phase0_test \
  venv/bin/python -m pytest tests/phase0
./scripts/phase0_test_db.sh down

cd ../Projects-001-FE
npm test
npm run lint
npm run build

cd ../Projects-001-BE
PYTHONDONTWRITEBYTECODE=1 DATABASE_URL=postgresql+asyncpg://test:test@127.0.0.1:65432/projects001_test \
  venv/bin/python -m pytest \
  tests/test_fund_service.py \
  tests/test_input_request_access_rules.py \
  tests/test_input_request_payment_rules.py \
  tests/test_mcp_read_contracts.py \
  tests/test_mcp_phase3_contracts.py \
  tests/test_mcp_phase4_contracts.py \
  tests/test_mcp_phase5_processing.py \
  tests/test_settings_customers.py \
  tests/test_flowaccount_service.py

cd ../Projects-001-MCP
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest \
  tests/contract tests/authorization tests/security
```

Required evidence before Phase 1:

- branch/commit/ancestor/diff output;
- clean or fully explained worktree;
- Docker health and masked preflight target;
- schema fingerprint, PostgreSQL major version, `vector` extension version,
  table count, and zero `boq_v2_*` public tables;
- golden fixture verification;
- exact pass/fail counts for focused backend, frontend, and MCP regressions;
- any skipped or unavailable checks with the reason.

Stitch was queried during Phase 0 but returned `Authentication required`. This
does not block backend-only Phase 1. It is a blocker for Phase 2 UI work and must
be retried before UI implementation.
