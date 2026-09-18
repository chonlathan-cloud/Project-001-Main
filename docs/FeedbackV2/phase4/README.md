# Phase 4 — Vendor Cost and Price Database

## Baseline and scope

- Branch at preflight: `feature`
- Phase 3 baseline: `f4265f8fa95a51e656ed52ee242dcda1325a4919`
- The working tree was clean and `HEAD` matched the baseline before Phase 4 edits.
- Scope is limited to Phase 4. No deployment, production-data access, IAM/authentication-architecture change, legacy-sync retirement, procurement automation, payment creation, AI pricing, or Phase 5 cleanup was performed.

## Architecture delivered

### Vendor offers and comparison

Project-scoped commercial vendors are deliberately separate from login/account identity. An offer freezes its quotation reference/date/validity, tax and discount basis, included charges, notes, evidence-object identity, and one or more component lines. Each line records the required and offered quantity, unit, specification, calculation basis version/fingerprint, original amount and—only when safe—a normalized ex-VAT comparison value.

Material and labor are independent components and may select different vendors. The service does not choose a cheapest offer. A partial offer is never eligible for selection; unit/specification differences and expired or unknown-tax offers require explicit warning acknowledgement and a reason. A later quantity/unit/specification change marks an incompatible current selection stale and requires explicit reconfirmation.

### Cost lifecycle and publication

`BOQV2CostPlan` is versioned as `WORKING`, `PUBLISHED`, or `SUPERSEDED`. Components preserve original estimate, current working estimate and explicit agreed values separately. Forecast uses a valid agreed value when present and otherwise an eligible estimate; missing required cost remains `UNKNOWN`/`NULL`. Actual paid cost is not copied into this model and remains owned by the existing finance ledger.

Offer entry and draft selection do not update Funds. Publish locks the project budget source and cost plan, checks expected plan and baseline versions, records actor/reason/effective time/audit, confirms the selections, emits approved price observations, and updates the V2 source fingerprint atomically. The Phase 0 public compatibility projection remains unchanged until the planned Phase 5 consumer cutover.

### Price Database

The catalog stores canonical code/name/specification/unit/category/tags/status with versioned current reference prices for material/labor sell/cost dimensions. Search covers code, name, specification, unit and category and supports category/status filtering plus pagination.

Promotion, catalog edits and reference updates are explicit Owner actions. Reuse copies values and catalog lineage into a draft snapshot; later catalog or draft edits do not cascade in either direction. Archived items retain their price and observation history.

Immutable observations are emitted only by approved business events: quotation issue/acceptance, vendor offer/selection and cost-plan publication. `event_key` prevents duplicate event rows; `sample_key` plus lineage root prevents revisions/copies of the same commercial event from inflating the distinct-sample count.

### Vendor-safe exports

Issued-snapshot-scoped RFQ and selected-vendor artifacts support XLSX and PDF. RFQ values are blank. Selected-vendor output requires a published confirmed selection and includes only that vendor's safe normalized values. Frozen audience payloads make retry/download reproducible and exclude customer sell values and competitor pricing.

### Authorization

- Admin/Owner: read vendors, offers, selections, plans and catalog/history.
- Owner only: create vendors/offers, select/reconfirm, edit/publish cost plans, promote/edit catalog/reference data and reuse into drafts.
- Export generation continues to use the existing Admin artifact authorization boundary, snapshot scope checks and private storage path.
- Evidence is metadata-only in Phase 4; no new public blob URL or attachment download route was introduced.

## Schema and API

Migration `20260917_0003` adds seven tables:

- `boq_v2_vendors`
- `boq_v2_vendor_offers`
- `boq_v2_vendor_offer_lines`
- `boq_v2_cost_selections`
- `boq_v2_catalog_items`
- `boq_v2_catalog_price_versions`
- `boq_v2_price_observations`

It also adds catalog lineage to scope nodes, cost-plan version/publication fields, original/agreed component values, and frozen vendor-audience export fields. The migration is additive and performs no business-data backfill.

The OpenAPI document exposes 13 Phase 4 paths covering project vendors/offers, selections, working/published cost plans, catalog search/detail/promotion/update/reference pricing/reuse, plus the extended snapshot export endpoint from Phase 3.

## Frontend

- BOQ workspace: collapsible internal vendor-cost panel, explicit offer comparison, warnings/reasons, selection, working/publish controls, promotion/reuse, and RFQ/selected-vendor export.
- Price Database: searchable/paginated master list, versioned reference prices, event/project/date provenance, distinct sample count, archive visibility and Owner-only explicit updates.
- Admin sees the internal data read-only; Owner mutation controls use the existing role contract.

## Evidence and review notes

Detailed command/results evidence is in [phase4-validation.md](evidence/phase4-validation.md). Representative desktop screenshots were captured through the local browser QA connector and returned with the Phase 4 handoff; the connector exposed them as evidence blocks rather than repository files.

Google Stitch could not be queried because its authentication was unavailable. The implementation therefore followed the checked-in `Design/DESIGN.md`, existing BOQ workspace primitives and established frontend tokens. This is the only design-source deviation.

Phase 4 stops here. Phase 5 sync retirement and consumer cutover remain intentionally untouched.
