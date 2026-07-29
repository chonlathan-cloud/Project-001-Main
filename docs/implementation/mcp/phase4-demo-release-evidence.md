# Phase 4 Demo release evidence

Evidence date: 2026-07-29
Environment: Demo (`project001-489710`, `asia-southeast1`)
Pilot role: Owner only
Status: passed

This report is the live gate for Project Operations and Product Audit. Evidence
below is bounded and contains no OAuth token, prompt, document body, share link,
signed URL, storage path or private content.

## Release baseline

| Item | Evidence | Result |
|---|---|---:|
| Repository commits | Phase 4 `88ffd28`; audit preflight `e60e9c6`; Cloud Run text-audit fix `5d75aad`; deterministic traffic routing `cb16046` | Pass |
| Database safety point | Demo Cloud SQL backup `1785321888841`, `SUCCESSFUL`, description `pre-phase4-mcp-demo-88ffd28-20260729` | Pass |
| Backend revision | `projects-001-be-00120-6zk`, 100% traffic, `/health` OK, 27 internal MCP contracts | Pass |
| MCP revision | `projects-001-mcp-00007-ztw`, image tag `cb16046a8200`, 100% traffic, reports `0.4.0` | Pass |
| Rollout cohort | Backend runtime has `MCP_ALLOWED_ROLES=owner`; Admin was not enabled | Pass |

The deployment preflight verifies the exact Demo audit resource, 90-day read
bound, sink/view existence, sink routing filter, exact view IAM and retained log
writer. It also fails if the environment mapping does not match Demo.

## Logging and Firestore prerequisites

| Gate | Evidence | Result |
|---|---|---:|
| Audit bucket/view | Bucket `projects-001-mcp-audit-demo`, region `asia-southeast1`, 90-day retention; view `projects-001-mcp-audit-demo-view` | Pass |
| Audit routing | Sink `projects-001-mcp-audit-demo-sink` restricts routing to Demo `projects-001-mcp` Product Audit events | Pass |
| View IAM | Exact view policy contains only `projects-001-mcp-demo@project001-489710.iam.gserviceaccount.com` with `roles/logging.viewAccessor` | Pass |
| Audit emission | MCP SA retains `roles/logging.logWriter`; runtime project roles are limited to log writer and Backend invoker, with no business-data write role | Pass |
| Firestore indexes | Exactly four composite indexes exist and are `READY`: `CICAgJim14AJ`, `CICAgJim18AI`, `CICAgOjXh4EJ`, `CICAgJiUpsMI` | Pass |

The dedicated view resource is:

`projects/project001-489710/locations/asia-southeast1/buckets/projects-001-mcp-audit-demo/views/projects-001-mcp-audit-demo-view`

## Live Owner tool evidence

The final live sample used Authorization Code with PKCE and the consenting Demo
Owner. The access token remained in process memory and was neither printed nor
written to disk. MCP initialization completed in `473.5 ms`; all 31 tools were
listed.

| Tool | Live assertion | Latency | Result |
|---|---|---:|---:|
| `list_inspection_items` | Project scope, bounded cursor and matching status/overdue filters | 704.8 ms | Pass |
| `get_inspection_item` | Safe event history and opaque document IDs; no storage path/signed URL/actor email | 443.9 ms | Pass |
| `list_daily_reports` | Project scope, bounded cursor and exact date/status filter | 403.8 ms | Pass |
| `get_daily_report` | Current read plus explicit immutable published-version read | 415.3 ms | Pass |
| `list_daily_report_versions` | Returned version metadata is immutable and bounded | 442.4 ms | Pass |
| `get_report_share_status` | State only; no token, token version, public link or signed URL | 363.6 ms | Pass |
| `get_dashboard_summary` | Calculation method, exact contract and source metadata present | 383.1 ms | Pass |
| `get_project_insights` | Independent source metadata and explicit partial state present | 552.4 ms | Pass |
| `search_audit_events` | Bounded dedicated-view query returned 26 allowlisted events | 1,782.7 ms | Pass |
| `get_audit_event` | Exact opaque event with allowlisted metadata only | 5,372.8 ms | Pass |

Post-restore contract assertions passed `15/15`. These additionally prove:

- generic `search` and `fetch` resolve authorized Inspection and Daily Report
  references;
- a nonexistent reference returns `NOT_FOUND_OR_FORBIDDEN` without echoing the
  requested identifier;
- Inspection and Daily Report pagination and filters remain bounded;
- explicit Daily Report version selection returns immutable state; and
- response leakage scans contain no prompt, body, credential, private key,
  signed URL, share URL or storage path.

## Security and failure gates

| Gate | Evidence | Result |
|---|---|---:|
| Cross-project Admin denial | Automated policy/contract test denies before Backend read; no Admin live pilot was enabled | Pass |
| Missing `financial_data_read` | Dashboard/insight contract test denies before source read | Pass |
| Missing `audit_log_read` | Audit contract test denies before view read | Pass |
| Mandatory audit outage | Sensitive reads fail closed before Backend/Logging source access | Pass |
| Firestore source outage | Backend Phase 4 contract returns explicit partial state and keeps sources separate | Pass |
| Source contradiction | Phase 4 `C-001` evaluator exposes `SOURCE_INCONSISTENCY` and Backend-primary calculation | Pass |
| Leakage scan | Zero forbidden fields across live tool responses and 57 Product Audit events | Pass |
| Cloud errors | Zero unexpected `ERROR` entries on Backend `00120-6zk` and MCP `00007-ztw` in the release window | Pass |

Focused security/failure verification passed `5/5`; Backend Phase 4 contracts
passed `5/5`; the complete MCP suite passed `68/68`; and Phase 4 Golden cases
G-010, G-011, G-012, G-013, G-015 and C-001 passed `6/6` (`100%`).

## Performance and audit coverage

| Gate | Evidence | Result |
|---|---|---:|
| Successful operations sample | Ten Phase 4 tools passed `10/10`; post-restore contract assertions passed `15/15` | Pass |
| Operations p95 | `5,372.8 ms`, target `<=15,000 ms` | Pass |
| Sensitive tool audit coverage | `14/14` start events have terminal events (`100%`) | Pass |
| Audit result minimization | 57/57 entries were Product Audit events; zero non-audit entries and zero forbidden fields | Pass |

The bounded Product Audit sample ran from `2026-07-29T11:15:31Z` through
`2026-07-29T11:29:32Z`. It contained 41 successful terminal events, 14 start
events, one expected denied event and one expected error event from the
fail-closed negative-reference test.

## Rollback and restore

| Service | Previous revision | Candidate revision | Evidence | Result |
|---|---|---|---|---:|
| Backend | `projects-001-be-00119-f7r` | `projects-001-be-00120-6zk` | Previous revision received 100% traffic and passed health; candidate restored to 100% and passed health | Pass |
| MCP | `projects-001-mcp-00006-v4m` | `projects-001-mcp-00007-ztw` | Previous revision received 100% traffic and passed health/Owner read behavior; candidate restored to 100%, returned 401 without OAuth and passed the 15/15 Owner post-restore assertions | Pass |

Final state is Backend `projects-001-be-00120-6zk` and MCP
`projects-001-mcp-00007-ztw`, each serving 100% of Demo traffic. No Beta resource,
SaaS resource, unrelated IAM binding or business data was changed.

## Release decision

All Phase 4 Demo live gates are passed. Phase 5 repository work and an explicitly
approved Demo release workflow are unblocked. Beta remains unchanged and requires
its own later authorization and release evidence.
