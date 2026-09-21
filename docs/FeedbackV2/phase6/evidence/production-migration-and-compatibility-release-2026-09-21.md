# Phase 6 production migration and compatibility release — 2026-09-21

> **Environment correction:** after this action, the Business Owner confirmed
> that `projects-001-*` and `project-001` are demo resources, while production
> beta is the separate `projects-001-*-beta` / `project-001-beta` environment.
> Therefore this evidence is a demo compatibility-release record despite its
> original title. No production-beta resource was changed. The subsequent flag
> enablement and reusable beta parity plan are in
> [demo-v2-rollout-2026-09-21.md](demo-v2-rollout-2026-09-21.md).

Result: **PASS for additive schema migration and feature-disabled compatibility
deployment. HOLD for production UAT, feature enablement, source activation, and
cutover.**

All timestamps below are UTC. The target was GCP project
`project001-489710`, region `asia-southeast1`, Cloud SQL instance
`project-001`, and Cloud Run services `projects-001-be`, `projects-001-fe`, and
`projects-001-mcp`. No SaaS service or database was operated on.

## Authority and release identity

The Business Owner separately approved the baseline stamp/additive migration
and the immutable compatibility deployment. The deployed images were built
from clean release source
`23ae47a9f050bccf3804b89e86bd8b30665c57de`; its application-code tip is
`30d3039`.

| Component | Artifact Registry manifest digest | Cloud Run platform digest |
| --- | --- | --- |
| Backend | `sha256:3bad885791cf7a5d4f6db9148c7123f3b54045c84550a6a1ba3c1a56f54088ae` | `sha256:57fcd0c5ef13d36f27c3df1750b71e1c766f99985437dec25ed41a4c1423eae2` |
| Frontend | `sha256:174d35b1bdf0dab4d169adae5fe500c9e13b088e1688967602c174d464d74635` | `sha256:6a91c8f6b2b0735646668583be190f640843fe0c8d9e93c8c125d928ce961f2e` |
| MCP | `sha256:b4d616f3b293c8d277e05b21a1bd352246a72d3037cd96bcf54e049a34f8b585` | `sha256:9cccee2f6ed1f4b4be5abd09fd859b9ef5aa1cd3169be81d316d2efe3c1c7ee5` |

The differing manifest/platform digests are expected: Artifact Registry stored
the BuildKit manifest index, while Cloud Run resolved its Linux platform image.

## Final backup and preflight

Cloud SQL had no pending operation. The source was `RUNNABLE`, deletion
protection was enabled, automated-backup retention was 30, and PITR retention
was seven days. A new maintenance-boundary backup was created:

- backup ID: `1789989485278`
- operation: `4043807d-9861-46ed-a020-44da00000031`
- start/end: `2026-09-21T11:18:05.289Z` /
  `2026-09-21T11:19:36.696Z`
- type/result: `ON_DEMAND` / `SUCCESSFUL`
- description: `phase6-final-pre-migration-23ae47a9f050-retain-not-before-2026-12-20`

The fail-closed schema gate then passed without a mismatch:

- PostgreSQL 18; pgvector `0.8.1`
- 15 public legacy tables; zero `boq_v2_*` tables
- no Alembic revision table and no budget-source table
- starting fingerprint
  `cb7206a7ef0a8d3c2a1cd0b864b1ef93a06c4f2ef5a5a36d6ac5743aef6c1b41`
- legacy aggregate SHA-256
  `94112d929c3e6e7152ba747cb2d6133141b1691d04101d2136e816b1d0d16320`

The 15 legacy table counts remained the rehearsed counts, including 963 BOQ
items, 8 projects, 14 installments, 8 transactions, 37 input requests, 3 fund
allocations, 8 fund buckets, and 7 fund ledger entries. No legacy sync request
was present in the bounded two-hour Cloud Run log query.

## Production migration

The migration used Cloud SQL Auth Proxy through a temporary local Unix socket;
no authorized-network or application connection configuration was changed.
The immutable current production schema was stamped, not re-created.

| Step | UTC interval | Result |
| --- | --- | --- |
| Stamp `20260915_0000` | `11:22:57`–`11:22:58` | passed |
| Upgrade `20260915_0001` | `11:23:09`–`11:23:13` | passed |
| Upgrade `20260917_0002` | `11:23:27`–`11:23:34` | passed |
| Upgrade `20260917_0003` | `11:23:44`–`11:23:50` | passed |
| Second `upgrade head` | `11:24:03`–`11:24:05` | no-op |

Post-migration invariants passed:

- current revision: `20260917_0003 (head)`
- 38 public tables and exactly 22 `boq_v2_*` tables
- all V2 business tables empty; budget-source rows zero
- invalid public indexes zero; unvalidated public constraints zero
- post-migration fingerprint
  `30759a530ce5bca72435cbcf900d2e221ae1a54033a66c24838906fb329da1ed`
- every legacy table count and content hash unchanged; aggregate remained
  `94112d929c3e6e7152ba747cb2d6133141b1691d04101d2136e816b1d0d16320`

The migration proxy was stopped, its exact temporary socket directory was
removed, and the TCP audit proxy was also stopped after final verification.

## Compatibility deployment

Images were supplied to Cloud Run by exact manifest digest. The updates were
image-only; no IAM, service account, secret, environment-variable, Cloud SQL
binding, resource, timeout, ingress, or scaling change was requested.

| Service | Previous revision | Deployed revision | Final traffic |
| --- | --- | --- | ---: |
| Backend | `projects-001-be-00131-gkw` | `projects-001-be-00132-tjj` | 100% |
| Frontend | `projects-001-fe-00060-l6h` | `projects-001-fe-00061-4bl` | 100% |
| MCP | `projects-001-mcp-00013-p9v` | `projects-001-mcp-00031-foy` | 100% |

Revision specs were canonicalized with only the container image removed. The
old and new spec hashes matched for all three services, proving configuration
preservation. `BOQ_V2_ENABLED` remained absent, so the application default
`false` applies.

MCP was deployed with zero traffic and a temporary `phase6` tag. Its tagged
health returned 200 and unauthenticated initialize returned 401 with OAuth
resource metadata. Traffic was then shifted to the new revision and the
temporary tag removed.

## Post-deployment validation

- Backend `/health`: 200 with `{"status":"ok"}`.
- Backend OpenAPI: 200 and 26 V2 BOQ/cost/vendor paths present.
- Unauthenticated V2 workspace request: 404
  `BOQ_V2_ROLLOUT_DISABLED` before authentication, proving fail-closed rollout.
- Unauthenticated retired sync request: 401 at the authentication boundary;
  the authenticated 410 contract remains covered by the executed backend tests
  and restored-clone application smoke.
- Frontend root: 200 `text/html`.
- MCP canonical health: 200; unauthenticated initialize: 401 with
  `resource_metadata` challenge.
- Bounded new-revision request logs: backend 8×200, 1×401, 1×404; frontend
  2×200; MCP 2×200, 2×401.
- Bounded error query across the three new revisions: no HTTP 5xx or
  severity-ERROR entries.
- Final database audit: revision `20260917_0003`, 22 V2 tables, every V2 table
  empty, and zero budget-source rows.

Pre-build validation was backend `172 passed, 15 skipped`, frontend `10
passed` plus lint/build, and MCP 133 tests passed with one existing Starlette
deprecation warning. The frontend production build retained its existing
large-chunk warning. Docker's npm install audit reported 10 dependency
findings (4 moderate, 6 high); these were not auto-fixed during the controlled
release and remain follow-up risk.

## Hold boundary

The Owner-supplied name `Renovation The Mall` still has no exact or partial
match among the eight projects in target database `project-001`; the final
post-deployment query also returned zero matches. Therefore an exact
application project UUID cannot be selected without new evidence.

No production UAT data was created, no V2 feature configuration was enabled,
no budget source was activated, and no cutover was performed. Authenticated
Owner business-flow UAT and external OCR/FlowAccount boundaries were not
exercised by this compatibility smoke. Phase 6 must remain on hold until the
correct environment/project is identified and the later UAT and cutover
authorities are separately granted.
