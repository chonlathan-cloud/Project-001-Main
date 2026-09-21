# Phase 6 — Controlled Production Handoff

> **Environment classification correction (2026-09-21):** repository
> environment ownership and the Business Owner confirm that
> `projects-001-fe`, `projects-001-be`, and `project-001` are the demo
> environment. Production beta is the separate `*-beta` service set and
> `project-001-beta`. The earlier compatibility work in this directory targeted
> demo despite using “production” in evidence filenames/text. Production beta
> was not migrated or deployed by that work. See the
> [demo rollout evidence](evidence/demo-v2-rollout-2026-09-21.md).

Status: **DEMO ENABLED — demo migration, compatibility deployment, and BOQ V2
feature enablement passed; production-beta migration/deployment and all
cutover actions remain unapproved**

Phase 6 is the operational release and same-project cutover described in
`ModifyV2-plan.md`. It is not complete merely because the Phase 0–5 code is
committed or a compatibility-shaped API is deployed.

## Current decision

The 2026-09-21 read-only preflight of what was then assumed to be the
production target found mandatory stop conditions. The later environment
classification correction identifies that target as demo. Approved recovery
work resolved its backup/restore prerequisite:
automated backups and seven-day PITR are enabled, fresh on-demand backup
`1789985068799` is successful, and an isolated restore matched all 15 source
tables by row count and content hash. The temporary restore instance was then
deleted while the source and backup were retained.

The subsequent data-bearing restored-clone rehearsal also passed: the exact
demo profile was stamped at `20260915_0000`, upgraded additively through
`20260917_0003`, retained all legacy content hashes, created exactly 22 empty
V2 tables, activated no source, and returned Dashboard/Project/Funds/Input
reads successfully with V2 disabled. The rehearsal instance was deleted.

Demo was subsequently stamped and upgraded through `20260917_0003`.
Exact-digest compatibility images are serving 100% on all three services with
schema/data invariants, public health, fail-closed behavior, configuration
preservation, and bounded error-log gates passing. The Owner then authorized
demo-only feature enablement. Backend revision `projects-001-be-00133-mwt` and
frontend revision `projects-001-fe-00062-l9k` now expose BOQ V2 in demo.
`Renovation The Mall` exists as demo project
`57cbf401-4870-4a13-b548-96445dc1c8f5`, and its empty Native BOQ workspace was
verified through the authenticated UI.

The remaining stop conditions are:

1. the Owner has not yet completed the demo BOQ business-flow walkthrough;
2. production beta has not undergone its own backup, schema preflight,
   migration, immutable deployment, or UAT; and
3. no production-beta source activation or cutover preview has been approved.

No IAM change, production-beta mutation, V2 draft write, budget-source
activation, or cutover was performed. Demo mutations were limited to the
approved backup/PITR work, additive schema migration, exact-digest deployment,
creation of the synthetic project record, and demo-only feature enablement.

## Review package

- [Production preflight evidence](evidence/production-preflight-2026-09-21.md)
- [Recovery-readiness evidence](evidence/recovery-readiness-2026-09-21.md)
- [Data-bearing migration rehearsal](evidence/data-bearing-migration-rehearsal-2026-09-21.md)
- [Production migration and compatibility release](evidence/production-migration-and-compatibility-release-2026-09-21.md)
- [Demo BOQ V2 rollout and production-beta parity packet](evidence/demo-v2-rollout-2026-09-21.md)
- [PostgreSQL 18 migration rehearsal](evidence/pg18-migration-rehearsal-2026-09-21.md)
- [Production schema drift review](schema-drift-review.md)
- [Proposed fail-closed schema profile](evidence/production-schema-profile-2026-09-21.json)
- [Cutover plan](cutover-plan.md)
- [Rollback plan](rollback-plan.md)
- [Approval record template](approval-record.md)

The production-beta preflight and applicable authority rows must be completed
before any production-beta mutation. Demo approval does not authorize beta.

## Completion boundary

The demo rollout is ready for Owner exploration but Phase 6 remains incomplete
until production beta separately proves the required migrations, healthy
release, sync freeze, UAT, clean monitoring, rollback, explicit Owner cutover,
and one approved V2 source for the chosen beta project.
