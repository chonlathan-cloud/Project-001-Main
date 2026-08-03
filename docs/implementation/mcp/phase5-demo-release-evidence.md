# Phase 5 Demo release evidence

Evidence date: 2026-08-03
Environment: Demo (`project001-489710`, `asia-southeast1`)
Pilot roles: Owner, then one explicitly authorized Admin
Status: **Passed**. Operational/IAM, Owner/Admin external-MCP, Internal Chat
parity, revocation, audit, latency and rollback gates passed in Demo.

This file is the live release gate for Curated GCP Operations, Internal Chat and
Admin MCP access. Do not mark a row passed from repository tests alone. Evidence
must omit OAuth tokens, prompts, document bodies, raw log queries, URLs, email
addresses, GCS paths, record UUIDs, service-account credentials and private
content.

## Release baseline

| Item | Evidence | Result |
|---|---|---:|
| Repository commit | `4d4010a`; Product Audit routing and opaque record correlation hardening | Passed |
| Phase 6 requalification commit | `2415f97`; MCP `0.6.0` Demo image and Private Plugin compatibility | Passed |
| Database safety point | Successful pre-Phase 5 Demo backup `1785386813588` recorded before rollout | Passed |
| Backend revision | `projects-001-be-00123-thg`; 28 service-authenticated MCP contracts | Passed |
| MCP revision | `projects-001-mcp-00012-sbs`; reports `0.5.0` and lists 37 tools | Passed |
| MCP 0.6 candidate | `projects-001-mcp-00013-p9v`; reports `0.6.0`, lists 37 read-only tools and serves 100% traffic after restore | Passed |
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
| Dashboard facts | A live Owner fixture returned exact matching dashboard money, calculation and source facts through the shared Backend contract used by External MCP and Internal Chat | Passed |
| Project insight facts | The same live Owner fixture resolved eight authorized projects through both adapters; project insight scope matched, source states stayed independent and the successful result was not partial | Passed |
| Persistence boundary | Chat-history row count was unchanged by the External MCP calls; the Product/operational audit scans contained neither prompts nor response bodies | Passed |
| Partial/failure behavior | The deployed shared adapter returned explicit healthy source state in the live fixture, while the exact deployed-commit source-outage fault case returned `partial` with separate unavailable-source metadata and no invented or silently merged fact | Passed |

## Admin and revocation matrix

| Gate | Required evidence | Result |
|---|---|---:|
| Explicit grant | The earlier single assigned-project Admin pilot was observed with `mcp_access` and only the pilot domain permissions before its six-tool allow/deny matrix; the temporary grant was removed after testing | Passed |
| Six-tool allow matrix | Product Audit recorded successful terminal events for all six operations tools for the single pilot Admin | Passed |
| Permission denial | Removing `infrastructure_read` produced `missing_product_permission` before a source read; restore returned to success | Passed |
| Cross-project denial | An out-of-scope project request was denied as `project_not_in_scope` without record disclosure | Passed |
| OAuth disable/revoke | Disabling External MCP caused the next access call to fail as `external_mcp_disabled`; restoring the binding returned to success | Passed |
| Unbind | Final sanitized directory inspection found both active Demo Admin entries with External MCP disabled and no issuer/subject binding; reconnect therefore requires a new Owner grant | Passed |
| Internal Chat denial | The shared directory resolver denied the missing-permission Admin before a source read, and final unbound directory state prevents both Admin entries from entering either External MCP or Internal Chat authorization | Passed |

## Security, performance and rollback

| Gate | Required evidence | Result |
|---|---|---:|
| Redaction scan | 144 Product Audit events scanned; zero token, credential, URL, email, path, raw UUID or prompt/body matches. Canonical record IDs were emitted only as `rid_` opaque correlations. | Passed |
| Audit coverage | 39 sensitive requests had 39 matching terminal events; missing pairs: 0. The Audit sink/preflight accepts direct `jsonPayload`, nested `jsonPayload.message` and `textPayload` Product Audit records. | Passed |
| Cloud errors | Backend/MCP runtime severity `ERROR` count: 0; failed release-window control-plane operations: 0 | Passed |
| Operations p95 | 82/82 audit-correlated successful calls; p95 1,287 ms; max 1,336 ms | Passed |
| MCP 0.6 requalification | 6/6 candidate calls succeeded; p95 498 ms; max 498 ms. One sensitive request had one terminal pair, zero missing pairs, zero raw UUID/credential/email/prompt/body matches and zero unexpected Backend/MCP `ERROR` events | Passed |
| Backend rollback/restore | Prior revision healthy; candidate `projects-001-be-00123-thg` restored to 100% and healthy | Passed |
| MCP rollback/restore | Prior `0.5.0` revision `projects-001-mcp-00012-sbs` was healthy and preserved the unauthenticated `401` boundary; candidate `projects-001-mcp-00013-p9v` was restored to 100%, reported `0.6.0`, and the Owner completed initialization and read-only calls with 37 tools | Passed |

## Release decision

**Passed for Demo.** All required Phase 5 live rows have direct sanitized
evidence. This decision qualifies the Demo implementation for Phase 6 image and
Private Plugin compatibility work only. It does not authorize Beta provisioning,
IAM changes, deployment or cohort rollout.
