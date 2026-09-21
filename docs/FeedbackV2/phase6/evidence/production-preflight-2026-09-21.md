# Phase 6 production preflight evidence — 2026-09-21

Classification: **NO-GO**

Scope: read-only inspection of repository, Cloud Run, Cloud Logging, and Cloud
SQL metadata/schema for `project001-489710`

Region: `asia-southeast1`

Excluded resources: Cloud SQL `Project-001-saas` and Cloud Run
`project-saas-001-be` / `project-saas-001-fe`

No secret payload, credential, full connection string, or private object was
read or recorded. Database inventory queries ran in a read-only transaction.

## 1. Repository baseline

- Branch: `feature`
- HEAD: `0d83502a2cacff8b94e711160936ebbcdd802289`
- Commit: `complete phase 5 budget cutover and sync retirement`
- Remote relation: `feature...origin/feature [ahead 34]`
- Phase 5 committed baseline is present.
- The worktree is **not clean**. Nine pre-existing/unrelated paths are modified:
  - `Projects-001-BE/app/api/v1/daily_reports.py`
  - `Projects-001-BE/app/core/rate_limit.py`
  - `Projects-001-BE/app/schemas/daily_report_schema.py`
  - `Projects-001-BE/app/services/daily_report_service.py`
  - `Projects-001-BE/tests/test_daily_report_service.py`
  - `Projects-001-BE/tests/test_phase8_security.py`
  - `Projects-001-FE/Dockerfile`
  - `Projects-001-FE/src/api.js`
  - `Projects-001-FE/src/components/dailyReports/CustomerReportWorkspace.jsx`

These files were not modified, staged, or included in this Phase 6 evidence.
A release must be built from a clean worktree at a reviewed commit.

## 2. Starting production application versions

The live revisions were re-read on 2026-09-21. All received 100% of their
service traffic and reported Ready:

| Service | Revision | Created (UTC) | Deployed image digest |
| --- | --- | --- | --- |
| Backend | `projects-001-be-00131-gkw` | `2026-09-21T08:36:28.550208Z` | `sha256:1a172a4350f400f3d2625bd45b88e30f0f193f61b2116dd98b03a11cf6963b9c` |
| Frontend | `projects-001-fe-00060-l6h` | `2026-09-21T08:39:59.631248Z` | `sha256:45566c2c1f6ff8a85a72af381a9ad2d1a211925fa4926886f800b99ccafa9b64` |
| MCP | `projects-001-mcp-00013-p9v` | `2026-08-03T05:07:07.208699Z` | `sha256:35f7e2fe1d6f0de0a6a3be8f8d41a221149df2f669a7a948205b20fbe4c1d15d` |

The registry/deployment metadata available during preflight did not map these
digests to a Git SHA. The services were configured from mutable `latest` tags;
the immutable revision digests above are therefore the only proven starting
application identities. The MCP health response reports version `0.6.0` and
environment `demo`; its August revision predates the September Phase 5 commit.

## 3. Runtime configuration and compatibility surface

- Backend `APP_ENV=production`.
- `BOQ_V2_ENABLED` is absent from the backend revision; the checked-in default
  is `false`. V2 authoring is therefore expected to fail closed.
- Obsolete `BOQ_BATCH_SYNC_MAX_TABS=5` remains in runtime configuration. Phase 5
  no longer consumes it; removal is configuration hygiene, not cutover proof.
- Backend `/health`: HTTP 200.
- Frontend `/`: HTTP 200.
- MCP `/health`: HTTP 200.
- Deployed OpenAPI: 188 paths, `ProjectBudgetSnapshot` schema present, native
  `/api/v1/projects/{project_id}/boq-workspace` present, and the legacy sync
  endpoint advertises HTTP 410.

This proves a compatibility-shaped backend is deployed, but not that it is the
exact Phase 5 commit or that retained flows are healthy.

## 4. Current release-health blocker

Cloud Logging returned three HTTP 500 responses from the current backend
revision for `GET /api/v1/dashboard/summary`:

- `2026-09-21T08:42:50.204233Z`
- `2026-09-21T08:43:23.237877Z`
- `2026-09-21T08:43:25.977831Z`

No exception type was available in the bounded log result, so the root cause is
not asserted as proven. The checked-in Dashboard path calls
`load_project_budget_contexts`, which unconditionally selects
`boq_v2_project_budget_sources`; production has no such table. That is a strong
code/schema-ordering inference and must be confirmed in a restored clone or
non-secret exception trace before remediation. A green `/health` does not
satisfy the retained-flow release gate.

## 5. Production database and migration state

Target: masked Cloud SQL instance `project-001`

- State: `RUNNABLE`
- Engine: PostgreSQL `18.3` (`POSTGRES_18`)
- `vector`: `0.8.1`
- Availability: `ZONAL`
- Deletion protection: enabled
- Public tables: 15
- `alembic_version`: absent; current revision is unstamped
- `boq_v2_*` tables: 0
- Local validated head: `20260917_0003`
- Production schema fingerprint:
  `cb7206a7ef0a8d3c2a1cd0b864b1ef93a06c4f2ef5a5a36d6ac5743aef6c1b41`
- Frozen PG16 legacy-baseline fingerprint:
  `1f5ef82d148f9a809709c2a2adfdc543aaee0b5d6e7556fd7aaf218fb6a1ac5a`

The fingerprints do not match. Material recorded drift includes:

- production-only hierarchy columns on `boq_items`: `raw_wbs_level`,
  `display_wbs_level`, `row_type`, `hierarchy_status`, `source_row_index`, and
  `sort_order`, plus `ix_boq_items_active_hierarchy_order`;
- production nullability/default differences on FlowAccount/accounting fields
  in `input_requests`;
- `fund_audit_events.detail` JSONB/default differences; and
- fund constraint/default/index shape and naming differences.

PostgreSQL 18 represents some constraints differently from the validated
PostgreSQL 16 harness, so a raw diff is not itself a remediation script. The
drift must be classified and rehearsed on a restored clone. Per CDR-005,
production must not be stamped `20260915_0000` merely because it appears close,
and the baseline `upgrade()` must not be run against the populated database.

Production row-count inventory at preflight:

| Entity | Count |
| --- | ---: |
| Projects | 8 |
| Legacy BOQ items | 963 |
| Installments | 14 |
| Transactions | 8 |
| Input requests | 37 |
| Fund allocations | 3 |

These are inventory counts, not proof of business reconciliation.

## 6. Budget source and legacy sync state

- No V2 source-selection table or V2 baseline exists in production.
- No project can yet have a recorded V2 active source; all eight projects remain
  on legacy behavior by absence/default, not by an auditable V2 selection row.
- No target project, candidate accepted MAIN/CO baseline, cost-plan version, or
  approving Owner was supplied. A cutover preview cannot yet be produced.
- The deployed legacy sync endpoints advertise 410 and current-revision logs
  contained zero `boq_sync`, `sync-jobs`, or sync-path matches in the bounded
  24-hour check.
- The removed Phase 5 job store was process-local rather than persistent, so no
  database queue remains to drain. This does not prove an unknown external old
  client or worker is absent; repeat the API/log/worker inventory immediately
  before migration and cutover.

## 7. Backup and restore readiness

- Automated backups: disabled
- Point-in-time recovery: disabled
- Transaction-log retention setting: 7 days, ineffective as PITR evidence while
  PITR is disabled
- Latest successful backup: on-demand backup ending
  `2026-07-30T04:48:14.810Z`
- No restore or clone operation was found in the bounded operation history used
  for preflight.

Backup/restore readiness is **insufficient**. Before migration, require an
approved fresh backup, enabled/verified recovery policy, and a successful
restore drill into an isolated non-production target with schema and critical
row-count verification. Each action is a separate production/cloud mutation
and was not performed during preflight.

## 8. Stop-gate decision

| Gate | Result | Required evidence to clear |
| --- | --- | --- |
| Clean release source | FAIL | Clean worktree at reviewed SHA; immutable images tied to that SHA |
| Schema matches approved stamp plan | FAIL | Classified drift and successful restored-clone rehearsal |
| Migration path equals tested path | FAIL | Approved PG18/vector 0.8.1 stamp + `0001` → `0003` proof |
| Backup/restore ready | FAIL | Fresh backup plus successful isolated restore drill |
| Compatibility release healthy | FAIL | Dashboard and retained authenticated smoke pass |
| Sync submissions frozen | PARTIAL | Repeated 410/log/worker proof at window start |
| V2 data ready | NOT READY | Named project, accepted MAIN/COs, published cost plan |
| Owner approval | MISSING | Exact preview and recorded Owner approval |

Decision: **do not deploy, stamp, migrate, enable V2, write designated test
data, or activate a source until the applicable failures are remediated and the
corresponding production authority is recorded.**

## 9. Commands and evidence classes used

Read-only evidence came from:

- `git status`, `git log`, and Phase 5 evidence/runbooks;
- bounded `gcloud run services/revisions describe` queries;
- bounded Cloud Logging queries with a 24-hour freshness window;
- `gcloud sql instances describe` and `gcloud sql backups list`;
- HTTP GET health/OpenAPI checks; and
- read-only PostgreSQL inventory/fingerprint queries through Cloud SQL Auth
  Proxy, followed by proxy shutdown verification.

No deployment command, Cloud SQL update, backup creation, migration command,
database write, feature-flag change, IAM operation, or source activation ran.
