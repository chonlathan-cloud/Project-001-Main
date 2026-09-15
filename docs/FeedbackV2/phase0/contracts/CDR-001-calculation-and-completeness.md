# CDR-001 — Calculation and cost completeness

Status: **LOCKED**
Scope: Phase 1 pure domain logic; no public behavior change

## Decision

BOQ V2 calculations use decimal arithmetic only. Input quantity and unit-rate
columns use a scale of four; persisted monetary totals use a scale of two. A
missing required cost is an unknown value, never an implicit zero.

## Precision and rounding

- Quantities and unit rates: PostgreSQL `NUMERIC(20,4)`.
- Monetary totals: PostgreSQL `NUMERIC(20,2)`.
- Python/API calculation values: `Decimal`; no binary float in domain logic.
- Component extended amount:
  `round_half_up(component_quantity * component_unit_rate, 0.01)`.
- Line material and labor totals are sums of already-rounded component amounts.
- Document subtotals and totals sum persisted leaf totals once. Structural nodes
  never contribute an editable amount.
- Percentage adjustments calculate from their declared basis and round half up
  to `0.01` at the adjustment boundary.
- Percentage fields have explicit semantics; markup and margin are not aliases.
- API decimal values in the new internal contract are canonical fixed-scale
  strings. Existing public legacy adapters retain their current numeric shape.
- Reject values that exceed database precision before persistence.

## Required-cost state

Each MATERIAL or LABOR component that is required by an included leaf has one of:

| State | Unit rate | Counts as complete | Meaning |
| --- | --- | --- | --- |
| `UNKNOWN` | `null` | No | Required price is not known |
| `PRICED` | Decimal, including intentional `0.0000` | Yes | Rate is explicitly supplied |
| `NOT_APPLICABLE` | `null` | Yes | Component is explicitly unnecessary |

An explicit zero in `PRICED` requires a reason/audit field. `0` without the
state and reason is not enough to distinguish free work from missing data.

Cost coverage is evaluated over required components, including items whose sell
price is zero. Excluded scope does not enter budget or coverage. A free-of-charge
customer item still requires its applicable internal costs.

```text
required_count = included leaf components where state != NOT_APPLICABLE
priced_count   = required components where state == PRICED and basis is current
COMPLETE       = required_count == priced_count
INCOMPLETE     = otherwise
```

Changing inherited quantity/unit/spec invalidates an offer or selected price
whose basis no longer covers the component. An explicitly overridden component
retains its quantity but is revalidated against its own basis.

## Cost totals

- `original_estimated_cost`: immutable first complete estimate for accepted
  scope membership; otherwise `null`.
- `agreed_cost`: sum of valid selected vendor costs only when all required
  components have valid selections; otherwise `null`.
- `forecast_cost`: agreed cost where valid, otherwise a current complete
  estimate. It is `null` when any required cost remains unknown/stale.
- `forecast_margin = net_sell_ex_vat - forecast_cost` only when both operands
  are known; otherwise `null`.
- VAT is not part of the operational project budget or margin basis. All figures
  above use THB ex-VAT.

No caller may coerce a V2 nullable forecast or margin to zero. Phase 1 public
legacy adapters continue returning their current values; V2 readiness/status is
kept internal until consumers explicitly support it.

## Adjustment and payment rules

- MAIN and ADD values are positive; DEDUCT changes reduce the active baseline
  exactly once through signed membership semantics.
- Percentage discount bases and fixed adjustments are explicit snapshot fields.
- Division-derived margin percent is `null` when the denominator is zero.
- Payment schedules allocate rounded installments and put the residual on the
  final installment. For THB 7,752.15 at 30/30/30/10, expected values are
  `2325.65`, `2325.65`, `2325.65`, `775.20`.

## Acceptance fixtures required in Phase 1

- Fractional quantity/rate multiplication and half-up boundaries.
- Nested groups where only leaf totals count.
- Unknown versus explicit zero versus not-applicable.
- Free customer line with required cost.
- Missing one component makes full forecast and margin `null`.
- Inherited and overridden quantity behavior after scope edits.
- Markup versus margin, percent/fixed discount, VAT basis, zero denominator,
  signed change orders, payment residual, and numeric overflow.

## Consequence

Current legacy columns remain `NUMERIC(15,2)` and retain zero-default behavior.
They are not silently reinterpreted as complete V2 costs. A legacy snapshot uses
`LEGACY_UNVERIFIED` completeness.
