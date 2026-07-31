# Phase 5 Demo release evidence

Evidence date: 2026-07-31
Environment: Demo (`project001-489710`, `asia-southeast1`)
Pilot roles: Owner, then one explicitly authorized Admin
Status: live validation in progress; targeted audit, latency and rollback gates passed

This file is the live release gate for Curated GCP Operations, Internal Chat and
Admin MCP access. Do not mark a row passed from repository tests alone. Evidence
must omit OAuth tokens, prompts, document bodies, raw log queries, URLs, email
addresses, GCS paths, record UUIDs, service-account credentials and private
content.

## Release baseline

| Item | Evidence | Result |
|---|---|---:|
| Repository commit | `4d4010a`; Product Audit routing and opaque record correlation hardening | Passed |
| Database safety point | Successful pre-Phase 5 Demo backup `1785386813588` recorded before rollout | Passed |
| Backend revision | `projects-001-be-00123-thg`; 28 service-authenticated MCP contracts | Passed |
| MCP revision | `projects-001-mcp-00012-sbs`; reports `0.5.0` and lists 37 tools | Passed |
| Frontend revision | `projects-001-fe-00051-7f6`; Owner MCP controls deployed | Passed |
| Rollout cohort | Owner first; one named-by-opaque-ID assigned Admin only after Owner pass | Pending |

## Operational Logging and IAM

| Gate | Required evidence | Result |
|---|---|---:|
| Operational bucket | `projects-001-mcp-ops-demo`, `asia-southeast1`, exactly 30-day retention | Pending |
| Sink filter | Exact resource type, region and three Demo Product services with `severity>=WARNING` | Pending |
| View filter | Exact resource type and region plus anchored regex `^(projects-001-fe\|projects-001-be\|projects-001-mcp)$`; severity already enforced by the sink | Pending |
| View IAM | Exact view grants the Demo MCP identity `roles/logging.viewAccessor` | Pending |
| Metadata IAM | Effective permissions are limited to approved Product resource metadata; no write/secret/BigQuery access | Pending |
| Excluded resources | No SaaS Cloud Run/Cloud SQL resource is queried, listed or returned | Pending |
| Deployment preflight | `./deploy_mcp.sh --preflight-only` passes against the exact Demo configuration | Pending |

## Live Owner evidence

| Tool | Required assertion | Latency | Result |
|---|---|---:|---:|
| `get_system_health` | Fixed components and safe status only; 13 correlated successful calls | p95 835 ms | Passed |
| `get_gcp_resource_summary` | Safe aliases/counts only; no enumeration or excluded resource; 13 correlated successful calls | p95 1,336 ms | Passed |
| `get_cloud_run_status` | Existing all-alias check covered `frontend`, `backend` and `mcp`; 10 correlated successful calls in the final batch omitted raw config/IAM/env | p95 422 ms | Passed |
| `search_application_errors` | G-014 bounded to the dedicated view; 21 successful, redacted calls with a non-future one-hour interval | p95 863 ms | Passed |
| `get_data_source_health` | Fixed sources and explicit partial/unavailable state; 12 correlated successful calls | p95 872 ms | Passed |
| `get_processing_status` | Existing Demo job read without mutation, external IDs or body; 13 correlated successful calls | p95 829 ms | Passed |

## Internal Chat consistency

| Gate | Required evidence | Result |
|---|---|---:|
| Dashboard facts | External MCP and Internal Chat exact money/calculation/source facts match | Pending |
| Project insight facts | Both channels use the same authorized scope and independent source state | Pending |
| Persistence boundary | External MCP prompts/responses absent from Product/operational logs; existing Chat history remains separate | Pending |
| Partial/failure behavior | Source outage is explicit and does not invent or silently merge a fact | Pending |

## Admin and revocation matrix

| Gate | Required evidence | Result |
|---|---|---:|
| Explicit grant | Active assigned-project Admin has `mcp_access` plus only pilot domain permissions | Pending |
| Six-tool allow matrix | All six operations tools succeed within granted scope | Pending |
| Permission denial | Missing `infrastructure_read` denies before GCP/Backend source access | Pending |
| Cross-project denial | Assigned Admin cannot infer or read another project | Pending |
| OAuth disable/revoke | Next external call is denied after disablement | Pending |
| Unbind | Issuer/subject and permission set are cleared; reconnect requires new Owner grant | Pending |
| Internal Chat denial | Removed/inactive/missing-permission Admin is denied by current directory state | Pending |

## Security, performance and rollback

| Gate | Required evidence | Result |
|---|---|---:|
| Redaction scan | 144 Product Audit events scanned; zero token, credential, URL, email, path, raw UUID or prompt/body matches. Canonical record IDs were emitted only as `rid_` opaque correlations. | Passed |
| Audit coverage | 39 sensitive requests had 39 matching terminal events; missing pairs: 0. The Audit sink/preflight accepts direct `jsonPayload`, nested `jsonPayload.message` and `textPayload` Product Audit records. | Passed |
| Cloud errors | Backend/MCP runtime severity `ERROR` count: 0; failed release-window control-plane operations: 0 | Passed |
| Operations p95 | 82/82 audit-correlated successful calls; p95 1,287 ms; max 1,336 ms | Passed |
| Backend rollback/restore | Prior revision healthy; candidate `projects-001-be-00123-thg` restored to 100% and healthy | Passed |
| MCP rollback/restore | Prior revision healthy; unauthenticated initialize returned 401; candidate `projects-001-mcp-00012-sbs` restored to 100%; Owner re-initialized with 37 tools | Passed |

## Release decision

Pending. Phase 6 Private Plugin and Beta work remain blocked until every required
row above has concrete sanitized evidence and the final decision is changed to
passed.
