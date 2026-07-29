# Phase 2 Demo release evidence

Evidence date: 2026-07-29
Environment: Demo (`project001-489710`, `asia-southeast1`)
Pilot role: Owner only

This report tracks the evidence required to close the Core Business Owner Pilot.
It contains no token, secret, prompt, document body or private file content.

## Automated verification

| Check | Result | Evidence |
|---|---:|---|
| MCP regression | Pass | 49 tests passed |
| MCP lint | Pass | Ruff passed |
| Backend MCP contracts | Pass | 30 focused tests passed |
| Backend MCP lint | Pass | Ruff passed |
| Core Golden fixture | Pass | 6/6 cases, 100% (threshold 95%) |
| BOQ/version fixture exactness | Pass | Exact money, version intervals and stable line identities validated |

Reproduce the Golden and BOQ result from `Projects-001-MCP`:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --isolated --no-project \
  --with-requirements requirements-dev.txt \
  python -m tests.evals.phase2_evaluator
```

The evaluated Core Phase 2 cases are `G-001-th`, `G-001-en`, `G-003`,
`G-004`, `G-005` and `G-009`. Later-phase cases remain out of this score.

## Live Demo evidence

| Gate | Result | Evidence |
|---|---:|---|
| OAuth Owner login | Pass | Auth0 Authorization Code flow completed with consent |
| MCP Inspector initialization | Pass | Streamable HTTP connected and tool inventory loaded |
| Search and fetch | Pass | Authorized project search returned a stable reference and fetch resolved it |
| BOQ current/history/as-of | Pass | Current v3 and point-in-time v2 resolved with source/version metadata |
| BOQ comparison | Pass | v2 to v3: 41 added, 37 removed and 6 changed lines |
| Unavailable project opacity | Pass | Returned `NOT_FOUND_OR_FORBIDDEN` without existence disclosure |
| Missing/malformed bearer | Pass | Both requests returned HTTP 401 |
| Simple-read latency | Pass | 39 successful requests; p95 0.597 seconds (target <=5 seconds) |
| Runtime errors | Pass | No Cloud Run ERROR entries in the bounded six-hour window |
| Sensitive audit leakage | Pass | 18 audit events; zero token/secret/prompt/document-body matches |
| Runtime write access | Pass | Dedicated MCP identity has logging only and no business-data write role or user-managed key |

## Remaining release gates

- Deploy the audit redaction fix and confirm live events retain
  `authorization_decision` while sensitive fields remain absent.
- Run one real Codex or ChatGPT Desktop Owner flow and record the prompt/tool/result
  evidence separately from deterministic fixture evaluation.
- Disable or clear the pilot Owner binding, prove that the next call is blocked,
  then restore the exact binding and prove access returns.
- Execute a reversible Cloud Run rollback drill and restore the approved revision.
- Record the final cross-environment denial and project-isolation evidence. The
  Owner pilot legitimately has all-project scope, so assigned-project isolation
  remains covered by automated policy tests rather than this Owner account.

Phase 3 must not begin until every remaining item is complete and this report is
updated to show a closed Phase 2 gate.
