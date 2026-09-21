# Phase 6 production cutover plan

Status: **proposal for review; not execution authority**

Every stage is fail-closed. An approval for a preparatory stage does not approve
migration, deployment, feature enablement, test-data writes, or source
activation. Record each approval separately in `approval-record.md`.

## Stage 0 — Clear preflight blockers

1. Preserve the unrelated dirty-worktree changes outside the release source.
   Build from a clean checkout of the reviewed Phase 5 commit or a later focused
   remediation commit.
2. Build backend, frontend, and MCP images with immutable Git-SHA tags. Record
   source SHA, build ID, image digest, dependency lock state, and deployer.
3. Diagnose the current Dashboard HTTP 500 without production writes. Repair and
   re-run retained-flow regression if the confirmed cause is code rather than
   only missing migration order.
4. Review `schema-drift-review.md`. Explicitly preserve the legacy hierarchy
   columns/index and finance/accounting data. Approve an exact allowlisted,
   non-destructive stamp/reconciliation decision; do not normalize drift by
   dropping data or rerunning historical manual SQL.
5. Validate the path on PostgreSQL 18 with `vector` 0.8.1, not only the Phase 5
   PostgreSQL 16 harness.

Exit evidence: clean SHA, three immutable image digests, Dashboard root-cause
record, approved schema-drift matrix, and passing focused/full regressions.

## Stage 1 — Establish recovery readiness

Requires explicit cloud-production authority.

1. Enable and verify the approved automated backup and PITR policy.
2. Take a fresh on-demand backup immediately before the rehearsal window.
3. Restore/clone that backup to an isolated non-production target.
4. Verify target isolation, database/extension versions, schema fingerprint,
   critical row counts, legacy BOQ/history access, and application connectivity.
5. Record measured restore duration, verification duration, RPO, RTO, backup ID,
   restored target ID, operator, timestamps, and cleanup owner.

Exit evidence: successful restore drill and documented RPO/RTO. A backup that
has not been restored and checked does not clear this stage.

## Stage 2 — Rehearse the production-specific migration

Run only on the isolated restored target.

1. Compare the restored schema with the frozen baseline and approved drift
   matrix.
2. Abort if any unapproved table, column, constraint, index, extension, or data
   invariant differs.
3. After the schema is explicitly accepted as the production baseline, stamp
   `20260915_0000`; never execute that baseline revision against populated
   production.
4. Upgrade additively in order:
   `20260915_0001` → `20260917_0002` → `20260917_0003`.
5. Run Alembic current/autogenerate checks and the schema verifier.
6. Verify 22 V2 tables, zero implicit V2 source activation, unchanged legacy
   counts/IDs/finance references, and a second upgrade no-op.
7. Run backend startup and authenticated Project/Dashboard/Funds/Input/Daily
   Reports/OCR/FlowAccount/Chat/MCP retained-flow smoke against the clone.

Exit evidence: exact command transcript, before/after fingerprints and
revision, invariant results, application smoke, duration, and approved drift
deviations.

## Stage 3 — Compatibility maintenance window

Requires explicit migration and deployment authority naming the target project,
region, revisions, image digests, migration range, and operators.

1. Capture live revision/digest/config/schema/row-count/log baselines and create
   the final fresh backup.
2. Confirm legacy sync endpoints reject submissions, no external worker is
   active, and bounded logs show no pending calls. Freeze new V2 mutations too.
3. Re-run the schema preflight. Abort on any difference from the approved clone
   rehearsal.
4. Stamp only the approved production baseline, then apply `0001` through
   `0003`. Record each revision and timing.
5. Deploy the exact immutable compatible backend, frontend, and MCP digests.
   Keep `BOQ_V2_ENABLED=false`; do not activate a project source.
6. Verify startup, migration head, health, auth, role boundaries, 410 sync
   behavior, and retained Project/Dashboard/Funds/Input/Daily Reports/OCR/
   FlowAccount/Chat/MCP flows. Confirm there are no critical logs.

Exit evidence: migration/deployment transcript, `20260917_0003`, 22 V2 tables,
healthy retained flows, exact final revisions/digests, and no source rows.

## Stage 4 — Enable controlled V2 authoring and production UAT

Requires separate feature/config authority and designated non-destructive data.

1. Enable `BOQ_V2_ENABLED` centrally; do not hardcode project IDs.
2. Use only the named production project and Owner-approved data.
3. Verify native create/read/save/reload, hierarchy, quotation lifecycle,
   accepted snapshots, vendor cost/Price Database, private export authorization,
   conflicts/idempotency, completeness, Funds gating, and role permissions.
4. Preserve all legacy rows and historical readers. Do not activate V2 from
   migration or feature enablement.
5. Produce the exact cutover preview below.

### Required cutover preview

Record, without confidential raw line pricing in logs:

- project ID/name and approving Owner identity;
- current source kind/version and legacy budget projection;
- candidate accepted MAIN/alternative revision and immutable snapshot IDs;
- ordered accepted ADD/DEDUCT change-order IDs and signed amounts;
- resulting net sell ex-VAT and calculation version;
- published cost-plan ID/version, completeness, missing component IDs, forecast
  cost/margin or `UNKNOWN_COST` state;
- projected Funds capacity/deficit and allocation eligibility;
- resulting baseline ID/version and source version; and
- legacy finance, payment, transaction, allocation, and BOQ reference counts.

If the preview is invalid, incomplete, stale, or contains `UNKNOWN_COST` that
the Owner has not explicitly accepted, stop.

## Stage 5 — Explicit Owner cutover

Requires the Owner to approve the exact immutable preview, not a generic Phase 6
request.

1. Re-read and compare the candidate versions under the project budget lock.
2. Atomically create/activate the V2 baseline and source selection using the
   existing audited service command.
3. Record actor, timestamp, project, baseline/version, MAIN/CO snapshot IDs,
   cost-plan version, calculation version, previous source/version, resulting
   source version, idempotency key, reason, and audit event.
4. Confirm legacy plus V2 were not summed and exactly one current source exists.

Do not run a direct SQL source flip.

## Stage 6 — Post-cutover verification and monitoring

Immediately verify:

- the named V2 source/baseline/version is the only active source;
- Project, Dashboard, Funds, Chat, Insights, and MCP agree on source identity
  and sell/forecast semantics;
- historical installments, transactions, payments, allocations, legacy BOQ IDs,
  and as-of reads are unchanged and not duplicated;
- accepted snapshots and exports reproduce and remain privately authorized;
- sync endpoints remain frozen and no old client can overwrite current intent;
- Owner/Admin/customer/subcontractor permissions match validated behavior; and
- no critical startup, save, lifecycle, export, conflict, baseline, allocation,
  latency, or audit errors appear during the agreed observation window.

Record the observation-window duration and quantitative error/latency evidence.
Do not claim Phase 6 complete before the window ends successfully.
