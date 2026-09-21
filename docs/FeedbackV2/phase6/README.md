# Phase 6 — Controlled Production Handoff

Status: **HOLD AFTER COMPATIBILITY RELEASE — migration and feature-disabled
deployment passed; production UAT, feature enablement, and cutover are not
authorized**

Phase 6 is the operational release and same-project cutover described in
`ModifyV2-plan.md`. It is not complete merely because the Phase 0–5 code is
committed or a compatibility-shaped API is deployed.

## Current decision

The 2026-09-21 read-only production preflight found mandatory stop conditions.
The approved recovery work has since resolved the backup/restore prerequisite:
automated backups and seven-day PITR are enabled, fresh on-demand backup
`1789985068799` is successful, and an isolated restore matched all 15 source
tables by row count and content hash. The temporary restore instance was then
deleted while the source and backup were retained.

The subsequent data-bearing restored-clone rehearsal also passed: the exact
production profile was stamped at `20260915_0000`, upgraded additively through
`20260917_0003`, retained all legacy content hashes, created exactly 22 empty
V2 tables, activated no source, and returned Dashboard/Project/Funds/Input
reads successfully with V2 disabled. The rehearsal instance was deleted.

Production was subsequently stamped and upgraded through `20260917_0003`.
Exact-digest compatibility images are serving 100% on all three services with
`BOQ_V2_ENABLED` still false. Schema/data invariants, public health,
fail-closed behavior, configuration preservation, and bounded error-log gates
passed.

The remaining stop conditions are:

1. the Owner-supplied application name `Renovation The Mall` has no exact or
   partial match among the eight projects in target database `project-001`, so
   its UUID remains unresolved;
2. authenticated Owner business-flow UAT and the external OCR/FlowAccount
   boundaries have not been executed against the compatibility release; and
3. no cutover preview has been approved by the identified Business Owner.

No IAM change, application-data write, feature enablement, source activation,
or cutover was performed. The production mutations were limited to the
explicitly approved backup/PITR work, additive schema migration, and
exact-digest compatibility image deployment.

## Review package

- [Production preflight evidence](evidence/production-preflight-2026-09-21.md)
- [Recovery-readiness evidence](evidence/recovery-readiness-2026-09-21.md)
- [Data-bearing migration rehearsal](evidence/data-bearing-migration-rehearsal-2026-09-21.md)
- [Production migration and compatibility release](evidence/production-migration-and-compatibility-release-2026-09-21.md)
- [PostgreSQL 18 migration rehearsal](evidence/pg18-migration-rehearsal-2026-09-21.md)
- [Production schema drift review](schema-drift-review.md)
- [Proposed fail-closed schema profile](evidence/production-schema-profile-2026-09-21.json)
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
