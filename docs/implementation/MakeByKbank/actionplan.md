# Forecast Margin Allocation — Action Plan

> แผนพัฒนาฟีเจอร์จัดสรร Margin ที่คาดการณ์ระหว่าง Project Buckets ซึ่งได้รับแรงบันดาลใจจากแนวคิด Envelope/Bucket Budgeting ของ MAKE by KBank โดยเป็นการออกแบบสำหรับ Projects-001 และไม่ได้คัดลอกแบรนด์หรือหน้าจอของ MAKE by KBank

| รายการ | ค่า |
|---|---|
| สถานะเอกสาร | Approved revised baseline — implementation alignment required |
| วันที่อัปเดต | 2026-08-07 |
| Product scope | Project Forecast Buckets, Company Operations, Forecast Margin Allocation Ledger |
| ผู้มีสิทธิ์จัดสรร Margin | `owner` เท่านั้น |
| ผู้มีสิทธิ์อ่าน | `owner`, `admin` ตาม project visibility ปัจจุบัน |
| ลักษณะรายการ | Virtual forecast allocation ภายในระบบ ไม่ใช่ cash movement หรือ bank transfer |
| Rollout target | Local/Demo → Beta → Production decision |

## 1. วัตถุประสงค์

สร้างวิธีบริหาร Margin ที่คาดการณ์ใน Projects-001 ให้แต่ละ Project เป็นเสมือน “Bucket” และสามารถจัดสรร forecast capacity ระหว่าง Bucket ได้ โดยมี `Company Operations` เป็น Bucket กลางสำหรับงบดำเนินงานของบริษัท

ฟีเจอร์ต้องทำให้ Owner:

1. เห็น `Projected BOQ Margin` และ Margin ส่วนที่ยังพร้อมจัดสรร
2. จัดสรร Margin ที่คาดการณ์จาก Project หนึ่งไปยัง `Company Operations` หรือ Project อื่นได้ด้วยตนเอง
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

- `Total Variance` เป็น Margin ที่ธุรกิจต้องการนำมาบริหาร แต่ยังไม่มี Forecast Bucket รองรับ
- ยังไม่มีตัวเลข `Available Margin to Allocate` หลังหักยอดที่จัดสรรออกและ Forecast Reserve
- ยังไม่มี ledger สำหรับการย้ายยอดระหว่าง Project
- `โครงการบริษัท` ถูกตรวจด้วยชื่อและ `project_type` ซึ่งเปราะบางหากมีการเปลี่ยนชื่อ
- ยังไม่มีระบบป้องกัน double submit, concurrent allocation หรือการแก้ประวัติย้อนหลัง

### 2.3 แนวทาง migration

ไม่สร้าง Operations Project ซ้ำ ให้ยกระดับ `โครงการบริษัท` ที่มีอยู่แล้วเป็น Default Operations Project และรักษา UUID เดิมเพื่อไม่ทำลาย Input Requests/ความสัมพันธ์ปัจจุบัน

### 2.4 Implementation Alignment Note — 2026-08-07

- Migration/table foundation ที่รันแล้วเก็บไว้ได้ เพราะ Bucket, Allocation, Ledger และ Audit ยังจำเป็น
- Calculation ที่ใช้ Paid Income, Paid Expense และ Approved Commitments เป็นเพดานถือเป็น superseded logic และต้องแก้ก่อนเปิด Owner mutation
- Frontend ต้องไม่ disable ปุ่มเพราะ actual cashflow เมื่อ Available Margin จาก Forecast เป็นบวก
- Summary API, posting validation, reverse validation และ UI ต้องใช้ Forecast formula ชุดเดียวกัน
- ห้ามแก้ migration ที่รันแล้ว; schema/constraint ที่ต้องเปลี่ยนให้ใช้ additive follow-up migration

## 3. Product Decision Register

Decision ต่อไปนี้เป็น baseline สำหรับ V1 หากต้องเปลี่ยนระหว่าง implementation ให้บันทึกเหตุผลในเอกสารหรือ ADR ก่อน

| ID | ข้อสรุป |
|---|---|
| D-01 | Project แต่ละรายการมี Fund Bucket หนึ่ง Bucket แบบ 1:1 |
| D-02 | หนึ่งบริษัท/หนึ่ง deployment ต้องมี Default `Company Operations` เพียงหนึ่งรายการ |
| D-03 | ใช้ `โครงการบริษัท` ชนิด `INTERNAL` ที่มีอยู่เป็นข้อมูลตั้งต้น ห้ามสร้างซ้ำ |
| D-04 | การจัดสรรเป็น virtual forecast allocation ภายในระบบ ไม่ได้สั่งโอนเงินจริงผ่านธนาคารและไม่ยืนยันว่ามีเงินสดอยู่จริง |
| D-05 | `Total Variance` เปลี่ยน label เป็น `Projected BOQ Margin` และเป็น forecast base ของ Project Bucket |
| D-06 | เพดานรายการใช้ `Available Margin to Allocate` ซึ่งคำนวณจาก Projected BOQ Margin/Opening Forecast Balance, Forecast Allocated In/Out และ Forecast Reserve |
| D-07 | Owner เป็นผู้สร้างและ Reverse allocation; Admin อ่าน summary/history ได้แต่ mutate ไม่ได้ |
| D-08 | การจัดสรรไม่เปลี่ยน BOQ, Revenue, Expense, Projected BOQ Margin หรือสถานะ Input Request; เปลี่ยนเฉพาะ forecast balance ของ Bucket |
| D-09 | Allocation ที่ Post แล้วเป็น immutable; ห้าม edit/delete และใช้ reversal เท่านั้น |
| D-10 | ทุก allocation ต้องสร้าง debit/credit ledger entries ภายใน database transaction เดียวกัน |
| D-11 | จำนวนเงินใช้ decimal สองตำแหน่ง ห้ามใช้ float ใน calculation/storage contract |
| D-12 | V1 อนุญาต Project → Operations, Project → Project และ Operations → Project โดยปลายทางต้อง Active |
| D-13 | `Company Operations` แสดงเป็น System Bucket แยกจากงานก่อสร้างและไม่รวมใน Project Health/Construction KPI |
| D-14 | Forecast Margin Allocation จาก Projected BOQ Margin คือ scope หลักของ V1 และต้องแยกจาก actual cashflow อย่างชัดเจน |
| D-15 | Owner เป็นผู้ระบุและยืนยัน Initial Opening Forecast Balance ของ Operations โดย Accounting/Admin เตรียมและตรวจตัวเลข |
| D-16 | Forecast Balance Start Date คือวันที่ 1 ของเดือนที่เลือกเปิดใช้งาน; เดือนถัดไปยก Previous Month Forecast Closing เป็น Monthly Forecast Opening อัตโนมัติ |
| D-17 | Subcontractor ไม่เห็น ไม่เลือก และไม่ส่ง Income/Expense เข้า Company Operations; เห็นเฉพาะ assigned Projects |
| D-18 | `PAID`, `APPROVED`, Income, Expense และ commitment ไม่อยู่ในสูตร Forecast Available และต้องแสดงใน Cashflow แยกต่างหาก |
| D-19 | Forecast Allocated In เพิ่ม Available ของ Bucket ปลายทางและสามารถจัดสรรต่อได้ภายใต้ validation เดียวกัน |
| D-20 | เมื่อ BOQ เปลี่ยน ให้ใช้ Projected BOQ Margin ล่าสุดทันที; หาก Raw Forecast Available ติดลบให้คง ledger เดิม แสดง Forecast Deficit และห้ามจัดสรรออกเพิ่ม |

## 4. คำศัพท์และ Financial Semantics

| คำในระบบ | ความหมาย |
|---|---|
| Projected BOQ Margin | `Customer BOQ - Subcontractor BOQ` ล่าสุด; เป็น forecast base ของ Project Bucket |
| Opening Forecast Balance | forecast base ที่ Owner กำหนดให้ Operations ครั้งแรก เพราะ Operations ไม่มี BOQ Margin |
| Forecast Allocated In | Margin ที่ Bucket ได้รับจาก Bucket อื่นผ่าน posted allocation |
| Forecast Allocated Out | Margin ที่ Bucket จัดสรรให้ Bucket อื่นผ่าน posted allocation |
| Forecast Reserve | Margin ที่ Owner กันไว้และห้ามจัดสรร; V1 กำหนดค่าเริ่มต้นเป็น 0 |
| Raw Forecast Available | Forecast balance ก่อนจำกัดค่าต่ำสุด |
| Available Margin to Allocate | `max(0, Raw Forecast Available)` และเป็นเพดานที่ Owner จัดสรรได้ |
| Forecast Deficit | ค่าสัมบูรณ์ของ Raw Forecast Available เมื่อ BOQ Margin/forecast base ลดต่ำกว่ายอดที่จัดสรรไปแล้ว |
| Actual Cashflow | Paid/Approved Income, Expense และ commitment; แสดงเป็นข้อมูลประกอบแต่ไม่เข้าร่วมสูตร allocation |

### 4.1 สูตร V1

```text
Forecast Base
= Projected BOQ Margin สำหรับ Project ทั่วไป
  หรือ Opening Forecast Balance สำหรับ Company Operations

Raw Forecast Available
= Forecast Base
+ Forecast Allocated In
- Forecast Allocated Out
- Forecast Reserve

Available Margin to Allocate = max(0, Raw Forecast Available)
Forecast Deficit             = max(0, -Raw Forecast Available)
```

กติกาการคำนวณ Forecast:

- Projected BOQ Margin ใช้ค่าล่าสุดจาก calculation เดียวกับหน้า BOQ Comparison; Frontend ห้ามคำนวณขึ้นเอง
- Income, Expense, `PENDING_ADMIN`, `APPROVED`, `PAID` และ commitment ไม่มีผลต่อสูตรนี้
- Allocation ไม่แก้ Projected BOQ Margin ต้นทาง; ใช้ Forecast Allocated Out เพื่อลดยอดที่ยังจัดสรรได้
- Forecast Allocated In เพิ่มยอดของปลายทางและสามารถจัดสรรต่อได้
- เมื่อ BOQ Margin ลดลง ระบบไม่แก้หรือลบ allocation เดิม
- Raw Forecast Available ติดลบให้แสดง Forecast Deficit และ disable การจัดสรรออกเพิ่ม

### 4.2 Opening Forecast Balance

`Company Operations` ไม่มี BOQ Margin จึงให้ Owner ระบุ Initial Opening Forecast Balance ในขั้นตอนเปิดใช้งานแบบควบคุม ตัวเลขนี้เป็นงบคาดการณ์ ไม่ใช่ยอดเงินสดหรือยอดธนาคาร:

- Accounting/Admin เตรียมและตรวจตัวเลขก่อนส่งให้ Owner
- Owner เป็นผู้กรอกยอดและยืนยันขั้นสุดท้ายในระบบ
- Owner เลือกเดือนเริ่มใช้งาน และระบบกำหนด Effective Date เป็นวันที่ 1 ของเดือนนั้น
- ใช้ Initial Opening Forecast Balance เพียงครั้งแรกในช่วง activation/setup
- Owner ระบุยอดและเหตุผล พร้อมตรวจ Preview ก่อนยืนยัน
- บันทึกเป็น immutable ledger entry ชนิด `OPENING_BALANCE` โดยระบุ semantic ว่าเป็น forecast
- ห้ามแก้ยอดเดิม; หากผิดให้สร้าง adjustment/reversal
- ค่าเริ่มต้นเป็น 0 จนกว่า Owner ยืนยันยอดเปิดระบบ
- Forecast movement ก่อน Balance Start Date ต้องไม่ถูกคำนวณซ้ำ เพราะถูกรวมอยู่ในยอดตั้งต้นแล้ว

### 4.3 Monthly Forecast Roll-forward

หลังเปิดใช้งานครั้งแรก Owner ไม่ต้องกรอก Opening Forecast Balance ใหม่ทุกเดือน:

```text
Monthly Forecast Opening วันที่ 1 ของเดือนปัจจุบัน
= Forecast Closing Balance ของเดือนก่อน
```

- Initial Opening Forecast Balance เป็น manual entry เพียงครั้งเดียว
- Monthly Forecast Opening หลังจากนั้นเป็น derived balance ไม่ใช่ Income, Expense หรือ Allocation
- Monthly Forecast Closing รวม forecast allocation movement ตั้งแต่วันที่ 1 ถึงวันสุดท้ายของเดือน โดยไม่รวม actual cashflow
- การแก้ยอดย้อนหลังใช้ Adjustment/Reverse พร้อม Audit Trail และระบบคำนวณ Monthly Forecast Closing/Opening ที่ได้รับผลกระทบใหม่

## 5. V1 Scope

### 5.1 In Scope

- Default Company Operations Project/System Bucket
- Project forecast summary และสูตร Available Margin to Allocate
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
- ไม่มีการอ้างว่า forecast allocation เป็นเงินสดจริงหรือเป็นคำสั่งโอนธนาคาร
- ไม่มี multi-currency; V1 ใช้ THB
- ไม่แก้ logic BOQ หรือสูตร Variance
- ไม่เปลี่ยน Input Request approval/payment flow
- ไม่อนุญาตลบ posted ledger data

## 6. Target UX

### 6.1 Project List

- ปักหมุด `Company Operations` ในส่วน `Company Funds` เหนือรายการ Construction Projects
- แสดง badge `System Bucket`
- แสดง `Available Margin to Allocate`, Forecast Deficit (ถ้ามี) และรายการล่าสุด
- ไม่แสดง Construction Progress, Customer BOQ หรือ Project Health สำหรับ Operations
- Operations ลบไม่ได้และ Archive ไม่ได้

### 6.2 Project Detail — Financial Overview

เพิ่มส่วน `Project Funds` ที่มีอย่างน้อยสอง card:

1. `Projected BOQ Margin`
   - แสดง Total Variance เดิม
   - badge `ประมาณการ`
   - helper text: “Margin คาดการณ์จาก BOQ และไม่ใช่เงินสดจริง”
2. `Available Margin to Allocate`
   - แสดงยอดที่คำนวณจาก Projected BOQ Margin/Opening Forecast Balance, Forecast Allocated In/Out และ Forecast Reserve
   - badge `พร้อมจัดสรร Margin`
   - ปุ่ม `จัดสรร Margin` สำหรับ Owner
   - Admin เห็นยอด แต่ไม่เห็น mutation action หรือเห็น disabled state พร้อมคำอธิบายตาม convention ปัจจุบัน

Paid Income, Paid Expense และ Approved Commitments อาจแสดงในส่วน Cashflow แยกต่างหาก แต่ห้ามอยู่ใน formula strip ของ Forecast Margin และห้ามมีผลต่อปุ่มจัดสรร

เพิ่มส่วน `Margin Allocation Ledger` ใต้ card:

- แสดง From, To, Amount, Reason, Status, Created by และ Created at
- แยก Allocated In/Out ด้วย label และ sign ไม่ใช้สีเป็นสัญญาณเพียงอย่างเดียว
- เปิดดูรายละเอียดและรายการ reversal ได้

### 6.3 Allocation Dialog

Dialog ใช้ flow เดียวกับ mockup ที่อนุมัติแล้ว:

1. `From` — ล็อกเป็น Project ปัจจุบัน
2. `Available Margin` — แสดงยอด Forecast ล่าสุด
3. `To` — searchable select; เสนอ Company Operations เป็นตัวเลือกแรก
4. `Amount` — decimal input พร้อมปุ่ม `ใช้ยอดสูงสุด`
5. `Reason` — บังคับกรอก
6. `Reference/Note` — optional หากต้องการใน implementation
7. `Preview` — แสดง source/target balance ก่อนและหลัง
8. Confirmation — “ยืนยันจัดสรร Margin ฿X”

ข้อความบังคับใน Dialog:

> เป็นการจัดสรร Margin ที่คาดการณ์ภายในระบบ ไม่ใช่เงินสดจริงและไม่ได้ทำรายการโอนผ่านธนาคาร

### 6.4 Dialog States

- Loading summary/options
- Ready
- Invalid amount
- Amount exceeds Available Margin
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
- ถ้า target ไม่มี Available Margin เพียงพอ ให้ block โดยไม่สร้าง Forecast Deficit ใหม่จาก reversal
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
2. `amount <= current Available Margin to Allocate`
3. Source และ Target ต้องไม่ใช่ Project เดียวกัน
4. Source/Target ต้อง Active และมี Fund Bucket
5. System Operations Bucket ต้องมีเพียงหนึ่งรายการต่อ company/deployment
6. Owner เท่านั้นที่ POST/Reverse ได้
7. Server ต้องโหลด Projected BOQ Margin/Opening Forecast Balance ล่าสุดและคำนวณ Available Margin ใหม่ภายใน transaction; ห้ามเชื่อค่าจาก Frontend
8. ถ้ายอดเปลี่ยนหลังเปิด Dialog ให้คืน `409 STALE_FUND_BALANCE`
9. Request ที่ส่งซ้ำด้วย idempotency key เดิมต้องคืน allocation เดิม ไม่สร้างรายการเพิ่ม
10. Posted allocation ห้าม update/delete
11. Reverse ต้องไม่ทำให้ Raw Forecast Available ของฝั่งที่คืน Margin ติดลบ
12. Allocation ไม่สร้าง Input Request, Transaction หรือ BOQ Item ใหม่
13. Allocation ไม่ถือเป็น Income/Expense, ไม่รวมใน actual cashflow KPI และไม่เปลี่ยนตามสถานะ `PAID`/`APPROVED`
14. ทุก create/reverse บันทึก actor, timestamp, reason และ before/after balances
15. Subcontractor query/project selector ต้องคืนเฉพาะ assigned Projects และ exclude `system_key='OPERATIONS'` เสมอ
16. Subcontractor สร้าง Income/Expense ที่อ้างถึง Operations ไม่ได้ แม้ส่ง project id โดยตรง
17. Operations expense ใช้ Internal Input Flow โดย internal authorized actor เท่านั้น; V1 ให้ Owner mutation และ Admin/Accounting เตรียม–ตรวจแบบ read-only

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
- balance_start_date DATE nullable; เมื่อ activate ต้องเป็นวันที่ 1 ของเดือน
- forecast_reserve NUMERIC(15,2) default 0
- status SETUP | ACTIVE | LOCKED
- created_at
- updated_at
```

Project ปัจจุบันทุกตัวต้องถูก backfill ให้มีหนึ่ง Bucket

หาก environment ใดรัน migration ที่ใช้ชื่อ physical column `protected_reserve` ไปแล้ว ให้คง column เดิมเพื่อ backward compatibility และตีความเป็น Forecast Reserve; การ rename ต้องทำด้วย additive follow-up migration ไม่แก้ migration ที่รันแล้ว

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
- `fund_allocation.rejected_insufficient_margin`
- `fund_allocation.rejected_stale_balance`
- `operations_bucket.bootstrap_completed`
- `operations_bucket.opening_forecast_balance_set`

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
  "forecast_base_type": "PROJECTED_BOQ_MARGIN",
  "projected_boq_margin": "1000000.00",
  "opening_forecast_balance": "0.00",
  "forecast_allocated_in": "200000.00",
  "forecast_allocated_out": "250000.00",
  "forecast_reserve": "50000.00",
  "raw_forecast_available": "900000.00",
  "available_margin_to_allocate": "900000.00",
  "forecast_deficit": "0.00",
  "calculated_at": "2026-08-06T10:42:00+07:00",
  "version": "opaque-balance-version"
}
```

Actual Income/Expense/Commitment ให้โหลดจาก Cashflow API/section แยกต่างหาก และห้ามนำมารวมใน response เพื่ออธิบายเพดาน Forecast Allocation

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

- `INSUFFICIENT_AVAILABLE_MARGIN`
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
2. Resolve Projected BOQ Margin ล่าสุดจาก calculation/source เดียวกับ BOQ Comparison หรือ Opening Forecast Balance ของ Operations
3. Aggregate posted forecast ledger entries
4. คำนวณ forecast margin summary ด้วย Decimal โดยไม่อ่าน Paid/Approved status มาเป็นตัวตั้ง
5. Lock source/target rows ตามลำดับ deterministic เพื่อลด deadlock
6. Recalculate source Available Margin ภายใน transaction
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
- เพิ่ม Available Margin to Allocate/Forecast Deficit states
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
- แสดง Operations forecast balance/allocation overview และแยก actual expense/cashflow เป็น informational section
- System Bucket badge และ protection จาก delete/archive
- Initial Opening Forecast Balance setup สำหรับ Owner พร้อม month selector ที่บังคับใช้วันที่ 1
- Monthly Forecast Opening/Closing display แบบ auto roll-forward
- Exclude Operations จาก Subcontractor project selectors และ routes

## 12. Backend และ Database Work Packages

### BE-01 — Migration และ Bootstrap

- เพิ่ม `projects.system_key`
- Upgrade existing `โครงการบริษัท` เป็น `OPERATIONS`
- สร้าง fund tables/indexes/constraints
- Backfill bucket ให้ทุก Project
- ทำ migration ให้ rerun-safe และไม่สร้าง Operations ซ้ำ

### BE-02 — Fund Calculation Service

- Implement Decimal aggregation
- ใช้ BOQ Comparison calculation เป็น source-of-truth ของ Projected BOQ Margin
- คำนวณ forecast summary และ balance version
- รองรับ Forecast Deficit เมื่อ Margin ล่าสุดลดต่ำกว่ายอดที่จัดสรรไปแล้ว

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
- Enforce Subcontractor exclusion ที่ API/authorization layer ไม่พึ่ง Frontend filter
- Implement one-time Initial Opening Forecast Balance และ monthly forecast roll-forward semantics

## 13. Test Plan

### 13.1 Unit Tests

- Formula: Projected BOQ Margin/Opening Forecast Balance, Forecast Allocated In/Out และ Forecast Reserve
- Projected BOQ Margin ล่าสุดจาก BOQ Comparison เป็น source-of-truth
- Raw Forecast Available positive/zero/negative
- Decimal precision และ rounding สองตำแหน่ง
- `PAID`, `APPROVED`, Income, Expense และ commitment ไม่เปลี่ยน Available Margin
- Balance version เปลี่ยนเมื่อ BOQ Margin, opening forecast, reserve หรือ ledger ที่เกี่ยวข้องเปลี่ยน
- Initial Balance Start Date ต้องเป็นวันที่ 1 ของเดือน
- Monthly Forecast Opening เท่ากับ Previous Month Forecast Closing และไม่สร้าง movement ซ้ำ

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
- Allocation ไม่เปลี่ยน BOQ/Input Request/actual cashflow values และไม่เปลี่ยน Projected BOQ Margin ต้นทาง
- Subcontractor project options ไม่คืน Operations
- Subcontractor ที่ส่ง Operations project id โดยตรงได้รับ `403`
- Initial Opening Forecast Balance สร้างได้ครั้งเดียวโดย Owner
- Monthly forecast roll-forward ไม่สร้าง Income/Expense/Allocation entries

### 13.3 Frontend Tests

- Owner/Admin rendering
- Button disabled เมื่อ Available Margin เป็น 0 หรือมี Forecast Deficit
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

### Phase 0 — Revised Decision Freeze และ Forecast Reconciliation

- [x] ยืนยันว่า V1 เป็น Forecast Margin Allocation และไม่ใช้ Paid/Approved/actual cashflow เป็นเพดาน
- [ ] ยืนยันว่า BOQ Comparison calculation เป็น source-of-truth เดียวของ Projected BOQ Margin
- [ ] ตรวจยอดและ UUID ของ existing `โครงการบริษัท` ใน Demo/Beta
- [ ] ยืนยัน display name ของ Operations
- [ ] Accounting/Admin เตรียม Initial Opening Forecast Balance working paper
- [ ] Owner เลือกเดือนเริ่มต้น; ระบบใช้วันที่ 1 เป็น Balance Start Date
- [ ] Owner กรอกและยืนยัน Initial Opening Forecast Balance ใน activation flow
- [ ] เก็บตัวอย่าง Project จริงอย่างน้อย 3 รายการเพื่อเทียบ Projected Margin, Allocated In/Out, Reserve และ Available Margin
- [ ] Audit implementation ปัจจุบันและจัดทำ change set เพื่อตัด Paid/Approved ออกจากสูตรก่อนเปิด mutation

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
- [ ] Reconcile summary กับ BOQ Margin และ forecast ledger

Exit gate: fund summary ของ sample projects ตรงกับการคำนวณ manual

### Phase 3 — Atomic Allocation

- [ ] Implement posting/idempotency/locking
- [ ] Implement reversal
- [ ] เพิ่ม audit events
- [ ] ทำ concurrency/failure tests

Exit gate: ไม่มีรายการใหม่เกิน Available Margin และไม่มี partial ledger entry ใน test matrix; Forecast Deficit จาก BOQ ที่ลดลงแสดงได้โดยไม่แก้ประวัติเดิม

### Phase 4 — Frontend UX

- [ ] Project Forecast cards และแยก actual cashflow ออกจากสูตร
- [ ] Margin Allocation Dialog
- [ ] Margin Allocation Ledger
- [ ] Company Operations presentation
- [ ] Responsive/accessibility states

Exit gate: lint/build ผ่านและ Owner walkthrough ผ่านทุก primary/error flow

### Phase 5 — Demo Rollout

- [ ] เปิดด้วย feature flag `FUND_ALLOCATION_ENABLED`
- [ ] Run migration/bootstrap
- [ ] Owner ยืนยัน Initial Opening Forecast Balance (รวมกรณียืนยันยอด 0) และเดือนเริ่มต้นผ่าน activation flow
- [ ] Reconcile forecast totals ก่อนเปิด mutation
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
- `INSUFFICIENT_AVAILABLE_MARGIN` count
- `STALE_FUND_BALANCE` count
- Duplicate idempotency replay count
- Posting latency
- Ledger imbalance count ซึ่งต้องเป็น 0
- Operations bucket duplication count ซึ่งต้องเป็น 0
- Project ที่ Raw Forecast Available ติดลบหลัง BOQ Margin เปลี่ยน
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
2. Owner เห็น Projected BOQ Margin เป็น forecast base และ Available Margin to Allocate เป็นยอดคงเหลือหลัง Allocated In/Out และ Forecast Reserve
3. Owner จัดสรร Margin ได้ไม่เกิน server-calculated Available Margin
4. Admin อ่าน summary/history ได้แต่ mutate ไม่ได้
5. Allocation ทุกตัวมี atomic debit/credit entries และ audit trail
6. Duplicate/concurrent requests ไม่ทำให้ยอดซ้ำหรือสร้าง Allocation เกิน Available Margin ณ เวลาที่ transaction ยืนยัน
7. Reverse สร้างประวัติใหม่และไม่ลบรายการเดิม
8. BOQ, Variance, Input Request และ actual cashflow ไม่ถูกแก้โดย allocation
9. Operations ไม่ปะปนใน Construction KPI/Project Health
10. Migration, backend tests, frontend lint/build และ manual walkthrough ผ่าน
11. Demo/Beta reconciliation ไม่พบ ledger imbalance
12. User-facing copy ระบุชัดว่าเป็นการจัดสรร Margin คาดการณ์ ไม่ใช่เงินสดจริงหรือ bank transfer
13. Initial Opening Forecast Balance ถูกยืนยันโดย Owner และ Balance Start Date เป็นวันที่ 1 ของเดือน
14. Monthly Forecast Opening ยกจาก Previous Month Forecast Closing อัตโนมัติโดยไม่สร้าง movement ซ้ำ
15. Subcontractor ไม่เห็น ไม่เลือก และไม่สามารถส่งรายการเข้า Company Operations ได้ทั้งจาก UI และ API
16. การเปลี่ยนสถานะ `PENDING_ADMIN`/`APPROVED`/`PAID` ไม่เปลี่ยน Available Margin
17. เมื่อ BOQ Margin ลดต่ำกว่ายอดที่จัดสรรไปแล้ว ระบบคง ledger เดิม แสดง Forecast Deficit และ block allocation ออกเพิ่ม

## 18. Confirmed Decisions และ Activation Inputs

Product decisions เพียงพอสำหรับเริ่ม implementation แล้ว:

| ID | ข้อสรุป | สถานะ |
|---|---|---|
| C-01 | ชื่อ `Company Operations / ค่าใช้จ่ายส่วนกลาง` | Confirmed |
| C-02 | Paid/Approved/Input Request/actual cashflow ไม่อยู่ในสูตร Forecast Margin Allocation | Confirmed revised baseline |
| C-03 | Accounting/Admin เตรียมตัวเลข; Owner กรอกและยืนยัน Initial Opening Forecast Balance | Confirmed |
| C-04 | Balance Start Date เป็นวันที่ 1 ของเดือนที่ Owner เลือก | Confirmed |
| C-05 | เดือนถัดไปยก Previous Month Forecast Closing เป็น Monthly Forecast Opening อัตโนมัติ | Confirmed |
| C-06 | Forecast Reserve เริ่มที่ 0 และยังไม่มี UI แก้ไขใน V1 | Confirmed baseline |
| C-07 | Project-to-Project และ Operations-to-Project allocation ใช้ validation เดียวกัน | Confirmed |
| C-08 | Subcontractor ไม่มี Operations visibility และเลือก/ส่งรายการเข้า Operations ไม่ได้ | Confirmed |
| C-09 | Forecast Margin Allocation จาก Projected BOQ Margin อยู่ใน V1 | Confirmed revised baseline |
| C-10 | Forecast Allocated In เพิ่ม Available Margin ของปลายทางและจัดสรรต่อได้ | Confirmed |
| C-11 | BOQ Margin ล่าสุดเปลี่ยน forecast base โดยไม่แก้ posted allocation เดิม | Confirmed |

Activation inputs ที่ยังไม่ต้องทราบตอนเขียนระบบ:

- จำนวน Initial Opening Forecast Balance ที่ Owner จะกรอก
- เดือนแรกที่เลือกเปิดใช้งาน
- หลักฐาน/working paper จาก Accounting/Admin
- Observation window บน Demo; ค่าแนะนำอย่างน้อย 3–5 วันทำการหรือครบ use cases ที่กำหนด

## 19. Suggested V2 Backlog

- Percentage rule เช่นจัดสรร 20% เข้า Operations
- Recurring monthly allocation
- Forecast Reserve management UI
- Allocation approval แบบ two-person control
- Notifications เมื่อ Project มี Forecast Deficit
- Company-level bucket board แบบ MAKE-style overview
- Forecast เปรียบเทียบ Margin Allocation กับ actual cashflow
- Actual cash allocation และ Bank/accounting reconciliation โดยเป็นโครงการแยกและไม่เปลี่ยน semantics ของ Forecast Margin Allocation
