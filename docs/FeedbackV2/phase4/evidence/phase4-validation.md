# Phase 4 validation evidence

Date: 2026-09-17 (Asia/Bangkok)

## Environment and safety

- Baseline: branch `feature`, HEAD `f4265f8fa95a51e656ed52ee242dcda1325a4919`, clean tree before implementation.
- Database: isolated PostgreSQL 16/pgvector container on `127.0.0.1:55433`, `tmpfs` storage, test-only credentials.
- Backend `.env` was not used for schema gates; commands supplied the isolated URL explicitly.
- No production database, deployment, IAM, credentials, or production data was accessed or changed.

## Focused Phase 4 behavior

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 APP_ENV=development \
DATABASE_URL="$PHASE4_TEST_URL" PHASE4_DATABASE_URL="$PHASE4_TEST_URL" \
BOQ_V2_ENABLED=true venv/bin/python -m pytest -q \
tests/phase4/test_vendor_cost_price_database_api.py
```

Result: **7 passed in 5.41s**.

Covered evidence:

- two vendors in one project and different MATERIAL/LABOR vendors;
- estimate-only forecast, agreed-cost forecast and unchanged accepted sell;
- partial quantity rejected; unit/spec/basis changes stale a selection;
- expired/spec/unit/unknown-tax warnings require acknowledgement and reason;
- full coverage and explicit reconfirmation accepted;
- replacement preserves history and never double-counts;
- `UNKNOWN`, explicit zero with reason and `NOT_APPLICABLE` remain distinct;
- offer entry leaves Funds source/version unchanged; publish changes the source identity explicitly;
- repeated selection/publish is idempotent; payload mismatch rejects reused keys;
- stale expected versions, concurrent publish and Funds-allocation races are serialized/rejected safely;
- Owner mutation and Admin read-only enforcement;
- cross-project vendor/component substitution rejection;
- evidence-object metadata is retained without exposing a public download;
- issue/acceptance/vendor offer/agreement/estimate observations and lineage-aware distinct samples;
- explicit promotion/reference versioning, snapshot reuse and archive history;
- RFQ and selected-vendor XLSX/PDF are snapshot-scoped and exclude customer/competitor prices.

## Regression suites

Backend full suite:

```bash
PYTHONDONTWRITEBYTECODE=1 APP_ENV=development \
DATABASE_URL="$PHASE4_TEST_URL" PHASE2_DATABASE_URL="$PHASE4_TEST_URL" \
PHASE3_DATABASE_URL="$PHASE4_TEST_URL" PHASE4_DATABASE_URL="$PHASE4_TEST_URL" \
BOQ_V2_ENABLED=true venv/bin/python -m pytest -q
```

Result: **170 passed in 11.65s**, no skips.

Backend MCP/access/security focus:

```bash
venv/bin/python -m pytest -q \
tests/test_mcp_read_contracts.py tests/test_mcp_phase3_contracts.py \
tests/test_mcp_phase4_contracts.py tests/test_mcp_phase5_processing.py \
tests/test_mcp_access_service.py tests/test_mcp_service_auth.py \
tests/test_phase8_security.py
```

Result: **61 passed in 1.59s**.

Standalone MCP repository:

```bash
cd Projects-001-MCP
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q
```

Result: **133 passed**. One pre-existing Starlette/httpx deprecation warning.

Frontend:

```bash
cd Projects-001-FE
npm test
npm run lint
npm run build
```

Results: **10 tests passed**; lint passed; production build passed. Vite retained the existing warning for chunks over 500 kB.

## Migration and compatibility gates

Fresh database path:

```bash
./scripts/phase1_test_db.sh down
./scripts/phase1_test_db.sh up
./scripts/phase1_test_db.sh upgrade-empty
./scripts/phase1_test_db.sh check
./scripts/phase1_test_db.sh current
./scripts/phase1_test_db.sh verify
```

Result: migrations `0000 -> 0001 -> 0002 -> 0003`; Alembic reported no pending operations; current revision `20260917_0003`; **22 BOQ V2 tables**, zero source/Phase 4 business rows after migration.

Existing 15-table baseline path:

```bash
./scripts/phase1_test_db.sh down
./scripts/phase1_test_db.sh up
./scripts/phase1_test_db.sh upgrade-current
./scripts/phase1_test_db.sh check
./scripts/phase1_test_db.sh current
./scripts/phase1_test_db.sh verify
./scripts/phase1_test_db.sh golden
./scripts/phase1_test_db.sh finance-history
./scripts/phase1_test_db.sh funds
```

Results:

- pre-Alembic 15-table schema upgraded to `20260917_0003`;
- schema check clean; 22 V2 tables; no business-data backfill;
- golden compatibility passed for `dual_boq`, `subcontractor_only`, and `no_boq`, 11 projections each;
- archived finance/as-of history preserved;
- Funds unknown-cost guard and reversal behavior passed.

Other checks:

```bash
ruff check <all changed backend Python files>
bash -n scripts/phase0_test_db.sh scripts/phase1_test_db.sh
docker compose ... config -q
PYTHONDONTWRITEBYTECODE=1 ... python -c 'import main; ...'
git diff --check
```

Results: Ruff passed; shell syntax and both Compose configurations passed; startup import passed; OpenAPI contained **13 Phase 4 paths**; final whitespace check passed.

## UI evidence

Local browser QA used an isolated development-only session and the test database; the session was removed immediately afterwards.

Observed Vendor Cost UI:

- published plan v3 with original estimate THB 8,000, agreed THB 4,500 and complete state;
- two comparable full-coverage material offers (THB 7,770 and THB 4,500);
- exactly one row marked selected;
- visible quantity/unit/specification, validity, tax and included-charge basis;
- explicit vendor-safe RFQ/selected-vendor export controls;
- explicit promotion and snapshot-reuse controls.

Observed Price Database UI:

- catalog version/status and current reference price version;
- two distinct samples across four issue/acceptance observations;
- observation type, source event, project identifier, date, quantity and unit;
- Owner-only explicit reference update form.

Representative screenshots were emitted as browser evidence blocks in the implementation handoff. The browser connector does not provide a filesystem-save primitive, so no screenshot binary is checked into the repository.

## Failed attempts, skips and unrun checks

- An initial focused test command used the root virtualenv, which lacked `openpyxl`; rerunning with the backend `venv` passed.
- An initial frontend command incorrectly appended `--run` to the Node test script; rerunning `npm test` passed 10/10.
- One initial focused backend run set only `PHASE4_DATABASE_URL`; application requests followed the local `.env` database path and failed before assertions. Rerunning with both explicit isolated `DATABASE_URL` and `PHASE4_DATABASE_URL` passed 7/7.
- No checks are currently skipped in the full backend run.
- Production/deployed-schema preflight, deployment and live external storage verification were intentionally not run because they are explicitly outside scope.
- Stitch was unavailable due authentication; checked-in design guidance and existing components were used instead.

## Remaining risks and deliberate boundaries

- The public Funds projection retains its Phase 0 consumer-specific formula until Phase 5; Phase 4 updates the active source identity/version only after explicit publication.
- Unit normalization is intentionally conservative: incompatible unit/specification offers are not silently converted. Any future conversion table needs a separate approved business decision.
- Evidence storage identity is recorded and protected by project-scoped APIs, but Phase 4 adds no upload/download workflow.
- Browser QA was desktop-focused. Responsive behavior relies on scoped CSS and the production build; a dedicated mobile UAT matrix remains follow-up work.
- Legacy BOQ/sync routes remain present by design and must not be retired before Phase 5.
