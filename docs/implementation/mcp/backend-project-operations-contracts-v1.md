# Backend Project Operations and Product Audit contracts v1

Status: Phase 4 repository implementation complete; not deployed.

The Product Backend remains authoritative for Inspection, Daily Report,
Dashboard and project-insight business meaning. The MCP owns tool transport,
policy enforcement, response envelopes, source citations and the separately
bounded Product Audit log-view adapter.

## Backend routes

All paths use the `/api/v1/internal/mcp` prefix, accept only `POST`, require the
matching MCP Google service identity, and re-resolve Product authorization from
the verified OAuth principal.

| Route | Purpose |
|---|---|
| `/inspection/items:list` | Bounded authorized defects by project/status/severity/due state |
| `/inspection/items:get` | One defect, opaque document IDs and at most 50 safe event records |
| `/daily-reports:list` | Bounded authorized report headers by project/date/status |
| `/daily-reports:get` | Current report content or an explicitly selected immutable version |
| `/daily-reports/versions:list` | Immutable publication-version metadata only |
| `/daily-reports/share-status:get` | Share configuration state without token or URL |
| `/dashboard:summary` | Exact permission-scoped project and aggregate finance summary |
| `/projects/insights:get` | Independent finance, inspection and Daily Report signals |

The existing `/search` and `/fetch` routes now resolve stable
`inspection:item:*` and `daily_reports:report:*` references through the same
authorization boundary.

## Safety and consistency semantics

- Inspection and Daily Report Firestore scans are capped at 250. If that bound
  can make a result incomplete, the response is marked partial with an explicit
  warning; completeness is never implied silently.
- Inspection files are represented only by opaque Document Gateway IDs. Event
  actor IDs, GCS paths, signed URLs and arbitrary event metadata are omitted.
- Daily Report list/detail responses do not expand source submissions, media,
  acknowledgements or questions. Explicit historical selectors read immutable
  publication snapshots. Version lists return metadata, not snapshot bodies.
- Share status returns state and safe timestamps/booleans only. Token, URL and
  token-version material are omitted.
- Money is always `{ "amount": "1234.50", "currency": "THB" }`. Dashboard
  calculations use SQL Decimal aggregates and state their calculation method.
- Project insights do not collapse finance, inspection and Daily Report sources
  into one unqualified fact. Each source has independent status and citation.
  A source outage produces `partial=true` and `SOURCE_UNAVAILABLE`; a detected
  contradiction produces `SOURCE_INCONSISTENCY`.
- Dashboard/insight tools require `financial_data_read` for Admin callers and
  are mandatory-audit sensitive reads.

## Product Audit adapter

`search_audit_events` and `get_audit_event` read Cloud Logging directly from the
exact `MCP_AUDIT_LOG_VIEW` locked to the active environment. They require Product
`audit_log_read` and mandatory sensitive-access audit before the read begins.

The adapter:

- builds all Logging filters server-side;
- fixes the Cloud Run service and Product Audit log type;
- caps searches at 50 events and a configured retention window of at most 365
  days (default 90);
- accepts only allowlisted time, tool, decision, domain, subject and event-ID
  selectors;
- validates every returned event against `ProductAuditEvent`;
- omits unknown fields, including prompt, response and document bodies;
- returns `NOT_FOUND_OR_FORBIDDEN` for inaccessible/missing events;
- fails closed if mandatory audit emission or the Logging source is unavailable.

## Deployment prerequisites

Repository completion does not create Logging or IAM resources. Before deploying
MCP `0.4.0` in Demo:

1. Create the Demo Product Audit log bucket and view named by
   `MCP_AUDIT_LOG_VIEW`, and route only allowlisted Product Audit events to it.
2. Apply the Phase 4 bounded-query indexes declared in
   `Projects-001-BE/infra/gcp/firestore.indexes.json` and wait until all four new
   indexes report `READY`.
3. Grant the Demo MCP service account read access at that exact view (the planned
   least-privilege binding is `roles/logging.viewAccessor` on the view), while
   retaining `roles/logging.logWriter` for emission. Do not grant broad access to
   unrelated project logs.
4. Add `MCP_AUDIT_LOG_VIEW` and `MCP_AUDIT_READ_MAX_DAYS=90` to the Demo revision.
5. Deploy Backend before MCP and verify all 27 internal routes remain callable
   only by the allowlisted Demo MCP service identity.
6. Keep the rollout Owner-only until a separate Admin pilot authorizes
   `financial_data_read` and/or `audit_log_read` grants.
