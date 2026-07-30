# Phase 5 repository evidence

Date: 2026-07-30
Scope: Curated GCP Operations, Internal Chat and Admin controls
Cloud state: unchanged

## Outcome

Phase 5 is complete in the repository and ready for an explicitly approved Demo
release. MCP version `0.5.0` exposes 37 read-only tools: the 31 Phase 4 tools plus
six curated operations tools. The Backend adds one processing-status route,
bringing the service-authenticated internal MCP route set to 28.

## Implemented capabilities

- `get_system_health`
- `get_gcp_resource_summary`
- `get_cloud_run_status`
- `search_application_errors`
- `get_data_source_health`
- `get_processing_status`
- Internal Chat adapter over shared dashboard/project-insight contracts
- Owner Settings controls for Admin MCP permissions, scope, OAuth binding and
  revoke/unbind

## Exit evidence

| Exit criterion | Repository result | Evidence |
|---|---:|---|
| No SaaS/out-of-scope visibility | Pass | Environment-compiled aliases, exact filters and exclusion tests contain only Product resources |
| Operations bounded and redacted | Pass | 30-day/50-row caps, exact Logging view, safe field projection and full credential/URL/PII/path/UUID redaction |
| Internal/External grounded consistency | Pass | Internal Chat invokes the exact shared Backend calculation services; exact fixture metrics match |
| Admin allow/deny matrix | Pass | All six operations tools pass authorized and missing-permission cases, 12/12 at 100% |
| Revocation | Pass | Backend re-resolves the directory on successive calls and observes disablement on the next call |
| Existing Chat history separation | Pass | MCP persists no prompt/response; existing Internal Chat history path remains separate |
| Golden Phase 5 case | Pass | G-014 and all Phase 5 control gates pass at 100% |
| Operations p95 <=15 seconds | Live proof pending | Requires deployed Demo sources and an authorized Owner/Admin sample |

## Verification results

- Backend full suite: `114 passed`.
- MCP full suite: `88 passed` (one non-failing Starlette/httpx deprecation
  warning).
- Phase 2, Phase 3, Phase 4 and Phase 5 evaluators: `100.0%`, all gates true.
- MCP Ruff: pass.
- Every changed Phase 5 Backend file Ruff: pass.
- Frontend ESLint: pass.
- Frontend production build: pass (the existing Vite large-chunk advisory is
  non-failing).
- Backend and non-root MCP production container builds: pass as
  `projects-001-be:phase5-local` and `projects-001-mcp:phase5-local`.
- `deploy_mcp.sh` Bash syntax and `git diff --check`: pass.

## Demo release prerequisites

Repository completion does not authorize cloud or pilot changes. Before Phase 5
live evidence can be marked complete:

1. Provision the dedicated Demo operational bucket/sink/view with exactly
   30-day retention and filters limited to `projects-001-fe`, `projects-001-be`,
   `projects-001-mcp` and `severity>=WARNING`.
2. Grant the Demo MCP identity exact operational-view access plus only the
   required Product resource metadata permissions. Prove excluded SaaS,
   BigQuery, Secret Manager and business-data write access are absent.
3. Populate the two operational-view environment values, deploy Backend first,
   then MCP `0.5.0`, and verify 37 tools plus 28 internal contracts.
4. Run all six operations tools with the consenting Demo Owner, including a
   bounded G-014 sample. Confirm no raw query, token, URL, email, GCS path,
   record UUID, environment data or service identity is returned.
5. Compare the same Dashboard and project-insight questions through External
   MCP and Internal Chat; exact money, source and calculation facts must match.
6. Select one assigned-project Admin, grant only the permissions needed for the
   pilot, and run the full allow/deny/cross-project matrix.
7. Revoke and unbind the Admin, then prove the immediately subsequent MCP call
   is denied without source access.
8. Confirm Product Audit coverage, zero unexpected Cloud Run errors, operations
   p95 `<=15 seconds`, rollback to prior Backend/MCP revisions, and candidate
   restore.

Phase 6 release work remains blocked until those live Demo results are recorded
in `phase5-demo-release-evidence.md`.
