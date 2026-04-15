# Phase 1 FE-BE Walkthrough

## Scope

Phase 1 connects these frontend pages to the backend:

- Dashboard
- Project List
- Project Detail

The work stays on the frontend side as much as possible. Backend contracts are adapted in FE instead of changing BE endpoints.

## Base URL

Frontend reads the backend base URL from:

- `VITE_API_BASE_URL`

Fallback default:

- `http://localhost:8000`

Example:

```bash
VITE_API_BASE_URL=http://localhost:8000
```

## Main Files

- `Project-001-Frontend/package.json`
- `Project-001-Frontend/src/api.js`
- `Project-001-Frontend/src/DashboardPage.jsx`
- `Project-001-Frontend/src/ProjectPage.jsx`
- `Project-001-Frontend/src/ProjectDetailPage.jsx`
- `Project-001-Frontend/src/App.jsx`
- `Project-001-Frontend/src/components/ShipmentChart.jsx`
- `Project-001-Frontend/src/components/BudgetChart.jsx`
- `Project-001-Frontend/src/components/SalesChart.jsx`

## Environment Fix

The original frontend environment failed to build for 2 reasons:

- the project was on `vite 8`, which requires a newer Node version than the current machine (`22.11.0`)
- the installed dependency tree expected rolldown native bindings that were not present in the local install

To make the project build on the current machine, the frontend dev dependencies were aligned to:

- `vite 6.4.0`
- `@vitejs/plugin-react 4.7.0`

This pair is compatible with the current Node runtime in this workspace.

## Data Flow

### 1. Shared API layer

`src/api.js` is now the integration entry point.

It does 3 jobs:

1. Calls backend endpoints with `fetch`
2. Unwraps FastAPI responses in the shape `{ status, data }`
3. Adapts backend fields into the shape expected by the current UI

Main exported functions:

- `getDashboardData()`
- `getProjectsData()`
- `getProjectDetailData(projectId)`

There is also a compatibility export `fetchData()` so pages not included in phase 1 still keep working.

### 2. Dashboard

FE page:

- `Project-001-Frontend/src/DashboardPage.jsx`

BE endpoint:

- `GET /api/v1/dashboard/summary`

Mapping summary:

- `kpis.total_budget` -> dashboard stat
- `kpis.actual_cost` -> dashboard stat
- `kpis.pending_approval_count` -> dashboard stat
- `kpis.total_profit_margin` -> dashboard stat
- `monthly_cashflow` -> chart series

Notes:

- Current dashboard chart titles were kept as-is in the UI components.
- Some chart cards still use provisional mappings because the FE visual design is more generic than the BE contract.

### 3. Project List

FE page:

- `Project-001-Frontend/src/ProjectPage.jsx`

BE endpoint:

- `GET /api/v1/projects`

Mapping summary:

- `project_id` or `id` -> `id`
- `name` -> `name`
- `status` -> normalized label
- `total_budget` -> `total`
- `progress_percent` -> `progressPercent`
- `spent` -> fallback from backend if present, otherwise derived from progress, otherwise `0`

Behavior change:

- Local fake editing was removed from the actual flow
- Local fake project creation was disabled in the UI for phase 1
- Clicking a project now routes with `projectId`

### 4. Project Detail

FE page:

- `Project-001-Frontend/src/ProjectDetailPage.jsx`

BE endpoints:

- `GET /api/v1/projects/{projectId}`
- `GET /api/v1/projects/{projectId}/boq`

Mapping summary:

- Detail endpoint provides the main project summary
- BOQ endpoint is used to derive provisional chart data for the current UI

Stats shown:

- Status
- Contingency budget
- Overhead percent
- Profit percent

Chart fallback approach:

- If BOQ data exists, top BOQ items are mapped into the chart components
- If BOQ data does not exist, chart arrays fall back to empty arrays

## Routing

`src/App.jsx` now supports:

- `/project/detail`
- `/project/detail/:projectId`

The preferred route is:

- `/project/detail/:projectId`

## Temporary Fallback Rules

These are intentional for phase 1:

- Missing number -> `0`
- Missing text -> `-`
- Missing list -> `[]`
- Missing project spend -> derive from progress if possible, else `0`
- BOQ fetch failure -> project detail still loads without BOQ charts

## Error Handling

Phase 1 pages now include basic:

- loading state
- request error state
- empty list state for project list

## Verification

What was verified:

- `npm run lint` passed
- `npm run build`

Build note:

- build now completes successfully on Node `22.11.0`
- Vite still reports a large chunk warning for the main JS bundle, but this is a performance warning, not a build failure
