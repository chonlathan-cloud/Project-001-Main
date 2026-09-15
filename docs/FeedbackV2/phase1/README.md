# Phase 1 — Additive domain and read compatibility

Status: **implemented locally; release preflight still required**
Branch baseline: `feature` at `ae91252f9fa299c4ce832bfcf20c4780d071cce1`

## Delivered scope

- Alembic migration ledger with an immutable current-schema baseline and one
  additive BOQ V2 foundation revision.
- Ten `boq_v2_*` tables for document/revision identity, scope nodes, cost plans,
  cost components, active baseline membership, source selection, idempotency,
  and audit events.
- Decimal calculation and completeness primitives locked to CDR-001.
- Stable logical/revision-row identity, hierarchy validation, optimistic
  version checks, canonical request hashing, and ordered project advisory locks.
- Internal `ProjectBudgetSnapshot` plus exact per-consumer legacy adapters.
- Source/version/completeness-aware Funds fingerprints and common lock order.
- Unknown-cost protection for a new outward allocation from a V2 source;
  incoming allocations and valid reversals retain their existing rules.
- Active-budget reads separated from historical finance joins so archived SCD2
  BOQ rows remain resolvable by Chat analytics.

## Compatibility boundary

Phase 1 does not expose a public V2 route or mutation command. It does not
activate V2 for any project, retire Google Sheets sync, modify the frontend,
generate quotations, implement offers/catalog/exports, or alter legacy public
response shapes. The absence of a row in `boq_v2_project_budget_sources` means
`LEGACY`, so migration alone cannot change an existing project budget.

The shared read service deliberately preserves the locked projections:

| Consumer | Legacy value retained |
| --- | --- |
| Project list | All current root rows; contingency only when there is no root row |
| Project detail | Existing CUSTOMER/SUBCONTRACTOR comparison rollup |
| Dashboard | CUSTOMER-like roots, then SUBCONTRACTOR roots, then contingency |
| Funds | Existing projected CUSTOMER minus SUBCONTRACTOR rollup |
| Chat/Insights | SUBCONTRACTOR leaves, then other leaves, then contingency |
| MCP | Trimmed, case-insensitive CUSTOMER root sum, else zero |

## Migration paths

The revisions are:

```text
<base> -> 20260915_0000  baseline current schema
20260915_0000 -> 20260915_0001  add BOQ V2 foundation
```

An empty integration database runs both revisions. A database proven by
read-only preflight to match the legacy baseline is stamped at
`20260915_0000`, then upgraded to head. A stamp is metadata only and must not be
used to conceal drift.

Migration commands require `ALEMBIC_DATABASE_URL`; Alembic does not load the
backend `.env`. Local targets must use loopback and a database ending `_test`.
A non-local target additionally requires `ALEMBIC_ALLOW_NONLOCAL=1`, but that
flag is only a technical safety acknowledgement and does not grant deployment
authority.

Destructive downgrades intentionally raise an error. Rollback means disabling
new mutations/restoring compatible application code while preserving additive
data, as required by CDR-005.

## Isolated test harness

```bash
cd Projects-001-BE
./scripts/phase1_test_db.sh up
./scripts/phase1_test_db.sh upgrade-empty
./scripts/phase1_test_db.sh check
./scripts/phase1_test_db.sh verify
./scripts/phase1_test_db.sh golden
./scripts/phase1_test_db.sh finance-history
./scripts/phase1_test_db.sh funds
./scripts/phase1_test_db.sh down
```

For the stamped-current rehearsal, start a fresh `tmpfs` container and replace
`upgrade-empty` with `upgrade-current`. The latter creates the frozen 15-table
pre-Alembic schema, stamps `20260915_0000`, and upgrades the additive revision.

## Release blockers and prerequisites

No business decision blocks completion of the local Phase 1 implementation.
Before any external migration or release, the owner must separately authorize
the target and record:

1. read-only deployed-schema fingerprint and drift comparison;
2. PostgreSQL/pgvector versions and exact Alembic current/head or approved stamp;
3. backup/restore readiness and deployment authority;
4. a compatible application release order (migration before this code);
5. confirmation that no source row is created or switched to V2.

Stitch authentication remains a Phase 2 UI prerequisite and is unrelated to
this backend-only phase.

See [validation evidence](evidence/phase1-validation.md).
