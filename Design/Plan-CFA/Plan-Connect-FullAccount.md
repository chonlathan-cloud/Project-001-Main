**Objective**
ลด human error จากการที่ Owner/Admin ต้องดูข้อมูลในหน้า Approval แล้วไปสร้างเอกสารเองใน FlowAccount โดยเปลี่ยนให้ระบบสร้างเอกสารค่าใช้จ่าย, แนบ receipt, และบันทึกการจ่ายเงินผ่าน FlowAccount API แบบมีสถานะ sync ชัดเจน

**Assumption**
- ใช้ FlowAccount Sandbox ก่อน เมื่อระบบ test สเถียร ค่อยขยับไปใน production
- บริษัทจด VAT
- Phase แรกใช้เฉพาะ `Expenses`, `Expense Attachment`, `Expense Payment`
- `Approve` = อนุมัติในระบบเท่านั้น
- `Sync to FlowAccount` = สร้างเอกสารใน FlowAccount
- `Mark Paid` = ต้องมี `payment_reference` และ sync payment เข้า FlowAccount
- ค่าแรงมี WHT 3%
- ค่าวัสดุ / ค่าเบิกล่วงหน้า ไม่มี WHT
- ยังไม่ใช้ Contacts API ใน phase แรก แต่ส่งข้อมูล vendor/contact เข้า expense document ตรง ๆ # อาจจะเปลียนใช้ Contacts api เนืองจากข้อมูล เพียงพอ และจะได้เป็นระบบด้วย

**Target Flow**
```text
Input Request submitted
-> Owner review/edit in Approval
-> Owner Approve
-> System checks accounting readiness
-> Owner clicks Sync to FlowAccount
-> Backend creates FlowAccount Expense
-> Backend attaches receipt
-> System saves FlowAccount document id/no/status
-> Owner enters payment_reference
-> Owner clicks Mark Paid
-> Backend sends Expense Payment to FlowAccount
-> System marks request PAID
```

**Phase 1: Backend Integration Foundation**
1. เพิ่ม FlowAccount config ใน backend env
```text
FLOWACCOUNT_BASE_URL=https://openapi.flowaccount.com/test
FLOWACCOUNT_CLIENT_ID=...
FLOWACCOUNT_CLIENT_SECRET=...
FLOWACCOUNT_SCOPE=flowaccount-api
FLOWACCOUNT_TOKEN_CACHE_SECONDS=84000
```

2. สร้าง service กลาง เช่น `flowaccount_service.py`
- `get_access_token()`
- `create_expense(input_request)`
- `attach_expense_receipt(flowaccount_expense_id, receipt_file)`
- `create_expense_payment(flowaccount_expense_id, payment_payload)`
- normalize error จาก FlowAccount
- timeout/retry แบบ conservative

3. Token handling
- ขอ token ด้วย `POST /token`
- cache token จนใกล้หมดอายุ
- ถ้า token fail ต้องไม่เปลี่ยนสถานะ request
- เก็บ error message สำหรับแสดงหน้า Approval

**Phase 2: Data Model**
เพิ่ม fields ใน `input_requests` หรือ table แยก `flowaccount_syncs`

แนะนำ fields:
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

สถานะที่ควรมี:
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
เริ่มจาก config ง่ายก่อน ยังไม่ต้องทำ Settings UI ทันที

```text
ค่าวัสดุ
-> item_name: ค่าวัสดุ
-> VAT: default 7% ถ้ามีใบกำกับภาษี
-> WHT: 0%
-> document: Expense

ค่าแรง
-> item_name: ค่าแรงผู้รับเหมา
-> VAT: ตามเอกสาร vendor
-> WHT: 3%
-> required: tax id, vendor name, address/branch ถ้ามี
-> document: Expense + WHT fields

ค่าเบิกล่วงหน้า
-> item_name: เงินเบิกล่วงหน้า
-> VAT: 0%
-> WHT: 0%
-> document: Expense
-> note: ควร tag เป็น advance เพื่อแยกจาก cost จริงใน reporting

ค่าใช้จ่ายทั่วไป
-> item_name: ค่าใช้จ่ายทั่วไป
-> VAT: default 7% ถ้ามีใบกำกับภาษี
-> WHT: 0%
-> document: Expense
```

เพิ่ม field ที่ควรให้ Owner confirm ก่อน sync:
```text
vat_mode: no_vat | vat_inclusive | vat_exclusive
wht_rate
expense_category
```

**Phase 4: Accounting Readiness Check**
ก่อนกด `Sync to FlowAccount` backend ต้อง validate:

Required ทุก request:
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

Required สำหรับ VAT/WHT:
```text
ถ้า VAT -> ต้องมี tax invoice/receipt info เท่าที่ระบบเก็บได้
ถ้า ค่าแรง/WHT 3% -> ต้องมี vendor tax id, vendor name, address/branch
```

Required ก่อน Mark Paid:
```text
flowaccount_sync_status = SYNCED หรือ PARTIAL_SYNC ที่ expense created แล้ว
payment_reference exists
payment date exists
payment amount exists
company payment channel selected
```

**Phase 5: API Endpoints ในระบบเรา**
เพิ่ม backend endpoints สำหรับ frontend:

```text
GET  /api/v1/input/admin/requests/{id}/accounting-readiness
POST /api/v1/input/admin/requests/{id}/sync-flowaccount
POST /api/v1/input/admin/requests/{id}/retry-flowaccount-attachment
POST /api/v1/input/admin/requests/{id}/mark-paid
```

`mark-paid` เดิมควรเปลี่ยน logic:
- ถ้าเปิด FlowAccount integration: sync payment สำเร็จก่อนค่อย set `PAID`
- ถ้า payment fail: ยังไม่ set `PAID`, เก็บ `PAYMENT_FAILED`

**Phase 6: Frontend Approval Page**
เพิ่ม section ใหม่ในหน้า Approval:

```text
Accounting / FlowAccount
- Readiness: Ready / Not ready
- Missing fields list
- FlowAccount sync status
- FlowAccount document no
- Attachment status
- Payment sync status
- Last error
```

เพิ่มปุ่ม:
```text
Approve
Sync to FlowAccount
Retry Sync
Retry Attachment
Mark Paid
```

Rules:
- Admin read-only เหมือนเดิม
- Owner เท่านั้นที่ sync/pay ได้
- `Sync to FlowAccount` enabled เฉพาะ `APPROVED + READY`
- `Mark Paid` enabled เฉพาะสร้าง FlowAccount Expense แล้ว และมี payment reference

**Scenarios**

1. Happy Path
```text
Subcontractor submit receipt
Owner review/edit
Owner approve
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
Owner approve
Readiness check finds missing tax id/address/vendor info
Sync button disabled
UI shows missing fields
Owner edits and saves
Readiness reruns
Sync becomes available
```

3. Duplicate Receipt
```text
Request has duplicate flag
Owner can approve, but sync requires explicit confirm
UI shows duplicate reason
Backend records override reason/audit event
Then sync proceeds
```

4. OCR Low Confidence
```text
OCR marks amount/date/vendor low confidence
Owner must edit or confirm reviewed
System stores confirmation
Sync allowed only after review confirmation
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
UI shows document no + attachment failed
Owner can retry attachment without creating duplicate expense
```

7. Duplicate Sync Click / Retry
```text
Owner clicks sync twice or retry after network issue
Backend checks existing flowaccount_expense_id/external_document_id
If already created, do not create new expense
Retry only missing step
```

8. Payment Reference Missing
```text
Owner clicks Mark Paid without payment_reference
Frontend/backend block action
UI says payment reference required
No FlowAccount payment call
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

10. ค่าแรง Withholding Tax
```text
request_type = ค่าแรง
Backend applies WHT 3%
Requires vendor tax id/name/address
Creates Expense with WHT fields
Payment amount should reflect payable amount after WHT policy
```

11. ค่าเบิกล่วงหน้า
```text
request_type = ค่าเบิกล่วงหน้า
VAT = 0
WHT = 0
Create Expense tagged/named as advance payment
Report should distinguish advance from normal actual cost
```

12. รายรับ `INCOME`
```text
Phase แรกยังไม่ sync FlowAccount
Approval can remain internal only
UI should show "FlowAccount sync not enabled for income yet"
Later choose Tax Invoice / Receipt / Cash Invoice policy
```

**Implementation Order**
1. Add FlowAccount env + backend service
2. Add DB fields/migration
3. Add mapping config
4. Add readiness endpoint
5. Add sync expense endpoint
6. Add attachment retry
7. Update mark-paid to require FlowAccount payment sync
8. Update Approval UI
9. Test with Sandbox happy path
10. Test failure/retry/idempotency cases

**Definition of Done**
- Owner can approve request without creating FlowAccount doc
- Owner can see whether request is ready for FlowAccount
- Owner can create FlowAccount Expense from Approved request
- Receipt is attached to FlowAccount document
- FlowAccount document id/no is saved and shown
- Mark Paid requires payment reference
- PAID status happens only after payment sync succeeds
- Retry does not create duplicate FlowAccount documents
- All FlowAccount errors are visible enough for admin/owner to fix data and retry