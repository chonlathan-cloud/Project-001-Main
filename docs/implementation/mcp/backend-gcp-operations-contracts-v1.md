# Backend GCP Operations and Internal Chat contracts v1

Status: Phase 5 repository implementation complete; not deployed.

Phase 5 adds six curated read-only operations tools, one service-authenticated
Backend processing-status contract, a shared Internal Chat adapter, and Owner
controls for Admin MCP entitlement and revocation. The Product MCP remains a
closed interface: it does not expose a generic GCP, Logging, job-system, path,
URL, SQL, Firestore, storage or secret tool.

## Public MCP tools

| Tool | Source | Closed input boundary |
|---|---|---|
| `get_system_health` | Product health endpoints and allowlisted GCP metadata APIs | Fixed component enum only |
| `get_gcp_resource_summary` | GCP metadata APIs | Fixed resource-type enum; safe aliases/counts only |
| `get_cloud_run_status` | Cloud Run v2 | `frontend`, `backend` or `mcp` alias only |
| `search_application_errors` | Dedicated operational Logging view | At most 30 days, allowlisted severity/service/workflow and 50 rows |
| `get_data_source_health` | Product health endpoints and allowlisted GCP metadata APIs | Fixed source enum only |
| `get_processing_status` | Product Backend | Fixed workflow enum and one opaque job ID |

All six tools require `infrastructure_read`. An Admin also requires `mcp_access`,
an active directory entry, the approved Admin rollout role, and an assigned
project unless `mcp_all_projects_read` is explicitly granted. Owner has the
approved implicit domain permissions. Product access is re-resolved before each
tool call.

## Environment and resource boundary

The runtime compiles exact resources from `MCP_ENVIRONMENT`; clients cannot
select an environment or resource name.

| Resource | Demo | Beta |
|---|---|---|
| Cloud Run aliases | `projects-001-fe`, `projects-001-be`, `projects-001-mcp` | `projects-001-fe-beta`, `projects-001-be-beta`, `projects-001-mcp-beta` |
| Cloud SQL | `project-001` | `project-001-beta` |
| Firestore | `(default)` | `prod-beta` |
| GCS | Five environment-specific Product buckets | Five environment-specific Product buckets |
| Artifact Registry | `projects-001` | `projects-001` |
| Operational view | `projects-001-mcp-ops-demo-view` | `projects-001-mcp-ops-beta-view` |

The adapter never enumerates projects or returns raw resource configurations,
IAM policies, environment variables, service-account identities, database
connection data, bucket names, arbitrary log fields, URLs or secret payloads.
The explicitly excluded SaaS Cloud Run and Cloud SQL resources and BigQuery are
absent from every mapping and server-built filter.

## Operational Logging contract

`search_application_errors` reads only `MCP_OPERATIONAL_LOG_VIEW`, which is
separate from the Product Audit view. Its server-built query fixes:

- `cloud_run_revision` resources in `asia-southeast1`;
- only the three Product service names for the active environment;
- `WARNING` or higher allowlisted severities;
- a requested interval no longer than `MCP_OPERATIONAL_LOG_READ_MAX_DAYS=30`;
- descending timestamp order and at most 50 results.

The client never accepts a raw Logging query. Returned entries are reduced to an
opaque event ID, timestamp, severity, service alias, safe workflow/error code and
a 500-character summary. Credential assignments and Bearer values, URLs, email
addresses, GCS paths and UUID-shaped record identifiers are redacted. Unknown
fields are discarded.

## Backend processing-status contract

`POST /api/v1/internal/mcp/processing/status:get` is the 28th internal MCP read
route. It is callable only by the environment-specific MCP service identity and
re-resolves Product authorization before reading one of these workflows:

- `boq_sync`
- `receipt_ocr`
- `daily_report_delivery`
- `flowaccount_sync`

The response contains safe state, timestamps, counts and component readiness.
It does not start/retry a job and omits document content, external IDs,
credentials, storage paths and raw error bodies.

## Internal Chat shared-contract behavior

`POST /api/v1/chat/ask` uses the current Product session, then re-resolves the
active Owner/Admin directory record and project memberships. Admin Chat requires
both `mcp_access` and `financial_data_read`; Owner retains implicit access. The
adapter calls the same `get_dashboard_summary` or `get_project_insights`
services used by External MCP and preserves their exact Decimal facts,
calculation method, project scope and sources.

The Phase 5 response is deterministic and does not send the shared contract to a
second LLM for rewriting. External MCP continues to persist no prompts or full
responses. Existing Internal Chat history remains on its existing Product path
and was not merged into MCP Product Audit or operational logs.

## Settings and revocation

The Owner-only Admin create/update endpoints already own the MCP fields. Phase 5
adds the matching Settings UI for:

- External MCP enable/disable;
- atomic OAuth issuer/subject binding;
- `mcp_access`, `financial_data_read`, `sensitive_documents_read`,
  `infrastructure_read` and `audit_log_read`;
- assigned-project versus all-project read scope; and
- revoke-and-unbind.

Issuer and subject are shown only to Owners. Enabling External MCP requires both
binding fields, and Admin enablement requires `mcp_access`. A revoke action
clears enablement, OAuth binding and permissions. The policy contract is called
again for every MCP operation, so the next call observes the revoked state.

## Demo deployment prerequisites

Repository completion does not create cloud resources or authorize deployment.
Before deploying MCP `0.5.0` in Demo:

1. Create the 30-day `projects-001-mcp-ops-demo` Logging bucket, sink and
   `projects-001-mcp-ops-demo-view`. Restrict both sink and view to the three
   Demo Product services and `severity>=WARNING`.
2. Grant the Demo MCP service account `roles/logging.viewAccessor` on that exact
   operational view. Retain the separate exact Product Audit view binding.
3. Grant only the metadata permissions required by the compiled resources:
   `run.services.get`, `cloudsql.instances.get`, `datastore.databases.get`,
   `storage.buckets.get`, `artifactregistry.repositories.get`,
   `logging.views.get` and `logging.logEntries.list`. Use resource-scoped or
   conditional bindings where supported; do not grant BigQuery, Secret Manager,
   business-data write, arbitrary object-read or excluded SaaS access.
4. Deploy Backend first, then MCP, and verify all 28 internal routes remain
   service-identity-only.
5. Keep the initial live verification Owner-only. Enable selected Admins only
   after the Owner records their project scope and explicit permission set.

`deploy_mcp.sh --preflight-only` validates the exact runtime mapping, all three
Cloud Run services, 30-day operational retention, sink/view filters,
destinations, exact view IAM and the existing Product Audit boundary before a
deployment can start.
