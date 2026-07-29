# Backend Finance and Document read contracts v1

Status: Phase 3 repository implementation complete; not deployed.

The Product Backend remains authoritative for finance calculations, payment
state, document classification and project authorization. The MCP service never
queries Cloud SQL, Firestore, GCS or FlowAccount directly for these tools.

## Routes

All paths have the `/api/v1/internal/mcp` prefix, accept only `POST`, require the
environment-specific MCP Google service identity, and re-resolve Product access
from the verified OAuth subject on every call.

| Route | Purpose |
|---|---|
| `/finance/projects:summary` | Exact authorized project budget, actual, paid, remaining, unpaid, pending and income amounts |
| `/finance/records:search` | Bounded search over input requests, payments, installments and transactions |
| `/payments:get` | One minimized payment record without bank or storage fields |
| `/payments/document-status:get` | Receipt, confirmation and accounting/FlowAccount readiness status only |
| `/documents:search` | Unified authorized receipt, confirmation, inspection and daily-report metadata search |
| `/documents/metadata:get` | Safe metadata for one opaque document ID and optional version |
| `/documents/content:read` | Bounded existing extraction returned as untrusted document data |
| `/daily-reports/share-status:get` | Share configuration state without token, link or token-version material |

The existing `/search` and `/fetch` contracts also route stable
`finance_payments:*` and `gcs_files:document:*` references through these same
Backend policies.

## Finance semantics

- Canonical money is always `{ "amount": "1234.50", "currency": "THB" }`.
  Binary floating-point values are not used in a finance response.
- Budget is the root-level Customer BOQ total, current when `as_of` is absent or
  selected by SCD2 validity when it is present.
- Actual is approved expense input, using approved amount when present and
  requested amount otherwise.
- Paid is the sum of Product payment records joined to the authorized project.
- Remaining is `budget - actual`; approved unpaid is `actual - paid`.
- Pending requested includes Draft and Pending Admin expenses. Approved income
  is reported separately and is not netted silently into expense actuals.
- Search is capped, date ranges cannot exceed 366 days, and cursors are signed
  and bound to the normalized filters.
- Payment results omit account number, bank transfer reference, storage prefix,
  receipt path, signed URL and FlowAccount credentials/IDs.
- FlowAccount fields are readiness and sync status metadata only. MCP never
  starts a sync, uploads an attachment or calls FlowAccount.

## Document Gateway semantics

- Clients receive opaque document IDs and Product citation URLs, never GCS
  bucket/object identifiers or signed download URLs.
- Metadata search includes only records already visible in Product scope.
  Financial receipts and payment confirmations additionally require
  `financial_data_read` for Admin callers.
- Document body reads require `sensitive_documents_read` for Admin callers and
  fail closed when `external_ai_blocked` is true.
- The initial content adapter returns only an existing, canonical receipt
  extraction. It never downloads arbitrary object bytes and never starts OCR.
  Other supported-but-unprocessed documents return a successful metadata result
  with `content_status=unprocessed` and a safe reason.
- Allowed MIME types are PDF, approved image types, plain text and CSV. Other
  types return `unsupported`.
- Default limits are 10 MiB, 50 pages and 20,000 characters. Environment
  variables may lower these values; the Backend schema caps bytes at 50 MiB.
  Oversized files/extractions return `too_large` without body content.
- Credential-shaped strings are redacted. Instruction-like document text is
  labeled `untrusted_document_data`, carries a prompt-injection indicator, and
  is never interpreted as policy or instructions.
- The MCP runtime emits a mandatory audit-start event before sensitive content
  access. If that audit write is unavailable, it does not call the Backend.

## Share-status boundary

Daily Report document versions and public-share state are separate entities.
The status contract returns only `not_configured`, `disabled`,
`rollout_disabled` or `active`, plus safe timestamps and booleans. It does not
return a share token, share link or token version.

## Backend configuration and migration

Phase 3 adds these fail-closed bounded-read settings:

| Variable | Default |
|---|---:|
| `MCP_DOCUMENT_MAX_BYTES` | `10485760` |
| `MCP_DOCUMENT_MAX_PAGES` | `50` |
| `MCP_DOCUMENT_MAX_CHARS` | `20000` |
| `MCP_DOCUMENT_SCAN_LIMIT` | `250` |

Run `scripts/migrations/20260729_mcp_document_gateway.sql` before deploying the
Backend revision. It adds `input_requests.external_ai_blocked` as non-null and
defaults existing records to `false`. Owners can then classify individual
receipt records through the existing protected Input Request update flow.

Repository completion does not authorize a cloud change. A Demo deployment
must apply the migration, deploy Backend before MCP, keep the Owner-only rollout
unless Admin is separately approved, and rerun the Phase 3 security/evaluator
gates against live sanitized records.
