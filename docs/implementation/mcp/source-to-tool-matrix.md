# Source-to-tool matrix

`Existing` means a Product endpoint or service can inform the new internal read
contract. It does not mean the current public endpoint is safe to call unchanged.
All backend routes below are under `/api/v1`.

## Phase 2 implementation status

The Core Pilot contracts are now implemented under `/internal/mcp`:

| Capability | Backend contract |
|---|---|
| Per-call authorization | `POST /internal/mcp/access-context:resolve` |
| Federated discovery | `POST /internal/mcp/search`, `POST /internal/mcp/fetch` |
| Projects | `POST /internal/mcp/projects:list`, `projects:get`, `projects:summary` |
| BOQ current/history | `POST /internal/mcp/boq:current`, `boq/versions:list`, `boq/versions:get`, `boq/versions:compare` |
| Users/access | `POST /internal/mcp/project-access:list`, `user-access:get` |

These are service-authenticated POST reads. They do not mutate Business Data;
POST is used so verified principal context never appears in URLs or intermediary
query logs. Future-domain rows below still describe required work.

| Tool | Source of truth | Existing contract / reusable source | Required new contract or adapter |
|---|---|---|---|
| `get_system_catalog` | MCP registry | None required | MCP registry, permission filtered |
| `describe_domain` | MCP registry | None required | MCP registry, permission filtered |
| `get_current_access` | Product authorization | `GET /auth/me`; Firestore Admin directory and Daily Report memberships | `POST /internal/mcp/access-context:resolve`; active state, MCP entitlements, permissions and projects |
| `search` | Federated domain sources | Project, Insight, Inspection and Daily Report reads | Bounded adapter fan-out, policy filter before ranking |
| `fetch` | Domain router | Existing record GET endpoints | Stable opaque reference resolver with policy re-check |
| `list_projects` | Product business rules + SQL | `GET /projects` | Versioned internal read with assigned-project filter and cursor pagination |
| `get_project` | Product business rules + SQL | `GET /projects/{project_id}` | Assigned-project enforcement and Product citation URL |
| `get_project_summary` | Product calculations | Project detail; Dashboard/Chat analytics services | Exact, project-scoped summary contract with source records |
| `get_boq_current` | Product BOQ rules + SQL | `GET /projects/{project_id}/boq`; current rows use `valid_to IS NULL` | Exact-money schema, stable line IDs, source/version metadata |
| `list_boq_versions` | BOQ version manifest | SCD2 `boq_items.valid_from/valid_to` | Stable version entity/number and deterministic manifest |
| `get_boq_version` | BOQ version manifest + rows | No current endpoint | Version/as-of resolver; never infer a version number in MCP |
| `compare_boq_versions` | Product BOQ comparison rules | Current-tree comparison helpers are reusable | Explicit A/B version comparison by stable line identity and Decimal values |
| `get_project_financial_summary` | Product finance rules + SQL | `GET /dashboard/summary`; Chat analytics | Project-scoped Decimal contract and calculation/source metadata |
| `search_financial_records` | Product finance rules + SQL | `GET /insights/rows`; `GET /input/admin/requests` | Cursor pagination, assigned-project filter, Decimal serialization and PII minimization |
| `get_payment` | Product payment rules + SQL | `GET /input/admin/requests/{request_id}`; payment relations | Stable payment read contract with project policy and redacted bank data |
| `get_payment_document_status` | Product payment/document state | Accounting readiness and payment-confirmation records | Status-only document contract; no storage key or signed URL |
| `list_project_access` | Product authorization | Settings Admin/Subcontractor/Customer reads; Daily Report memberships | Project-centric access view with PII minimization |
| `get_user_access` | Product authorization | Settings directory reads | Opaque user lookup, authorized visibility and MCP entitlements |
| `list_inspection_items` | Inspection business service | Inspection rounds/zones/defects GET routes | Bounded project-scoped internal read, no signed URLs |
| `get_inspection_item` | Inspection business service | Defect and event GET routes | Stable item contract with authorized file metadata only |
| `list_daily_reports` | Daily Report business service | `GET /daily-reports/queue` and customer/staff reads | Project/date/status filters with cursor pagination |
| `get_daily_report` | Daily Report business service | `GET /daily-reports/reports/{report_id}` | Current-published semantics and Product citation URL |
| `list_daily_report_versions` | Firestore immutable snapshots | `GET /daily-reports/reports/{report_id}/versions` | Stable version references and source timestamps |
| `get_report_share_status` | Share-link state | `GET /daily-reports/projects/{project_id}/share-link` | New status-only response that never includes token/link material |
| `search_documents` | Product metadata | Receipt, inspection and daily-report metadata are fragmented | Unified opaque document metadata search |
| `get_document_metadata` | Product metadata | Fragmented file metadata | Classification, `external_ai_blocked`, extraction status and citation route |
| `read_document_content` | GCS bytes + Product access policy | Existing endpoints issue signed URLs | Document Gateway that streams bounded content server-side and audits sensitive reads |
| `get_dashboard_summary` | Backend derived calculations | `GET /dashboard/summary` | Authorized scope, Decimal values and calculation/source metadata |
| `get_project_insights` | Backend derived calculations | `GET /insights/summary` and Chat analytics | Project-scoped bounded result with source references |
| `search_audit_events` | Product Audit log bucket | None | Dedicated Logging view adapter with allowlisted filters |
| `get_audit_event` | Product Audit log bucket | None | Opaque event lookup; `NOT_FOUND_OR_FORBIDDEN` semantics |
| `get_system_health` | Health adapters/GCP APIs | Backend `/health` | Curated aggregate status with no raw resource enumeration |
| `get_gcp_resource_summary` | GCP APIs | Local diagnostic MCP is reference only | Hard-coded Demo/Beta resource allowlist adapter |
| `get_cloud_run_status` | Cloud Run API | Local diagnostic MCP validation patterns | Exact allowed service aliases only |
| `search_application_errors` | Cloud Logging | Local diagnostic MCP redaction patterns | Bounded time/severity/workflow filters; server-generated query |
| `get_data_source_health` | Backend/GCP health | Backend `/health` plus platform APIs | Named allowlisted source checks |
| `get_processing_status` | Backend/GCP task state | BOQ sync job GET and approved processing sources | Curated workflow/status enum; no arbitrary job system access |

## Ownership conclusions

- Product Backend owns business meaning, calculations and authorization.
- MCP owns transport, tool contracts, orchestration, response envelopes and
  pre-delivery controls.
- GCP APIs own operational facts.
- Direct SQL/Firestore/GCS is a named, bounded, read-only fallback only after the
  corresponding contract and IAM gate pass.
- The local generic diagnostic MCP is not a runtime dependency or deploy source.
