---
name: flowaccount-integration
description: Use when Codex needs to plan, implement, review, or debug Projects-001 integration with FlowAccount/OpenAPI, including OAuth client-credentials auth, expenses, expense attachments, expense payments, Supplier Invoice/input VAT handling, accounting readiness, idempotent sync, retries, or Approval page FlowAccount status UI.
---

# FlowAccount Integration

## Operating Rules

- Keep FlowAccount secrets out of committed files, docs, skills, tests, logs, screenshots, and final answers.
- Treat FlowAccount as backend-owned. Frontend code may show readiness/status and collect Owner choices, but it must not call FlowAccount directly or hold API credentials.
- Respect repository instructions. If backend edits are disallowed by the active prompt, get explicit approval before editing `Projects-001-BE/`.
- Start with the sandbox base URL. Move to production only after sandbox sync, attachment, Supplier Invoice, payment, retry, and duplicate-click cases are verified.
- Before implementing API payloads, verify the current official docs if exact endpoint fields or enum values matter. Use `references/flowaccount-api.md` as the local quick reference.

## Quick Workflow

1. Read the current implementation around input requests, Approval actions, receipt storage, request statuses, and payment state.
2. Read [references/flowaccount-api.md](references/flowaccount-api.md) before writing FlowAccount request payloads, readiness checks, or payment logic.
3. Confirm required config exists or add safe placeholders to env examples only.
4. Implement backend first: service client, token caching, mapping, readiness, persistence, idempotency, endpoints, and safe error normalization.
5. Implement frontend after backend contracts are stable: status section, missing fields, action buttons, retry affordances, and Owner/Admin permissions.
6. Verify with lint/build and focused sandbox/manual flows. Do not mark internal requests `PAID` until FlowAccount payment sync succeeds when integration is enabled.

## Project Policy

Use this Phase 1 policy unless the user changes it:

- Sync only `EXPENSE` input requests to FlowAccount.
- Owner approval inside Projects-001 is separate from FlowAccount sync.
- Create a FlowAccount Expense first, attach the receipt, then create Supplier Invoice/input VAT data when VAT tax filing fields are ready, then sync payment on Mark Paid.
- Default payment method is transfer and requires a configured FlowAccount `bankAccountId`.
- `approved_amount` is whatever appears on the receipt.
- Labor `approved_amount` is the net amount actually paid to the subcontractor.
- Labor uses 3% withholding tax. Material, advance payment, and general expense do not use WHT by default.
- Preserve OCR line items when available; fall back to a single configured item only when line items are absent or unusable.
- Allow Owner to link an existing manually created FlowAccount document instead of creating a duplicate.

## Backend Shape

Prefer a small integration boundary:

- `flowaccount_service.py`: token retrieval/cache, HTTP client, create expense, attach receipt, create supplier invoice, create expense payment, get categories/channels helpers, error normalization.
- mapping/config module: request type to FlowAccount expense category/accounting ids, VAT defaults, WHT defaults, payment channel defaults.
- persistence: prefer a separate `flowaccount_syncs` table if the lifecycle grows; otherwise add narrowly scoped fields to `input_requests`.
- endpoints under the existing input/admin router, e.g. readiness, sync, retry attachment, link existing document, supplier invoice sync/retry, and mark paid/payment retry.

Store enough sync state to be idempotent:

- local request id
- FlowAccount `recordId`/`documentId`
- FlowAccount `documentSerial`
- `externalDocumentId`
- expense sync status/error/timestamp
- attachment status/error/timestamp
- supplier invoice status/error/timestamp
- payment status/error/timestamp
- last payload hash or local idempotency marker when useful

## Readiness Rules

Do not enable Sync until backend readiness passes:

- request status is approved
- entry type is `EXPENSE`
- approved amount is positive
- request type exists
- vendor/contact name exists
- document date exists
- receipt storage key exists unless Owner is linking an existing document
- mapping exists for the request type
- no existing FlowAccount document is already linked, unless retrying missing post-create steps

For VAT/Supplier Invoice readiness, require valid tax invoice fields before creating Supplier Invoice/input VAT data. Expense creation may still succeed without Supplier Invoice if the UX clearly shows tax-filing readiness is incomplete.

For payment readiness, require:

- FlowAccount expense id exists
- payment date exists
- payment reference exists
- payment amount exists
- default transfer `bankAccountId` or Owner-selected payment channel exists

## Idempotency And Retry

- Generate `externalDocumentId` from the local request id and environment, e.g. `projects-001:<env>:input-request:<uuid>`.
- Before creating a new FlowAccount Expense, check local sync state. If a FlowAccount id exists, retry only the missing step.
- If a network error happens after create, do not blindly create again. Search/get by saved id if present; otherwise use `externalDocumentId` and manual review before retry if the API cannot guarantee lookup.
- If Expense creation succeeds but attachment/Supplier Invoice/payment fails, save the created document id and mark partial state.
- Normalize FlowAccount errors into user-safe messages while keeping raw diagnostic detail only in protected backend logs.

## Frontend Expectations

Add FlowAccount UI to the Approval workflow only after backend contracts exist:

- Readiness: Ready/Not ready plus missing fields.
- Expense sync status and FlowAccount document number.
- Attachment status.
- Supplier Invoice/input VAT status.
- Payment sync status.
- Last user-safe error.
- Owner-only actions: Sync, Retry, Retry Attachment, Retry Supplier Invoice, Link Existing FlowAccount Document, Mark Paid/Retry Payment.
- Admin remains read-only.

Do not add a Settings UI in Phase 1 unless explicitly requested. Use backend config/env for category and payment mapping.

## Verification

At minimum verify:

- token failure leaves request status unchanged
- missing readiness data disables sync
- happy path creates Expense, attaches receipt, creates Supplier Invoice when VAT-ready, and marks paid only after payment sync
- duplicate click does not create duplicate Expense
- attachment failure produces partial sync and retry works
- payment failure does not mark internal request `PAID`
- manually linked existing document skips duplicate creation
- income requests clearly show FlowAccount sync is not enabled yet

