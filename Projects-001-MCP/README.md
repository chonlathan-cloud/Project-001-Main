# Projects-001 Product MCP

Standalone, read-only Product MCP service for Projects-001. The service provides
a Streamable HTTP `/mcp` endpoint, OAuth resource-server validation, per-call
Product policy resolution, common envelopes, separated audit telemetry, and the
Phase 2 Core Business, Phase 3 Finance/Document Gateway, and Phase 4 Project
Operations/Product Audit tools, plus the Phase 5 Curated GCP Operations tools.

## Current scope

Implemented tools:

- `get_system_catalog`
- `describe_domain`
- `get_current_access`
- `search`
- `fetch`
- `list_projects`
- `get_project`
- `get_project_summary`
- `get_boq_current`
- `list_boq_versions`
- `get_boq_version`
- `compare_boq_versions`
- `list_project_access`
- `get_user_access`
- `get_project_financial_summary`
- `search_financial_records`
- `get_payment`
- `get_payment_document_status`
- `search_documents`
- `get_document_metadata`
- `read_document_content`
- `list_inspection_items`
- `get_inspection_item`
- `list_daily_reports`
- `get_daily_report`
- `list_daily_report_versions`
- `get_report_share_status`
- `get_dashboard_summary`
- `get_project_insights`
- `search_audit_events`
- `get_audit_event`
- `get_system_health`
- `get_gcp_resource_summary`
- `get_cloud_run_status`
- `search_application_errors`
- `get_data_source_health`
- `get_processing_status`

They require a valid OAuth access token and a successful response from the
service-authenticated Backend contracts. The MCP forwards only the verified OAuth
subject, issuer, client ID and locked environment; the Backend re-resolves role,
permissions and project scope for every call. Production has no auth bypass.

The deployed Phase 4 baseline remains Owner-only. Phase 5 Admin permission,
scope and revocation support is implemented behind the Backend
`MCP_ALLOWED_ROLES` rollout gate and must not be enabled before the explicit
Demo Admin pilot.

## Local setup

```bash
cd Projects-001-MCP
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.server.main:app --reload --port 8080
```

The example OAuth/backend URLs are intentionally non-functional. Configure a
standards-compliant Demo issuer and the service-authenticated Backend contract
before attempting authenticated calls.

## Verification

```bash
ruff check app tests
pytest
python -m tests.evals.phase2_evaluator
python -m tests.evals.phase3_evaluator
python -m tests.evals.phase4_evaluator
python -m tests.evals.phase5_evaluator
docker build --tag projects-001-mcp:local .
```

The evaluators report the Phase 2 Core Golden/BOQ gate, Phase 3 exact
Finance/Document security gate, and Phase 4 Project Operations/Audit gate from
the versioned `demo-sanitized` dataset. Phase 5 additionally gates G-014,
operations allowlists/redaction, shared Internal Chat facts, the Admin matrix and
next-call revocation. Real-client operational-view access, Admin consent and
operations p95 remain separate Demo release gates.

Deployment is intentionally separate from the Backend lifecycle. From the
repository root, copy the matching `mcp.deploy.*.example` and
`cloudrun-mcp*.env.yaml.example`, replace placeholders, then run
`./deploy_mcp.sh --preflight-only`. Omit `--preflight-only` only when a real
deployment has been explicitly approved.

## Security properties

- No Product session-token reuse and no inbound-token passthrough.
- Asymmetric OAuth JWT verification with issuer, audience/resource, expiry,
  environment and scope checks.
- Product authorization is re-resolved for each tool call.
- Finance reads require Product `financial_data_read` for Admins; sensitive
  document bodies require `sensitive_documents_read` and mandatory audit.
- Document content is bounded, credential-redacted and explicitly labeled as
  untrusted; no GCS path or signed URL is returned.
- Owner-only rollout by default; future Admin access needs both rollout inclusion
  and explicit `mcp_access`.
- No environment input, generic query/path tool or business write.
- Bounded inputs plus per-verified-subject and Backend defense-in-depth rate
  limits.
- Audit and operational log schemas are separate and recursively redacted.
- Audit reads require Product `audit_log_read`, mandatory pre-read audit, and
  access to the exact environment-locked Product Audit log view. Results are
  validated against the allowlisted event schema and never include prompts or
  document bodies.
- Dashboard and project insights require `financial_data_read` for Admins,
  preserve exact money strings, cite independent sources, and mark missing or
  inconsistent sources explicitly.
- GCP Operations requires `infrastructure_read`, uses only compiled
  Demo/Beta aliases, and never exposes arbitrary GCP inventory or a raw Logging
  query.
- Application-error reads use a separate exact operational view, a maximum
  30-day range and 50 rows, and redact credentials, URLs, email, GCS paths and
  record identifiers.
- Internal Chat invokes the same Backend dashboard/insight calculation services
  and policy scope as External MCP. Existing Chat history remains separate; MCP
  does not persist prompts or full responses.

See `docs/implementation/mcp/` for contracts, ADRs and phase status.
