# Phase 6 production authority and approval record

Blank fields mean **not approved**. Chat approval must
be copied here with approver identity, timestamp, exact scope, and evidence
reference before execution. A broad request such as “continue Phase 6” does not
authorize production mutation.

## Release identity

- Git SHA for recovery tooling: `6cf1ada`
- Recovery authority record: `62e5661`
- Backend image digest: _not approved_
- Frontend image digest: _not approved_
- MCP image digest: _not approved_
- Target GCP project/region: `project001-489710` / `asia-southeast1`
- Target Cloud SQL instance: `project-001`
- Intended application project ID/name: _not designated; the supplied
  `project001-489710` is the GCP project ID_
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
| Apply approved baseline stamp and additive migrations | — | — | — | — | NOT APPROVED |
| Deploy immutable compatibility images | — | — | — | — | NOT APPROVED |
| Change central BOQ V2 feature configuration | — | — | — | — | NOT APPROVED |
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

## Approval boundary recorded 2026-09-21

The Business Owner explicitly withheld deployment, baseline stamp, migration,
V2 feature enablement, application data creation, project cutover, and source
activation until the restore drill passed. The restore drill has now passed,
but that prerequisite does not grant any later authority. Those rows remain
`NOT APPROVED` until separately approved with exact scope.
