# Phase 5 Demo release evidence

Evidence date: pending
Environment: Demo (`project001-489710`, `asia-southeast1`)
Pilot roles: Owner, then one explicitly authorized Admin
Status: pending

This file is the live release gate for Curated GCP Operations, Internal Chat and
Admin MCP access. Do not mark a row passed from repository tests alone. Evidence
must omit OAuth tokens, prompts, document bodies, raw log queries, URLs, email
addresses, GCS paths, record UUIDs, service-account credentials and private
content.

## Release baseline

| Item | Evidence | Result |
|---|---|---:|
| Repository commit | Pending | Pending |
| Database safety point | Pending | Pending |
| Backend revision | Pending; must expose 28 service-authenticated MCP contracts | Pending |
| MCP revision | Pending; must report `0.5.0` and list 37 tools | Pending |
| Frontend revision | Pending; must expose Owner MCP controls | Pending |
| Rollout cohort | Owner first; one named-by-opaque-ID assigned Admin only after Owner pass | Pending |

## Operational Logging and IAM

| Gate | Required evidence | Result |
|---|---|---:|
| Operational bucket | `projects-001-mcp-ops-demo`, `asia-southeast1`, exactly 30-day retention | Pending |
| Sink/view filter | Only the three Demo Product services and `severity>=WARNING` | Pending |
| View IAM | Exact view grants the Demo MCP identity `roles/logging.viewAccessor` | Pending |
| Metadata IAM | Effective permissions are limited to approved Product resource metadata; no write/secret/BigQuery access | Pending |
| Excluded resources | No SaaS Cloud Run/Cloud SQL resource is queried, listed or returned | Pending |
| Deployment preflight | `./deploy_mcp.sh --preflight-only` passes against the exact Demo configuration | Pending |

## Live Owner evidence

| Tool | Required assertion | Latency | Result |
|---|---|---:|---:|
| `get_system_health` | Fixed components and safe status only | Pending | Pending |
| `get_gcp_resource_summary` | Safe aliases/counts only; no enumeration or excluded resource | Pending | Pending |
| `get_cloud_run_status` | Each of `frontend`, `backend`, `mcp`; no raw config/IAM/env | Pending | Pending |
| `search_application_errors` | G-014 bounded to the dedicated view; safe redacted fields only | Pending | Pending |
| `get_data_source_health` | Fixed sources and explicit partial/unavailable state | Pending | Pending |
| `get_processing_status` | One safe status per approved workflow; no mutation/external IDs/body | Pending | Pending |

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
| Redaction scan | Zero token, credential, URL, email, path, UUID, prompt/body or service-identity leakage | Pending |
| Audit coverage | Sensitive operations have matching start/terminal Product Audit events | Pending |
| Cloud errors | Zero unexpected Backend/MCP errors in the bounded release window | Pending |
| Operations p95 | `<=15,000 ms` across successful Phase 5 operations | Pending |
| Backend rollback/restore | Prior revision health, then candidate restored to 100% | Pending |
| MCP rollback/restore | Prior revision health/401 boundary, then candidate restored to 100% | Pending |

## Release decision

Pending. Phase 6 Private Plugin and Beta work remain blocked until every required
row above has concrete sanitized evidence and the final decision is changed to
passed.
