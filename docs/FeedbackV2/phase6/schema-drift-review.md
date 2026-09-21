# Production schema drift review

Status: **proposal; not approved for production stamp or migration**

Direct production fingerprint observed on 2026-09-21:
`cb7206a7ef0a8d3c2a1cd0b864b1ef93a06c4f2ef5a5a36d6ac5743aef6c1b41`.

The production schema-only rehearsal proved that V2 migrations `0001` through
`0003` are additive against the current 15-table shape. It also proved that
`alembic check` remains red after the upgrade. This document classifies those
legacy differences so an authorized reviewer can choose preservation/allowlist
or a separately tested reconciliation. No row or schema mutation is proposed as
an implicit part of BOQ V2 cutover.

## Decision principles

1. Preserve intentional production constraints/indexes when they are equivalent
   to or stronger than current ORM metadata.
2. Never generate a migration from the raw autogenerate output. It includes
   column/index removal and JSONB-to-JSON conversion operations that violate the
   Phase 6 preservation boundary.
3. Do not add `NOT NULL`, rewrite defaults, or convert finance/accounting JSON
   types during BOQ V2 handoff without a separate data scan, lock assessment,
   rollback plan, and approval.
4. A target-specific allowlist must match exact object definitions and the
   direct fingerprint; it must reject unknown drift.
5. Stamp `20260915_0000` only after this matrix and a data-bearing restored-clone
   rehearsal are approved.

## Drift matrix

| Area | Production shape | ORM/frozen-baseline shape | Proposed Phase 6 treatment | Risk if normalized blindly |
| --- | --- | --- | --- | --- |
| Legacy `boq_items` hierarchy | Six nullable columns: `raw_wbs_level`, `display_wbs_level`, `row_type`, `hierarchy_status`, `source_row_index`, `sort_order`; composite active-order index | Columns/index absent | Preserve and exact-allowlist as historical sync/read metadata | Autogenerate proposes dropping historical fields and index |
| `projects.system_key` | Partial unique index `uq_projects_system_key` where value is not null | ORM full unique constraint | Preserve partial index and exact-allowlist; semantics remain unique for populated keys | Replacing the index can lock the table and is unrelated to V2 |
| Fund bucket project identity | Named unique constraint plus a non-unique lookup index | ORM expresses `unique=True,index=True` as a unique index | Preserve production objects and allowlist their equivalent ownership/lookup semantics | Dropping/recreating uniqueness risks bucket identity |
| Fund allocation reversal | Production unique constraint name and composite source/target chronological indexes | Different unique name; single-column generated indexes | Preserve production constraint and stronger composite indexes | Autogenerate would replace useful ordering indexes and touch finance tables |
| Fund ledger opening balance | Partial unique index permits one `OPENING_BALANCE` per bucket; composite chronological bucket index | Partial unique index absent from ORM; generated single-column index | Preserve production partial/composite indexes; record as intentional manual-SQL contract | Removing the partial index weakens financial integrity |
| Fund audit detail | `JSONB NOT NULL DEFAULT '{}'::jsonb`; composite event-time index | Generic `JSON`; Python-side default; generated single-column index | Preserve JSONB/default/composite index; allowlist exact definitions | JSONB-to-JSON conversion and index replacement are destructive/unnecessary |
| Input accounting readiness | Several readiness/status/linked fields nullable with server defaults; readiness errors stored as JSONB | ORM marks fields non-null with Python defaults and generic JSON | Preserve during Phase 6; require a separate null/data scan and operational migration decision later | `SET NOT NULL` can fail or lock; type rewrite touches accounting data |
| Input external-AI comment | Production column comment present | ORM metadata has no comment | Preserve/allowlist comment | Removing documentation adds no V2 value |

## Proposed stamp gate

The production stamp may be considered only when all statements below are
proved on a fresh restored clone:

- direct source fingerprint and clone inventory correspond to the same fresh
  backup;
- every difference is represented by an exact object-level allowlist entry;
- no unclassified table, column, constraint, index, extension, default,
  nullability, comment, or type difference exists;
- all legacy hierarchy columns/indexes remain after `0001` → `0003`;
- fund constraints/indexes/JSONB definitions remain byte-for-byte equivalent in
  normalized inventory;
- input accounting/FlowAccount definitions and values are unchanged;
- critical legacy row counts, foreign keys, finance/history IDs and aggregates
  match before/after;
- V2 tables are the only new business-schema objects and contain no rows; and
- authenticated retained-flow smoke passes against the migrated clone.

The normal clean-schema `alembic check` should continue to pass in CI. For this
specific target, do not suppress autogenerate globally. Use a separate
production-stamp verifier that compares the exact approved drift inventory and
fails on additions, removals, or changed definitions.

`Projects-001-BE/scripts/phase6_schema_gate.py` implements that read-only gate.
It requires `PHASE6_DATABASE_URL`, never loads the backend `.env`, reads the
schema twice to detect a concurrent change, and validates the exact profile,
database, PostgreSQL major, pgvector version, Alembic state and source-table
state. The checked-in profile remains `PROPOSED`; the command must fail until
the approval fields are completed through an explicitly reviewed commit.

## Review decision

- Technical reviewer: _missing_
- Decision: _not approved_
- Approved fingerprint/inventory artifact: _missing_
- Data-bearing restored-clone evidence: _missing_
- Approval timestamp: _missing_
- Deviations/exceptions: _none approved_
