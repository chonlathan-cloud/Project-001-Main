# Default Company Operations — Product & UX Plan

> Approved revised concept for the default Operations System Project and the Forecast Margin Bucket experience

| Item | Value |
|---|---|
| Status | Approved revised baseline — implementation alignment required |
| Last updated | 2026-08-07 |
| Default display name | `Company Operations` |
| Thai description | `ค่าใช้จ่ายส่วนกลางของบริษัท` (Company-wide operating expenses) |
| System identifier | `OPERATIONS` |
| Mutation role | `owner` only |
| Initial forecast owner | The Owner enters and confirms the Opening Forecast Balance in the system |
| Balance start rule | The first day of the selected activation month |
| Thai version | [plan.md](plan.md) |
| Related implementation plan | [actionplan.en.md](actionplan.en.md) |

## 1. Product Concept

`Company Operations` is the company's central Forecast Bucket. It receives forecast margin allocated from Projects and supports planning for company-wide operating budgets such as payroll, software subscriptions, office costs, taxes, and administrative expenses.

Forecast Margin Allocation is planning data, not actual cash, and is independent of `PENDING_ADMIN`, `APPROVED`, and `PAID` status. Actual income and expense remain visible in a separate Cashflow view. Operations is not a Construction Project and must not display BOQ or construction-progress information.

## 2. Default Operations Rules

1. Each company/deployment has exactly one Operations System Project.
2. Migration/bootstrap creates or upgrades Operations automatically; the user does not create it manually.
3. The current `โครงการบริษัท` project with type `INTERNAL` and its existing UUID must be reused. The system must not create a duplicate.
4. System lookup uses `system_key='OPERATIONS'`; it must not depend on the display name.
5. The Owner may change the display name but cannot change the system key or system type.
6. Operations cannot be deleted, archived, or converted into a Construction Project.
7. Operations is excluded from Active Construction Project counts, Project Health, Progress, Risk, and BOQ KPIs.
8. Each new Project receives its own Fund Bucket, but it never creates another Operations project.
9. The Owner enters the Initial Opening Forecast Balance once during activation because Operations has no BOQ Margin.
10. Accounting/Admin prepares and verifies the figures; the Owner performs the final review and confirmation.
11. The Balance Start Date must be the first day of the month selected by the Owner.
12. From the following month onward, the system carries Previous Month Forecast Closing into Monthly Forecast Opening. Users must not re-enter it each month.
13. Company Operations is internal-only and has no relationship with Subcontractors.

## 3. Information Architecture

The Projects page is divided into two sections:

```text
PROJECTS

Company Funds
┌───────────────────────────────────────────┐
│ Company Operations        [System Bucket] │
│ Company-wide operating expenses           │
│                                           │
│ Available Margin       THB 500,000        │
│ Allocated In           THB 200,000        │
│ Allocated Out           THB 50,000        │
│                                           │
│ [Open]           [Allocate Margin]        │
└───────────────────────────────────────────┘

Active Construction Projects
┌──────────────────┐  ┌──────────────────┐
│ SENA Park        │  │ Office Renovation│
└──────────────────┘  └──────────────────┘
```

### UX Rules on the Projects Page

- Pin Operations at the top in the `Company Funds` section.
- Display a `System Bucket` badge.
- Show the `Allocate Margin` action to the Owner.
- Show Admins the information in read-only mode with a `Read only` badge and no mutation controls.
- If there is a Forecast Deficit, show the amount and state explicitly rather than relying on color alone.
- Do not accidentally mix Operations into Construction status search or filtering.

## 4. Company Operations Detail Page

The Operations page uses the same header and visual language as Project Detail, but removes all construction-specific sections.

```text
Company Operations                         [System Bucket]
Company-wide operating expenses

┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ Available Margin│ │ Allocated In    │ │ Allocated Out   │
│ THB 500,000     │ │ THB 200,000     │ │ THB 50,000      │
│ [Allocate Margin]││ Forecast        │ │ Forecast        │
└─────────────────┘ └─────────────────┘ └─────────────────┘

[Overview] [Actual Expenses] [Margin Allocations]

Recent activity
SENA Park → Company Operations      +THB 200,000
Company Operations → Project B      −THB 50,000
```

### 4.1 Header

- Name: `Company Operations`
- Description: `ค่าใช้จ่ายส่วนกลางของบริษัท` / Company-wide operating expenses
- Badge: `System Bucket`
- Do not show Customer, Construction status, or progress.
- The Owner may change the display name through the designated Settings UI without changing the system identity.

### 4.2 Summary Cards

1. `Available Margin to Allocate`
   - Shows forecast margin that remains available for allocation.
   - The Owner sees an `Allocate Margin` button.
   - If the value is zero, disable the button and show an explanation.
2. `Forecast Allocated In`
   - Margin received by Operations from Project Buckets.
3. `Forecast Allocated Out`
   - Margin allocated from Operations to Project Buckets.

Approved Commitments and Paid This Month may appear as secondary Cashflow metrics, but must be identified as actual activity and must not affect Available Margin.

### 4.3 Tabs

#### Overview

- Summary cards
- Recent expenses
- Recent Margin Allocations
- Forecast Deficit warning, when applicable

#### Actual Expenses

- Shows Input Requests associated with Operations.
- Separates Pending, Approved, and Paid items.
- Reuses the current approval/payment flow.
- Margin Allocations are not shown as Income or Expense, and those statuses do not change Available Margin.

#### Margin Allocations

- Shows Allocation In and Allocation Out.
- Shows From, To, Amount, Reason, Reference, Actor, and Timestamp.
- Provides allocation detail and a Reverse action for the Owner.
- Admins can read but cannot reverse.

### 4.4 Content That Must Not Appear

- Customer BOQ
- Subcontractor BOQ
- Projected BOQ Margin/Total Variance
- Matching Coverage
- Construction Progress
- Execution/BOQ charts
- Construction-specific Risk/Health metrics

## 5. First-use and Empty State

When Operations has no balance:

```text
Available Margin to Allocate
THB 0.00

No forecast margin is available in Company Operations yet.

[Set Opening Forecast]  [Receive Margin from Project]
```

### Set Opening Forecast Balance

- Show this only to the Owner and only while no Initial Opening Forecast Balance entry exists.
- Accounting/Admin prepares and verifies the figures for the Owner.
- The Owner enters the Amount, selects the activation month, and performs the final confirmation in the system.
- The system automatically sets the Effective Date to the first day of the selected month.
- Require a Reason and show a Preview before confirmation.
- State clearly that this is an opening forecast budget, not actual cash, a bank balance, or customer income.
- Store it as an immutable `OPENING_BALANCE` ledger entry with forecast semantics.
- If it is incorrect, use Adjustment/Reverse; never edit or delete the original record.

### Monthly Forecast Roll-forward

The Owner does not enter a new Opening Forecast Balance every month. The system carries it forward automatically:

```text
August Forecast Closing Balance
          ↓ automatically
September 1 Forecast Opening Balance
```

- The Initial Opening Forecast Balance is entered only once during activation.
- On the first day of each following month, `Monthly Forecast Opening = Previous Month Forecast Closing`.
- Monthly carry-forward does not create new Income, Expense, or Allocation activity.
- Forecast movement before the Balance Start Date is represented by the Initial Opening Forecast Balance and must not be counted again.
- Corrections use Adjustment/Reverse with an Audit Trail; Monthly Forecast Opening values are never edited directly.

### Receive Margin from a Project

- Open the Allocation Dialog.
- Let the Owner choose an Active Project that has Available Margin as the Source.
- Lock the Target to Company Operations.
- Show before-and-after balances for both sides before confirmation.

## 6. Allocation UX

### 6.1 From a Construction Project

When the Owner selects `Allocate Margin` from a regular Project:

```text
From: SENA Park
To:   Company Operations  ← default selection
```

- Company Operations is the first destination option.
- The Owner may change the destination to another Active Project.
- The maximum amount is the Source Project's Available Margin to Allocate.
- Projected BOQ Margin is the Project's forecast base and participates in the ceiling together with Forecast Allocated In/Out and Forecast Reserve.
- Paid/Approved Income, Expense, and commitments do not affect this ceiling.

### 6.2 From Company Operations

When the Owner selects `Allocate Margin` from Operations:

```text
From: Company Operations
To:   Select an Active Project
```

This flow assigns forecast capacity back to a Project under the same validation rules; it does not assert that actual cash was injected.

### 6.3 Dialog Fields

1. From — locked when opened from a detail page
2. Available Margin — server-calculated forecast balance
3. To — Active destination selector
4. Amount — numeric/decimal input
5. `Use maximum`
6. Reason — required
7. Before/After Preview
8. `Confirm Margin Allocation THB X`

Required notice:

> This allocates forecast margin inside the product. It is not actual cash and does not initiate a bank transfer.

## 7. User Permissions

| Capability | Owner | Admin | Subcontractor |
|---|---:|---:|---:|
| View Operations Detail | Yes | Yes | No |
| View Available Margin/Forecast Allocation | Yes | Yes | No |
| View Allocation History | Yes | Yes | No |
| Allocate Margin | Yes | No | No |
| Reverse Allocation | Yes | No | No |
| Set Opening Forecast Balance | Yes | No | No |
| Change display name | Yes | No | No |
| Delete/Archive Operations | No | No | No |

### Subcontractor Input Policy

Company Operations is internal-only and has no relationship with Subcontractors:

- Subcontractors see only the Projects to which they are assigned.
- Company Operations must not appear in a Subcontractor Project selector.
- Subcontractors cannot submit Income or Expense items to Operations.
- Subcontractors cannot view the Operations page, Available Margin, Opening Forecast Balance, Commitments, or Allocation History.
- Operations expenses are entered through the Internal Input Flow by an authorized internal user. In V1, the Owner performs mutations while Admin/Accounting prepares and verifies information in read-only mode.
- If a Subcontractor performs work for the company, such as an office renovation, create a real Construction/Internal Work Project and assign that Subcontractor. Do not use Company Operations as a substitute for a Project.

## 8. Loading, Error, and Protection States

- Loading summary/history
- Empty Operations
- Opening Forecast Balance required
- Forecast Deficit
- Available Margin equals zero
- Read-only Admin
- Feature disabled
- Operations bucket missing/configuration error
- Stale balance while the Dialog is open
- Insufficient available margin
- Duplicate submission
- Allocation success
- Reverse blocked because the target has insufficient Available Margin

If the Operations record is missing, the UI must not silently create a replacement because doing so could produce a duplicate. Show a configuration error and use an auditable bootstrap/recovery process.

## 9. Required User-facing Copy

| Location | Copy |
|---|---|
| Operations title | `Company Operations` |
| Operations subtitle | `Company-wide operating expenses` |
| System badge | `System Bucket` |
| Available card | `Available Margin to Allocate` |
| Zero balance | `No forecast margin is currently available to allocate.` |
| Deficit | `Forecast margin is below the amount already allocated.` |
| Allocation CTA | `Allocate Margin` |
| Opening CTA | `Set Opening Forecast Balance` |
| Internal-only notice | `This allocates forecast margin. It is not actual cash and does not initiate a bank transfer.` |
| Admin state | `Read only — Owner permission is required` |

## 10. UX Acceptance Criteria

1. Operations appears at the top of Company Funds and is clearly separated from Construction Projects.
2. Users understand from the Projects page that Operations represents company-wide expenses rather than construction work.
3. Operations has no BOQ, Margin, or Progress UI.
4. The Owner can reach Margin Allocation within no more than two actions from the Projects page.
5. Company Operations is the default destination when allocating from a Construction Project.
6. The Owner sees a Before/After Preview before confirmation.
7. Admins can read complete information but have no mutation controls.
8. Subcontractors cannot view the Operations page or its financial values.
9. Empty, Forecast Deficit, and Error states provide a clear next action.
10. Users cannot delete, archive, or create a duplicate Operations record through the UI.
11. Primary and Reverse flows work on mobile and with keyboard navigation.
12. Allocation is presented as Forecast Margin, never as a Bank Transfer, actual cash, or Income/Expense.
13. Changing `PENDING_ADMIN`/`APPROVED`/`PAID` status does not change Available Margin or the action state.
14. If BOQ Margin falls below prior allocations, the system shows Forecast Deficit without rewriting history.

## 11. Activation Inputs

Product and UX decisions are sufficient to begin implementation. The following values are supplied during activation and do not need to be known while building the system:

1. The Initial Opening Forecast Balance amount entered by the Owner
2. The first activation month; the system uses the first day of that month as the Balance Start Date
3. The evidence or working paper used by Accounting/Admin to prepare the balance
4. The Demo observation window before Beta rollout

Development defaults:

- Display name: `Company Operations`
- Thai subtitle: `ค่าใช้จ่ายส่วนกลางของบริษัท`
- Forecast Reserve: 0
- Operations is the default allocation destination
- Owner-only mutations and Admin read-only access
- Accounting/Admin prepares the figures; the Owner enters and confirms the Initial Opening Forecast Balance
- Monthly Forecast Opening automatically carries forward from the Previous Month Forecast Closing
- Subcontractors have no Operations visibility and cannot select or submit activity to Operations
