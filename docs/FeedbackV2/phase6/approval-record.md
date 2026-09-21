# Phase 6 production authority and approval record

Blank fields mean **not approved**. Chat approval must
be copied here with approver identity, timestamp, exact scope, and evidence
reference before execution. A broad request such as “continue Phase 6” does not
authorize production mutation.

## Release identity

- Git SHA for recovery tooling/evidence: `6cf1ada`
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
| Enable backup/PITR policy | `project001-489710` / `project-001`; preserve `14:00 UTC` window; 30 retained automated backups; PITR with 14 retained transaction-log days | Chonlathan Wisetwongsa | `2026-09-21T09:59:08Z` | User approval in Codex thread `01a09eff-59ee-7990-8181-de02ba545998` | APPROVED |
| Create fresh on-demand backup | Same instance; standard on-demand backup; do not manually delete before `2026-12-20T09:59:08Z` (90 days) | Chonlathan Wisetwongsa | `2026-09-21T09:59:08Z` | User approved retention range 30–90 days; 90-day boundary selected | APPROVED |
| Create isolated restore/clone drill target | Restore the fresh backup to a new temporary instance in `asia-southeast1`; no application wiring; verify read-only; delete only the temporary instance after evidence while retaining the backup | Chonlathan Wisetwongsa | `2026-09-21T09:59:08Z` | User explicitly approved isolated restore drill | APPROVED |
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

_No production actions recorded._

## Approval boundary recorded 2026-09-21

The Business Owner explicitly withheld deployment, baseline stamp, migration,
V2 feature enablement, application data creation, project cutover, and source
activation until the restore drill passes. Those rows remain `NOT APPROVED`.
