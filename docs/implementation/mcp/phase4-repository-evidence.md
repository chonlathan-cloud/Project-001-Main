# Phase 4 repository evidence

Date: 2026-07-29
Scope: Project Operations and Product Audit repository implementation
Cloud state: unchanged

## Outcome

Phase 4 is complete in the repository and ready for an explicitly approved Demo
release. MCP version `0.4.0` exposes 31 read-only tools: the 21 Phase 3 tools plus
ten Phase 4 tools. The Backend exposes seven new service-authenticated routes,
bringing the internal MCP route set to 27.

## Implemented tools

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

## Exit evidence

| Exit criterion | Repository result | Evidence |
|---|---:|---|
| Scoped domain contract/policy tests | Pass | Cross-project and missing-permission requests deny before Backend/audit source reads |
| Cross-domain sources and no silent merge | Pass | Insight responses preserve independent source status/references and explicit partial/conflict warnings |
| Inspection/Daily Report safety | Pass | Bounded scans, immutable versions, opaque document IDs, and no share token/path/signed URL |
| Dashboard exactness | Pass | Decimal money objects, exact remaining arithmetic and named calculation method |
| Product Audit minimization | Pass | Dedicated-view server filters and allowlisted event validation omit document/prompt bodies |
| Sensitive audit fail-closed | Pass | Dashboard/insight/audit readers do not start when mandatory audit emission fails |
| Golden Phase 4 cases | Pass | G-010, G-011, G-012, G-013, G-015 and C-001 pass 6/6 at 100% |
| Operations p95 <=15 seconds | Live proof pending | Requires the deployed Demo revision and real authorized source reads |

## Verification results

- Backend full suite: `105 passed`.
- MCP full suite: `67 passed` (one non-failing Starlette/httpx deprecation warning).
- Phase 2 evaluator: 6/6, `100.0%`.
- Phase 3 evaluator: 5/5, `100.0%`.
- Phase 4 evaluator: 6/6, `100.0%`, all gates true.
- MCP Ruff: pass.
- New Phase 4 Backend service/tests Ruff: pass. Legacy Backend files retain
  pre-existing lint findings outside the new service boundary.
- `git diff --check`: pass.
- Production images build as `projects-001-be:phase4-local` and
  `projects-001-mcp:phase4-local`.

## Demo release prerequisites

Repository completion does not authorize cloud changes. Before Phase 4 live
evidence can begin:

1. Create and route the dedicated Demo Product Audit bucket/view named by the
   environment-locked `MCP_AUDIT_LOG_VIEW`.
2. Apply the four Phase 4 Firestore indexes declared in
   `Projects-001-BE/infra/gcp/firestore.indexes.json` and wait for `READY`.
3. Grant only the Demo MCP service identity read access to that exact view and
   retain its existing log-writer role. Do not grant unrelated-log, Beta or SaaS
   visibility.
4. Add the two audit-read environment values, deploy Backend first, then deploy
   MCP `0.4.0` while keeping `MCP_ALLOWED_ROLES=owner`.
5. Verify all 31 tools are closed-input/read-only and all 27 Backend contracts
   remain service-identity-only.
6. Run G-010/G-011/G-012/G-013/G-015 and C-001 with sanitized live Demo records;
   prove source citations, immutable versions, partial/conflict behavior and
   zero share-token/path/body leakage.
7. Confirm mandatory Product Audit events exist for dashboard, insight and audit
   tools; confirm no prompt, document body, token, secret or signed URL appears.
8. Measure successful operations requests and record p95 <=15 seconds, bounded
   Cloud Run errors and rollback/restore evidence.

Phase 5 must not begin as a release until these Phase 4 Demo gates are recorded.
