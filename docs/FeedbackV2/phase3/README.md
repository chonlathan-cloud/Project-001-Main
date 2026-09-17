# Phase 3 — Quotation lifecycle and exports

Status: **implemented locally behind the existing disabled-by-default BOQ V2
feature gates; not released**

Phase 3 implementation baseline: `feature` at
`4d77323102743b90007562b1dafdf4c423114cdb`.

## Delivered scope

- MAIN quotation revisions, mutually exclusive alternatives, and ADD/DEDUCT
  change orders with explicit issue, reject, withdraw, and record-acceptance
  transitions.
- Immutable issue/acceptance snapshots containing calculation policy,
  project/customer document data, scope, sell prices, tax, terms, payment
  schedule, totals, and rendered page metadata.
- Stable `QT-YYYY-NNNNNN` and `CO-YYYY-NNNNNN` document numbers allocated by a
  transactional PostgreSQL sequence table. Revision numbers use an atomic
  per-document counter rather than `count + 1`.
- Exactly one active accepted MAIN revision per project. Replacing an active
  MAIN requires an explicit retain-or-absorb decision for every accepted
  change order. Accepted change orders enter the baseline once.
- DEDUCT change orders pin their accepted target scope and remaining quantity;
  stale, overlapping, or excessive deductions fail closed. Customer sell
  deductions do not silently change internal/vendor cost state.
- Acceptance records preserve actor, agreed date, recorded timestamp, and
  evidence/reference metadata. The action records an internal agreement; it is
  not customer e-signature or a customer portal.
- Pinned preview links load an exact `revision_id` and `snapshot_id`; historical
  views and rerenders never fall forward to the latest mutable revision.
- Real customer XLSX and PDF exports plus internal XLSX exports. Exporters use
  audience-specific allowlists and backend-authoritative frozen snapshot data.
- Private artifact metadata ties the file to project, document, revision,
  snapshot, calculation version, audience, and applicable cost-plan version.
  Downloads use the existing bounded signed-URL infrastructure.
- Responsive quotation lifecycle UI integrated into the native BOQ workspace,
  including immutable/read-only states, lifecycle commands, acceptance and
  rebaseline confirmation, ADD/DEDUCT creation, export status, and historical
  preview.

## State and budget invariants

- DRAFT revisions are mutable. ISSUE freezes a customer document snapshot.
- ISSUED and ACCEPTED revisions are not editable; changes require a new
  revision, alternative, or change order.
- ISSUED but unaccepted quotations do not enter the V2 baseline.
- Accepting a MAIN creates or explicitly replaces the active V2 MAIN baseline.
- Alternatives share a lineage but are mutually exclusive in the active
  baseline. Concurrent acceptance is serialized at the project boundary.
- Accepted ADD/DEDUCT change orders are recorded once against their pinned base
  baseline and snapshot.
- Payment terms remain document terms only; no finance transaction,
  installment, Input, or Approval row is created.
- Legacy operational budget consumers remain on their Phase 1 compatibility
  behavior. Phase 3 records the accepted V2 source contract but does not perform
  the Phase 5 public-consumer cutover or retire legacy sync.

## API additions

All routes are under `/api/v1`, require the existing BOQ V2 feature gate, and
retain project/resource ownership checks.

| Method | Route | Access | Purpose |
| --- | --- | --- | --- |
| `POST` | `/boq/revisions/{revision_id}/preview-snapshots` | Owner | Freeze a preview of the current draft version |
| `GET` | `/boq/revisions/{revision_id}/preview?snapshot_id=...` | Admin/Owner | Load an exact historical snapshot |
| `POST` | `/boq/revisions/{revision_id}/issue` | Owner | Validate and issue an immutable customer snapshot |
| `POST` | `/boq/revisions/{revision_id}/revise` | Owner | Create the next revision in the same lineage |
| `POST` | `/boq/revisions/{revision_id}/alternatives` | Owner | Create an explicitly exclusive alternative |
| `POST` | `/projects/{project_id}/boq/change-orders` | Owner | Create an ADD or DEDUCT change order |
| `POST` | `/boq/revisions/{revision_id}/record-acceptance` | Owner | Record agreement and activate/update the baseline |
| `POST` | `/boq/revisions/{revision_id}/reject` | Owner | Reject an issued revision |
| `POST` | `/boq/revisions/{revision_id}/withdraw` | Owner | Withdraw an issued revision |
| `POST` | `/boq/revisions/{revision_id}/exports` | Admin/Owner | Render a permitted audience/format artifact |
| `GET` | `/boq/revisions/{revision_id}/exports/{artifact_id}` | Admin/Owner | Read artifact status and identity |
| `GET` | `/boq/revisions/{revision_id}/exports/{artifact_id}/download` | Admin/Owner | Authorize a bounded private download |

Mutation requests use `Idempotency-Key` and expected versions where applicable.
Issue performs the authoritative lifecycle validation; there is no second,
divergent validation path in the client.

## Export boundary

Customer exports are constructed from a customer-only snapshot projection.
They never query or serialize cost, margin, vendor pricing, internal notes, or
cost-plan state. Internal XLSX uses its own allowlist and pins the applicable
cost-plan version. Text cells beginning with spreadsheet formula control
characters are escaped, while money and quantity cells remain numeric.

PDF rendering uses ReportLab with the packaged Noto Thai font path and A4 page
rules. XLSX rendering uses OpenPyXL. Both identify the document and revision;
table headers repeat across PDF pages and payment allocation is derived from
the frozen authoritative totals.

## Persistence

Alembic revision `20260917_0002` adds quotation header fields and five Phase 3
tables:

- `boq_v2_document_sequences`
- `boq_v2_revision_snapshots`
- `boq_v2_change_order_deductions`
- `boq_v2_acceptances`
- `boq_v2_export_artifacts`

It also pins MAIN/change-order baseline membership to exact document and
snapshot identities. The migration was verified only against the isolated
loopback PostgreSQL harness; no production database was contacted.

## Scope boundary

Phase 3 does not implement supplier offers, vendor selection, a price catalog,
imports, e-signature, customer/vendor portals, automatic email/LINE delivery,
automatic finance records, legacy sync retirement, deployment, IAM changes, or
production data changes.

See [validation evidence](evidence/phase3-validation.md) and the representative
captures:

- [Accepted lifecycle workspace](evidence/screenshots/accepted-lifecycle.png)
- [Pinned historical preview](evidence/screenshots/pinned-preview.png)
- [Admin read-only state](evidence/screenshots/admin-readonly.png)
- [Responsive API error state](evidence/screenshots/api-error-responsive.png)
