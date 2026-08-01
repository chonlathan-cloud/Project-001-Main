# Phase 5 Demo release evidence

Evidence date: 2026-07-31
Environment: Demo (`project001-489710`, `asia-southeast1`)
Pilot roles: Owner, then one explicitly authorized Admin
Status: live validation in progress; operational/IAM, Owner/Admin external-MCP,
audit, latency and rollback gates passed; seven rows remain

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
| Rollout cohort | Product Audit shows one Owner pilot first, followed by exactly one assigned Admin actor; raw subjects were not retained in this evidence | Passed |

## Operational Logging and IAM

| Gate | Required evidence | Result |
|---|---|---:|
| Operational bucket | Read-only inspection confirmed `projects-001-mcp-ops-demo` is active in `asia-southeast1` with exactly 30-day retention | Passed |
| Sink filter | Read-only inspection confirmed exact Cloud Run revision type, Demo region, three Product services and `severity>=WARNING` | Passed |
| View filter | Read-only inspection confirmed exact resource type/region and anchored Product-service regex; severity remains enforced by the sink | Passed |
| View IAM | Read-only policy inspection confirmed only the Demo MCP identity has `roles/logging.viewAccessor` on the exact view | Passed |
| Metadata IAM | The Demo MCP identity has the seven-permission read-only metadata role on exact approved resources; no write, secret or BigQuery grant was found | Passed |
| Excluded resources | Live preflight and successful bounded tool evidence returned no SaaS Cloud Run/Cloud SQL or BigQuery resource | Passed |
| Deployment preflight | `./deploy_mcp.sh --preflight-only` passed against the exact Demo configuration on 2026-08-01 | Passed |

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
| Six-tool allow matrix | Product Audit recorded successful terminal events for all six operations tools for the single pilot Admin | Passed |
| Permission denial | Removing `infrastructure_read` produced `missing_product_permission` before a source read; restore returned to success | Passed |
| Cross-project denial | An out-of-scope project request was denied as `project_not_in_scope` without record disclosure | Passed |
| OAuth disable/revoke | Disabling External MCP caused the next access call to fail as `external_mcp_disabled`; restoring the binding returned to success | Passed |
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

Pending. Seven rows still require direct sanitized evidence: four Internal Chat
consistency gates plus Admin explicit-grant, unbind and Internal Chat denial.
Phase 6 Demo Plugin compatibility may proceed, but Beta provisioning and rollout
remain blocked until all seven pass and the final decision changes to passed.
