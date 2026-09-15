# CDR-003 — Permissions, concurrency, and idempotency

Status: **LOCKED**
Scope: BOQ V2 internal commands and future routes

## Authorization matrix

| Capability | Owner | Admin | Customer | Subcontractor/vendor |
| --- | --- | --- | --- | --- |
| Internal BOQ, cost, library, price history read | Yes | Read-only | No | No |
| Draft/cost/offer edits | Yes | No | No | No |
| Issue/revise/alternative/change-order commands | Yes | No | No | No |
| Record acceptance / activate baseline | Yes | No | No | No |
| Internal export | Yes | Read-only when explicitly allowed by existing admin read policy | No | No |
| Customer export | Yes | Read-only when explicitly allowed | Only through an explicitly authorized existing customer surface in a later phase | No |
| RFQ/selected-vendor export | Yes | Read-only when explicitly allowed | No | Only a future audience-allowlisted private artifact |
| Funds mutation | Yes | No | No | No |

Project access is checked server-side on every node, offer, acceptance, baseline,
and artifact lookup. IDs alone do not grant access. Existing customer,
subcontractor, settings, reports, and explicit Admin access-management guards are
preserved; this matrix does not make unrelated application actions owner-only.

Private artifacts/evidence require authorization at download time and must use
audience-specific DTO allowlists. Customer output cannot contain internal costs,
vendor identities/offers, margins, internal notes, or price provenance. Vendor
output cannot contain customer prices or competing offers.

## Optimistic concurrency

- Mutable aggregates expose an integer `version`/ETag derived from persisted
  state, not a client timestamp.
- Every edit/reorder/lifecycle request supplies the version it read.
- Stale writes fail with a stable conflict response and current version; they are
  not silently rebased.
- Issue serializes with save; alternative acceptance serializes within the
  project; baseline activation serializes with cost-plan publication and Funds
  outward allocation.
- One summary read must come from one coherent baseline/cost-plan version even
  when a concurrent publication occurs.

## Lock order

All paths that can affect an operational budget acquire locks in this order:

1. Stable project-budget advisory lock keyed by project UUID; multiple projects
   are sorted by UUID before locking.
2. Active baseline row.
3. Published cost-plan row.
4. `FundBucket` row(s), sorted by project UUID.
5. Ledger/idempotency rows required by the command.

Do not introduce a path with a different order. Database uniqueness remains the
last defense for one active baseline and one accepted alternative.

## Idempotency

Every retryable mutation has a caller-supplied idempotency key and a persisted
record containing:

- actor/principal identity;
- project ID;
- command type;
- idempotency key;
- canonical request hash;
- aggregate/result identity and response reference;
- final state and timestamps.

The uniqueness boundary is `(actor, project_id, command_type, idempotency_key)`.
The same key and same request returns the prior result. The same key with a
different request hash fails with a stable conflict. A retry must not duplicate
revisions, acceptance, CO membership, offer selection, audit events, artifacts,
or Funds ledger entries.

## Transaction and audit boundary

Domain transition, calculated totals, aggregate version, baseline/cost-plan
membership, and audit event commit in one transaction. Artifact rendering occurs
after that commit from the immutable snapshot; render failure is retryable and
does not roll back acceptance.

Audit records contain actor, command, entity IDs, before/after state references,
calculation version, and timestamp. Logs and audit payloads must not contain raw
credentials, private documents, or unrestricted customer/vendor payloads.
