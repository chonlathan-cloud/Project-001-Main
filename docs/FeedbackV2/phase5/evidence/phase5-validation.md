# Phase 5 validation evidence

Validation date: 2026-09-18 (Asia/Bangkok)

## Scope and baseline

- Branch: `feature`
- Phase 4 baseline: `7a10f93f8b55375cacf51f226bfeb584f5ff50a0`
- Worktree was clean at Phase 5 preflight.
- All database validation used the loopback-only PostgreSQL/pgvector test harness at `127.0.0.1:55433` with `tmpfs` storage and a database name ending in `_test`.
- No deployment, production-data access, IAM mutation, authentication redesign, legacy-row deletion, or Phase 6 enablement was performed.

## Automated regression

### Backend

The complete suite, including Phase 2–4 PostgreSQL integration tests and the new Phase 5 contracts, was executed with the isolated database variables and development-only debug authentication expected by those integration tests:

```bash
PYTHONDONTWRITEBYTECODE=1 \
APP_ENV=development \
DATABASE_URL='postgresql+asyncpg://phase1:phase1@127.0.0.1:55433/projects001_phase1_test' \
PHASE2_DATABASE_URL='postgresql+asyncpg://phase1:phase1@127.0.0.1:55433/projects001_phase1_test' \
PHASE3_DATABASE_URL='postgresql+asyncpg://phase1:phase1@127.0.0.1:55433/projects001_phase1_test' \
PHASE4_DATABASE_URL='postgresql+asyncpg://phase1:phase1@127.0.0.1:55433/projects001_phase1_test' \
BOQ_V2_ENABLED=true \
uv run --with-requirements requirements-dev.txt python -m pytest -q
```

Result: `180 passed in 10.65s`.

Focused Phase 5 contracts:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with-requirements requirements-dev.txt \
  python -m pytest tests/phase5/test_active_budget_cutover_contracts.py -q
```

Result: `9 passed`. The cases cover shared V2 sell projections, Funds forecast-margin projection, UNKNOWN-cost nullability, locked legacy formulas, all four authenticated sync tombstones, removal of runtime sync services, and stable V2 MCP version/line identities.

`ruff` was run on every modified Python module and test. Result: `All checks passed!`.

### Standalone MCP

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with-requirements requirements-dev.txt python -m pytest -q
```

Result: all `133` collected tests passed. One existing Starlette/httpx deprecation warning remains in `tests/contract/test_gcp_operations.py`.

### Frontend

```bash
npm test
npm run lint
npm run build
```

Results:

- Node tests: `10 passed`, `0 failed`.
- ESLint: passed.
- Vite production build: passed (`2965` modules transformed).
- The existing `>500 kB` chunk-size advisory remains; no new build error was introduced.

## Clean schema and cutover proof

The local test container was deleted and recreated before the final schema proof. Migrations were applied from an empty database through `20260917_0003`.

```bash
./scripts/phase1_test_db.sh down
./scripts/phase1_test_db.sh up
./scripts/phase1_test_db.sh upgrade-empty
./scripts/phase1_test_db.sh check
./scripts/phase1_test_db.sh current
./scripts/phase1_test_db.sh verify
./scripts/phase1_test_db.sh golden
./scripts/phase1_test_db.sh finance-history
./scripts/phase1_test_db.sh funds
./scripts/phase1_test_db.sh phase5-cutover
```

Evidence:

- Alembic autogenerate: `No new upgrade operations detected.`
- Current revision: `20260917_0003 (head)`.
- Phase 4 schema: `22` V2 tables, `0` source-selection rows, `0` Phase 4 business rows after empty migration.
- Legacy golden contract: all `3` scenarios and `11` consumer projections per scenario passed.
- Archived legacy BOQ finance references and as-of source reads were preserved.
- Funds: incoming to unknown V2 passed; new outward was blocked; valid reversal passed.
- Same-project cutover: legacy `900,000.00` changed to V2 MAIN `1,200,000.00` + ADD `100,000.00` − DEDUCT `50,000.00` = `1,250,000.00`, while legacy BOQ, installment, transaction, pre-activation as-of reads, and stable MCP V2 references remained available.
- Every verifier used a rollback transaction; the container was removed after validation.

The first final schema-verifier invocation was intentionally rejected because local UAT/integration fixtures were still present. Recreating the `tmpfs` test container restored the required empty-migration precondition and the full sequence above passed. This did not involve production data.

## Browser UAT and UI review

Chrome headless was run against local Vite and FastAPI instances with a separate temporary browser profile and the isolated test database. The normal Chrome tab could not be automated because another browser extension UI was open, so the fallback did not reuse the user's active browser state.

Validated routes and viewports:

- Project list at `1440 × 1000`.
- Project list at `390 × 844`.
- Project detail/active budget at `1440 × 1000`.

Observed evidence:

- Project list loaded successfully using the batched project response.
- Project detail showed `Active budget 900,000.00 THB · LEGACY · NO_BUDGET_DATA` and the `Open Native BOQ` action.
- No Google Sheets or sync control/copy was present on Project list/detail (`syncText=false`).
- Desktop and mobile document widths matched their viewport widths; no horizontal document overflow was detected.
- Loading, read-only, no-budget-data, empty ledger, and empty BOQ states remained explicit.
- The established mobile navigation remains vertically expanded; this is pre-existing shell behavior and was not changed by the Phase 5 sync-control removal.

UI release assessment for the Phase 5 scope: ready. Stitch was unavailable due authentication, so the removal-only work was reviewed against the checked-in design system and existing component patterns; no new Stitch-authored layout was introduced.

The local profile request attempted to sign an existing GCS avatar URL and logged an ADC signing error. Project APIs and Phase 5 UAT routes still returned successfully; deployed workload identity/signBlob readiness remains an environment preflight concern, not a Phase 5 code regression.

The broader Phase 2–4 authoring, alternative/revision/change-order, vendor-cost, Price Database, export confidentiality, conflict, concurrency and authorization matrix was re-executed through the `180`-test backend suite and the frontend component/build checks. Those protected workflows were not each repeated as interactive browser scenarios in this Phase 5 removal-only UAT, so they are recorded as automated regression coverage rather than browser PASS. Offline browser simulation and real private-GCS download were unavailable in the local environment.

## Result classification

| Classification | Evidence |
| --- | --- |
| PASS | Backend `180`; Phase 5 focused `9`; standalone MCP `133`; frontend `10`; lint/build; clean migration/Alembic; golden/history/Funds/cutover; targeted Ruff; static/config checks; applicable Project list/detail desktop/mobile UAT |
| FAIL | None after the correct isolated-test preconditions were applied |
| SKIP | None in the final full backend run; broader protected workflows were not mislabeled as browser PASS |
| WARNING | Existing Vite chunk-size advisory; existing Starlette/httpx deprecation warning; established mobile navigation density |
| UNAVAILABLE | Stitch fetch (authentication); normal-tab automation (another extension UI open); local private-GCS signed download/offline browser simulation |

## Static/configuration validation

The following checks passed:

```bash
git diff --check
bash -n Projects-001-BE/scripts/phase1_test_db.sh
bash -n deploy_frontend.sh
docker compose -f Projects-001-BE/tests/postgres/docker-compose.phase1.yml config -q
python3 -m json.tool Projects-001-MCP/contracts/tool-input-schemas-v1.json
python3 -m json.tool Projects-001-MCP/tests/fixtures/demo-sanitized.json
```

Backend startup import passed with the isolated database configuration. Repository search confirmed that runtime references to removed sync services/config/frontend helpers are gone. Remaining `boq_sync` references are limited to tested 410 compatibility behavior, historical log-query compatibility, MCP schema compatibility at the backend boundary, and retirement tests/documentation.

## Release evidence still required outside this implementation

Before a real rollout:

1. Run deployed-schema preflight and confirm `20260917_0003` on the target without writing business data.
2. Confirm backup/restore readiness and that no external legacy sync worker can write after cutover.
3. Perform explicit Owner preview/activation and monitor source identity, UNKNOWN-cost allocation rejection, conflicts, exports, latency, and audit availability.
4. Verify the deployed runtime service account can sign private GCS URLs where that existing feature is required.
5. Keep Phase 6 rollout enablement separate.
