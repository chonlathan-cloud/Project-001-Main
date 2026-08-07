# Default Company Operations — Product & UX Plan

> Approved revised concept สำหรับ Default Operations System Project และประสบการณ์ใช้งานแบบ Forecast Margin Bucket

| รายการ | ค่า |
|---|---|
| สถานะ | Approved revised baseline — implementation alignment required |
| วันที่อัปเดต | 2026-08-07 |
| Default display name | `Company Operations` |
| Thai description | `ค่าใช้จ่ายส่วนกลางของบริษัท` |
| System identifier | `OPERATIONS` |
| Mutation role | `owner` เท่านั้น |
| Initial forecast owner | Owner เป็นผู้ระบุและยืนยัน Opening Forecast Balance ในระบบ |
| Balance start rule | วันที่ 1 ของเดือนที่เลือกเริ่มใช้งาน |
| Related implementation plan | [actionplan.md](actionplan.md) |

## 1. Product Concept

`Company Operations` คือ “กระเป๋า Forecast กลางของบริษัท” สำหรับรับ Margin ที่จัดสรรมาจาก Project และวางแผนงบดำเนินงานส่วนกลาง เช่น เงินเดือน ค่าเช่า Software ค่าใช้จ่ายสำนักงาน ภาษี และค่าใช้จ่ายบริหาร

Forecast Margin Allocation เป็นการบริหารประมาณการ ไม่ใช่เงินสดจริงและไม่ผูกกับสถานะ `PENDING_ADMIN`, `APPROVED` หรือ `PAID` ส่วนรายรับ–รายจ่ายจริงยังคงแสดงเป็น Cashflow แยกต่างหาก Operations ไม่ถือเป็น Construction Project และต้องไม่แสดงข้อมูล BOQ หรือความคืบหน้างาน

## 2. Default Operations Rules

1. ทุกบริษัท/ทุก deployment มี Operations System Project เพียงหนึ่งรายการ
2. ระบบสร้างหรือ upgrade Operations ระหว่าง migration/bootstrap ผู้ใช้ไม่ต้องกดสร้างเอง
3. ระบบปัจจุบันต้องใช้ `โครงการบริษัท` ชนิด `INTERNAL` และ UUID เดิมเป็นฐาน ห้ามสร้างรายการซ้ำ
4. ใช้ `system_key='OPERATIONS'` ในการค้นหา ห้ามอิงชื่อที่แสดง
5. Owner เปลี่ยน display name ได้ แต่เปลี่ยน system key/type ไม่ได้
6. Operations ลบ, Archive หรือเปลี่ยนเป็น Construction Project ไม่ได้
7. Operations ไม่รวมใน Active Construction Project count, Project Health, Progress, Risk และ BOQ KPI
8. Project ใหม่ทุก Project ต้องมี Fund Bucket ของตัวเอง แต่จะไม่สร้าง Operations เพิ่ม
9. Owner เป็นผู้ระบุ Initial Opening Forecast Balance ในระบบเพียงครั้งแรก เพราะ Operations ไม่มี BOQ Margin
10. Accounting/Admin เตรียมและตรวจตัวเลข ส่วน Owner ตรวจและยืนยันขั้นสุดท้าย
11. Balance Start Date ต้องเป็นวันที่ 1 ของเดือนที่ Owner เลือกเริ่มใช้งาน
12. ตั้งแต่เดือนถัดไป Monthly Forecast Opening ต้องยกมาจาก Previous Month Forecast Closing โดยอัตโนมัติ ห้ามกรอกใหม่ทุกเดือน
13. Company Operations เป็น Internal-only และไม่เกี่ยวข้องกับ Subcontractor ทุกกรณี

## 3. Information Architecture

หน้า Projects แบ่งเป็นสองส่วน:

```text
PROJECTS

Company Funds
┌───────────────────────────────────────────┐
│ Company Operations        [System Bucket] │
│ ค่าใช้จ่ายส่วนกลางของบริษัท               │
│                                           │
│ Available Margin       ฿500,000           │
│ Allocated In           ฿200,000           │
│ Allocated Out           ฿50,000           │
│                                           │
│ [เปิดดู]       [จัดสรร Margin]            │
└───────────────────────────────────────────┘

Active Construction Projects
┌──────────────────┐  ┌──────────────────┐
│ SENA Park        │  │ Office Renovation│
└──────────────────┘  └──────────────────┘
```

### UX Rules บนหน้า Projects

- ปักหมุด Operations ไว้บนสุดในส่วน `Company Funds`
- แสดง badge `System Bucket`
- Owner เห็นปุ่ม `จัดสรร Margin`
- Admin เห็นข้อมูลแบบ read-only พร้อม badge `Read only` และไม่แสดง mutation controls
- ถ้ามี Forecast Deficit ให้แสดงจำนวนและสถานะอย่างชัดเจน โดยไม่ใช้สีเพียงอย่างเดียว
- Operations ไม่ถูกค้นหาหรือกรองปะปนกับ Construction status โดยไม่ตั้งใจ

## 4. Company Operations Detail Page

หน้า Operations ใช้ header และ visual language เดียวกับ Project Detail แต่ตัดส่วนที่เกี่ยวกับการก่อสร้างออก

```text
Company Operations                         [System Bucket]
ค่าใช้จ่ายส่วนกลางของบริษัท

┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ Available Margin│ │ Allocated In    │ │ Allocated Out   │
│ ฿500,000        │ │ ฿200,000        │ │ ฿50,000         │
│ [จัดสรร Margin] │ │ Forecast        │ │ Forecast        │
└─────────────────┘ └─────────────────┘ └─────────────────┘

[ภาพรวม] [รายจ่ายจริง] [การจัดสรร Margin]

รายการล่าสุด
SENA Park → Company Operations      +฿200,000
Company Operations → Project B      −฿50,000
```

### 4.1 Header

- ชื่อ `Company Operations`
- คำอธิบาย `ค่าใช้จ่ายส่วนกลางของบริษัท`
- badge `System Bucket`
- ไม่แสดง Customer, Construction status หรือ progress
- Owner สามารถแก้ display name ผ่าน Settings ที่กำหนด ไม่แก้ system identity

### 4.2 Summary Cards

1. `Available Margin to Allocate`
   - Forecast Margin ที่ยังสามารถจัดสรรออกได้
   - Owner มีปุ่ม `จัดสรร Margin`
   - ถ้ายอดเป็น 0 ปุ่ม disabled พร้อมข้อความอธิบาย
2. `Forecast Allocated In`
   - Margin ที่ Operations ได้รับจาก Project Buckets
3. `Forecast Allocated Out`
   - Margin ที่ Operations จัดสรรกลับไปยัง Project Buckets

Approved Commitments และ Paid This Month อาจแสดงเป็น secondary Cashflow metrics แต่ต้องระบุว่าเป็น actual activity และไม่มีผลต่อ Available Margin

### 4.3 Tabs

#### ภาพรวม

- Summary cards
- รายการรายจ่ายล่าสุด
- Margin Allocation ล่าสุด
- Forecast Deficit warning ถ้ามี

#### รายจ่ายจริง

- แสดง Input Requests ที่ผูกกับ Operations
- แยก Pending, Approved และ Paid
- ใช้ approval/payment flow ปัจจุบัน
- Margin Allocation ไม่ถูกแสดงเป็น Income/Expense และสถานะของรายการเหล่านี้ไม่เปลี่ยน Available Margin

#### การจัดสรร Margin

- Allocation In และ Allocation Out
- From, To, Amount, Reason, Reference, Actor และ Timestamp
- Allocation detail และ Reverse action สำหรับ Owner
- Admin อ่านได้แต่ Reverse ไม่ได้

### 4.4 สิ่งที่ห้ามแสดง

- Customer BOQ
- Subcontractor BOQ
- Projected BOQ Margin/Total Variance
- Matching Coverage
- Construction Progress
- Execution/BOQ charts
- Risk/Health ที่คำนวณแบบ Construction Project

## 5. First-use และ Empty State

หาก Operations ยังไม่มียอด:

```text
Available Margin to Allocate
฿0.00

ยังไม่มี Forecast Margin ใน Company Operations

[กำหนด Opening Forecast]  [รับ Margin จาก Project]
```

### กำหนด Opening Forecast Balance

- แสดงเฉพาะ Owner และเฉพาะเมื่อยังไม่มี Initial Opening Forecast Balance entry
- Accounting/Admin เป็นผู้เตรียมและตรวจสอบตัวเลขให้ Owner
- Owner เป็นผู้กรอก Amount, เลือกเดือนเริ่มต้น และยืนยันขั้นสุดท้ายในระบบ
- Effective Date ถูกกำหนดเป็นวันที่ 1 ของเดือนที่เลือกโดยอัตโนมัติ
- ต้องกรอก Reason และแสดง Preview ก่อนยืนยัน
- แจ้งชัดเจนว่าเป็น Forecast Budget ตั้งต้น ไม่ใช่เงินสด ยอดธนาคาร หรือรายการรับเงินจากลูกค้า
- บันทึกเป็น immutable `OPENING_BALANCE` ledger entry ที่มี forecast semantics
- หากผิดให้ใช้ Adjustment/Reverse ห้ามแก้หรือลบ record เดิม

### Monthly Forecast Roll-forward

Opening Forecast Balance ไม่ใช่ยอดที่ Owner ต้องกรอกทุกเดือน ระบบต้องยกยอดให้อัตโนมัติ:

```text
Forecast Closing Balance เดือนสิงหาคม
            ↓ อัตโนมัติ
Forecast Opening Balance วันที่ 1 กันยายน
```

- Initial Opening Forecast Balance กรอกเพียงครั้งแรกตอนเปิดใช้งาน
- วันที่ 1 ของเดือนถัดไป `Monthly Forecast Opening = Previous Month Forecast Closing`
- การยกยอดรายเดือนไม่สร้าง Income, Expense หรือ Allocation ใหม่
- Forecast movement ก่อน Balance Start Date ถูกรวมอยู่ใน Initial Opening Forecast Balance และต้องไม่ถูกนำมาคำนวณซ้ำ
- หากต้องแก้ไขยอด ใช้ Adjustment/Reverse พร้อม Audit Trail ไม่แก้ Monthly Forecast Opening โดยตรง

### รับ Margin จาก Project

- เปิด Allocation Dialog
- Source ให้ Owner เลือก Active Project ที่มี Available Margin
- Target ล็อกเป็น Company Operations
- แสดงยอดก่อน–หลังทั้งสองฝั่งก่อนยืนยัน

## 6. Allocation UX

### 6.1 จาก Construction Project

เมื่อ Owner กด `จัดสรร Margin` จาก Project ทั่วไป:

```text
From: SENA Park
To:   Company Operations  ← default selection
```

- Company Operations เป็นปลายทางแรก
- Owner เปลี่ยนเป็น Active Project อื่นได้
- จำนวนสูงสุดคือ Available Margin to Allocate ของ Source
- Projected BOQ Margin เป็น forecast base ของ Project และถูกใช้ในสูตรเพดานร่วมกับ Forecast Allocated In/Out และ Forecast Reserve
- Paid/Approved Income, Expense และ commitment ไม่มีผลต่อเพดานนี้

### 6.2 จาก Company Operations

เมื่อ Owner กด `จัดสรร Margin` จาก Operations:

```text
From: Company Operations
To:   เลือก Active Project
```

ใช้สำหรับจัดสรร forecast capacity กลับไปช่วย Project และอยู่ภายใต้ validation เดียวกัน ไม่ได้ยืนยันว่ามีการเติมเงินสดจริง

### 6.3 Dialog Fields

1. From — locked เมื่อเปิดจาก detail page
2. Available Margin — server-calculated forecast balance
3. To — Active destination selector
4. Amount — numeric/decimal input
5. `ใช้ยอดสูงสุด`
6. Reason — required
7. Before/After Preview
8. `ยืนยันจัดสรร Margin ฿X`

ข้อความบังคับ:

> เป็นการจัดสรร Margin ที่คาดการณ์ภายในระบบ ไม่ใช่เงินสดจริงและไม่ได้ทำรายการโอนผ่านธนาคาร

## 7. User Permissions

| Capability | Owner | Admin | Subcontractor |
|---|---:|---:|---:|
| เห็น Operations Detail | Yes | Yes | No |
| เห็น Available Margin/Forecast Allocation | Yes | Yes | No |
| เห็น Allocation History | Yes | Yes | No |
| จัดสรร Margin | Yes | No | No |
| Reverse Allocation | Yes | No | No |
| กำหนด Opening Forecast Balance | Yes | No | No |
| เปลี่ยน display name | Yes | No | No |
| ลบ/Archive Operations | No | No | No |

### Subcontractor Input Policy

Company Operations เป็น Internal-only และไม่มีความสัมพันธ์กับ Subcontractor:

- Subcontractor เห็นเฉพาะ Projects ที่ได้รับมอบหมายให้เข้าไปทำงาน
- Company Operations ต้องไม่ปรากฏใน Project selector ของ Subcontractor
- Subcontractor ส่ง Income หรือ Expense เข้า Operations ไม่ได้
- Subcontractor ไม่เห็นหน้า Operations, Available Margin, Opening Forecast Balance, Commitments หรือ Allocation History
- ค่าใช้จ่าย Operations ถูกบันทึกผ่าน Internal Input Flow โดยผู้ใช้ภายในที่ได้รับสิทธิ์; V1 ให้ Owner เป็นผู้ mutation และ Admin/Accounting เตรียม–ตรวจข้อมูลแบบ read-only
- หาก Subcontractor ทำงานให้บริษัท เช่นปรับปรุงสำนักงาน ต้องสร้าง Construction/Internal Work Project จริงและ assign ให้ Subcontractor ห้ามใช้ Company Operations แทน Project

## 8. Loading, Error และ Protection States

- Loading summary/history
- Empty Operations
- Opening Forecast Balance required
- Forecast Deficit
- Available Margin เท่ากับ 0
- Read-only Admin
- Feature disabled
- Operations bucket missing/configuration error
- Stale balance ระหว่างเปิด Dialog
- Insufficient available margin
- Duplicate submit
- Allocation success
- Reverse blocked เพราะ target Available Margin ไม่พอ

หาก Operations record หาย ระบบไม่ควรสร้างใหม่จากหน้า UI แบบเงียบ ๆ เพราะอาจเกิด duplicate ให้แสดง configuration error และใช้ bootstrap/recovery process ที่ตรวจสอบได้

## 9. Required User-facing Copy

| จุดใช้งาน | Copy |
|---|---|
| Operations title | `Company Operations` |
| Operations subtitle | `ค่าใช้จ่ายส่วนกลางของบริษัท` |
| System badge | `System Bucket` |
| Available card | `Available Margin to Allocate` / `Margin พร้อมจัดสรร` |
| Zero balance | `ยังไม่มี Forecast Margin ที่สามารถจัดสรรได้` |
| Deficit | `Forecast Margin ต่ำกว่ายอดที่จัดสรรไปแล้ว` |
| Allocation CTA | `จัดสรร Margin` |
| Opening CTA | `กำหนด Opening Forecast Balance` |
| Internal-only notice | `เป็นการจัดสรร Margin ที่คาดการณ์ ไม่ใช่เงินสดจริงและไม่ได้ทำรายการโอนผ่านธนาคาร` |
| Admin state | `Read only — Owner permission is required` |

## 10. UX Acceptance Criteria

1. Operations อยู่บนสุดในส่วน Company Funds และแยกจาก Construction Projects อย่างชัดเจน
2. ผู้ใช้เข้าใจจากหน้าแรกว่า Operations คือค่าใช้จ่ายส่วนกลาง ไม่ใช่งานก่อสร้าง
3. Operations ไม่มี BOQ, Margin หรือ Progress UI
4. Owner เข้าถึง Margin Allocation ได้ภายในไม่เกินสอง actions จากหน้า Projects
5. Company Operations ถูกเลือกเป็น destination เริ่มต้นเมื่อจัดสรรจาก Construction Project
6. Owner เห็น Before/After Preview ก่อนยืนยัน
7. Admin เห็นข้อมูลครบแต่ไม่มี mutation controls
8. Subcontractor ไม่เห็นหน้า Operations หรือยอดการเงิน
9. Empty/Forecast Deficit/Error states มีคำแนะนำที่ดำเนินการต่อได้
10. ลบ/Archive/สร้าง Operations ซ้ำผ่าน UI ไม่ได้
11. Mobile และ keyboard flow ใช้งาน Primary/Reverse flow ได้ครบ
12. Allocation ถูกนำเสนอว่าเป็น Forecast Margin ไม่ใช่ Bank Transfer, เงินสดจริง หรือ Income/Expense
13. การเปลี่ยนสถานะ `PENDING_ADMIN`/`APPROVED`/`PAID` ไม่เปลี่ยน Available Margin หรือสถานะปุ่ม
14. เมื่อ BOQ Margin ลดต่ำกว่ายอดที่จัดสรรไปแล้ว ระบบแสดง Forecast Deficit และไม่แก้ประวัติเดิม

## 11. Activation Inputs

Product/UX decisions เพียงพอสำหรับเริ่ม implementation แล้ว ข้อมูลต่อไปนี้ให้ระบุในขั้นตอนเปิดใช้งาน ไม่จำเป็นต้องทราบตอนเขียนระบบ:

1. จำนวน Initial Opening Forecast Balance ที่ Owner จะกรอก
2. เดือนแรกที่เลือกเปิดใช้งาน โดยระบบใช้วันที่ 1 ของเดือนนั้นเป็น Balance Start Date
3. หลักฐานหรือ working paper ที่ Accounting/Admin ใช้เตรียมตัวเลข
4. ช่วง observation บน Demo ก่อน rollout ไป Beta

ค่าตั้งต้นสำหรับการพัฒนาสามารถใช้:

- Display name: `Company Operations`
- Thai subtitle: `ค่าใช้จ่ายส่วนกลางของบริษัท`
- Forecast Reserve: 0
- Operations เป็น default allocation destination
- Owner-only mutation และ Admin read-only
- Accounting/Admin เตรียมตัวเลข และ Owner กรอก/ยืนยัน Initial Opening Forecast Balance
- Monthly Forecast Opening ยกมาจาก Previous Month Forecast Closing อัตโนมัติ
- Subcontractor ไม่มี Operations visibility และเลือก/ส่งรายการเข้า Operations ไม่ได้
