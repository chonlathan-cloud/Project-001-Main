# CDR-004 — ProjectBudgetSnapshot and legacy compatibility

Status: **LOCKED**
Scope: Phase 1 internal read model and consumer adapters

## Canonical internal contract

`ProjectBudgetSnapshot` is the sole internal representation of the active
project budget. Its machine-readable schema is
`project-budget-snapshot.schema.json`.

| Field | Contract |
| --- | --- |
| `source_kind` | `LEGACY` or `V2` |
| `status` | `READY`, `NO_BUDGET_DATA`, `NO_ACTIVE_BASELINE`, or `UNKNOWN_COST` |
| `project_id` | Existing project UUID; project identity never changes at cutover |
| `currency` | `THB` in V2 |
| `baseline_id`, `baseline_version`, `main_revision_id` | Nullable for legacy/no active V2 baseline |
| `accepted_change_order_ids` | Stable sorted UUID list; empty for legacy |
| `cost_plan_version` | Nullable until a V2 cost plan participates |
| `calculation_version` | Versioned calculation contract, not an amount hash |
| `activated_at` | Effective active-source timestamp, nullable for legacy |
| `net_sell_ex_vat` | Active accepted sell budget, fixed-scale decimal string or null |
| `original_estimated_cost` | Preserved initial complete estimate or null |
| `agreed_cost` | Complete selected/agreed cost or null |
| `forecast_cost` | Agreed-or-estimated complete current forecast or null |
| `forecast_margin` | Sell minus forecast cost, or null when either is unknown |
| `cost_completeness` | State, counts, and stable missing component IDs |
| `forecast_basis` | `LEGACY_SYNC`, `ESTIMATED`, `PARTLY_AGREED`, `AGREED`, or `NONE` |
| `as_of` | Snapshot/read time in UTC |

`READY` means the selected source has a usable budget identity. It does not turn
unverified legacy zero defaults into proven complete costs. Legacy data with BOQ
rows uses `cost_completeness.state=LEGACY_UNVERIFIED` and
`forecast_basis=LEGACY_SYNC`.

V2 behavior:

- no active accepted baseline → `NO_ACTIVE_BASELINE`, sell/cost/margin null;
- active baseline with required unknown/stale cost → `UNKNOWN_COST`, sell may be
  known, full forecast cost/margin null;
- complete active baseline/cost plan → `READY` and calculated values;
- empty legacy source → `NO_BUDGET_DATA`; adapter still applies each consumer's
  historical contingency/zero fallback.

## Source selection

Phase 1 defaults every existing project to `LEGACY`. Merely creating V2 drafts,
revisions, or tables cannot affect any operational budget. A later explicit
owner-authorized cutover transaction is the only operation that may activate V2.
There is exactly one selected source at a time; V2 replaces rather than adds to
legacy totals.

Snapshot lookup is batchable and returns one coherent baseline/cost-plan view.
Cache/fingerprint identity includes source kind, baseline ID/version, main and CO
membership, cost-plan version, completeness, and calculation version—even when
the resulting amount is unchanged.

## Legacy compatibility adapters

Phase 1 must preserve the exact current public shape and value semantics captured
in `legacy_budget_consumers.json`:

| Consumer | Legacy adapter value |
| --- | --- |
| Project list API | Sum current root CUSTOMER + SUBCONTRACTOR rows; contingency only when no grouped row exists |
| Project detail BOQ | Separate CUSTOMER and SUBCONTRACTOR rollups; variance and existing nullable percent behavior unchanged |
| Dashboard | CUSTOMER if non-zero, else SUBCONTRACTOR if non-zero, else contingency |
| Funds | CUSTOMER − SUBCONTRACTOR |
| Chat | SUBCONTRACTOR if non-zero, else CUSTOMER if non-zero, else contingency |
| MCP read/finance/operations | Current root CUSTOMER sum, else zero |
| Frontend enriched project card | CUSTOMER if non-zero, else SUBCONTRACTOR if non-zero, else pre-existing project value/contingency |

This intentional divergence is a migration boundary. The shared service may
calculate canonical source facts, but public adapters keep consumer-specific
legacy projections until each contract is explicitly migrated and tested for
readiness/null behavior. Phase 1 must not silently make all consumers equal.

## Historical finance separation

Changing the active budget source does not change financial record identity.
Installments, transactions, Input/Approval records, Funds ledger entries, and
other history remain linked to their existing project and legacy BOQ rows.
Historical readers must resolve archived SCD2 `boq_items`; they must not filter
those joins by `valid_to IS NULL` merely because active budget selection does.

`as_of` before a later V2 activation returns legacy source semantics. V2 source
activation is not a delete, reconciliation, payment replay, or legacy rewrite.

## Public evolution rule

New status/nullable fields are additive only after the relevant FE and MCP
consumer supports them. Existing non-null numeric fields continue through the
legacy adapter in Phase 1. No public `ProjectBudgetSnapshot` route is created in
Phase 1.
