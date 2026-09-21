# Phase 6 rollback plan

Status: **proposal for review; data-preserving rollback only**

Rollback restores a compatible application/configuration state while preserving
both legacy and V2 data. Production downgrade migrations are prohibited.

## Before V2 source activation

If migration or compatibility smoke fails:

1. stop new V2 mutations and keep `BOQ_V2_ENABLED=false`;
2. route traffic to the recorded starting compatible application revisions only
   if their schema compatibility has been proved;
3. preserve additive V2 tables and any diagnostic/audit records;
4. repair forward for schema issues; and
5. re-verify retained flows and monitor before reopening the window.

Do not drop V2 tables, downgrade Alembic, delete records, rewrite finance, or
rerun the baseline migration. If the starting backend is not compatible with
the additive schema or has the current Dashboard failure, use the separately
validated rollback image—not an assumed previous `latest` tag.

## After V2 source activation

If an application regression occurs:

1. freeze V2 mutation commands;
2. keep the recorded V2 source and immutable accepted history intact;
3. deploy/route to the validated compatible rollback image;
4. verify reads and finance/history access against the unchanged source; and
5. repair forward and re-open only after smoke and monitoring pass.

Application rollback must not silently change the project's source back to
legacy.

## Budget-source rollback

Changing the source from V2 to legacy is a separate business operation, not a
deployment rollback. Before it can occur:

1. stop and produce an impact preview covering accepted V2 changes, allocations,
   current Funds capacity/deficit, history/as-of behavior, and every downstream
   consumer;
2. require explicit Owner approval for the named project and exact source
   versions;
3. execute an atomic audited command with actor, timestamp, reason, before/after
   source IDs/versions, and idempotency evidence; and
4. verify no double counting, finance replay, deletion, or historical rewrite.

If the operation cannot preserve those invariants, do not perform it.

## Prohibited rollback actions

- drop or truncate V2 tables;
- delete V2 records, snapshots, exports, offers, prices, audits, or idempotency
  records;
- delete or rewrite legacy BOQ rows;
- replay payments, transactions, allocations, or reversals;
- rewrite accepted V2 history;
- run destructive Alembic downgrade;
- use mutable `latest` as rollback identity; or
- treat disabling the UI flag as a budget-source rollback.

## Rollback evidence record

For any rollback, record:

- trigger and first observed timestamp;
- decision maker and explicit authority;
- affected project/source/version and release revisions/digests;
- frozen command surface and observation window;
- exact application/config actions;
- schema and finance counts before/after;
- retained-flow, authorization, history, and export verification;
- monitoring results and residual risk; and
- follow-up owner and repair-forward plan.
