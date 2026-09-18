# Phase 5 — Integrated Regression and Sync Retirement

## Baseline and scope

- Branch at preflight: `feature`
- Committed Phase 4 baseline: `7a10f93f8b55375cacf51f226bfeb584f5ff50a0`
- The working tree was clean before Phase 5 implementation.
- Scope is limited to active-budget consumer cutover, Funds compatibility, Google Sheets BOQ sync retirement, MCP contract migration, regression/cutover proof, and release documentation.
- No deployment, production-data access, IAM change, authentication redesign, legacy-row deletion, finance replay/reconciliation, or Phase 6 flag enablement was performed.

## Active budget contract

`ProjectBudgetSnapshot` is the single current-budget identity for Project list/detail, Dashboard, Funds, Chat, MCP reads/finance/project operations, and frontend displays. It carries source kind, readiness, baseline/version, main revision, accepted change orders, cost-plan version, calculation version, cost completeness, activation time, sell/forecast values, and as-of time.

- Legacy projects retain their Phase 0 consumer-specific compatibility projections.
- V2 Project/Dashboard/Chat/MCP sell-side reads use `net_sell_ex_vat` from the active baseline.
- V2 Funds uses `forecast_margin` only when the active snapshot is `READY`.
- `UNKNOWN_COST` retains the known sell budget but exposes no assessable forecast margin, available margin, or deficit.
- Historical finance and legacy BOQ references are loaded independently from current-budget selection. A V2 activation neither deletes nor hides legacy rows.
- Project-list budget and execution totals are loaded with bounded batch queries; the former frontend per-project BOQ lookup was removed.

## Native BOQ workflow

BOQ authoring is native to the application. There is no Excel/CSV import or Google Sheets ingestion path. The workflow preserves:

- stable hierarchy and line identities;
- explicit `UNKNOWN`, `PRICED`, and `NOT_APPLICABLE` cost states;
- server-authoritative calculations and conflict/idempotency controls;
- MAIN, alternative, revision, and signed ADD/DEDUCT change-order lifecycle;
- immutable issue/acceptance snapshots and pinned historical preview;
- customer/internal/RFQ/selected-vendor XLSX/PDF export allowlists;
- vendor offers, component-level vendor selection, cost-plan publication, and Price Database provenance.

## Funds behavior

Funds now fingerprints and calculates against the active source identity, not only a legacy projection.

- New outward allocation from a V2 `UNKNOWN_COST` project fails with `BOQ_BUDGET_NOT_READY`.
- Incoming allocation to that project remains valid.
- A valid reversal/correction uses ledger capacity and is not blanket-blocked by later BOQ cost incompleteness.
- Existing allocations are never auto-reversed when cost changes.
- A complete but reduced forecast exposes the resulting deficit; it is not silently corrected.
- Company Operations opening balance, reserve, monthly roll-forward, and actual-cash separation remain unchanged.

## Google Sheets BOQ sync retirement

The runtime parser, sync job service, frontend drawer/polling/tab selection, settings/support copy, and sync-only configuration were removed. Authenticated legacy callers receive a stable `410 Gone` response with code `BOQ_SYNC_RETIRED` and a native-workspace replacement for:

- `POST /api/v1/projects/boq/sync`
- `POST /api/v1/projects/boq/tabs`
- `POST /api/v1/projects/boq/sync-batch`
- `GET /api/v1/projects/boq/sync-jobs/{job_id}`

The public MCP `get_processing_status` workflow enum no longer advertises `boq_sync`; the backend compatibility boundary returns an actionable 410 for an older caller. Receipt OCR, daily-report delivery, and FlowAccount processing remain supported. Shared Google authentication, Gemini OCR/answer polishing, storage, and FlowAccount infrastructure were not removed.

## MCP and history

Current/summary/finance/project-operation reads carry the active budget snapshot. V2 BOQ current/version/diff/search/fetch reads expose stable baseline IDs (`boqv2_<baseline-id>`) and stable line IDs derived from document plus logical identity. Legacy `boqv_*` versions and `boql_*` line references remain resolvable, including historical/as-of reads before V2 activation.

## Cutover and rollback

The isolated same-project rehearsal and operational procedure are documented in [cutover-runbook.md](cutover-runbook.md). The dependency retirement proof is in [sync-dependency-inventory.md](sync-dependency-inventory.md). Command results are in [phase5-validation.md](evidence/phase5-validation.md).

Rollback is application/configuration rollback with data preservation. Returning a project to legacy source is never an automatic feature-flag side effect; it requires an explicit Owner decision and impact preview. V2 tables, accepted documents, allocations, legacy BOQ rows, and historical finance references must remain intact.

## Release prerequisites

1. Run deployed-schema preflight and confirm Alembic revision `20260917_0003` before application rollout.
2. Deploy compatibility code before enabling V2 entry; centrally set the runtime flag rather than hardcoding project IDs.
3. Confirm no old sync client or pending out-of-process sync worker can write after cutover.
4. Back up/restore-test the database, then perform the Owner cutover preview and explicit activation.
5. Monitor save/transition/export failures, version conflicts, baseline changes, UNKNOWN-cost allocation rejection, latency, and audit availability without logging confidential payloads.
6. Stitch authentication remains a UI-review prerequisite when a new Stitch-authored layout is introduced. Phase 5 removed obsolete controls using the checked-in design system and did not introduce a new design.

Phase 6 rollout enablement remains separate.
