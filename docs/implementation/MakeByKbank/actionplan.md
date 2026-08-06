# Project Fund Allocation — Action Plan

> แผนพัฒนาฟีเจอร์จัดสรรเงินระหว่าง Project Buckets ซึ่งได้รับแรงบันดาลใจจากแนวคิด Envelope/Bucket Budgeting ของ MAKE by KBank โดยเป็นการออกแบบสำหรับ Projects-001 และไม่ได้คัดลอกแบรนด์หรือหน้าจอของ MAKE by KBank

| รายการ | ค่า |
|---|---|
| สถานะเอกสาร | Proposed planning baseline — implementation not started |
| วันที่จัดทำ | 2026-08-06 |
| Product scope | Project Fund Buckets, Company Operations, Fund Allocation Ledger |
| ผู้มีสิทธิ์จัดสรรเงิน | `owner` เท่านั้น |
| ผู้มีสิทธิ์อ่าน | `owner`, `admin` ตาม project visibility ปัจจุบัน |
| ลักษณะรายการ | Virtual allocation ภายในระบบ ไม่ใช่ bank transfer |
| Rollout target | Local/Demo → Beta → Production decision |

## 1. วัตถุประสงค์

สร้างวิธีจัดการเงินใน Projects-001 ให้ผู้ใช้เข้าใจว่าแต่ละ Project เป็นเสมือน “Bucket” และสามารถจัดสรรเงินระหว่าง Bucket ได้ โดยมี `Company Operations` เป็น Bucket เริ่มต้นสำหรับค่าใช้จ่ายส่วนกลางของบริษัท

ฟีเจอร์ต้องทำให้ Owner:

1. เห็นความแตกต่างระหว่างกำไรโดยประมาณกับเงินที่จัดสรรได้จริง
2. จัดสรรเงินจาก Project หนึ่งไปยัง `Company Operations` หรือ Project อื่นได้ด้วยตนเอง
3. ตรวจยอดก่อน–หลังยืนยันรายการ
4. ตรวจสอบประวัติและผู้ทำรายการย้อนหลังได้
5. แก้ไขข้อผิดพลาดด้วยรายการ Reverse โดยไม่ลบประวัติเดิม

## 2. Current-State Baseline

### 2.1 สิ่งที่มีอยู่แล้ว

- Project Detail แสดง `Total Variance` จากผลต่าง Customer BOQ และ Subcontractor BOQ
- ระบบมี Input Request ประเภท `INCOME` และ `EXPENSE` พร้อมสถานะ `PENDING_ADMIN`, `APPROVED` และ `PAID`
- หน้า Project Detail มีภาพรวมรายรับ–รายจ่ายของแต่ละ Project จาก Input Request
- มี Project ชื่อ `โครงการบริษัท` ชนิด `INTERNAL` และ UUID คงที่จาก migration เดิม
- Owner มีสิทธิ์ mutation ส่วน Admin เป็น read-only ตาม authorization model ปัจจุบัน

### 2.2 ปัญหาปัจจุบัน

- `Total Variance` ดูคล้ายกำไร แต่ไม่ใช่เงินสดที่รับแล้ว
- ยังไม่มีตัวเลข `Available to Allocate`
- ยังไม่มี ledger สำหรับการย้ายยอดระหว่าง Project
- `โครงการบริษัท` ถูกตรวจด้วยชื่อและ `project_type` ซึ่งเปราะบางหากมีการเปลี่ยนชื่อ
- ยังไม่มีระบบป้องกัน double submit, concurrent allocation หรือการแก้ประวัติย้อนหลัง

### 2.3 แนวทาง migration

ไม่สร้าง Operations Project ซ้ำ ให้ยกระดับ `โครงการบริษัท` ที่มีอยู่แล้วเป็น Default Operations Project และรักษา UUID เดิมเพื่อไม่ทำลาย Input Requests/ความสัมพันธ์ปัจจุบัน

## 3. Product Decision Register

Decision ต่อไปนี้เป็น baseline สำหรับ V1 หากต้องเปลี่ยนระหว่าง implementation ให้บันทึกเหตุผลในเอกสารหรือ ADR ก่อน

| ID | ข้อสรุป |
|---|---|
| D-01 | Project แต่ละรายการมี Fund Bucket หนึ่ง Bucket แบบ 1:1 |
| D-02 | หนึ่งบริษัท/หนึ่ง deployment ต้องมี Default `Company Operations` เพียงหนึ่งรายการ |
| D-03 | ใช้ `โครงการบริษัท` ชนิด `INTERNAL` ที่มีอยู่เป็นข้อมูลตั้งต้น ห้ามสร้างซ้ำ |
| D-04 | การจัดสรรเป็น virtual allocation ภายในระบบ ไม่ได้สั่งโอนเงินจริงผ่านธนาคาร |
| D-05 | `Total Variance` เปลี่ยน label เป็น `Projected BOQ Margin` หรือคำไทยที่สื่อว่าเป็นประมาณการ และไม่ใช่เพดานการย้ายเงิน |
| D-06 | เพดานรายการใช้ `Available to Allocate` ซึ่งคำนวณจาก cash/commitment/allocations |
| D-07 | Owner เป็นผู้สร้างและ Reverse allocation; Admin อ่าน summary/history ได้แต่ mutate ไม่ได้ |
| D-08 | การจัดสรรไม่เปลี่ยน BOQ, Revenue, Expense, Projected Margin หรือสถานะ Input Request |
| D-09 | Allocation ที่ Post แล้วเป็น immutable; ห้าม edit/delete และใช้ reversal เท่านั้น |
| D-10 | ทุก allocation ต้องสร้าง debit/credit ledger entries ภายใน database transaction เดียวกัน |
| D-11 | จำนวนเงินใช้ decimal สองตำแหน่ง ห้ามใช้ float ใน calculation/storage contract |
| D-12 | V1 อนุญาต Project → Operations, Project → Project และ Operations → Project โดยปลายทางต้อง Active |
| D-13 | `Company Operations` แสดงเป็น System Bucket แยกจากงานก่อสร้างและไม่รวมใน Project Health/Construction KPI |
| D-14 | Planned Allocation จากกำไรในอนาคตไม่อยู่ใน V1 และต้องไม่ปะปนกับยอดเงินจริง |

## 4. คำศัพท์และ Financial Semantics

| คำในระบบ | ความหมาย |
|---|---|
| Projected BOQ Margin | `Customer BOQ - Subcontractor BOQ`; เป็นประมาณการจาก BOQ |
| Paid Income | รายรับของ Project ที่สถานะ `PAID` |
| Paid Expense | รายจ่ายของ Project ที่สถานะ `PAID` |
| Approved Commitment | รายจ่ายที่ Owner อนุมัติแล้วแต่ยังไม่จ่าย (`APPROVED`) |
| Allocated In | เงินที่ได้รับจาก Bucket อื่นผ่าน posted allocation |
| Allocated Out | เงินที่ส่งไป Bucket อื่นผ่าน posted allocation |
| Protected Reserve | ยอดที่กันไว้และห้ามจัดสรร; V1 กำหนดค่าเริ่มต้นเป็น 0 |
| Raw Available | ยอดคำนวณก่อนจำกัดค่าต่ำสุด |
| Available to Allocate | `max(0, Raw Available)` และเป็นเพดานที่ Owner จัดสรรได้ |
| Funding Deficit | ค่าสัมบูรณ์ของ Raw Available เมื่อ Raw Available ติดลบ |

### 4.1 สูตร V1

```text
Raw Available
= Paid Income
+ Allocated In
- Paid Expense
- Approved Expense Commitments
- Allocated Out
- Protected Reserve

Available to Allocate = max(0, Raw Available)
Funding Deficit       = max(0, -Raw Available)
```

กติกาการนับเงิน:

- ใช้ `approved_amount` เมื่อมีค่า มิฉะนั้นใช้ `amount`
- `PAID` และ `APPROVED` ต้องเป็นชุดสถานะที่ไม่ซ้ำกัน เพื่อไม่หักรายการเดียวสองครั้ง
- V1 ไม่นับ `PENDING_ADMIN` เป็น commitment
- Approved Income ยังไม่ถือเป็นเงินที่จัดสรรได้จนกว่าจะ `PAID`
- ต้องเลือก finance source-of-truth เพียงชุดเดียวต่อรายการ ห้ามรวม Input Request และ Transaction ที่อ้างถึงธุรกรรมเดียวกันซ้ำ
- เงินติดลบแสดงเป็น Funding Deficit แต่ปุ่มจัดสรรถูก disable

### 4.2 Opening Balance

`Company Operations` อาจมีเงินก่อนเริ่มใช้ฟีเจอร์ จึงต้องรองรับ Opening Balance แบบควบคุม:

- ใช้เฉพาะช่วง migration/setup
- Owner ระบุยอดและเหตุผล
- บันทึกเป็น immutable ledger entry ชนิด `OPENING_BALANCE`
- ห้ามแก้ยอดเดิม; หากผิดให้สร้าง adjustment/reversal
- ค่าเริ่มต้นเป็น 0 จนกว่า Owner ยืนยันยอดเปิดระบบ

## 5. V1 Scope

### 5.1 In Scope

- Default Company Operations Project/System Bucket
- Project fund summary และสูตร Available to Allocate
- Owner manual allocation dialog
- Project-to-project และ project-to-operations allocation
- Allocation history/ledger
- Reverse allocation
- Owner/Admin read access ตามสิทธิ์
- Atomic posting, idempotency และ concurrency validation
- Audit event สำหรับ create/reverse/failure
- Demo/Beta migration และ reconciliation

### 5.2 Non-goals

- ไม่เชื่อม Bank API หรือสั่งโอนเงินจริง
- ไม่เชื่อม MAKE by KBank
- ไม่คัดลอก branding, icon หรือหน้าจอของ MAKE by KBank
- ไม่มี Scheduled/Recurring Allocation
- ไม่มี Percentage-based auto allocation
- ไม่มี Planned Allocation จาก Variance ที่ยังไม่เป็นเงินสด
- ไม่มี multi-currency; V1 ใช้ THB
- ไม่แก้ logic BOQ หรือสูตร Variance
- ไม่เปลี่ยน Input Request approval/payment flow
- ไม่อนุญาตลบ posted ledger data

## 6. Target UX

### 6.1 Project List

- ปักหมุด `Company Operations` ในส่วน `Company Funds` เหนือรายการ Construction Projects
- แสดง badge `System Bucket`
- แสดง `Available to Allocate`, Funding Deficit (ถ้ามี) และรายการล่าสุด
- ไม่แสดง Construction Progress, Customer BOQ หรือ Project Health สำหรับ Operations
- Operations ลบไม่ได้และ Archive ไม่ได้

### 6.2 Project Detail — Financial Overview

เพิ่มส่วน `Project Funds` ที่มีอย่างน้อยสอง card:

1. `Projected BOQ Margin`
   - แสดง Total Variance เดิม
   - badge `ประมาณการ`
   - helper text: “ใช้สำหรับวางแผน ยังไม่ใช่เงินสดที่ย้ายได้”
   - ไม่มีปุ่มจัดสรรเงิน
2. `Available to Allocate`
   - แสดงยอดที่คำนวณจาก actual/commitment/allocation
   - badge `พร้อมจัดสรร`
   - ปุ่ม `จัดสรรเงิน` สำหรับ Owner
   - Admin เห็นยอด แต่ไม่เห็น mutation action หรือเห็น disabled state พร้อมคำอธิบายตาม convention ปัจจุบัน

เพิ่มส่วน `Allocation Ledger` ใต้ card:

- แสดง From, To, Amount, Reason, Status, Created by และ Created at
- แยก Allocated In/Out ด้วย label และ sign ไม่ใช้สีเป็นสัญญาณเพียงอย่างเดียว
- เปิดดูรายละเอียดและรายการ reversal ได้

### 6.3 Allocation Dialog

Dialog ใช้ flow เดียวกับ mockup ที่อนุมัติแล้ว:

1. `From` — ล็อกเป็น Project ปัจจุบัน
2. `Available` — แสดงยอดล่าสุด
3. `To` — searchable select; เสนอ Company Operations เป็นตัวเลือกแรก
4. `Amount` — decimal input พร้อมปุ่ม `ใช้ยอดสูงสุด`
5. `Reason` — บังคับกรอก
6. `Reference/Note` — optional หากต้องการใน implementation
7. `Preview` — แสดง source/target balance ก่อนและหลัง
8. Confirmation — “ยืนยันจัดสรร ฿X”

ข้อความบังคับใน Dialog:

> เป็นการจัดสรรเงินภายในระบบ ไม่ได้ทำรายการโอนผ่านธนาคาร

### 6.4 Dialog States

- Loading summary/options
- Ready
- Invalid amount
- Amount exceeds available
- Missing reason
- Stale balance (`409`) พร้อมโหลดตัวเลขใหม่
- Duplicate submit คืนผลเดิมด้วย idempotency
- Success พร้อม reference number
- Permission denied
- Target inactive/archived
- Network/server failure โดยคงค่าที่ผู้ใช้กรอกไว้

### 6.5 Reverse Flow

- ปุ่ม `Reverse allocation` อยู่ใน allocation detail และแสดงเฉพาะ Owner
- ต้องกรอกเหตุผล reversal
- แสดง preview การคืนยอด
- ถ้า target ไม่มี Available เพียงพอ ให้ block โดยไม่สร้างยอดติดลบ
- รายการเดิมเปลี่ยนสถานะเชิงอ้างอิงเป็น `REVERSED` แต่ ledger เดิมไม่ถูกลบ
- สร้าง allocation/entries ฝั่งตรงข้ามและเชื่อม `reversal_of`

### 6.6 Responsive และ Accessibility

- Desktop ใช้ centered dialog; Mobile ใช้ full-width sheet/dialog
- ใช้ native input/select/button และ keyboard navigation
- Focus เข้า dialog เมื่อเปิดและกลับปุ่มเดิมเมื่อปิด
- แสดง validation ด้วยข้อความ ไม่พึ่งสีอย่างเดียว
- จำนวนเงินมี label และ screen-reader text ที่ชัดเจน
- ป้องกัน double click ระหว่าง submit

## 7. Business Rules และ Validation

1. `amount > 0`
2. `amount <= current Available to Allocate`
3. Source และ Target ต้องไม่ใช่ Project เดียวกัน
4. Source/Target ต้อง Active และมี Fund Bucket
5. System Operations Bucket ต้องมีเพียงหนึ่งรายการต่อ company/deployment
6. Owner เท่านั้นที่ POST/Reverse ได้
7. Server ต้องคำนวณ Available ใหม่ภายใน transaction; ห้ามเชื่อค่าจาก Frontend
8. ถ้ายอดเปลี่ยนหลังเปิด Dialog ให้คืน `409 STALE_FUND_BALANCE`
9. Request ที่ส่งซ้ำด้วย idempotency key เดิมต้องคืน allocation เดิม ไม่สร้างรายการเพิ่ม
10. Posted allocation ห้าม update/delete
11. Reverse ต้องไม่ทำให้ Available ของฝั่งที่คืนเงินติดลบ
12. Allocation ไม่สร้าง Input Request, Transaction หรือ BOQ Item ใหม่
13. Allocation ไม่ถือเป็น Income/Expense และไม่รวมใน actual cashflow KPI
14. ทุก create/reverse บันทึก actor, timestamp, reason และ before/after balances

## 8. Proposed Data Design

ชื่อจริงของ table/field สามารถปรับตาม migration convention ของ repository แต่ต้องรักษา semantics ต่อไปนี้

### 8.1 Projects

เพิ่ม identifier ที่ไม่อิงชื่อ:

```text
projects.system_key nullable unique
```

ค่าที่รองรับใน V1:

```text
OPERATIONS
```

Migration ต้อง:

- หา existing UUID `11111111-1111-4111-8111-111111111111` หรือ fallback ด้วย `name='โครงการบริษัท'` และ `project_type='INTERNAL'`
- กำหนด `system_key='OPERATIONS'`
- รักษา `project_type='INTERNAL'` และ `status='ACTIVE'`
- เปลี่ยน display name ได้โดยไม่ทำให้ system lookup เสีย
- เพิ่ม unique constraint แบบ nullable เพื่อให้มี Operations เพียงหนึ่งรายการ

### 8.2 Fund Buckets

```text
fund_buckets
- id UUID PK
- project_id UUID UNIQUE FK projects.id
- bucket_type PROJECT | OPERATIONS
- currency THB
- protected_reserve NUMERIC(15,2) default 0
- status ACTIVE | LOCKED
- created_at
- updated_at
```

Project ปัจจุบันทุกตัวต้องถูก backfill ให้มีหนึ่ง Bucket

### 8.3 Fund Allocations

```text
fund_allocations
- id UUID PK
- reference_no VARCHAR UNIQUE
- source_bucket_id UUID FK
- target_bucket_id UUID FK
- amount NUMERIC(15,2)
- currency THB
- reason TEXT
- status POSTED | REVERSED
- reversal_of UUID nullable FK fund_allocations.id
- idempotency_key VARCHAR UNIQUE
- created_by VARCHAR/UUID
- created_at TIMESTAMPTZ
```

Constraints:

- amount > 0
- source_bucket_id != target_bucket_id
- reversal_of unique เมื่อใช้หนึ่ง reversal ต่อ allocation
- ห้าม update/delete ด้วย service policy; database permission/trigger พิจารณาเพิ่มหากเหมาะสม

### 8.4 Fund Ledger Entries

```text
fund_ledger_entries
- id UUID PK
- allocation_id UUID FK
- bucket_id UUID FK
- direction DEBIT | CREDIT
- entry_type ALLOCATION | REVERSAL | OPENING_BALANCE | ADJUSTMENT
- amount NUMERIC(15,2)
- created_at TIMESTAMPTZ
```

Posted allocation ปกติต้องมีสอง entries:

- Source: `DEBIT`
- Target: `CREDIT`

ทั้งสอง entries และ allocation header ต้อง commit/rollback พร้อมกัน

### 8.5 Audit

Audit event อย่างน้อย:

- `fund_allocation.created`
- `fund_allocation.reversed`
- `fund_allocation.rejected_insufficient_funds`
- `fund_allocation.rejected_stale_balance`
- `operations_bucket.bootstrap_completed`
- `operations_bucket.opening_balance_set`

ห้ามเก็บข้อมูลลับหรือข้อมูลธนาคารใน audit payload

## 9. Proposed API Contracts

### 9.1 Read APIs

```text
GET /api/v1/fund-buckets/options
GET /api/v1/projects/{project_id}/funds/summary
GET /api/v1/fund-allocations?project_id={id}&cursor={cursor}
GET /api/v1/fund-allocations/{allocation_id}
```

Summary response ต้องแยกอย่างชัดเจน:

```json
{
  "project_id": "uuid",
  "currency": "THB",
  "projected_boq_margin": "1000000.00",
  "paid_income": "900000.00",
  "paid_expense": "300000.00",
  "approved_expense_commitment": "150000.00",
  "allocated_in": "200000.00",
  "allocated_out": "250000.00",
  "protected_reserve": "50000.00",
  "raw_available": "350000.00",
  "available_to_allocate": "350000.00",
  "funding_deficit": "0.00",
  "calculated_at": "2026-08-06T10:42:00+07:00",
  "version": "opaque-balance-version"
}
```

### 9.2 Mutation APIs

```text
POST /api/v1/fund-allocations
POST /api/v1/fund-allocations/{allocation_id}/reverse
```

Create request:

```json
{
  "source_project_id": "uuid",
  "target_project_id": "uuid",
  "amount": "200000.00",
  "currency": "THB",
  "reason": "จัดสรรสำหรับค่าใช้จ่ายส่วนกลางเดือนสิงหาคม",
  "expected_source_balance_version": "opaque-balance-version",
  "idempotency_key": "client-generated-uuid"
}
```

Success response ต้องคืน:

- allocation id/reference
- source/target ก่อนและหลัง
- posted timestamp
- actor
- balance versions ใหม่

Structured errors อย่างน้อย:

- `INSUFFICIENT_AVAILABLE_FUNDS`
- `STALE_FUND_BALANCE`
- `INVALID_SOURCE_TARGET`
- `TARGET_BUCKET_INACTIVE`
- `OPERATIONS_BUCKET_MISSING`
- `ALLOCATION_ALREADY_REVERSED`
- `REVERSAL_WOULD_OVERDRAW_TARGET`
- `FORBIDDEN`

## 10. Calculation และ Posting Service

สร้าง service boundary กลางเพื่อไม่ให้ Router หรือ Frontend คำนวณ business rules เอง

หน้าที่หลัก:

1. Resolve fund bucket และ authorization scope
2. Aggregate paid/approved Input Requests โดยไม่ double count
3. Aggregate posted ledger entries
4. คำนวณ fund summary ด้วย Decimal
5. Lock source/target rows ตามลำดับ deterministic เพื่อลด deadlock
6. Recalculate source available ภายใน transaction
7. Validate expected balance version และ amount
8. Create allocation + debit/credit entries
9. Emit audit event หลัง commit สำเร็จ
10. Return before/after snapshots

ข้อกำหนดสำคัญ:

- ห้ามใช้ค่าที่ Frontend ส่งมาเป็น source of truth
- ห้ามสร้าง allocation หาก audit/ledger persistence ที่จำเป็นล้มเหลว
- ต้องมี deterministic ordering ตอน lock สอง buckets
- ต้องกำหนด timeout/error behavior เมื่อ concurrent requests ชนกัน
- Query summary และ posting ต้องใช้ calculation function ชุดเดียวกัน

## 11. Frontend Work Packages

### FE-01 — API Adapter และ State

- เพิ่ม fund summary/options/history/create/reverse API functions
- Normalize decimal strings โดยไม่ทำให้ precision สูญหาย
- รองรับ `409` และ structured errors
- ป้องกัน submit ซ้ำระหว่าง pending

### FE-02 — Project Fund Summary

- เพิ่ม Project Funds section ใน Project Detail
- เปลี่ยน label Total Variance เป็น Projected BOQ Margin
- เพิ่ม Available to Allocate/Funding Deficit states
- Owner CTA และ Admin read-only behavior

### FE-03 — Allocation Dialog

- Source locked
- Destination selector
- Amount/max/reason
- Before/after preview
- Validation/loading/error/success states
- Responsive และ accessible focus behavior

### FE-04 — Allocation Ledger

- Recent history ใน Project Detail
- Full history/detail route หรือ panel
- Direction/status/reference/actor/timestamp
- Reverse action สำหรับ Owner

### FE-05 — Company Operations Experience

- ปักหมุด Operations ใน Projects page
- ไม่แสดง BOQ/Construction-specific sections
- แสดง Operations cash/commitment/allocation/expense overview
- System Bucket badge และ protection จาก delete/archive

## 12. Backend และ Database Work Packages

### BE-01 — Migration และ Bootstrap

- เพิ่ม `projects.system_key`
- Upgrade existing `โครงการบริษัท` เป็น `OPERATIONS`
- สร้าง fund tables/indexes/constraints
- Backfill bucket ให้ทุก Project
- ทำ migration ให้ rerun-safe และไม่สร้าง Operations ซ้ำ

### BE-02 — Fund Calculation Service

- Implement Decimal aggregation
- กำหนด single finance source-of-truth
- คำนวณ summary และ balance version
- รองรับ Funding Deficit

### BE-03 — Allocation Posting Service

- Atomic double-entry posting
- Row locking/concurrency guard
- Idempotency
- Immutable records
- Reversal

### BE-04 — APIs, Auth และ Audit

- Read APIs สำหรับ Owner/Admin
- Mutation APIs สำหรับ Owner
- Structured errors
- Audit events และ safe logging
- Pagination สำหรับ history

### BE-05 — Operations Rules

- Replace name-based lookup ด้วย `system_key='OPERATIONS'`
- ป้องกัน delete/archive/type change ของ system project
- รองรับ display-name change โดยไม่กระทบ lookup
- Exclude Operations จาก construction metrics

## 13. Test Plan

### 13.1 Unit Tests

- Formula: income/expense/approved commitment/allocation/reserve
- `approved_amount` fallback ไป `amount`
- Raw Available positive/zero/negative
- Decimal precision และ rounding สองตำแหน่ง
- BOQ Margin ไม่รวมใน Available
- Balance version เปลี่ยนเมื่อ input/ledger ที่เกี่ยวข้องเปลี่ยน

### 13.2 API/Service Tests

- Owner สร้าง allocation สำเร็จ
- Admin mutation ได้ `403`
- amount 0/negative/เกิน available ถูก reject
- same source/target ถูก reject
- inactive target ถูก reject
- duplicate idempotency key คืนผลเดิม
- concurrent requests ไม่ทำให้ยอดติดลบ
- stale version ได้ `409`
- allocation สร้าง ledger entries ครบสองรายการ
- failure ระหว่าง posting rollback ทั้งหมด
- reversal สำเร็จและเชื่อมรายการเดิม
- reversal ซ้ำถูก reject
- reversal ที่ทำให้ target ติดลบถูก reject
- Operations bootstrap rerun แล้วไม่สร้าง duplicate
- Allocation ไม่เปลี่ยน BOQ/Input Request/actual cashflow values

### 13.3 Frontend Tests

- Owner/Admin rendering
- Button disabled เมื่อ available เป็น 0
- Max amount และ preview คำนวณถูกต้อง
- Validation error และ stale-balance refresh
- Double-click ไม่สร้างสอง requests
- Focus management/keyboard/mobile layout
- Ledger direction และ reversal state

### 13.4 Verification Commands

```bash
cd Projects-001-FE
npm run lint
npm run build

cd ../Projects-001-BE
pytest
```

เพิ่ม migration dry-run และ API smoke test ตาม environment runbook ก่อน deploy

## 14. Rollout Plan

### Phase 0 — Decision Freeze และ Data Reconciliation

- [ ] ยืนยัน finance source-of-truth สำหรับ Paid/Approved
- [ ] ตรวจยอดและ UUID ของ existing `โครงการบริษัท` ใน Demo/Beta
- [ ] ยืนยัน display name ของ Operations
- [ ] กำหนด Opening Balance และ effective date
- [ ] เก็บตัวอย่าง Project จริงอย่างน้อย 3 รายการเพื่อเทียบสูตร

Exit gate: สูตรและยอดตัวอย่างได้รับการอนุมัติจาก Owner

### Phase 1 — Database Foundation

- [ ] สร้าง backward-compatible migration
- [ ] Upgrade existing Operations project
- [ ] Backfill fund buckets
- [ ] สร้าง allocation/ledger constraints
- [ ] ทดสอบ rerun/rollback strategy

Exit gate: migration ผ่านบนสำเนาข้อมูลและไม่สร้าง duplicate

### Phase 2 — Backend Read Model

- [ ] Implement fund summary service
- [ ] Implement read APIs
- [ ] เพิ่ม authorization และ tests
- [ ] Reconcile summary กับข้อมูลจริง

Exit gate: fund summary ของ sample projects ตรงกับการคำนวณ manual

### Phase 3 — Atomic Allocation

- [ ] Implement posting/idempotency/locking
- [ ] Implement reversal
- [ ] เพิ่ม audit events
- [ ] ทำ concurrency/failure tests

Exit gate: ไม่มี negative balance และไม่มี partial ledger entry ใน test matrix

### Phase 4 — Frontend UX

- [ ] Project Funds cards
- [ ] Allocation Dialog
- [ ] Allocation Ledger
- [ ] Company Operations presentation
- [ ] Responsive/accessibility states

Exit gate: lint/build ผ่านและ Owner walkthrough ผ่านทุก primary/error flow

### Phase 5 — Demo Rollout

- [ ] เปิดด้วย feature flag `FUND_ALLOCATION_ENABLED`
- [ ] Run migration/bootstrap
- [ ] ตั้ง Opening Balance ถ้าจำเป็น
- [ ] Reconcile fund totals ก่อนเปิด mutation
- [ ] เปิด read-only summary ก่อน
- [ ] เปิด Owner posting หลัง reconciliation ผ่าน
- [ ] Monitor errors/audit/concurrency

Exit gate: Demo ใช้งานครบและยอดไม่คลาดเคลื่อนตลอด observation window ที่กำหนด

### Phase 6 — Beta Rollout

- [ ] ทำ preflight และ reconciliation ซ้ำกับ Beta
- [ ] Deploy migration/backend/frontend ตามลำดับ
- [ ] Smoke test Owner/Admin
- [ ] ตรวจ audit และ rollback readiness

Exit gate: Beta acceptance criteria ผ่านก่อนตัดสินใจ Production

## 15. Monitoring และ Reconciliation

ติดตามอย่างน้อย:

- Allocation create/reverse success rate
- `INSUFFICIENT_AVAILABLE_FUNDS` count
- `STALE_FUND_BALANCE` count
- Duplicate idempotency replay count
- Posting latency
- Ledger imbalance count ซึ่งต้องเป็น 0
- Operations bucket duplication count ซึ่งต้องเป็น 0
- Project ที่ Raw Available ติดลบ
- Difference ระหว่าง ledger aggregate และ allocation headers ซึ่งต้องเป็น 0

สร้าง reconciliation query/report ที่ตรวจว่า:

```text
ทุก POSTED allocation:
sum(DEBIT) == sum(CREDIT) == allocation.amount
```

## 16. Rollback Strategy

- ปิด `FUND_ALLOCATION_ENABLED` เพื่อหยุด mutation ทันที
- คง read-only ledger/history ไว้เพื่อ audit
- Frontend สามารถซ่อน CTA โดยไม่ลบข้อมูล
- Backend ต้อง reject mutation เมื่อ flag ปิด
- ห้ามลบ posted allocations เพื่อ rollback
- หาก calculation ผิด ให้แก้ service และรัน reconciliation; ใช้ adjustment/reversal ที่ตรวจสอบได้แทนการแก้ row เดิม
- Database migration ควร additive ในระยะแรกเพื่อให้ rollback application version ได้

## 17. Acceptance Criteria / Definition of Done

ฟีเจอร์ V1 ถือว่าเสร็จเมื่อ:

1. มี Operations System Bucket เพียงหนึ่งรายการและใช้ record เดิมโดยไม่สร้างซ้ำ
2. Owner เห็น Projected BOQ Margin และ Available to Allocate เป็นคนละตัวเลข/ความหมาย
3. Owner จัดสรรเงินได้ไม่เกิน server-calculated Available
4. Admin อ่าน summary/history ได้แต่ mutate ไม่ได้
5. Allocation ทุกตัวมี atomic debit/credit entries และ audit trail
6. Duplicate/concurrent requests ไม่ทำให้ยอดซ้ำหรือติดลบ
7. Reverse สร้างประวัติใหม่และไม่ลบรายการเดิม
8. BOQ, Variance, Input Request และ actual cashflow ไม่ถูกแก้โดย allocation
9. Operations ไม่ปะปนใน Construction KPI/Project Health
10. Migration, backend tests, frontend lint/build และ manual walkthrough ผ่าน
11. Demo/Beta reconciliation ไม่พบ ledger imbalance
12. User-facing copy ระบุชัดว่าเป็นการจัดสรรภายในระบบ ไม่ใช่ bank transfer

## 18. Open Decisions ก่อนเริ่ม Implementation

รายการต่อไปนี้ไม่ขัดขวางการเขียน plan แต่ต้องยืนยันก่อนเริ่ม production implementation:

| ID | คำถาม | ค่าแนะนำสำหรับ V1 |
|---|---|---|
| O-01 | ชื่อที่แสดงของ Operations | `Company Operations / ค่าใช้จ่ายส่วนกลาง` |
| O-02 | แหล่งข้อมูล Paid/Approved หลัก | Input Request finance rows; ห้ามรวม derived Transaction ซ้ำ |
| O-03 | Opening Balance ของ Operations | Owner ระบุยอด ณ cut-off date พร้อมเหตุผลและหลักฐานอ้างอิง |
| O-04 | Protected Reserve | เริ่มที่ 0 และยังไม่มี UI แก้ไขใน V1 |
| O-05 | Project-to-Project allocation | อนุญาตสำหรับ Active Projects โดย Operations แสดงเป็นตัวเลือกแรก |
| O-06 | Operations → Project | อนุญาตด้วย validation เดียวกัน |
| O-07 | ช่วง observation ใน Demo | อย่างน้อย 3–5 วันทำการหรือครบ use cases ที่กำหนด |
| O-08 | Planned Allocation | ย้ายไป V2 หลัง actual allocation เสถียร |

## 19. Suggested V2 Backlog

- Planned Allocation จาก Projected Margin
- Percentage rule เช่นจัดสรร 20% เข้า Operations
- Recurring monthly allocation
- Protected Reserve management UI
- Allocation approval แบบ two-person control
- Notifications เมื่อ Project มี Funding Deficit
- Company-level bucket board แบบ MAKE-style overview
- Forecast เปรียบเทียบ Planned vs Actual Allocation
- Bank/accounting reconciliation โดยเป็นโครงการแยกและไม่เปลี่ยน semantics ของ internal allocation

