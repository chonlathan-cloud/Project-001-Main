# CDR-002 — Scope identity, hierarchy, and lifecycle

Status: **LOCKED**
Scope: Phase 1 additive domain model and command invariants

## Identity and hierarchy

- A logical scope node has a stable UUID independent of display numbering,
  description, array position, revision, and persistence row ID.
- Each revision carries immutable revision-row UUIDs that refer to logical node
  UUIDs. Copy/revise preserves lineage but does not reuse the persistence row.
- Every node is owned by exactly one project and one document revision.
- Allowed structural kinds are SECTION, CATEGORY, optional SUBCATEGORY, and ITEM.
  Only ITEM is billable. CATEGORY may contain ITEM directly.
- Parent/project/revision consistency is enforced at command validation and with
  database constraints where expressible.
- Reject cycles, orphans, cross-project/cross-revision parents, and item parents.
- Sibling order is explicit. Display paths/item numbers are derived presentation
  data, never identity or foreign keys.
- Changing an ITEM into a structural node requires an explicit draft command to
  move its values into a child or discard them with an impact confirmation.
- Hard delete is limited to unreferenced draft rows. Issued/accepted lineage is
  immutable and retained.

The existing hierarchy SQL/helper is not accepted as proof that these rules are
integrated. Phase 1 must implement and test the V2 model independently without
changing legacy `boq_items` semantics.

## Document kinds and membership

- `MAIN`: a principal quotation revision chain.
- `ALTERNATIVE`: mutually exclusive commercial alternatives; selecting one does
  not add the unselected alternatives.
- `CHANGE_ORDER`: signed ADD or DEDUCT scope tied to the accepted baseline and
  stable logical items.

Exactly one active baseline exists per project. It contains one accepted MAIN
revision plus zero or more accepted change orders. Budget totals derive from
that explicit membership, never from all issued/accepted documents in a project.

Rebaselining MAIN requires a preview and explicit per-change-order decision to
retain or absorb. Retain/absorb preserves original-estimate provenance and
vendor obligation/award identity and is committed atomically. Equal totals are
not evidence that one change order absorbed another.

## Lifecycle commands

State changes are explicit commands, not free-form status patches:

```text
DRAFT --validate--> DRAFT
DRAFT --issue--> ISSUED
ISSUED --record-acceptance--> ACCEPTED
DRAFT|ISSUED --withdraw--> WITHDRAWN
ISSUED --reject--> REJECTED
ACCEPTED --supersede via accepted replacement--> SUPERSEDED
```

- `revise` creates a new DRAFT linked to its predecessor.
- `create-alternative` creates a distinct alternative lineage.
- `create-change-order` records baseline/version and affected logical item IDs.
- `activate-baseline` requires an accepted MAIN, validates accepted CO membership
  and an eligible cost-plan version, then writes baseline, audit, and version
  atomically.
- Draft/issued content never enters the operational project budget.
- Issued/accepted customer document payloads and render inputs are immutable
  snapshots. Corrections create a new revision.
- Acceptance is an internal RAYADEE record with actor/time/evidence reference; it
  does not create a customer portal or e-signature workflow.

## Change-order guards

- A CO references the exact baseline/version it modifies.
- Reject stale or overlapping deductions, deductions beyond remaining scope,
  duplicate acceptance, and double membership.
- A sell deduction does not erase cost/vendor obligations until an explicit cost
  adjustment records the consequence.
- MAIN replacement cannot make accepted COs disappear or count twice.

## Phase boundary

Phase 1 may add the minimum data model and internal command primitives needed to
prove these invariants, but it must not expose public mutation routes or activate
V2 for a project. Quotation document generation, offer selection, catalog flows,
and exports remain later phases.
