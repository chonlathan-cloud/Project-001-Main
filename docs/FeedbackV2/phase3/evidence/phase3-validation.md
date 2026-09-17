# Phase 3 validation evidence

Date: 2026-09-17 (Asia/Bangkok)

Execution scope: local repository, loopback services, isolated PostgreSQL, and
synthetic non-sensitive quotation fixtures.

Production deployment, production data access/mutation, IAM, credential, and
authentication architecture changes: **not performed**.

## Repository baseline

- Branch: `feature`
- Starting Phase 3 HEAD:
  `4d77323102743b90007562b1dafdf4c423114cdb`
- That commit is the committed Phase 2 implementation baseline.
- Existing Phase 2 create/load/save/copy, hierarchy identity, price-state,
  server calculation, Owner/Admin, feature-gate, offline/conflict, legacy
  history, and legacy sync behavior was retained.

## Migration evidence

The local PostgreSQL 16 + pgvector harness remained bound to
`127.0.0.1:55433`, backed by Docker `tmpfs`, and used no backend `.env`.

Two upgrade paths were exercised:

1. Fresh database: Alembic upgraded an empty schema through `20260915_0001`
   and Phase 3 `20260917_0002`.
2. Frozen current-schema bootstrap: the 15-table pre-Alembic baseline was
   stamped, upgraded through Phase 1 and Phase 3, and checked for metadata
   drift.

Results:

- `alembic current`: `20260917_0002 (head)`
- `alembic check`: no new upgrade operations detected
- Phase 1/3 schema verifier: 15 V2 tables; zero source-selection rows in the
  clean fixture
- Legacy golden verifier: 3 scenarios × 11 projections passed
- Historical finance verifier: passed
- Funds source/completeness verifier: passed

The migration deliberately has no destructive downgrade. Release still
requires the separately authorized deployed-schema preflight and backup/restore
gate from Phase 0 CDR-005.

## Automated results

| Gate | Result |
| --- | --- |
| Phase 3 focused backend integration/export | 7 passed |
| Phase 0–3 backend integration set | 32 passed |
| Complete backend suite | 163 passed |
| Ruff on Phase 3 and modified Python files | passed |
| Backend startup/OpenAPI | passed; 202 routes |
| Frontend tests | 9 passed |
| Frontend lint | passed |
| Frontend production build | passed; existing Vite >500 kB chunk warning remains |
| MCP complete suite | 133 passed; one existing Starlette/httpx deprecation warning |
| Migration empty/current-schema paths | passed |
| `git diff --check` | passed |

The repository-wide backend Ruff command is not a green gate: it reports seven
pre-existing findings in unrelated legacy modules (`input_requests.py`,
`responses.py`, `ai_service.py`, `boq_hierarchy.py`, and
`flowaccount_service.py`). Modified Phase 3 Python files pass the targeted Ruff
gate; those unrelated findings were not changed under this scope.

## Lifecycle and concurrency evidence

The Phase 3 integration suite verifies:

- draft → issue → record acceptance, including invalid state and stale-version
  rejection;
- immutable issued/accepted rows and a frozen accepted snapshot;
- accepted MAIN replacement only after explicit retained/absorbed CO mapping;
- mutual exclusion for alternatives and one winner under concurrent acceptance;
- accepted ADD/DEDUCT membership counted once;
- issued, rejected, withdrawn, and other unaccepted revisions omitted from the
  active baseline;
- stale, duplicate, overlapping, and over-quantity deductions rejected;
- eight concurrent document-number allocations produce eight unique numbers;
- retrying an idempotent lifecycle or export command does not duplicate the
  baseline, acceptance, upload, or artifact;
- later mutable project/customer/scope edits do not alter historical snapshot
  payloads or pinned preview identity.

The accepted-only source assertions use the V2 baseline contract directly.
Public project, Dashboard, Funds, Chat, MCP, and legacy BOQ consumers remain on
the Phase 1 compatibility behavior pending the explicitly out-of-scope Phase 5
cutover.

## Export evidence

Generated files were parsed and rendered, not checked by extension alone:

- Customer XLSX opens as an OOXML workbook; quantities/rates/totals are numeric,
  Thai strings survive round-trip, hierarchy/subtotals/VAT/payment schedules
  match the frozen snapshot, and formula-leading text is neutralized.
- Customer workbook and PDF allowlists exclude cost, margin, vendor pricing,
  internal notes, and internal cost-plan fields.
- Internal XLSX includes only the approved internal cost/consolidated projection
  and is tied to the frozen cost-plan version.
- A representative multi-page A4 customer PDF renders to images, preserves Thai
  text, repeats headers, carries document/revision/page identity, and has no
  clipped representative rows.
- Export retries reuse the original snapshot rather than current mutable rows.
- Artifact ownership and cross-project revision/artifact access fail closed;
  READY downloads receive a 15-minute signed URL using the existing private GCS
  pattern.

## Browser evidence

The checked-in captures render the production BOQ/quotation React components
with synthetic fixtures. A temporary local screenshot entrypoint was used only
to isolate deterministic states and was removed before commit. No production
route, login, or external identity state was changed.

| State | Artifact | Dimensions | SHA-256 |
| --- | --- | --- | --- |
| Accepted immutable lifecycle | [accepted-lifecycle.png](screenshots/accepted-lifecycle.png) | 1440 × 1600 | `e9c0c84b1abf3d866fa53498e661eaaf6ece99a767e83b7a1f22cec7841c41a3` |
| Exact pinned snapshot preview | [pinned-preview.png](screenshots/pinned-preview.png) | 1440 × 1600 | `f53adc5d42497ebe6a7203e4a12479f73134903f47b80f2d0436160f9af7652d` |
| Admin read-only lifecycle | [admin-readonly.png](screenshots/admin-readonly.png) | 1440 × 1200 | `f39941e81f1f80a03d5c2dbdf23d150e88337888e2426f4da042f057b44083eb` |
| Responsive API failure/retry | [api-error-responsive.png](screenshots/api-error-responsive.png) | 720 × 1000 | `843a1a85efa8dd863300e50fe9298c409bbd1d8906feec845ec635cfe605c1ca` |

Google Stitch was queried before frontend implementation as required by the
local UI skill, but the connector returned `Authentication required`. The
checked-in `Design/DESIGN.md`, approved BOQ hierarchy contract, Phase 2
components, and existing design tokens were used as the fallback. No visual
contract was inferred from production data.

## Commands

```bash
cd Projects-001-BE
./scripts/phase1_test_db.sh down
./scripts/phase1_test_db.sh up
./scripts/phase1_test_db.sh upgrade-empty
./scripts/phase1_test_db.sh current
./scripts/phase1_test_db.sh check

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
PHASE3_DATABASE_URL=postgresql+asyncpg://phase1:phase1@127.0.0.1:55433/projects001_phase1_test \
BOQ_V2_ENABLED=true \
venv/bin/python -m pytest tests/phase3 -q

PYTHONDONTWRITEBYTECODE=1 \
DATABASE_URL=postgresql+asyncpg://phase1:phase1@127.0.0.1:55433/projects001_phase1_test \
PHASE2_DATABASE_URL=postgresql://phase1:phase1@127.0.0.1:55433/projects001_phase1_test \
PHASE3_DATABASE_URL=postgresql+asyncpg://phase1:phase1@127.0.0.1:55433/projects001_phase1_test \
BOQ_V2_ENABLED=true \
venv/bin/python -m pytest -q

PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m ruff check \
  app/api/v1/boq_v2.py app/models/boq_v2.py \
  app/schemas/boq_v2_schema.py app/schemas/boq_quotation_schema.py \
  app/services/boq_document_service.py app/services/boq_export_service.py \
  app/services/boq_numbering_service.py app/services/boq_quotation_service.py \
  app/services/gcs_storage_service.py tests/phase3

cd ../Projects-001-FE
npm test
npm run lint
npm run build

cd ../Projects-001-MCP
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q
```

## Remaining release prerequisites and risks

- The feature gates still default to disabled. No release/deployment was done.
- Apply Phase 0 CDR-005 deployed-schema, backup, migration-order, and monitoring
  gates before any real release.
- Stitch authentication is still required for a future direct comparison with
  the latest remote design source.
- Phase 4 supplier/catalog/cost-plan publication behavior is intentionally not
  present. Internal export only consumes an already frozen applicable
  cost-plan version.
- Phase 5 must explicitly migrate public operational consumers before legacy
  budget behavior or sync endpoints can be retired.
