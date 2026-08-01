# Phase 6 repository evidence

Evidence date: 2026-08-01

Status: repository implementation complete; live Private Plugin/Beta gates are
blocked as recorded in `phase6-beta-release-evidence.md`.

## Implemented scope

- Product MCP version `0.6.0`; the 37-tool read-only contract remains additive
  and unchanged.
- Valid `projects-001-product` private plugin manifest and `.app.json` boundary.
- Bundled `projects-001-workflows` skill for permission-aware, source-grounded
  multi-tool workflows.
- Deterministic ChatGPT registered-app binding/validation; fake IDs fail closed.
- Safe release-copy preparation that leaves the checked-in plugin unbound and
  stores a real Demo/Beta connection ID only under an ignored output path.
- Exact Beta service-account identity, 365-day audit window/retention, and
  immutable Demo-tested image-digest enforcement.
- Owner/Admin consent, connection, troubleshooting and revocation guide.
- Privacy notice plus deployment, rollback, OAuth rotation, IAM, audit outage,
  source outage, incident, schema, support and retention runbook.
- Phase 6 contract tests and evaluator separate repository readiness from live
  release evidence.

## Verification

Focused validation before the full regression:

| Check | Result |
|---|---|
| Phase 6/config/protocol tests | 49 passed |
| MCP Ruff | Passed after formatting corrections |
| Official plugin package validator | Passed |
| Bundled skill quick validator | Passed |
| Deployment script syntax | Passed |
| Patch whitespace | Passed |

Full verification:

| Check | Result |
|---|---|
| MCP full suite | 131 passed; one non-failing Starlette/httpx deprecation warning |
| Backend full suite | 114 passed with `PYTHONPATH=.` |
| Phase 2–5 evaluators | 100%; all repository gates passed |
| Phase 6 evaluator | Repository gate passed; live gate deliberately `not_evaluated`; 7 Phase 5 pending rows detected |
| Frontend | ESLint passed; Vite production build passed with the existing large-chunk warning |
| MCP production image | Local Docker build passed |
| Backend production image | Local Docker regression build passed |
| MCP container smoke | `/health` = `200` with version `0.6.0`; unauthenticated initialize = `401` with resource metadata |
| MCP Ruff | Passed |
| Backend Ruff | Full scan found eight pre-existing findings in unrelated untouched files; no Backend file changed in Phase 6 |
| Plugin and skill validators | Passed |
| Deploy syntax / patch whitespace | Passed |

## Live boundary

The checked-in `.app.json` has an empty `apps` object by design. ChatGPT creates
the real `plugin_asdk_app...` ID only when a Demo or Beta MCP connection is
registered. The repository can now produce an ignored, bound Demo release copy
without changing source. Live ChatGPT registration/binding, workspace sharing,
GCP provisioning, deployment, IAM, OAuth configuration and cohort enablement
have not been performed by Phase 6 repository work.

Read-only inventory found the Beta Backend, frontend, Cloud SQL, Firestore and
five data buckets, but not the Beta MCP service account, MCP Cloud Run service,
Product Audit bucket, or operational bucket. Therefore the Beta decision is
NO-GO until the missing resources and all earlier/live gates are approved and
verified.
