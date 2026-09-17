# Phase 2 validation evidence

Date: 2026-09-15 (Asia/Bangkok)
Execution scope: local repository, loopback services, and isolated PostgreSQL
Production/deployment/IAM/data mutation: **not performed**

## Repository baseline and scope

- Branch: `feature`
- Phase 1 baseline commit:
  `92fcc27002fd4aeade09893862c85902302f7c63`
- Phase 2 changes remain uncommitted.
- Phase 1 migration and compatibility code was preserved.
- No Phase 3 lifecycle/export, Phase 4 vendor/catalog, Phase 5 sync retirement,
  or Phase 6 deployment work was added.

## Isolated database

- Image: `pgvector/pgvector:pg16` pinned by digest
  `sha256:7d400e340efb42f4d8c9c12c6427adb253f726881a9985d2a471bf0eed824dff`
- Target: `127.0.0.1:55433/projects001_phase1_test`
- Storage: Docker `tmpfs`
- Frozen 15-table legacy schema was created, stamped at `20260915_0000`, and
  upgraded to `20260915_0001`.
- `alembic current`: `20260915_0001 (head)`
- `alembic check`: `No new upgrade operations detected.`
- Phase 1 schema verifier: 10 V2 tables; zero source-selection rows after
  migration.

The database was recreated from a fresh `tmpfs` container before the recorded
schema and compatibility checks. An earlier golden run against an accumulated
local test database exceeded an existing dashboard pagination window; it was
discarded and not used as evidence.

## Automated results

| Gate | Result |
| --- | --- |
| Phase 2 focused backend integration | 2 passed |
| Backend complete suite with Phase 2 enabled | 156 passed |
| Ruff on new Phase 2 Python files | passed |
| Frontend tests | 8 passed, including 3 native BOQ state tests |
| Frontend lint | passed |
| Frontend production build | passed; existing >500 kB chunk warning remains |
| MCP contract/authorization/security | 128 passed; existing deprecation warning only |
| Legacy database golden verifier | 3 scenarios × 11 projections passed before and after the complete backend suite |
| Historical finance verifier | passed |
| Funds source/completeness verifier | passed |
| Backend startup/OpenAPI | passed; 190 routes |
| Migration metadata drift | none detected |

The focused backend integration verifies:

- disabled-by-default rollout fails closed;
- Owner create/save/copy and Admin read-only behavior;
- idempotent create/save retry and conflicting-key rejection;
- optimistic stale-version conflict with current version;
- orphan rejection and revision-owned row/component identity;
- hierarchy save/reload and sibling reorder with stable row/logical IDs;
- revision copy with preserved logical lineage and new persistence IDs;
- unknown vs explicit priced zero vs not-applicable completeness;
- null forecast/margin while required cost is unknown;
- server item/document totals and derived SECTION/CATEGORY subtotals;
- no project source-selection or accepted baseline row from a DRAFT.

## Local API and browser evidence

An isolated five-row hierarchy was created through the local API after the
final subtotal implementation. The response reported:

```text
document sell total: 8000.00
known estimated cost: 5000.00
forecast cost: null
SECTION subtotal: 8000.00
CATEGORY subtotal: 8000.00
SUBCATEGORY subtotal: 8000.00
```

Interactive local browser checks covered create/load, editing, reorder,
save/reload, `Ctrl/Cmd+S`, failed-save dirty-state retention and retry, copy to
an empty project, consolidated and cost views, and 1440/1024/390 responsive
layouts. The server-derived subtotal adjustment was verified through the API
and the final browser DOM before the representative captures.

Final screenshot capture used a user-initialized synthetic browser session and
runtime-only local dependency overrides. No real Google/LINE login or external
identity write was performed. Mobile capture exposed an ITEM description field
overflow caused by a more-specific generic input width rule; the BOQ component
CSS was corrected, the mobile screenshot was recaptured, and frontend
test/lint/build were rerun successfully.

| Viewport | Artifact | SHA-256 |
| --- | --- | --- |
| Desktop 1440 × 900 | [native-boq-desktop-1440.jpg](screenshots/native-boq-desktop-1440.jpg) | `4f087b11c41359436766f981536a99f13f002b436e7761fb1ce96ec807e4c946` |
| Tablet 1024 × 768 | [native-boq-tablet-1024.jpg](screenshots/native-boq-tablet-1024.jpg) | `1a811d3880fc8090bd844a2a87d210309c0eafb4e53a1c4cc95a08b4f44cc955` |
| Mobile 390 × 844 | [native-boq-mobile-390.jpg](screenshots/native-boq-mobile-390.jpg) | `880379609f6296d65d245ce461ad72de439d7e945d78738ebc650dc168e93a19` |

Chrome full-page capture produced JPEG payloads at 1434 × 1611, 1018 × 2044,
and 384 × 4416 pixels respectively after accounting for browser chrome and the
vertical scrollbar. The requested viewport overrides were reset after capture.
The existing application shell also issued its normal read-only notification
and access-list requests; no external mutation request was made.

Google Stitch was queried before UI implementation as required by the local UI
skill, but the connector returned `Authentication required`. The checked-in
`Design/DESIGN.md`, BOQ hierarchy contract, and existing component system were
used as the authoritative fallback. Stitch authentication remains an external
prerequisite for a future design-source comparison, not a Phase 2 data or
security blocker.

## Commands

```bash
cd Projects-001-BE
./scripts/phase1_test_db.sh down
./scripts/phase1_test_db.sh up
./scripts/phase1_test_db.sh upgrade-current
./scripts/phase1_test_db.sh current
./scripts/phase1_test_db.sh check
./scripts/phase1_test_db.sh verify
./scripts/phase1_test_db.sh golden
./scripts/phase1_test_db.sh finance-history
./scripts/phase1_test_db.sh funds

PYTHONDONTWRITEBYTECODE=1 \
DATABASE_URL=postgresql+asyncpg://phase1:phase1@127.0.0.1:55433/projects001_phase1_test \
PHASE2_DATABASE_URL=postgresql://phase1:phase1@127.0.0.1:55433/projects001_phase1_test \
BOQ_V2_ENABLED=true \
venv/bin/python -m pytest -q

PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m ruff check \
  app/api/v1/boq_v2.py \
  app/schemas/boq_v2_schema.py \
  app/services/boq_document_service.py \
  tests/phase2/test_boq_document_api.py

cd ../Projects-001-FE
npm test
npm run lint
npm run build

cd ../Projects-001-MCP
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest \
  tests/contract tests/authorization tests/security --disable-warnings
```

## Remaining release prerequisites

Phase 2 is ready only as a local, disabled-by-default implementation. Before an
external release, separately authorize and record the Phase 1 CDR-005 deployed
schema preflight, backup/restore readiness, migration-before-code ordering,
runtime feature-gate configuration, and post-release monitoring. Do not create
or switch a V2 operational budget source during Phase 2.
