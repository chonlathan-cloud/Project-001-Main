# Phase 2 — Native single-entry BOQ

Status: **implemented locally behind disabled-by-default feature gates; not released**
Phase 2 baseline: `feature` at `92fcc27002fd4aeade09893862c85902302f7c63`

## Delivered scope

- Native MAIN/DRAFT BOQ create, load, atomic save, reload, revision copy, move,
  reorder, duplicate, and subtree delete.
- Stable logical identity across revisions and stable persistence row identity
  across saves and reorders within one revision.
- One hierarchy shared by customer sell and estimated material/labor cost views.
- Explicit cost states for `UNKNOWN`, intentional zero-price `PRICED`, and
  `NOT_APPLICABLE`, including an explicit reason for a priced zero.
- Server-authoritative Decimal calculations, completeness, known cost,
  forecast cost/margin, item totals, and derived structural subtotals.
- Optimistic version checks, idempotency keys, project-scoped database locks,
  audit events, cross-revision identity rejection, and explicit confirmation
  before discarding item financial fields.
- Owner mutation and Admin/Owner read contracts. Admin receives a read-only
  workspace; the API remains authoritative for authorization.
- Responsive native workspace with consolidated/customer/cost views, keyboard
  save, offline state, failed-save retry, conflict recovery, and local draft
  backup/recovery JSON.
- Project actions route to the native workspace only when the frontend feature
  gate is enabled. The legacy BOQ view and sync endpoints remain available.

## Persistence and calculation boundary

Structural nodes persist identity, hierarchy, inclusion, and descriptive data
only. Their `sell_total` remains zero to preserve the Phase 1 database
constraint. The API derives structural subtotals from included descendant ITEM
totals when it constructs a response, so display rows cannot be counted as
billable leaves.

An excluded node excludes its complete subtree from document sell totals, cost
completeness, known cost, and forecast cost. Unknown required components keep
the known-cost subtotal available but make full forecast cost and margin null.
An intentional zero and a not-applicable component are complete states.

## API surface

| Method | Route | Access | Purpose |
| --- | --- | --- | --- |
| `GET` | `/api/v1/projects/{project_id}/boq-workspace` | Admin/Owner | Workspace metadata, revisions, and reuse sources |
| `GET` | `/api/v1/boq/revisions/{revision_id}` | Admin/Owner | Load one native BOQ revision |
| `POST` | `/api/v1/projects/{project_id}/boq/documents` | Owner | Create an empty MAIN/DRAFT document |
| `PATCH` | `/api/v1/boq/revisions/{revision_id}` | Owner | Atomically save the complete draft |
| `POST` | `/api/v1/projects/{project_id}/boq/revisions/{source_revision_id}/copy` | Owner | Copy scope and cost state with lineage |

Mutation routes require an `Idempotency-Key`. Saves also require
`expected_version`. The backend feature gate returns
`BOQ_V2_ROLLOUT_DISABLED` while disabled.

## Rollout boundary

Both gates default to false:

```text
BOQ_V2_ENABLED=false
VITE_BOQ_V2_ENABLED=false
```

Creating or editing a Phase 2 draft does not insert a
`boq_v2_project_budget_sources` row, create a project baseline, or change the
legacy operational budget. Existing project, Dashboard, Funds, Chat, Insights,
MCP, and BOQ sync behavior therefore remains on the Phase 1 compatibility
path.

Phase 2 deliberately does not implement issue/acceptance, alternatives,
change orders, quotations, PDF/Excel exports, vendor offers, a price catalog,
operational source cutover, or sync retirement. Those remain Phase 3–5 work.

## Local use

Start the isolated PostgreSQL harness and apply the Phase 1 schema first. Use
explicit local environment overrides; the harness remains on loopback and
stores data in Docker `tmpfs`.

```bash
cd Projects-001-BE
./scripts/phase1_test_db.sh up
./scripts/phase1_test_db.sh upgrade-current

PYTHONDONTWRITEBYTECODE=1 \
DATABASE_URL=postgresql+asyncpg://phase1:phase1@127.0.0.1:55433/projects001_phase1_test \
PHASE2_DATABASE_URL=postgresql://phase1:phase1@127.0.0.1:55433/projects001_phase1_test \
BOQ_V2_ENABLED=true \
venv/bin/python -m pytest tests/phase2/test_boq_document_api.py -q

./scripts/phase1_test_db.sh down
```

See [validation evidence](evidence/phase2-validation.md).

Representative final-build captures:

- [Desktop 1440 × 900](evidence/screenshots/native-boq-desktop-1440.jpg)
- [Tablet 1024 × 768](evidence/screenshots/native-boq-tablet-1024.jpg)
- [Mobile 390 × 844](evidence/screenshots/native-boq-mobile-390.jpg)
