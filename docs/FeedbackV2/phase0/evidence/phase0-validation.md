# Phase 0 validation record

Date: 2026-09-14 (Asia/Bangkok)

## Baseline

```text
branch: feature
HEAD: ae91252f9fa299c4ce832bfcf20c4780d071cce1
plan baseline: 8f53197c6cf369b60a5cb2d6771a9bcc7b6b4020
merge-base ancestor check: pass
baseline..HEAD commit count: 1
baseline..HEAD source/config/test changes: 0
baseline..HEAD only path: docs/FeedbackV2/ModifyV2-plan.md
initial worktree: clean
tracking: feature...origin/feature [ahead 29]
```

## Isolated database

```text
image: pgvector/pgvector:pg16@sha256:7d400e340efb42f4d8c9c12c6427adb253f726881a9985d2a471bf0eed824dff
container: projects001_phase0-postgres-1
binding: 127.0.0.1:55432 -> 5432
database: projects001_phase0_test
storage: tmpfs
health: healthy
registered tables created: 15
PostgreSQL: 16.13
vector: 0.8.2
boq_v2_* tables: 0
schema fingerprint: 1f5ef82d148f9a809709c2a2adfdc543aaee0b5d6e7556fd7aaf218fb6a1ac5a
```

No backend `.env` URL was used. The verifier's fixture inserts were enclosed in
a transaction and rolled back. The Compose database was removed after evidence
capture.

## Golden compatibility

```text
contract version: 1
scenarios: dual_boq, subcontractor_only, no_boq
projections per scenario: 11
result: pass
```

The database-backed verifier called current project list, project BOQ detail,
Dashboard, Funds margin, Chat snapshot/rollup, and MCP customer-budget code. It
also applied the current frontend card fallback rule. The golden artifact locks
existing divergence; it does not endorse the formulas as the V2 canonical
calculation.

## Automated regression results

| Area | Command summary | Result |
| --- | --- | --- |
| Backend focused + Phase 0 | `pytest tests/phase0` plus Funds, Input, MCP backend, Settings, FlowAccount files listed in Phase 0 README | 70 passed |
| Frontend baseline | `npm test` | 5 passed; only two configured test globs |
| Frontend lint | `npm run lint` | passed |
| Frontend build | `npm run build` | passed; existing >500 kB chunk warning |
| MCP contract/access/security | `.venv/bin/python -m pytest tests/contract tests/authorization tests/security` | 128 passed; one Starlette/httpx deprecation warning |
| Golden DB verifier | `./scripts/phase0_test_db.sh verify` | passed, 3 scenarios × 11 projections |
| Schema preflight | `./scripts/phase0_test_db.sh fingerprint` | passed; fingerprint above |

All Python commands used `PYTHONDONTWRITEBYTECODE=1`. Backend unit/regression
imports received an explicit loopback dummy test URL; the database-backed golden
verification used only the isolated Compose URL.

## Non-passing/unavailable checks

- Google Stitch design query returned `Authentication required`. No UI code was
  changed in Phase 0, and Phase 1 is backend-only foundation, so this is not a
  Phase 0/1 blocker. It must be resolved before Phase 2 UI implementation.
- One earlier MCP attempt using the backend Python environment could not run 16
  async tests because that environment lacks `pytest-asyncio`. The documented
  project-local MCP `.venv` was then used and all 128 selected tests passed.

## Scope evidence

- No BOQ V2 ORM table or migration was added.
- No route, service, public response, sync flow, IAM, deployment file, credential,
  or production data was changed.
- New executable behavior is confined to test/preflight tooling and tests.
