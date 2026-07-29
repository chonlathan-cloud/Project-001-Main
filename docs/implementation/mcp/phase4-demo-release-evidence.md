# Phase 4 Demo release evidence

Evidence date: pending
Environment: Demo (`project001-489710`, `asia-southeast1`)
Pilot role: Owner only
Status: not started

This report is the live gate for Project Operations and Product Audit. Do not
mark an item passed without retaining a bounded, non-sensitive command result or
test artifact. Never paste OAuth tokens, prompts, document bodies, share links,
signed URLs, storage paths or private log content into this file.

## Release baseline

| Item | Required evidence | Result |
|---|---|---:|
| Repository commit | Tested Phase 4 commit SHA and clean/understood worktree | Pending |
| Database safety point | Demo backup ID recorded before Backend rollout | Pending |
| Backend revision | Revision containing 27 internal MCP contracts | Pending |
| MCP revision | Revision reporting version `0.4.0` | Pending |
| Rollout cohort | `MCP_ALLOWED_ROLES=owner`; no Admin enablement | Pending |

## Logging and Firestore prerequisites

| Gate | Required evidence | Result |
|---|---|---:|
| Audit bucket/view | Exact environment-locked `MCP_AUDIT_LOG_VIEW` exists | Pending |
| Audit routing | Only Product Audit events are routed into the view | Pending |
| View IAM | Demo MCP SA has view-level accessor; no unrelated-log/Beta/SaaS read | Pending |
| Audit emission | Existing log-writer behavior remains intact | Pending |
| Firestore indexes | Four Phase 4 indexes from `infra/gcp/firestore.indexes.json` are `READY` | Pending |

## Live tool evidence

Run with an authorized Demo Owner and sanitized records.

| Tool | Required assertion | Result |
|---|---|---:|
| `list_inspection_items` | Project scoped; open/overdue filter; bounded cursor | Pending |
| `get_inspection_item` | Safe event history and opaque document IDs; no path/URL | Pending |
| `list_daily_reports` | Project/date/status scope; bounded cursor | Pending |
| `get_daily_report` | Current content and explicit immutable version behavior | Pending |
| `list_daily_report_versions` | Stable immutable metadata; no source expansion | Pending |
| `get_report_share_status` | State only; no token, link or token version | Pending |
| `get_dashboard_summary` | Exact money, period trend, sources and calculation method | Pending |
| `get_project_insights` | Independent sources; explicit partial/conflict behavior | Pending |
| `search_audit_events` | Allowlisted metadata only; bounded view query | Pending |
| `get_audit_event` | Exact opaque event; no prompt/document body | Pending |

Also prove that generic `search` and `fetch` resolve authorized Inspection and
Daily Report references and that a non-existent or out-of-scope reference returns
`NOT_FOUND_OR_FORBIDDEN` without existence disclosure.

## Security and failure gates

| Gate | Required evidence | Result |
|---|---|---:|
| Cross-project Admin denial | Automated only unless Admin pilot is separately approved | Pending |
| Missing `financial_data_read` | Dashboard/insight source read does not start | Pending |
| Missing `audit_log_read` | Audit view read does not start | Pending |
| Mandatory audit outage | Sensitive Backend/Logging read does not start | Pending |
| Firestore source outage | Insight returns explicit partial result; no fabricated facts | Pending |
| Source contradiction | `SOURCE_INCONSISTENCY` and Backend-primary calculation are visible | Pending |
| Leakage scan | Zero prompt/body/token/secret/share URL/signed URL/storage path matches | Pending |
| Cloud errors | Zero unexpected ERROR entries in the bounded release window | Pending |

## Performance and audit coverage

| Gate | Target | Result |
|---|---:|---:|
| Successful operations sample | Record request count and bounded time window | Pending |
| Operations p95 | `<=15 seconds` | Pending |
| Sensitive tool audit coverage | 100% start and terminal events | Pending |
| Audit result minimization | 0 prompt/document-body/private-content fields | Pending |

## Rollback and release decision

Record the previous Backend and MCP revisions before rollout. Move traffic back,
verify public health, fail-closed authentication and one authorized Owner read,
then restore the candidate revisions and repeat those checks.

Phase 4 is complete in Demo only when every gate above is passed. Until then,
Phase 5 release work remains blocked; repository planning may continue without
changing cloud state.
