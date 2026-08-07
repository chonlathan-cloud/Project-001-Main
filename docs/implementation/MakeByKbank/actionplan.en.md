# Forecast Margin Allocation — Action Plan

> Implementation plan for allocating forecast margin between Project Buckets, inspired by the Envelope/Bucket Budgeting concept used by MAKE by KBank. This design is specific to Projects-001 and does not copy MAKE by KBank branding or screens.

| Item | Value |
|---|---|
| Document status | Approved revised baseline — implementation alignment required |
| Last updated | 2026-08-07 |
| Product scope | Project Forecast Buckets, Company Operations, Forecast Margin Allocation Ledger |
| Margin allocation permission | `owner` only |
| Read permission | `owner` and `admin`, subject to current project visibility |
| Transaction type | Virtual forecast allocation; not cash movement or a bank transfer |
| Rollout target | Local/Demo → Beta → Production decision |
| Thai version | [actionplan.md](actionplan.md) |
| Related Product/UX plan | [plan.en.md](plan.en.md) |

## 1. Objective

Introduce a forecast-margin management model in which each Project is a Bucket and forecast capacity can be allocated between Buckets. `Company Operations` is the central Bucket for company-wide operating budgets.

The feature must enable the Owner to:

1. See `Projected BOQ Margin` and the remaining margin available for allocation.
2. Manually allocate forecast margin from one Project to `Company Operations` or another Project.
3. Review before-and-after balances before confirming.
4. Review history and identify who performed each action.
5. Correct mistakes through a Reverse transaction without deleting the original history.

## 2. Current-State Baseline

### 2.1 Existing Capabilities

- Project Detail displays `Total Variance`, calculated from Customer BOQ minus Subcontractor BOQ.
- The system has `INCOME` and `EXPENSE` Input Requests with `PENDING_ADMIN`, `APPROVED`, and `PAID` statuses.
- Project Detail already displays project-level income and expense summaries from Input Requests.
- A project named `โครงการบริษัท` with type `INTERNAL` and a fixed UUID already exists from a previous migration.
- The Owner has mutation permissions, while Admin is read-only under the current authorization model.

### 2.2 Current Problems

- `Total Variance` is the margin the business wants to manage, but there is no Forecast Bucket model.
- There is no `Available Margin to Allocate` after Allocated Out and Forecast Reserve.
- There is no ledger for moving balances between Projects.
- `โครงการบริษัท` is currently identified by name and `project_type`, which is fragile when the display name changes.
- There is no protection against duplicate submission, concurrent allocation, or retroactive history edits.

### 2.3 Migration Approach

Do not create a duplicate Operations Project. Upgrade the existing `โครงการบริษัท` record into the default Operations Project and preserve its UUID so existing Input Requests and relationships remain intact.

### 2.4 Implementation Alignment Note — 2026-08-07

- Keep the applied migration/table foundation; Bucket, Allocation, Ledger, and Audit structures are still required.
- Any calculation that uses Paid Income, Paid Expense, or Approved Commitments as the ceiling is superseded and must be replaced before enabling Owner mutations.
- The Frontend must not disable allocation because of actual cashflow when forecast Available Margin is positive.
- Summary API, posting validation, reverse validation, and UI must use the same forecast formula.
- Never edit an applied migration. Use an additive follow-up migration for required schema or constraint changes.

## 3. Product Decision Register

The following decisions are the V1 baseline. If implementation requires a change, record the reason in this document or an ADR before proceeding.

| ID | Decision |
|---|---|
| D-01 | Each Project has exactly one Fund Bucket in a 1:1 relationship. |
| D-02 | Each company/deployment has exactly one default `Company Operations` record. |
| D-03 | Reuse the existing `โครงการบริษัท` record with type `INTERNAL`; do not create a duplicate. |
| D-04 | Allocation is a virtual forecast movement. It does not initiate a bank transfer and does not assert that cash exists. |
| D-05 | Rename `Total Variance` to `Projected BOQ Margin`; it is the forecast base of a regular Project Bucket. |
| D-06 | The ceiling is `Available Margin to Allocate`, calculated from Projected BOQ Margin/Opening Forecast Balance, Forecast Allocated In/Out, and Forecast Reserve. |
| D-07 | The Owner creates and reverses allocations. Admin can read summary/history but cannot mutate. |
| D-08 | Allocation does not change BOQ, Revenue, Expense, Projected BOQ Margin, or Input Request status; it changes only the Bucket's forecast balance. |
| D-09 | A posted Allocation is immutable. It cannot be edited or deleted; correction uses a reversal. |
| D-10 | Every Allocation creates source and target ledger entries in one database transaction. |
| D-11 | Monetary values use two-decimal fixed precision. Do not use float for calculation or storage contracts. |
| D-12 | V1 supports Project → Operations, Project → Project, and Operations → Project when the destination is Active. |
| D-13 | `Company Operations` is displayed as a System Bucket, separate from construction work, and excluded from Project Health and Construction KPIs. |
| D-14 | Forecast Margin Allocation from Projected BOQ Margin is the core V1 scope and must remain clearly separate from actual cashflow. |
| D-15 | The Owner enters and confirms the Initial Opening Forecast Balance for Operations; Accounting/Admin prepares and verifies the figures. |
| D-16 | The Forecast Balance Start Date is the first day of the selected activation month. Each following month uses the Previous Month Forecast Closing as Monthly Forecast Opening. |
| D-17 | Subcontractors cannot view, select, or submit Income/Expense activity to Company Operations. They see assigned Projects only. |
| D-18 | `PAID`, `APPROVED`, Income, Expense, and commitments are excluded from Forecast Available and remain in a separate Cashflow view. |
| D-19 | Forecast Allocated In increases the destination Bucket's Available Margin and may be allocated onward under the same validation rules. |
| D-20 | Use the latest Projected BOQ Margin after BOQ changes. If Raw Forecast Available becomes negative, preserve the ledger, show Forecast Deficit, and block further outgoing allocation. |

## 4. Terminology and Financial Semantics

| Product term | Meaning |
|---|---|
| Projected BOQ Margin | Latest `Customer BOQ - Subcontractor BOQ`; the forecast base of a regular Project Bucket |
| Opening Forecast Balance | Forecast base set once by the Owner for Operations, which has no BOQ Margin |
| Forecast Allocated In | Margin received from another Bucket through a posted Allocation |
| Forecast Allocated Out | Margin allocated to another Bucket through a posted Allocation |
| Forecast Reserve | Margin set aside and unavailable for allocation; V1 default is 0 |
| Raw Forecast Available | Forecast balance before applying the lower bound |
| Available Margin to Allocate | `max(0, Raw Forecast Available)` and the maximum the Owner may allocate |
| Forecast Deficit | Absolute value of negative Raw Forecast Available after the forecast base decreases below prior allocations |
| Actual Cashflow | Paid/Approved Income, Expense, and commitments; informational only and excluded from allocation calculations |

### 4.1 V1 Formula

```text
Forecast Base
= Projected BOQ Margin for a regular Project
  or Opening Forecast Balance for Company Operations

Raw Forecast Available
= Forecast Base
+ Forecast Allocated In
- Forecast Allocated Out
- Forecast Reserve

Available Margin to Allocate = max(0, Raw Forecast Available)
Forecast Deficit             = max(0, -Raw Forecast Available)
```

Forecast calculation rules:

- Use the latest Projected BOQ Margin from the same calculation/source as BOQ Comparison; the Frontend must not calculate it independently.
- Income, Expense, `PENDING_ADMIN`, `APPROVED`, `PAID`, and commitments do not affect this formula.
- Allocation does not mutate Projected BOQ Margin; Forecast Allocated Out reduces the remaining allocatable margin.
- Forecast Allocated In increases the destination balance and can be allocated onward.
- A later BOQ Margin decrease never edits or deletes an existing Allocation.
- When Raw Forecast Available is negative, show Forecast Deficit and disable further outgoing Allocation.

### 4.2 Opening Forecast Balance

`Company Operations` has no BOQ Margin. The Owner enters an Initial Opening Forecast Balance during a controlled activation flow. It is a forecast budget, not a cash or bank balance:

- Accounting/Admin prepares and verifies the figures before sending them to the Owner.
- The Owner enters the amount and performs the final confirmation in the system.
- The Owner selects the activation month; the system sets the Effective Date to the first day of that month.
- The Initial Opening Forecast Balance is used once during activation/setup.
- The Owner provides the amount and reason and reviews a Preview before confirming.
- Store it as an immutable ledger entry of type `OPENING_BALANCE` with forecast semantics.
- Never edit the original balance. Use Adjustment/Reverse if it is wrong.
- The default remains 0 until the Owner confirms activation, including an explicit confirmation of a zero balance.
- Forecast movement before the Balance Start Date must not be counted again because it is already represented in the opening amount.

### 4.3 Monthly Forecast Roll-forward

After initial activation, the Owner does not enter a new Opening Forecast Balance every month:

```text
Monthly Forecast Opening on the first day of the current month
= Previous Month Forecast Closing Balance
```

- The Initial Opening Forecast Balance is the only manual opening entry.
- Subsequent Monthly Forecast Opening values are derived balances, not Income, Expense, or Allocation activity.
- Monthly Forecast Closing includes forecast allocation movement from the first through the last day of the month and excludes actual cashflow.
- Historical corrections use Adjustment/Reverse with an Audit Trail, and the system recalculates affected Monthly Forecast Closing/Opening values.

## 5. V1 Scope

### 5.1 In Scope

- Default Company Operations Project/System Bucket
- Project forecast summary and the Available Margin to Allocate formula
- Owner manual Allocation Dialog
- Project-to-Project and Project-to-Operations allocation
- Allocation history/ledger
- Reverse Allocation
- Owner/Admin read access under current permissions
- Atomic posting, idempotency, and concurrency validation
- Audit events for create, reverse, and failure
- Demo/Beta migration and reconciliation

### 5.2 Non-goals

- No Bank API integration or real bank-transfer initiation
- No MAKE by KBank integration
- No copying of MAKE by KBank branding, icons, or screens
- No Scheduled/Recurring Allocation
- No percentage-based automatic Allocation
- No representation of forecast allocation as real cash or a bank-transfer instruction
- No multi-currency; V1 uses THB
- No change to BOQ logic or the Variance formula
- No change to the Input Request approval/payment flow
- No deletion of posted ledger data

## 6. Target UX

### 6.1 Project List

- Pin `Company Operations` in a `Company Funds` section above Construction Projects.
- Display a `System Bucket` badge.
- Show `Available Margin to Allocate`, Forecast Deficit when applicable, and recent activity.
- Do not show Construction Progress, Customer BOQ, or Project Health for Operations.
- Operations cannot be deleted or archived.

### 6.2 Project Detail — Financial Overview

Add a `Project Funds` section with at least two cards:

1. `Projected BOQ Margin`
   - Displays the existing Total Variance value.
   - Shows an `Estimate` badge.
   - Helper text: “Forecast margin from BOQ; this is not actual cash.”
2. `Available Margin to Allocate`
   - Displays the amount calculated from Projected BOQ Margin/Opening Forecast Balance, Forecast Allocated In/Out, and Forecast Reserve.
   - Shows an `Available Margin` badge.
   - Shows an `Allocate Margin` button to the Owner.
   - Admin sees the balance in read-only mode with no mutation action, consistent with current UI conventions.

Paid Income, Paid Expense, and Approved Commitments may appear in a separate Cashflow section, but must not appear in the Forecast Margin formula strip or affect the allocation action.

Add a `Margin Allocation Ledger` section beneath the cards:

- Show From, To, Amount, Reason, Status, Created by, and Created at.
- Distinguish Allocated In and Allocated Out with labels and signs, not color alone.
- Allow users to open detail and view reversal relationships.

### 6.3 Allocation Dialog

Use the approved mockup flow:

1. `From` — locked to the current Project
2. `Available Margin` — latest server-calculated forecast value
3. `To` — searchable selector with Company Operations listed first
4. `Amount` — decimal input with a `Use maximum` action
5. `Reason` — required
6. `Reference/Note` — optional if retained during implementation
7. `Preview` — source and target balances before and after
8. Confirmation — `Confirm Margin Allocation THB X`

Required notice:

> This allocates forecast margin inside the product. It is not actual cash and does not initiate a bank transfer.

### 6.4 Dialog States

- Loading summary/options
- Ready
- Invalid amount
- Amount exceeds Available Margin
- Missing reason
- Stale balance (`409`) with refreshed values
- Duplicate submission returns the existing result through idempotency
- Success with reference number
- Permission denied
- Target inactive/archived
- Network/server failure while preserving user-entered values

### 6.5 Reverse Flow

- Show `Reverse allocation` in Allocation Detail to the Owner only.
- Require a reversal reason.
- Show a preview of the returned balances.
- If the current target does not have enough Available Margin, block the Reverse rather than creating a new Forecast Deficit.
- Mark the original record as `REVERSED` by reference, but never delete its ledger entries.
- Create the opposite Allocation/entries and link them through `reversal_of`.

### 6.6 Responsive and Accessibility

- Use a centered dialog on desktop and a full-width sheet/dialog on mobile.
- Use native input, select, and button elements with keyboard navigation.
- Move focus into the dialog when opened and restore focus to the trigger when closed.
- Provide validation text rather than relying on color alone.
- Give money fields clear labels and screen-reader text.
- Prevent double-click submission while a request is pending.

## 7. Business Rules and Validation

1. `amount > 0`
2. `amount <= current Available Margin to Allocate`
3. Source and Target must be different Projects.
4. Source and Target must be Active and have Fund Buckets.
5. Exactly one System Operations Bucket exists per company/deployment.
6. Only the Owner may POST or Reverse.
7. The server loads the latest Projected BOQ Margin/Opening Forecast Balance and recalculates Available Margin inside the transaction; it never trusts the Frontend value.
8. If the balance changes after the Dialog opens, return `409 STALE_FUND_BALANCE`.
9. Retrying the same idempotency key returns the existing Allocation instead of creating another one.
10. A posted Allocation cannot be updated or deleted.
11. A Reverse cannot make the returning side's Raw Forecast Available negative.
12. Allocation does not create an Input Request, Transaction, or BOQ Item.
13. Allocation is not Income/Expense, is excluded from actual cashflow KPIs, and does not change with `PAID`/`APPROVED` status.
14. Every Create/Reverse records actor, timestamp, reason, and before/after balances.
15. Subcontractor queries and Project selectors return assigned Projects only and always exclude `system_key='OPERATIONS'`.
16. A Subcontractor cannot create Income/Expense activity against Operations even by submitting the Project ID directly.
17. Operations expenses use the Internal Input Flow through an authorized internal actor. In V1, the Owner performs mutations while Admin/Accounting prepares and verifies information in read-only mode.

## 8. Proposed Data Design

Final table and field names may follow repository migration conventions, but implementation must preserve these semantics.

### 8.1 Projects

Add a stable identifier that does not depend on the display name:

```text
projects.system_key nullable unique
```

V1 supported value:

```text
OPERATIONS
```

Migration requirements:

- Find existing UUID `11111111-1111-4111-8111-111111111111`, or fall back to `name='โครงการบริษัท'` and `project_type='INTERNAL'`.
- Set `system_key='OPERATIONS'`.
- Preserve `project_type='INTERNAL'` and `status='ACTIVE'`.
- Allow the display name to change without breaking system lookup.
- Add a nullable unique constraint so exactly one Operations record exists.

### 8.2 Fund Buckets

```text
fund_buckets
- id UUID PK
- project_id UUID UNIQUE FK projects.id
- bucket_type PROJECT | OPERATIONS
- currency THB
- balance_start_date DATE nullable; when activated, it must be the first day of a month
- forecast_reserve NUMERIC(15,2) default 0
- status SETUP | ACTIVE | LOCKED
- created_at
- updated_at
```

Backfill exactly one Bucket for every existing Project.

If an environment already ran a migration with the physical column name `protected_reserve`, retain that column for backward compatibility and interpret it as Forecast Reserve. Rename it only through an additive follow-up migration; never edit an applied migration.

### 8.3 Fund Allocations

```text
fund_allocations
- id UUID PK
- reference_no VARCHAR UNIQUE
- source_bucket_id UUID FK
- target_bucket_id UUID FK
- amount NUMERIC(15,2)
- currency THB
- reason TEXT
- status POSTED | REVERSED
- reversal_of UUID nullable FK fund_allocations.id
- idempotency_key VARCHAR UNIQUE
- created_by VARCHAR/UUID
- created_at TIMESTAMPTZ
```

Constraints:

- amount > 0
- source_bucket_id != target_bucket_id
- `reversal_of` is unique when allowing only one reversal per Allocation
- Enforce no update/delete through service policy; consider database permissions or triggers when appropriate

### 8.4 Fund Ledger Entries

```text
fund_ledger_entries
- id UUID PK
- allocation_id UUID FK
- bucket_id UUID FK
- direction DEBIT | CREDIT
- entry_type ALLOCATION | REVERSAL | OPENING_BALANCE | ADJUSTMENT
- amount NUMERIC(15,2)
- created_at TIMESTAMPTZ
```

A normal posted Allocation has exactly two entries:

- Source: `DEBIT`
- Target: `CREDIT`

Both entries and the Allocation header commit or roll back together.

These directions are product-ledger semantics for balance decrease/increase and are not a replacement for the company's General Ledger or FlowAccount records.

### 8.5 Audit

At minimum, emit:

- `fund_allocation.created`
- `fund_allocation.reversed`
- `fund_allocation.rejected_insufficient_margin`
- `fund_allocation.rejected_stale_balance`
- `operations_bucket.bootstrap_completed`
- `operations_bucket.opening_forecast_balance_set`

Audit payloads must not contain secrets or bank details.

## 9. Proposed API Contracts

### 9.1 Read APIs

```text
GET /api/v1/fund-buckets/options
GET /api/v1/projects/{project_id}/funds/summary
GET /api/v1/fund-allocations?project_id={id}&cursor={cursor}
GET /api/v1/fund-allocations/{allocation_id}
```

The Summary response must keep each value explicit:

```json
{
  "project_id": "uuid",
  "currency": "THB",
  "forecast_base_type": "PROJECTED_BOQ_MARGIN",
  "projected_boq_margin": "1000000.00",
  "opening_forecast_balance": "0.00",
  "forecast_allocated_in": "200000.00",
  "forecast_allocated_out": "250000.00",
  "forecast_reserve": "50000.00",
  "raw_forecast_available": "900000.00",
  "available_margin_to_allocate": "900000.00",
  "forecast_deficit": "0.00",
  "calculated_at": "2026-08-06T10:42:00+07:00",
  "version": "opaque-balance-version"
}
```

Load actual Income/Expense/Commitment data through a separate Cashflow API/section. Do not include those values to explain or calculate the Forecast Allocation ceiling.

### 9.2 Mutation APIs

```text
POST /api/v1/fund-allocations
POST /api/v1/fund-allocations/{allocation_id}/reverse
```

Create request:

```json
{
  "source_project_id": "uuid",
  "target_project_id": "uuid",
  "amount": "200000.00",
  "currency": "THB",
  "reason": "Allocate funds for August company-wide operating expenses",
  "expected_source_balance_version": "opaque-balance-version",
  "idempotency_key": "client-generated-uuid"
}
```

The success response returns:

- Allocation ID/reference
- Source/target balances before and after
- Posted timestamp
- Actor
- New balance versions

At minimum, use these structured errors:

- `INSUFFICIENT_AVAILABLE_MARGIN`
- `STALE_FUND_BALANCE`
- `INVALID_SOURCE_TARGET`
- `TARGET_BUCKET_INACTIVE`
- `OPERATIONS_BUCKET_MISSING`
- `ALLOCATION_ALREADY_REVERSED`
- `REVERSAL_WOULD_OVERDRAW_TARGET`
- `FORBIDDEN`

## 10. Calculation and Posting Service

Create a central service boundary so neither the Router nor the Frontend implements business calculations independently.

Core responsibilities:

1. Resolve the Fund Bucket and authorization scope.
2. Resolve the latest Projected BOQ Margin from the same calculation/source as BOQ Comparison, or the Operations Opening Forecast Balance.
3. Aggregate posted forecast ledger entries.
4. Calculate forecast margin summary values using Decimal without using Paid/Approved status as an input.
5. Lock source and target rows in deterministic order to reduce deadlocks.
6. Recalculate source Available Margin inside the transaction.
7. Validate expected balance version and amount.
8. Create Allocation plus source/target ledger entries.
9. Emit an audit event after successful commit.
10. Return before-and-after snapshots.

Requirements:

- Never use Frontend-calculated values as the source of truth.
- Do not create an Allocation if required audit/ledger persistence fails.
- Use deterministic ordering when locking two Buckets.
- Define timeout and error behavior for colliding concurrent requests.
- Read summaries and posting validation must use the same calculation function.

## 11. Frontend Work Packages

### FE-01 — API Adapter and State

- Add fund summary, options, history, create, and reverse API functions.
- Normalize decimal strings without losing precision.
- Handle `409` and structured errors.
- Prevent duplicate submission while a request is pending.

### FE-02 — Project Fund Summary

- Add the Project Funds section to Project Detail.
- Rename Total Variance to Projected BOQ Margin.
- Add Available Margin to Allocate and Forecast Deficit states.
- Implement Owner actions and Admin read-only behavior.

### FE-03 — Allocation Dialog

- Locked Source
- Destination selector
- Amount, maximum, and reason fields
- Before-and-after preview
- Validation, loading, error, and success states
- Responsive and accessible focus behavior

### FE-04 — Allocation Ledger

- Recent history in Project Detail
- Full history/detail route or panel
- Direction, status, reference, actor, and timestamp
- Reverse action for the Owner

### FE-05 — Company Operations Experience

- Pin Operations on the Projects page.
- Remove BOQ and other construction-specific sections.
- Show Operations forecast balance/allocation overview and keep actual expense/cashflow in a separate informational section.
- Add `System Bucket` badge and delete/archive protection.
- Add Initial Opening Forecast Balance setup for the Owner, with a month selector that enforces the first day.
- Display Monthly Forecast Opening/Closing with automatic roll-forward.
- Exclude Operations from Subcontractor Project selectors and routes.

## 12. Backend and Database Work Packages

### BE-01 — Migration and Bootstrap

- Add `projects.system_key`.
- Upgrade the existing `โครงการบริษัท` record to `OPERATIONS`.
- Create fund tables, indexes, and constraints.
- Backfill one Bucket per Project.
- Make migration rerun-safe and prevent duplicate Operations records.

### BE-02 — Fund Calculation Service

- Implement Decimal aggregation.
- Use BOQ Comparison calculation as the source of truth for Projected BOQ Margin.
- Calculate forecast summary and balance version.
- Support Forecast Deficit when the latest Margin falls below prior allocations.

### BE-03 — Allocation Posting Service

- Atomic source/target ledger posting
- Row locking and concurrency guard
- Idempotency
- Immutable records
- Reversal

### BE-04 — APIs, Authorization, and Audit

- Read APIs for Owner/Admin
- Mutation APIs for Owner
- Structured errors
- Audit events and safe logging
- History pagination

### BE-05 — Operations Rules

- Replace name-based lookup with `system_key='OPERATIONS'`.
- Prevent delete, archive, and type changes for the System Project.
- Allow display-name changes without affecting lookup.
- Exclude Operations from construction metrics.
- Enforce Subcontractor exclusion at the API/authorization layer rather than relying on Frontend filtering.
- Implement one-time Initial Opening Forecast Balance and monthly forecast roll-forward semantics.

## 13. Test Plan

### 13.1 Unit Tests

- Formula coverage for Projected BOQ Margin/Opening Forecast Balance, Forecast Allocated In/Out, and Forecast Reserve
- Latest Projected BOQ Margin from BOQ Comparison is the source of truth
- Positive, zero, and negative Raw Forecast Available
- Decimal precision and two-decimal rounding
- `PAID`, `APPROVED`, Income, Expense, and commitments do not change Available Margin
- Balance version changes when BOQ Margin, opening forecast, reserve, or relevant Ledger activity changes
- Initial Balance Start Date must be the first day of a month
- Monthly Forecast Opening equals Previous Month Forecast Closing and creates no duplicate movement

### 13.2 API/Service Tests

- Owner creates an Allocation successfully.
- Admin mutation returns `403`.
- Zero, negative, and over-available amounts are rejected.
- Same source and target are rejected.
- Inactive target is rejected.
- Duplicate idempotency key returns the existing result.
- Concurrent requests cannot create a negative balance.
- Stale version returns `409`.
- Allocation creates exactly two source/target ledger entries.
- Failure during posting rolls back all changes.
- Reversal succeeds and links to the original Allocation.
- A second reversal is rejected.
- Reversal that would overdraw the target is rejected.
- Re-running Operations bootstrap creates no duplicate.
- Allocation does not change BOQ, Input Request, actual cashflow values, or the source Projected BOQ Margin.
- Subcontractor Project options do not return Operations.
- A Subcontractor submitting an Operations Project ID directly receives `403`.
- Only the Owner can create the Initial Opening Forecast Balance, and only once.
- Monthly forecast roll-forward creates no Income, Expense, or Allocation entries.

### 13.3 Frontend Tests

- Owner/Admin rendering
- Allocation disabled when Available Margin is zero or there is a Forecast Deficit
- Maximum amount and preview calculations
- Validation errors and stale-balance refresh
- Double click does not create two requests
- Focus management, keyboard flow, and mobile layout
- Ledger direction and reversal state

### 13.4 Verification Commands

```bash
cd Projects-001-FE
npm run lint
npm run build

cd ../Projects-001-BE
pytest
```

Add migration dry-run and API smoke tests from the environment runbook before deployment.

## 14. Rollout Plan

### Phase 0 — Revised Decision Freeze and Forecast Reconciliation

- [x] Confirm V1 is Forecast Margin Allocation and excludes Paid/Approved/actual cashflow from the ceiling.
- [ ] Confirm BOQ Comparison calculation as the sole source of truth for Projected BOQ Margin.
- [ ] Verify the existing `โครงการบริษัท` UUID and values in Demo/Beta.
- [ ] Confirm the Operations display name.
- [ ] Accounting/Admin prepares the Initial Opening Forecast Balance working paper.
- [ ] The Owner selects the activation month; the system uses the first day as the Balance Start Date.
- [ ] The Owner enters and confirms the Initial Opening Forecast Balance in the activation flow.
- [ ] Collect at least three real Projects to compare Projected Margin, Allocated In/Out, Reserve, and Available Margin.
- [ ] Audit the current implementation and prepare a change set that removes Paid/Approved from the formula before enabling mutations.

Exit gate: The Owner approves the formula and sample balances.

### Phase 1 — Database Foundation

- [ ] Create a backward-compatible migration.
- [ ] Upgrade the existing Operations Project.
- [ ] Backfill Fund Buckets.
- [ ] Create Allocation/Ledger constraints.
- [ ] Test rerun and rollback strategy.

Exit gate: Migration passes against a data copy and creates no duplicate Operations record.

### Phase 2 — Backend Read Model

- [ ] Implement the fund summary service.
- [ ] Implement read APIs.
- [ ] Add authorization and tests.
- [ ] Reconcile summary values against BOQ Margin and the forecast ledger.

Exit gate: Sample Project summaries match manual calculations.

### Phase 3 — Atomic Allocation

- [ ] Implement posting, idempotency, and locking.
- [ ] Implement reversal.
- [ ] Add audit events.
- [ ] Run concurrency and failure tests.

Exit gate: No new Allocation exceeds Available Margin and there are no partial ledger entries. A Forecast Deficit caused by lower BOQ Margin is displayed without rewriting history.

### Phase 4 — Frontend UX

- [ ] Project Forecast cards with actual cashflow separated from the formula
- [ ] Margin Allocation Dialog
- [ ] Margin Allocation Ledger
- [ ] Company Operations presentation
- [ ] Responsive and accessibility states

Exit gate: Lint/build passes and the Owner walkthrough passes all primary and error flows.

### Phase 5 — Demo Rollout

- [ ] Enable with feature flag `FUND_ALLOCATION_ENABLED`.
- [ ] Run migration/bootstrap.
- [ ] Owner confirms the Initial Opening Forecast Balance, including an explicit zero, and activation month through the activation flow.
- [ ] Reconcile forecast totals before enabling mutations.
- [ ] Enable read-only summary first.
- [ ] Enable Owner posting after reconciliation passes.
- [ ] Monitor errors, audit, and concurrency.

Exit gate: Demo completes all use cases with no balance discrepancy throughout the defined observation window.

### Phase 6 — Beta Rollout

- [ ] Repeat preflight and reconciliation against Beta.
- [ ] Deploy migration, Backend, and Frontend in order.
- [ ] Smoke test Owner/Admin behavior.
- [ ] Verify audit and rollback readiness.

Exit gate: Beta acceptance criteria pass before any Production decision.

## 15. Monitoring and Reconciliation

Monitor at least:

- Allocation create/reverse success rate
- `INSUFFICIENT_AVAILABLE_MARGIN` count
- `STALE_FUND_BALANCE` count
- Duplicate idempotency replay count
- Posting latency
- Ledger imbalance count, which must be zero
- Operations Bucket duplication count, which must be zero
- Projects with negative Raw Forecast Available after a BOQ Margin change
- Difference between Ledger aggregates and Allocation headers, which must be zero

Provide a reconciliation query/report that verifies:

```text
For every POSTED Allocation:
sum(DEBIT) == sum(CREDIT) == allocation.amount
```

## 16. Rollback Strategy

- Disable `FUND_ALLOCATION_ENABLED` to stop mutations immediately.
- Keep Ledger/history available in read-only mode for audit.
- The Frontend may hide the CTA without deleting data.
- The Backend rejects mutations while the feature flag is disabled.
- Never delete posted Allocations as part of rollback.
- If calculation logic is wrong, fix the service and run reconciliation. Use an auditable Adjustment/Reverse instead of editing the original row.
- Keep the first database migration additive so the application version can be rolled back safely.

## 17. Acceptance Criteria / Definition of Done

V1 is complete when:

1. Exactly one Operations System Bucket exists and reuses the existing record without creating a duplicate.
2. The Owner sees Projected BOQ Margin as the forecast base and Available Margin to Allocate as the balance after Allocated In/Out and Forecast Reserve.
3. The Owner cannot allocate more Margin than the server-calculated Available Margin.
4. Admin can read summary/history but cannot mutate.
5. Every Allocation has atomic source/target ledger entries and an Audit Trail.
6. Duplicate and concurrent requests do not create duplicates or an Allocation above Available Margin at transaction commit time.
7. Reverse creates new history and does not delete the original record.
8. Allocation does not change BOQ, Variance, Input Request, or actual cashflow values.
9. Operations is excluded from Construction KPIs and Project Health.
10. Migration, Backend tests, Frontend lint/build, and manual walkthrough pass.
11. Demo/Beta reconciliation finds no ledger imbalance.
12. User-facing copy clearly states that this allocates forecast Margin and is neither actual cash nor a bank transfer.
13. The Owner confirms the Initial Opening Forecast Balance and the Balance Start Date is the first day of a month.
14. Monthly Forecast Opening carries forward from Previous Month Forecast Closing without creating duplicate movement.
15. Subcontractors cannot view, select, or submit activity to Company Operations through either UI or API.
16. Changing `PENDING_ADMIN`/`APPROVED`/`PAID` status does not change Available Margin.
17. When BOQ Margin falls below prior allocations, the system preserves the Ledger, shows Forecast Deficit, and blocks further outgoing Allocation.

## 18. Confirmed Decisions and Activation Inputs

Product decisions are sufficient to begin implementation:

| ID | Decision | Status |
|---|---|---|
| C-01 | Display name: `Company Operations / ค่าใช้จ่ายส่วนกลาง` | Confirmed |
| C-02 | Paid/Approved/Input Request/actual cashflow is excluded from Forecast Margin Allocation calculations | Confirmed revised baseline |
| C-03 | Accounting/Admin prepares the figures; the Owner enters and confirms the Initial Opening Forecast Balance | Confirmed |
| C-04 | Balance Start Date is the first day of the month selected by the Owner | Confirmed |
| C-05 | Each following month uses Previous Month Forecast Closing as Monthly Forecast Opening | Confirmed |
| C-06 | Forecast Reserve starts at 0 and has no editing UI in V1 | Confirmed baseline |
| C-07 | Project-to-Project and Operations-to-Project allocations use the same validation rules | Confirmed |
| C-08 | Subcontractors have no Operations visibility and cannot select or submit activity to Operations | Confirmed |
| C-09 | Forecast Margin Allocation from Projected BOQ Margin is included in V1 | Confirmed revised baseline |
| C-10 | Forecast Allocated In increases the destination's Available Margin and may be allocated onward | Confirmed |
| C-11 | The latest BOQ Margin changes the forecast base without editing posted Allocations | Confirmed |

Activation inputs that are not required while building the system:

- Initial Opening Forecast Balance amount entered by the Owner
- First activation month
- Evidence/working paper from Accounting/Admin
- Demo observation window; recommended minimum is 3–5 business days or completion of all defined use cases

## 19. Suggested V2 Backlog

- Percentage rules, such as allocating 20% to Operations
- Recurring monthly Allocation
- Forecast Reserve management UI
- Two-person approval for Allocation
- Notifications when a Project has a Forecast Deficit
- Company-level MAKE-style Bucket board
- Forecast Margin Allocation versus actual cashflow comparison
- Actual cash allocation and bank/accounting reconciliation as a separate project that does not change Forecast Margin Allocation semantics
