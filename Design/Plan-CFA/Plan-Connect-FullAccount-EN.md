**Objective**

Reduce human error caused by Owner/Admin users reviewing data in the Approval page and manually recreating the same accounting records in FlowAccount. The integration will let the system create expense documents, attach receipts, and record payments through the FlowAccount API while exposing clear sync statuses in the application.

**Assumptions**

- Start with the FlowAccount Sandbox. Move to Production only after the sandbox flow is stable.
- The company is VAT registered.
- Phase 1 uses only `Expenses`, `Expense Attachment`, and `Expense Payment`.
- `Approve` means approving the request inside Projects-001 only.
- `Sync to FlowAccount` means creating the accounting document in FlowAccount.
- `Mark Paid` requires a `payment_reference` and must sync payment data to FlowAccount.
- Labor payments require 3% withholding tax (WHT).
- Material cost and advance payment requests do not require WHT.
- Phase 1 will not use the Contacts API yet. Vendor/contact fields will be sent directly into the FlowAccount expense document.
- Contacts API can be considered later because the system already stores vendor name, tax ID, branch, address, phone, email, and bank account data.

**Target Flow**

```text
Input Request submitted
-> Owner reviews/edits in Approval
-> Owner approves
-> System checks accounting readiness
-> Owner clicks Sync to FlowAccount
-> Backend creates FlowAccount Expense
-> Backend attaches receipt
-> System saves FlowAccount document ID/number/status
-> Owner enters payment_reference
-> Owner clicks Mark Paid
-> Backend sends Expense Payment to FlowAccount
-> System marks request PAID
```

**Phase 1: Backend Integration Foundation**

1. Add FlowAccount configuration to backend environment variables.

```text
FLOWACCOUNT_BASE_URL=https://openapi.flowaccount.com/test
FLOWACCOUNT_CLIENT_ID=...
FLOWACCOUNT_CLIENT_SECRET=...
FLOWACCOUNT_SCOPE=flowaccount-api
FLOWACCOUNT_TOKEN_CACHE_SECONDS=84000
```

2. Create a central backend service, for example `flowaccount_service.py`.

- `get_access_token()`
- `create_expense(input_request)`
- `attach_expense_receipt(flowaccount_expense_id, receipt_file)`
- `create_expense_payment(flowaccount_expense_id, payment_payload)`
- Normalize FlowAccount errors into safe internal error messages.
- Use conservative timeouts and retry behavior.

3. Token handling.

- Request tokens through `POST /token`.
- Cache the token until it is close to expiry.
- If token retrieval fails, do not change the request status.
- Store the error message so the Approval page can show it to the Owner/Admin.

**Phase 2: Data Model**

Add fields to `input_requests`, or create a separate `flowaccount_syncs` table if the sync lifecycle should be isolated from request data.

Recommended fields:

```text
flowaccount_sync_status
flowaccount_expense_id
flowaccount_document_no
flowaccount_synced_at
flowaccount_sync_error
flowaccount_attachment_status
flowaccount_attachment_error
flowaccount_payment_status
flowaccount_payment_synced_at
flowaccount_payment_error
external_document_id
accounting_ready
accounting_readiness_errors
```

Recommended statuses:

```text
NOT_READY
READY
SYNCING
SYNCED
PARTIAL_SYNC
FAILED
PAYMENT_SYNCED
PAYMENT_FAILED
```

**Phase 3: Expense Mapping**

Start with a simple backend config. Do not build a Settings UI immediately.

```text
ค่าวัสดุ / Material Cost
-> item_name: ค่าวัสดุ
-> VAT: default 7% if the document is a tax invoice
-> WHT: 0%
-> document: Expense

ค่าแรง / Labor
-> item_name: ค่าแรงผู้รับเหมา
-> VAT: based on the vendor document
-> WHT: 3%
-> required: tax ID, vendor name, address/branch if available
-> document: Expense + WHT fields

ค่าเบิกล่วงหน้า / Advance Payment
-> item_name: เงินเบิกล่วงหน้า
-> VAT: 0%
-> WHT: 0%
-> document: Expense
-> note: tag as advance payment so reports can distinguish it from actual project cost

ค่าใช้จ่ายทั่วไป / General Expense
-> item_name: ค่าใช้จ่ายทั่วไป
-> VAT: default 7% if the document is a tax invoice
-> WHT: 0%
-> document: Expense
```

Fields that should be confirmed by the Owner before syncing:

```text
vat_mode: no_vat | vat_inclusive | vat_exclusive
wht_rate
expense_category
```

**Phase 4: Accounting Readiness Check**

Before enabling `Sync to FlowAccount`, the backend must validate the request.

Required for every request:

```text
status = APPROVED
entry_type = EXPENSE
approved_amount > 0
request_type exists
vendor_name exists
document_date exists
receipt_storage_key exists
external_document_id not already synced
```

Required for VAT/WHT cases:

```text
If VAT applies -> require the available tax invoice/receipt fields.
If request_type = ค่าแรง / Labor with 3% WHT -> require vendor tax ID, vendor name, and address/branch.
```

Required before Mark Paid:

```text
flowaccount_sync_status = SYNCED, or PARTIAL_SYNC with an already-created FlowAccount expense
payment_reference exists
payment date exists
payment amount exists
company payment channel selected
```

**Phase 5: Internal API Endpoints**

Add backend endpoints for the frontend Approval page.

```text
GET  /api/v1/input/admin/requests/{id}/accounting-readiness
POST /api/v1/input/admin/requests/{id}/sync-flowaccount
POST /api/v1/input/admin/requests/{id}/retry-flowaccount-attachment
POST /api/v1/input/admin/requests/{id}/mark-paid
```

Update the existing `mark-paid` behavior:

- If FlowAccount integration is enabled, set `PAID` only after FlowAccount payment sync succeeds.
- If payment sync fails, do not set `PAID`; store `PAYMENT_FAILED`.

**Phase 6: Frontend Approval Page**

Add a new section to the Approval page:

```text
Accounting / FlowAccount
- Readiness: Ready / Not ready
- Missing fields list
- FlowAccount sync status
- FlowAccount document number
- Attachment status
- Payment sync status
- Last error
```

Add action buttons:

```text
Approve
Sync to FlowAccount
Retry Sync
Retry Attachment
Mark Paid
```

Rules:

- Admin remains read-only.
- Only Owner can sync or mark paid.
- `Sync to FlowAccount` is enabled only for `APPROVED + READY`.
- `Mark Paid` is enabled only after a FlowAccount Expense has been created and a payment reference exists.

**Scenarios**

1. Happy Path

```text
Subcontractor submits receipt
Owner reviews/edits
Owner approves
System status = APPROVED
Readiness = READY
Owner clicks Sync to FlowAccount
Backend creates Expense
Backend attaches receipt
System status = SYNCED
Owner fills payment_reference
Owner clicks Mark Paid
Backend syncs payment
System status = PAID + PAYMENT_SYNCED
```

2. Missing Vendor Data

```text
Owner approves
Readiness check finds missing tax ID/address/vendor info
Sync button is disabled
UI shows missing fields
Owner edits and saves
Readiness reruns
Sync becomes available
```

3. Duplicate Receipt

```text
Request has duplicate flag
Owner can approve, but sync requires explicit confirmation
UI shows duplicate reason
Backend records override reason/audit event
Sync proceeds
```

4. OCR Low Confidence

```text
OCR marks amount/date/vendor as low confidence
Owner must edit or confirm reviewed
System stores confirmation
Sync is allowed only after review confirmation
```

5. FlowAccount Token Failure

```text
Owner clicks sync
Token request fails
No Expense is created
Request remains APPROVED
flowaccount_sync_status = FAILED
UI shows error
Owner can retry
```

6. Expense Created but Attachment Failed

```text
Backend creates FlowAccount Expense successfully
Receipt attachment fails
flowaccount_sync_status = PARTIAL_SYNC
flowaccount_expense_id is saved
UI shows document number + attachment failed
Owner can retry attachment without creating a duplicate expense
```

7. Duplicate Sync Click / Retry

```text
Owner clicks sync twice or retries after a network issue
Backend checks existing flowaccount_expense_id/external_document_id
If already created, do not create a new expense
Retry only the missing step
```

8. Payment Reference Missing

```text
Owner clicks Mark Paid without payment_reference
Frontend/backend block the action
UI says payment reference is required
No FlowAccount payment call is made
Request remains APPROVED
```

9. Payment Sync Failure

```text
Expense already synced
Owner clicks Mark Paid
FlowAccount payment API fails
Request remains APPROVED
flowaccount_payment_status = PAYMENT_FAILED
UI shows retry payment
```

10. Labor Withholding Tax

```text
request_type = ค่าแรง / Labor
Backend applies WHT 3%
Requires vendor tax ID/name/address
Creates Expense with WHT fields
Payment amount should reflect payable amount after WHT policy
```

11. Advance Payment

```text
request_type = ค่าเบิกล่วงหน้า / Advance Payment
VAT = 0
WHT = 0
Create Expense tagged/named as advance payment
Reports should distinguish advance payments from normal actual cost
```

12. Income Requests

```text
Phase 1 does not sync INCOME requests to FlowAccount
Approval can remain internal only
UI should show "FlowAccount sync not enabled for income yet"
Later, choose a Tax Invoice / Receipt / Cash Invoice policy
```

**Implementation Order**

1. Add FlowAccount environment variables and backend service.
2. Add DB fields/migration.
3. Add mapping config.
4. Add readiness endpoint.
5. Add sync expense endpoint.
6. Add attachment retry endpoint.
7. Update `mark-paid` to require successful FlowAccount payment sync.
8. Update Approval UI.
9. Test the Sandbox happy path.
10. Test failure, retry, and idempotency cases.

**Definition of Done**

- Owner can approve a request without creating a FlowAccount document.
- Owner can see whether a request is ready for FlowAccount.
- Owner can create a FlowAccount Expense from an approved request.
- Receipt is attached to the FlowAccount document.
- FlowAccount document ID/number is saved and shown.
- Mark Paid requires a payment reference.
- `PAID` status happens only after payment sync succeeds.
- Retry does not create duplicate FlowAccount documents.
- All FlowAccount errors are visible enough for Owner/Admin users to fix the data and retry.
