# Phase 6 production authority and approval record

> **Environment correction (2026-09-21):** the recorded target
> `projects-001-*` / `project-001` is demo. Production beta is
> `projects-001-*-beta` / `project-001-beta` and was not operated on under the
> authorities below. Later production-beta work requires new, explicit
> approvals. See the [demo rollout and parity packet](evidence/demo-v2-rollout-2026-09-21.md).

Blank fields mean **not approved**. Chat approval must
be copied here with approver identity, timestamp, exact scope, and evidence
reference before execution. A broad request such as “continue Phase 6” does not
authorize production mutation.

## Release identity

- Git SHA for recovery tooling: `6cf1ada`
- Recovery authority record: `62e5661`
- Clean candidate release source: `23ae47a9f050bccf3804b89e86bd8b30665c57de`
- Application-code tip within candidate: `30d3039`
- Backend image digest: `sha256:3bad885791cf7a5d4f6db9148c7123f3b54045c84550a6a1ba3c1a56f54088ae`
- Frontend image digest: `sha256:174d35b1bdf0dab4d169adae5fe500c9e13b088e1688967602c174d464d74635`
- MCP image digest: `sha256:b4d616f3b293c8d277e05b21a1bd352246a72d3037cd96bcf54e049a34f8b585`
- Deployed revisions: backend `projects-001-be-00132-tjj`; frontend
  `projects-001-fe-00061-4bl`; MCP `projects-001-mcp-00031-foy`
- Target GCP project/region: `project001-489710` / `asia-southeast1`
- Target Cloud SQL instance: `project-001`
- Demo application project: `Renovation The Mall`, UUID
  `57cbf401-4870-4a13-b548-96445dc1c8f5` (Owner-authorized synthetic record in
  demo database `project-001`)
- Production operator: Codex using the current authenticated gcloud principal;
  the Cloud SQL operation ledger is authoritative for principal identity
- Business Owner: `Chonlathan Wisetwongsa` (self-identified by the requesting
  user; local Git identity corroborates the display name)

## Independent authorities

| Action | Exact approved scope | Approver | Timestamp | Evidence/result | Status |
| --- | --- | --- | --- | --- | --- |
| Enable backup/PITR policy | `project001-489710` / `project-001`; preserve `14:00 UTC` window; 30 retained automated backups; PITR within approved 7–14 day range | Chonlathan Wisetwongsa | `2026-09-21T09:59:08Z` | Effective transaction-log retention is 7 days, the Cloud SQL Enterprise maximum; operation `4e075804-e5f5-4452-b7bd-2e8e00000031` | EXECUTED |
| Create fresh on-demand backup | Same instance; standard on-demand backup; do not manually delete before `2026-12-20T09:59:08Z` (90 days) | Chonlathan Wisetwongsa | `2026-09-21T09:59:08Z` | Backup `1789985068799`; operation `a4139256-040d-4193-9bcd-2cc200000031` | EXECUTED |
| Create isolated restore/clone drill target | Restore the fresh backup to a new temporary instance in `asia-southeast1`; no application wiring; verify read-only; delete only the temporary instance after evidence while retaining the backup | Chonlathan Wisetwongsa | `2026-09-21T09:59:08Z` | [Recovery-readiness evidence](evidence/recovery-readiness-2026-09-21.md); restore passed and temporary instance was deleted | VERIFIED / CLEANED UP |
| Apply approved baseline stamp and additive migrations | Rehearse first on an isolated restore of backup `1789985068799`; only after every rehearsal/preflight invariant passes, stamp `20260915_0000` on `project001-489710` / `project-001` and upgrade additively through `20260917_0003`; preserve all legacy objects/data; no downgrade, V2 source row, or cutover | Chonlathan Wisetwongsa | `2026-09-21T10:45:21Z` | [Production migration and compatibility evidence](evidence/production-migration-and-compatibility-release-2026-09-21.md); all invariants passed | EXECUTED / VERIFIED |
| Deploy immutable compatibility images | Build from clean reviewed release SHA `23ae47a9f050bccf3804b89e86bd8b30665c57de`, record immutable digests, and deploy to `projects-001-be`, `projects-001-fe`, and `projects-001-mcp` in `asia-southeast1`; preserve existing runtime configuration and keep `BOQ_V2_ENABLED=false`; no UAT write, project source activation, or cutover | Chonlathan Wisetwongsa | `2026-09-21T10:45:21Z` | [Production migration and compatibility evidence](evidence/production-migration-and-compatibility-release-2026-09-21.md); image-only deployment passed health, fail-closed, config-preservation, traffic, and bounded-log gates | EXECUTED / VERIFIED |
| Create synthetic demo project | Create `Renovation The Mall` in demo only with type `COMMERCIAL`, status `ACTIVE`, VAT 7%, and zero initial fallback budget; no BOQ draft or source activation | Chonlathan Wisetwongsa | `2026-09-21T15:02:35Z` | Project `57cbf401-4870-4a13-b548-96445dc1c8f5`; [demo rollout evidence](evidence/demo-v2-rollout-2026-09-21.md) | EXECUTED / VERIFIED |
| Enable BOQ V2 in demo | Add fail-closed frontend flag wiring; enable `BOQ_V2_ENABLED=true` on `projects-001-be`; deploy `projects-001-fe` built with `VITE_BOQ_V2_ENABLED=true`; preserve all other configuration; do not modify `*-beta` services or `project-001-beta` | Chonlathan Wisetwongsa | `2026-09-21` current Codex turn | [Demo rollout and production-beta parity packet](evidence/demo-v2-rollout-2026-09-21.md) | EXECUTED / VERIFIED |
| Change production-beta central BOQ V2 feature configuration | — | — | — | — | NOT APPROVED |
| Create/use designated production UAT data | — | — | — | — | NOT APPROVED |
| Activate exact V2 baseline/source preview | — | — | — | — | NOT APPROVED |
| Roll back application/configuration | — | — | — | — | NOT APPROVED |
| Change active budget source back to legacy | — | — | — | — | NOT APPROVED |

## Owner cutover approval

- Preview artifact/version: _missing_
- Current legacy source/version: _missing_
- Candidate MAIN/alternative snapshot: _missing_
- Accepted ADD/DEDUCT snapshots: _missing_
- Candidate baseline/source versions: _missing_
- Cost-plan ID/version and completeness: _missing_
- Projected Funds impact: _missing_
- Known `UNKNOWN_COST` exception explicitly accepted: _none / not approved_
- Owner approval statement: _missing_
- Owner identity: _missing_
- Approval timestamp: _missing_
- Activation audit event: _not executed_

## Final production action log

Append each action in timestamp order with command/action category, operator,
approved scope reference, result, and evidence location. Never include secrets,
connection strings, tokens, or confidential raw pricing payloads.

| Timestamp (UTC) | Action | Result | Evidence |
| --- | --- | --- | --- |
| `2026-09-21T10:00:36Z` | Enable automated backups/PITR on `project-001` | DONE; 30 backups, 7-day PITR, existing `14:00 UTC` window | Operation `4e075804-e5f5-4452-b7bd-2e8e00000031`; [recovery evidence](evidence/recovery-readiness-2026-09-21.md) |
| `2026-09-21T10:04:28Z` | Create fresh standard on-demand backup | DONE; backup `1789985068799` SUCCESSFUL | Operation `a4139256-040d-4193-9bcd-2cc200000031`; [recovery evidence](evidence/recovery-readiness-2026-09-21.md) |
| `2026-09-21T10:07:33Z` | Restore backup to isolated temporary instance | DONE; schema and all 15 table contents verified | Operation `a91fe354-bb8a-4d6b-88cc-e37a00000031`; [recovery evidence](evidence/recovery-readiness-2026-09-21.md) |
| `2026-09-21T10:17:02Z` | Disable deletion protection on temporary drill instance only | DONE | Operation `3e203ba6-8d6a-43d3-9d5b-897900000031` |
| `2026-09-21T10:17:19Z` | Delete temporary drill instance only | DONE; source instance and backup retained | Operation `dada1c2f-0db9-4b38-86d7-00d500000031`; [recovery evidence](evidence/recovery-readiness-2026-09-21.md) |
| `2026-09-21T10:46:05Z` | Restore backup to isolated data-bearing migration-rehearsal instance | DONE | Operation `d79ef0c4-6c85-4796-adf9-06c400000031`; [migration rehearsal](evidence/data-bearing-migration-rehearsal-2026-09-21.md) |
| `2026-09-21T10:54:08Z` | Stamp `20260915_0000` and upgrade temporary rehearsal instance through `20260917_0003` | DONE; 22 empty V2 tables, no source activation, legacy hash unchanged | [Migration rehearsal](evidence/data-bearing-migration-rehearsal-2026-09-21.md) |
| `2026-09-21T10:59:53Z` | Disable deletion protection on temporary migration-rehearsal instance only | DONE | Operation `986412db-2a7a-4cf2-91fb-25aa00000031` |
| `2026-09-21T11:00:08Z` | Delete temporary migration-rehearsal instance only | DONE; source instance and backup retained | Operation `37b9dd01-7937-4c45-abbd-44c100000031`; [migration rehearsal](evidence/data-bearing-migration-rehearsal-2026-09-21.md) |
| `2026-09-21T11:18:05Z` | Create final pre-migration on-demand backup | DONE; backup `1789989485278` SUCCESSFUL and retained through at least `2026-12-20` | Operation `4043807d-9861-46ed-a020-44da00000031`; [production evidence](evidence/production-migration-and-compatibility-release-2026-09-21.md) |
| `2026-09-21T11:22:57Z` | Stamp production baseline `20260915_0000` | DONE after exact profile gate | [Production evidence](evidence/production-migration-and-compatibility-release-2026-09-21.md) |
| `2026-09-21T11:23:09Z` | Upgrade production through `20260917_0003` | DONE; second `upgrade head` no-op; legacy hashes unchanged; 22 empty V2 tables; source rows zero | [Production evidence](evidence/production-migration-and-compatibility-release-2026-09-21.md) |
| `2026-09-21T11:25:30Z` | Deploy exact backend image digest | DONE; revision `projects-001-be-00132-tjj`, 100% traffic, health/fail-closed/log gates passed | [Production evidence](evidence/production-migration-and-compatibility-release-2026-09-21.md) |
| `2026-09-21T11:26:41Z` | Deploy exact frontend image digest | DONE; revision `projects-001-fe-00061-4bl`, 100% traffic, root health passed | [Production evidence](evidence/production-migration-and-compatibility-release-2026-09-21.md) |
| `2026-09-21T11:27:46Z` | Deploy exact MCP image digest with zero traffic and temporary tag | DONE; revision `projects-001-mcp-00031-foy`, tagged health and fail-closed auth passed | [Production evidence](evidence/production-migration-and-compatibility-release-2026-09-21.md) |
| `2026-09-21T11:29:33Z` | Finalize MCP canonical traffic and remove temporary tag | DONE; `projects-001-mcp-00031-foy` serves 100% | [Production evidence](evidence/production-migration-and-compatibility-release-2026-09-21.md) |
| `2026-09-21T15:02:35Z` | Create synthetic project `Renovation The Mall` in demo through the authenticated UI | DONE; UUID `57cbf401-4870-4a13-b548-96445dc1c8f5`; no BOQ draft/source | [Demo rollout evidence](evidence/demo-v2-rollout-2026-09-21.md) |
| `2026-09-21T15:13:17Z` | Enable backend BOQ V2 flag in demo | DONE; revision `projects-001-be-00133-mwt`, 100% traffic, health/auth/log gates passed | [Demo rollout evidence](evidence/demo-v2-rollout-2026-09-21.md) |
| `2026-09-21T15:13:52Z` | Deploy V2-enabled frontend image to demo | DONE; revision `projects-001-fe-00062-l9k`, 100% traffic, bundle/browser/log gates passed | [Demo rollout evidence](evidence/demo-v2-rollout-2026-09-21.md) |

## Approval boundary recorded 2026-09-21

The Business Owner explicitly withheld deployment, baseline stamp, migration,
V2 feature enablement, application data creation, project cutover, and source
activation until the restore drill passed. The restore drill passed, and the
Owner subsequently granted the migration and compatibility-deployment
authorities recorded above. Feature enablement, application data creation,
project cutover, source activation, and rollback remain `NOT APPROVED`. The
approved migration and compatibility deployment have now been executed and
verified without exercising any of those withheld authorities.
