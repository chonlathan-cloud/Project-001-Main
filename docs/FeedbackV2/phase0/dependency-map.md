# BOQ V2 dependency map

Verified against the current `feature` tree at
`ae91252f9fa299c4ce832bfcf20c4780d071cce1`.

## Current write paths

| Surface | Files / symbols | Current behavior | Phase 1 rule |
| --- | --- | --- | --- |
| Single-sheet sync | `app/api/v1/projects.py`: `/projects/boq/sync` | Fetches/parses Google Sheet and writes SCD2 `boq_items` | Preserve unchanged |
| Batch sync/jobs | `app/api/v1/projects.py`: `/tabs`, `/sync-batch`, `/sync-jobs/{job_id}`, `_JOB_STORE` | Starts/polls in-memory jobs | Preserve unchanged |
| Sync service | `app/services/boq_sync_service.py` | Expires current legacy rows and inserts new UUID rows | Preserve unchanged |
| Hierarchy migration | `scripts/migrations/20260608_boq_hierarchy_contract.sql` | Adds hierarchy-related columns if run manually | Do not treat as applied; do not replay automatically |
| Manual bootstrap | `scripts/create_missing_tables.py` | Creates missing current ORM tables | Not a migration ledger; do not use for Phase 1 deployment |
| Seed script | `scripts/seed_round1_data.py` | Drops/recreates tables and seeds data | Prohibited for Phase 0/Phase 1 verification |

## Current budget and finance readers

| Consumer | Files / callers | Current legacy selection | Locked compatibility |
| --- | --- | --- | --- |
| Project list API | `app/api/v1/projects.py::list_projects`; FE `ProjectPage.jsx` | Sum all current root rows without BOQ type filter; contingency fallback | Preserve public result until an explicit compatibility migration |
| Project detail BOQ | `app/api/v1/projects.py::get_project_boq`; `boq_margin_service.projected_boq_totals`; FE `ProjectDetailPage.jsx`, `BoqWorkbench.jsx`, `BoqSheetCharts.jsx` | Separately roll up CUSTOMER and SUBCONTRACTOR; margin is difference | Preserve response shape and exact legacy values |
| Dashboard | `app/api/v1/dashboard.py::get_dashboard_summary`; FE dashboard consumers | CUSTOMER, else SUBCONTRACTOR, else contingency | Preserve public result; source selection moves behind adapter only |
| Funds | `app/services/fund_service.py::_projected_boq_margin`, `_source_fingerprint`; `app/api/v1/funds.py`; FE `fundMoney.js` and Funds pages | CUSTOMER − SUBCONTRACTOR; fingerprint is amount-oriented | Preserve formula; Phase 1 may add source/version/completeness to fingerprint without enabling V2 allocations |
| Chat analytics | `app/services/chat_analytics_service.py::_load_snapshot`, `_build_project_rollups`; chat API callers | Leaf totals; displayed budget prefers SUBCONTRACTOR, then CUSTOMER, then contingency | Preserve answer values; split active budget from historical joins internally |
| Insight Warehouse | `app/services/insight_warehouse_service.py`; Chat snapshot callers | Reuses Chat snapshot; no independent BOQ-budget ingestion | Do not describe it as a direct BOQ budget reader |
| MCP read | `app/services/mcp_read_service.py::list_projects`, `_current_customer_budget`, `get_project`; `app/api/v1/mcp_internal.py`; MCP adapter/handlers | Current CUSTOMER roots only | Preserve money envelope and legacy values |
| MCP finance documents | `app/services/mcp_finance_document_service.py`; internal router; MCP handlers | Current CUSTOMER roots for active budget; historical finance joins differ from Chat | Preserve document/access behavior and historical references |
| MCP project operations | `app/services/mcp_project_operations_service.py::get_dashboard_summary`; internal router; MCP handlers | Current CUSTOMER roots only | Change only active budget source behind compatibility adapter |
| Frontend project cards | `src/ProjectPage.jsx`, `src/api.js` | Per-project `/boq` enrichment, CUSTOMER then SUBCONTRACTOR then prior project value/contingency; BOQ errors are swallowed | Preserve visible values in Phase 1; the N+1/error behavior is recorded debt, not Phase 0 scope |

## Models, schemas, registration, and configuration

| Area | Actual files | Dependency / constraint |
| --- | --- | --- |
| ORM registry | `app/models/__init__.py`, `main.py` | New Phase 1 models must be imported for metadata/migrations without changing startup behavior |
| Legacy BOQ model | `app/models/boq.py` | `NUMERIC(15,2)`, dual `boq_type`, SCD2 dates, vector(768); no native revision/baseline model |
| Finance history | `app/models/finance.py`, `app/models/input_request.py` | Existing FKs and historical rows must remain resolvable; no mandatory V2 line mapping |
| Public BOQ schemas | `app/schemas/boq_schema.py` | Sync/tree/compare response types are live contracts |
| Project/fund/dashboard schemas | Project contracts in `app/schemas/boq_schema.py`, plus `fund_schema.py` and `dashboard_schema.py` | Numeric fields are currently non-null public outputs |
| MCP schemas | `app/schemas/mcp_schema.py`, `Projects-001-MCP/` | Tool manifests, adapters, handlers, contract tests, authorization, and security tests are callers |
| Settings | `app/core/config.py`, `.env.example`, `app/api/v1/settings.py` | Sheets-related settings can be shared by other Google/OCR features; no removal in Phase 1 |
| Frontend normalizers | `Projects-001-FE/src/api.js` | Several helpers coerce absent numeric values to zero; V2 unknown state cannot flow publicly until consumers are ready |
| Frontend test discovery | `Projects-001-FE/package.json` | Baseline `npm test` targets only funds and daily-report test files |

## Registration and call-chain checks required in Phase 1

```text
HTTP route -> auth dependency -> compatibility adapter -> project_budget_service
MCP handler -> internal HTTP route -> auth/access service -> compatibility adapter
Funds mutation -> bucket/source locks -> snapshot + fingerprint -> ledger transaction
Chat/Insights historical finance -> legacy BOQ FK lookup independent of active budget source
```

Every public caller must continue receiving its current legacy representation.
The shared service may expose the canonical `ProjectBudgetSnapshot` only to new
internal code until the readiness/null contract is implemented end to end.

## Section 12 file verification inventory

Every existing path named in §12 was present and inspected. The following
additional callers/registration points were found and must be included in future
change searches:

- `Projects-001-BE/main.py` and `app/models/__init__.py` for router/model
  registration.
- `app/schemas/fund_schema.py`, `app/schemas/dashboard_schema.py`,
  `app/api/v1/funds.py`, `app/api/v1/mcp_internal.py`, and
  `app/api/v1/bills.py` for public/internal response and historical finance
  boundaries.
- `app/services/boq_hierarchy.py`,
  `scripts/migrations/20260608_boq_hierarchy_contract.sql`, and
  `scripts/create_missing_tables.py` for the partially implemented hierarchy and
  manual schema paths.
- MCP adapter, handler, registry, contract, authorization, security, and plugin
  skill files under `Projects-001-MCP/`; BOQ sync/status is not isolated to one
  service file.
- Frontend dashboard and fund consumers/normalizers in addition to the pages and
  components named by §12.

Inspection confirmed that all proposed BOQ V2 modules listed after the §12 table
are absent. No `project_budget_service`, native document/calculation/cost/catalog/
export service, Alembic directory, or V2 frontend module exists at this baseline.

## Repository drift and risk register

| ID | Finding | Impact / required handling |
| --- | --- | --- |
| R01 | The plan baseline is one commit behind current HEAD, but the delta is only the plan file | Safe to proceed on current `feature`; re-check before Phase 1 |
| R02 | `main` no longer differs from current HEAD | Treat plan wording as historical; do not switch branches |
| R03 | Hierarchy design claims more integration than code provides | Phase 1 migrations must inspect live schema; do not infer columns from docs |
| R04 | Budget formulas diverge by consumer | Golden fixture is the compatibility source of truth; do not “normalize” silently |
| R05 | Historical finance can disappear from Chat due to current-row join filter | Phase 1 must add preservation tests before refactoring reads |
| R06 | No migration ledger; manual SQL files can mutate data | Adopt Alembic additively; never replay scripts as an assumed ordered chain |
| R07 | Backend config loads `.env` at import | All Phase 0 commands set an explicit safe `DATABASE_URL`; harness scripts use only `PHASE0_DATABASE_URL` |
| R08 | Wrong Python environment lacks MCP async test support | Use `Projects-001-MCP/.venv`, not the backend venv, for MCP tests |
| R09 | Stitch authentication unavailable | Non-blocking for Phase 0/1 backend; blocks Phase 2 UI work |
| R10 | Sync remains active across API, FE, settings, MCP, and job state | Preserve until controlled Phase 5 retirement/cutover |

## Phase 1 implementation sequence

1. Re-run baseline and schema preflight; record actual deployed-schema variance
   read-only when separate production authorization exists. Phase 1 can be built
   locally without that access, but cannot be released without it.
2. Initialize Alembic against current ORM metadata and create an explicit
   baseline/stamp runbook. Do not manufacture a historical order for manual SQL.
3. Add minimum V2 core tables, constraints, indexes, status enums/checks, stable
   logical IDs, revisions, active baseline membership, cost-plan version, and
   audit/idempotency records. No public write endpoints.
4. Implement calculation/completeness pure functions with contract fixtures.
5. Implement internal `ProjectBudgetSnapshot` selector defaulting all existing
   projects to `LEGACY`.
6. Route each budget consumer through a consumer-specific compatibility adapter;
   preserve its golden output exactly. Batch project reads and maintain coherent
   snapshot/version boundaries.
7. Separate historical finance joins from current active-budget selection in
   Chat/Insights/MCP and add archived-row regression fixtures.
8. Add Funds source/version/completeness fingerprint and lock order while keeping
   current legacy margin and existing allocations unchanged.
9. Run upgrade/startup/legacy golden/historical finance/concurrency regressions.
   Confirm no V2 writes or totals are publicly reachable before closing Phase 1.
