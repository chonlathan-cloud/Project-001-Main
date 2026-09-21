# Phase 6 — Controlled Production Handoff

Status: **NO-GO — preflight completed; production mutation not authorized**

Phase 6 is the operational release and same-project cutover described in
`ModifyV2-plan.md`. It is not complete merely because the Phase 0–5 code is
committed or a compatibility-shaped API is deployed.

## Current decision

The 2026-09-21 read-only production preflight found mandatory stop conditions:

1. the production database is unstamped and differs from the frozen legacy
   schema used to validate the Alembic path;
2. production has no `boq_v2_*` tables, while the deployed backend queries the
   V2 source table from retained Dashboard reads;
3. three Dashboard summary requests returned HTTP 500 on the current backend
   revision;
4. automated backups and point-in-time recovery are disabled, the newest
   successful backup is from 2026-07-30, and no restore drill is evidenced;
5. the deployed images cannot be mapped to a Git SHA through available build
   provenance, and the MCP revision predates the Phase 5 implementation;
6. the repository working tree contains unrelated uncommitted Daily Reports
   and frontend changes, so it is not a safe deployment source; and
7. no intended production project or approving Owner has been designated.

No deployment, migration, database write, backup/config change, IAM change,
feature enablement, or cutover was performed.

## Review package

- [Production preflight evidence](evidence/production-preflight-2026-09-21.md)
- [PostgreSQL 18 migration rehearsal](evidence/pg18-migration-rehearsal-2026-09-21.md)
- [Production schema drift review](schema-drift-review.md)
- [Cutover plan](cutover-plan.md)
- [Rollback plan](rollback-plan.md)
- [Approval record template](approval-record.md)

The preflight must be reviewed and the applicable authority rows in the
approval record must be completed before any production mutation. Approval of
one stage does not authorize a later stage.

## Completion boundary

Phase 6 remains incomplete until all ten completion criteria in the goal are
proved: additive migrations, healthy compatibility release, sync freeze,
explicit Owner cutover, one V2 source for the named project, preserved finance,
production smoke/UAT, clean monitoring, viable rollback, and a complete action
and approval record.
