# Project Fund Allocation — Action Plan

> Implementation plan for allocating funds between Project Buckets, inspired by the Envelope/Bucket Budgeting concept used by MAKE by KBank. This design is specific to Projects-001 and does not copy MAKE by KBank branding or screens.

| Item | Value |
|---|---|
| Document status | Proposed planning baseline — implementation not started |
| Created | 2026-08-06 |
| Product scope | Project Fund Buckets, Company Operations, Fund Allocation Ledger |
| Allocation permission | `owner` only |
| Read permission | `owner` and `admin`, subject to current project visibility |
| Transaction type | Virtual allocation within the product; not a bank transfer |
| Rollout target | Local/Demo → Beta → Production decision |
| Thai version | [actionplan.md](actionplan.md) |
| Related Product/UX plan | [plan.en.md](plan.en.md) |

## 1. Objective

Introduce a fund-management model in which users understand each Project as a Bucket and can allocate funds between Buckets. `Company Operations` is the default Bucket for company-wide operating expenses.

The feature must enable the Owner to:

1. Distinguish projected profit from funds that are actually available to allocate.
2. Manually allocate funds from one Project to `Company Operations` or another Project.
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

- `Total Variance` resembles profit but does not represent cash already received.
- There is no `Available to Allocate` value.
- There is no ledger for moving balances between Projects.
- `โครงการบริษัท` is currently identified by name and `project_type`, which is fragile when the display name changes.
- There is no protection against duplicate submission, concurrent allocation, or retroactive history edits.

### 2.3 Migration Approach

Do not create a duplicate Operations Project. Upgrade the existing `โครงการบริษัท` record into the default Operations Project and preserve its UUID so existing Input Requests and relationships remain intact.

## 3. Product Decision Register

The following decisions are the V1 baseline. If implementation requires a change, record the reason in this document or an ADR before proceeding.

| ID | Decision |
|---|---|
| D-01 | Each Project has exactly one Fund Bucket in a 1:1 relationship. |
| D-02 | Each company/deployment has exactly one default `Company Operations` record. |
| D-03 | Reuse the existing `โครงการบริษัท` record with type `INTERNAL`; do not create a duplicate. |
| D-04 | Allocation is a virtual product-internal movement and does not initiate a bank transfer. |
| D-05 | Rename the `Total Variance` label to `Projected BOQ Margin`, or equivalent Thai copy that clearly indicates an estimate. It is not the allocation ceiling. |
| D-06 | The allocation ceiling is `Available to Allocate`, calculated from cash, commitments, and allocations. |
| D-07 | The Owner creates and reverses allocations. Admin can read summary/history but cannot mutate. |
| D-08 | Allocation does not change BOQ, Revenue, Expense, Projected Margin, or Input Request status. |
| D-09 | A posted Allocation is immutable. It cannot be edited or deleted; correction uses a reversal. |
| D-10 | Every Allocation creates source and target ledger entries in one database transaction. |
| D-11 | Monetary values use two-decimal fixed precision. Do not use float for calculation or storage contracts. |
| D-12 | V1 supports Project → Operations, Project → Project, and Operations → Project when the destination is Active. |
| D-13 | `Company Operations` is displayed as a System Bucket, separate from construction work, and excluded from Project Health and Construction KPIs. |
| D-14 | Planned Allocation from future margin is outside V1 and must not be mixed with actual available funds. |
| D-15 | The Owner enters and confirms the Initial Opening Balance; Accounting/Admin prepares and verifies the figures. |
| D-16 | The Balance Start Date is the first day of the selected activation month. Each following month automatically uses the Previous Month Closing as the Monthly Opening. |
| D-17 | Subcontractors cannot view, select, or submit Income/Expense activity to Company Operations. They see assigned Projects only. |

## 4. Terminology and Financial Semantics

| Product term | Meaning |
|---|---|
| Projected BOQ Margin | `Customer BOQ - Subcontractor BOQ`; a BOQ-based estimate |
| Paid Income | Project income with `PAID` status |
| Paid Expense | Project expense with `PAID` status |
| Approved Commitment | An Owner-approved expense that has not been paid (`APPROVED`) |
| Allocated In | Funds received from another Bucket through a posted Allocation |
| Allocated Out | Funds sent to another Bucket through a posted Allocation |
| Protected Reserve | Funds set aside and not available for allocation; V1 default is 0 |
| Raw Available | Calculated balance before applying the lower bound |
| Available to Allocate | `max(0, Raw Available)` and the maximum amount the Owner may allocate |
| Funding Deficit | Absolute value of Raw Available when Raw Available is negative |

### 4.1 V1 Formula

```text
Raw Available
= Paid Income
+ Allocated In
- Paid Expense
- Approved Expense Commitments
- Allocated Out
- Protected Reserve

Available to Allocate = max(0, Raw Available)
Funding Deficit       = max(0, -Raw Available)
```

Money-counting rules:

- Use `approved_amount` when present; otherwise use `amount`.
- `PAID` and `APPROVED` must be mutually exclusive sets so the same item is not deducted twice.
- V1 does not count `PENDING_ADMIN` as a commitment.
- Approved Income is not allocatable until it reaches `PAID`.
- Select one finance source of truth per business transaction. Never sum an Input Request and a derived Transaction for the same activity twice.
- When Raw Available is negative, show a Funding Deficit and disable allocation.

### 4.2 Opening Balance

`Company Operations` has no predefined Initial Opening Balance. The Owner enters the actual amount during a controlled activation flow:

- Accounting/Admin prepares and verifies the figures before sending them to the Owner.
- The Owner enters the amount and performs the final confirmation in the system.
- The Owner selects the activation month; the system sets the Effective Date to the first day of that month.
- The Initial Opening Balance is used once during activation/setup.
- The Owner provides the amount and reason and reviews a Preview before confirming.
- Store it as an immutable ledger entry of type `OPENING_BALANCE`.
- Never edit the original balance. Use Adjustment/Reverse if it is wrong.
- The default remains 0 until the Owner confirms activation, including an explicit confirmation of a zero balance.
- Activity before the Balance Start Date must not be counted again because it is already represented in the opening amount.

### 4.3 Monthly Balance Roll-forward

After initial activation, the Owner does not enter a new Opening Balance every month:

```text
Monthly Opening on the first day of the current month
= Previous Month Closing Balance
```

- The Initial Opening Balance is the only manual opening entry.
- Subsequent Monthly Opening values are derived balances, not Income, Expense, or Allocation activity.
- Monthly Closing includes movements from the first through the last day of the month.
- Historical corrections use Adjustment/Reverse with an Audit Trail, and the system recalculates affected monthly closing/opening values.

## 5. V1 Scope

### 5.1 In Scope

- Default Company Operations Project/System Bucket
- Project fund summary and the Available to Allocate formula
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
- No Planned Allocation from Variance that has not become cash
- No multi-currency; V1 uses THB
- No change to BOQ logic or the Variance formula
- No change to the Input Request approval/payment flow
- No deletion of posted ledger data

## 6. Target UX

### 6.1 Project List

- Pin `Company Operations` in a `Company Funds` section above Construction Projects.
- Display a `System Bucket` badge.
- Show `Available to Allocate`, Funding Deficit when applicable, and recent activity.
- Do not show Construction Progress, Customer BOQ, or Project Health for Operations.
- Operations cannot be deleted or archived.

### 6.2 Project Detail — Financial Overview

Add a `Project Funds` section with at least two cards:

1. `Projected BOQ Margin`
   - Displays the existing Total Variance value.
   - Shows an `Estimate` badge.
   - Helper text: “For planning purposes; this is not cash available to allocate.”
   - Has no allocation action.
2. `Available to Allocate`
   - Displays the amount calculated from actual cash, commitments, and allocations.
   - Shows an `Available` badge.
   - Shows an `Allocate funds` button to the Owner.
   - Admin sees the balance in read-only mode with no mutation action, consistent with current UI conventions.

Add an `Allocation Ledger` section beneath the cards:

- Show From, To, Amount, Reason, Status, Created by, and Created at.
- Distinguish Allocated In and Allocated Out with labels and signs, not color alone.
- Allow users to open detail and view reversal relationships.

### 6.3 Allocation Dialog

Use the approved mockup flow:

1. `From` — locked to the current Project
2. `Available` — latest server-calculated value
3. `To` — searchable selector with Company Operations listed first
4. `Amount` — decimal input with a `Use maximum` action
5. `Reason` — required
6. `Reference/Note` — optional if retained during implementation
7. `Preview` — source and target balances before and after
8. Confirmation — `Confirm allocation THB X`

Required notice:

> This is an internal fund allocation. It does not initiate a bank transfer.

### 6.4 Dialog States

- Loading summary/options
- Ready
- Invalid amount
- Amount exceeds Available
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
- If the current target does not have enough Available balance, block the Reverse rather than creating a negative balance.
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
2. `amount <= current Available to Allocate`
3. Source and Target must be different Projects.
4. Source and Target must be Active and have Fund Buckets.
5. Exactly one System Operations Bucket exists per company/deployment.
6. Only the Owner may POST or Reverse.
7. The server recalculates Available inside the transaction and never trusts the Frontend value.
8. If the balance changes after the Dialog opens, return `409 STALE_FUND_BALANCE`.
9. Retrying the same idempotency key returns the existing Allocation instead of creating another one.
10. A posted Allocation cannot be updated or deleted.
11. A Reverse cannot make the returning side's Available balance negative.
12. Allocation does not create an Input Request, Transaction, or BOQ Item.
13. Allocation is not Income/Expense and is excluded from actual cashflow KPIs.
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
- protected_reserve NUMERIC(15,2) default 0
- status SETUP | ACTIVE | LOCKED
- created_at
- updated_at
```

Backfill exactly one Bucket for every existing Project.

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
- `fund_allocation.rejected_insufficient_funds`
- `fund_allocation.rejected_stale_balance`
- `operations_bucket.bootstrap_completed`
- `operations_bucket.opening_balance_set`

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
  "projected_boq_margin": "1000000.00",
  "paid_income": "900000.00",
  "paid_expense": "300000.00",
  "approved_expense_commitment": "150000.00",
  "allocated_in": "200000.00",
  "allocated_out": "250000.00",
  "protected_reserve": "50000.00",
  "raw_available": "350000.00",
  "available_to_allocate": "350000.00",
  "funding_deficit": "0.00",
  "calculated_at": "2026-08-06T10:42:00+07:00",
  "version": "opaque-balance-version"
}
```

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

- `INSUFFICIENT_AVAILABLE_FUNDS`
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
2. Aggregate paid/approved Input Requests without double counting.
3. Aggregate posted ledger entries.
4. Calculate fund summary values using Decimal.
5. Lock source and target rows in deterministic order to reduce deadlocks.
6. Recalculate source Available inside the transaction.
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
- Add Available to Allocate and Funding Deficit states.
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
- Show Operations cash, commitment, allocation, and expense overview.
- Add `System Bucket` badge and delete/archive protection.
- Add Initial Opening Balance setup for the Owner, with a month selector that enforces the first day.
- Display monthly opening/closing with automatic roll-forward.
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
- Establish a single finance source of truth.
- Calculate summary and balance version.
- Support Funding Deficit.

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
- Implement one-time Initial Opening Balance and monthly roll-forward semantics.

## 13. Test Plan

### 13.1 Unit Tests

- Formula coverage for income, expense, approved commitment, allocation, and reserve
- `approved_amount` fallback to `amount`
- Positive, zero, and negative Raw Available
- Decimal precision and two-decimal rounding
- BOQ Margin excluded from Available
- Balance version changes when relevant Input or Ledger activity changes
- Initial Balance Start Date must be the first day of a month
- Monthly Opening equals Previous Month Closing and creates no duplicate movement

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
- Allocation does not change BOQ, Input Request, or actual cashflow values.
- Subcontractor Project options do not return Operations.
- A Subcontractor submitting an Operations Project ID directly receives `403`.
- Only the Owner can create the Initial Opening Balance, and only once.
- Monthly roll-forward creates no Income, Expense, or Allocation entries.

### 13.3 Frontend Tests

- Owner/Admin rendering
- Allocation disabled when Available is zero
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

### Phase 0 — Decision Freeze and Data Reconciliation

- [ ] Confirm the finance source of truth for Paid/Approved activity.
- [ ] Verify the existing `โครงการบริษัท` UUID and values in Demo/Beta.
- [ ] Confirm the Operations display name.
- [ ] Accounting/Admin prepares the Initial Opening Balance working paper.
- [ ] The Owner selects the activation month; the system uses the first day as the Balance Start Date.
- [ ] The Owner enters and confirms the Initial Opening Balance in the activation flow.
- [ ] Collect at least three real Project examples for manual formula comparison.

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
- [ ] Reconcile summary values against real data.

Exit gate: Sample Project summaries match manual calculations.

### Phase 3 — Atomic Allocation

- [ ] Implement posting, idempotency, and locking.
- [ ] Implement reversal.
- [ ] Add audit events.
- [ ] Run concurrency and failure tests.

Exit gate: The test matrix produces no negative balances and no partial ledger entries.

### Phase 4 — Frontend UX

- [ ] Project Funds cards
- [ ] Allocation Dialog
- [ ] Allocation Ledger
- [ ] Company Operations presentation
- [ ] Responsive and accessibility states

Exit gate: Lint/build passes and the Owner walkthrough passes all primary and error flows.

### Phase 5 — Demo Rollout

- [ ] Enable with feature flag `FUND_ALLOCATION_ENABLED`.
- [ ] Run migration/bootstrap.
- [ ] Owner confirms the Initial Opening Balance, including an explicit zero, and activation month through the activation flow.
- [ ] Reconcile fund totals before enabling mutations.
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
- `INSUFFICIENT_AVAILABLE_FUNDS` count
- `STALE_FUND_BALANCE` count
- Duplicate idempotency replay count
- Posting latency
- Ledger imbalance count, which must be zero
- Operations Bucket duplication count, which must be zero
- Projects with negative Raw Available
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
2. The Owner sees Projected BOQ Margin and Available to Allocate as different values with different meanings.
3. The Owner cannot allocate more than the server-calculated Available value.
4. Admin can read summary/history but cannot mutate.
5. Every Allocation has atomic source/target ledger entries and an Audit Trail.
6. Duplicate and concurrent requests do not create duplicate or negative balances.
7. Reverse creates new history and does not delete the original record.
8. Allocation does not change BOQ, Variance, Input Request, or actual cashflow values.
9. Operations is excluded from Construction KPIs and Project Health.
10. Migration, Backend tests, Frontend lint/build, and manual walkthrough pass.
11. Demo/Beta reconciliation finds no ledger imbalance.
12. User-facing copy clearly states that this is an internal allocation, not a bank transfer.
13. The Owner confirms the Initial Opening Balance and the Balance Start Date is the first day of a month.
14. Monthly Opening automatically carries forward from Previous Month Closing without creating duplicate movement.
15. Subcontractors cannot view, select, or submit activity to Company Operations through either UI or API.

## 18. Confirmed Decisions and Activation Inputs

Product decisions are sufficient to begin implementation:

| ID | Decision | Status |
|---|---|---|
| C-01 | Display name: `Company Operations / ค่าใช้จ่ายส่วนกลาง` | Confirmed |
| C-02 | Paid/Approved uses Input Request finance rows and must not double-count derived Transactions | Technical baseline |
| C-03 | Accounting/Admin prepares the figures; the Owner enters and confirms the Initial Opening Balance | Confirmed |
| C-04 | Balance Start Date is the first day of the month selected by the Owner | Confirmed |
| C-05 | Each following month automatically uses Previous Month Closing as Monthly Opening | Confirmed |
| C-06 | Protected Reserve starts at 0 and has no editing UI in V1 | Confirmed baseline |
| C-07 | Project-to-Project and Operations-to-Project allocations use the same validation rules | Confirmed |
| C-08 | Subcontractors have no Operations visibility and cannot select or submit activity to Operations | Confirmed |
| C-09 | Planned Allocation moves to V2 | Confirmed |

Activation inputs that are not required while building the system:

- Initial Opening Balance amount entered by the Owner
- First activation month
- Evidence/working paper from Accounting/Admin
- Demo observation window; recommended minimum is 3–5 business days or completion of all defined use cases

## 19. Suggested V2 Backlog

- Planned Allocation from Projected Margin
- Percentage rules, such as allocating 20% to Operations
- Recurring monthly Allocation
- Protected Reserve management UI
- Two-person approval for Allocation
- Notifications when a Project has a Funding Deficit
- Company-level MAKE-style Bucket board
- Planned versus Actual Allocation forecast
- Bank/accounting reconciliation as a separate project that does not change internal Allocation semantics
