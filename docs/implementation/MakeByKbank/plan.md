# Default Company Operations — Product & UX Plan

> Approved concept สำหรับ Default Operations System Project และประสบการณ์ใช้งานแบบ Project Bucket

| รายการ | ค่า |
|---|---|
| สถานะ | Approved concept — implementation not started |
| วันที่อัปเดต | 2026-08-06 |
| Default display name | `Company Operations` |
| Thai description | `ค่าใช้จ่ายส่วนกลางของบริษัท` |
| System identifier | `OPERATIONS` |
| Mutation role | `owner` เท่านั้น |
| Initial balance owner | Owner เป็นผู้ระบุและยืนยันในระบบ |
| Balance start rule | วันที่ 1 ของเดือนที่เลือกเริ่มใช้งาน |
| Related implementation plan | [actionplan.md](actionplan.md) |

## 1. Product Concept

`Company Operations` คือ “กระเป๋ากลางของบริษัท” สำหรับรับเงินที่จัดสรรมาจาก Project และรองรับรายจ่ายส่วนกลาง เช่น เงินเดือน ค่าเช่า Software ค่าใช้จ่ายสำนักงาน ภาษี และค่าใช้จ่ายบริหาร

Operations อยู่ในระบบ Projects เพื่อใช้ flow รายรับ–รายจ่ายและสิทธิ์เดิมร่วมกัน แต่ไม่ถือเป็น Construction Project และต้องไม่แสดงข้อมูล BOQ หรือความคืบหน้างาน

## 2. Default Operations Rules

1. ทุกบริษัท/ทุก deployment มี Operations System Project เพียงหนึ่งรายการ
2. ระบบสร้างหรือ upgrade Operations ระหว่าง migration/bootstrap ผู้ใช้ไม่ต้องกดสร้างเอง
3. ระบบปัจจุบันต้องใช้ `โครงการบริษัท` ชนิด `INTERNAL` และ UUID เดิมเป็นฐาน ห้ามสร้างรายการซ้ำ
4. ใช้ `system_key='OPERATIONS'` ในการค้นหา ห้ามอิงชื่อที่แสดง
5. Owner เปลี่ยน display name ได้ แต่เปลี่ยน system key/type ไม่ได้
6. Operations ลบ, Archive หรือเปลี่ยนเป็น Construction Project ไม่ได้
7. Operations ไม่รวมใน Active Construction Project count, Project Health, Progress, Risk และ BOQ KPI
8. Project ใหม่ทุก Project ต้องมี Fund Bucket ของตัวเอง แต่จะไม่สร้าง Operations เพิ่ม
9. Owner เป็นผู้ระบุ Initial Opening Balance ในระบบเพียงครั้งแรก
10. Accounting/Admin เตรียมและตรวจตัวเลข ส่วน Owner ตรวจและยืนยันขั้นสุดท้าย
11. Balance Start Date ต้องเป็นวันที่ 1 ของเดือนที่ Owner เลือกเริ่มใช้งาน
12. ตั้งแต่เดือนถัดไป Opening Balance ต้องยกมาจาก Closing Balance เดือนก่อนโดยอัตโนมัติ ห้ามกรอกใหม่ทุกเดือน
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
│ Available              ฿500,000           │
│ รอจ่าย                 ฿120,000           │
│ จ่ายเดือนนี้            ฿85,000           │
│                                           │
│ [เปิดดู]       [จัดสรรเงิน]               │
└───────────────────────────────────────────┘

Active Construction Projects
┌──────────────────┐  ┌──────────────────┐
│ SENA Park        │  │ Office Renovation│
└──────────────────┘  └──────────────────┘
```

### UX Rules บนหน้า Projects

- ปักหมุด Operations ไว้บนสุดในส่วน `Company Funds`
- แสดง badge `System Bucket`
- Owner เห็นปุ่ม `จัดสรรเงิน`
- Admin เห็นข้อมูลแบบ read-only พร้อม badge `Read only` และไม่แสดง mutation controls
- ถ้ามี Funding Deficit ให้แสดงจำนวนและสถานะอย่างชัดเจน โดยไม่ใช้สีเพียงอย่างเดียว
- Operations ไม่ถูกค้นหาหรือกรองปะปนกับ Construction status โดยไม่ตั้งใจ

## 4. Company Operations Detail Page

หน้า Operations ใช้ header และ visual language เดียวกับ Project Detail แต่ตัดส่วนที่เกี่ยวกับการก่อสร้างออก

```text
Company Operations                         [System Bucket]
ค่าใช้จ่ายส่วนกลางของบริษัท

┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ Available       │ │ Approved        │ │ Paid This Month │
│ ฿500,000        │ │ ฿120,000        │ │ ฿85,000         │
│ [จัดสรรเงิน]    │ │ รอจ่าย          │ │ 8 รายการ        │
└─────────────────┘ └─────────────────┘ └─────────────────┘

[ภาพรวม] [รายจ่าย] [การจัดสรรเงิน]

รายการล่าสุด
SENA Park → Company Operations      +฿200,000
ค่าเช่า Software                    −฿12,000
ค่าใช้จ่ายสำนักงาน                  −฿8,500
```

### 4.1 Header

- ชื่อ `Company Operations`
- คำอธิบาย `ค่าใช้จ่ายส่วนกลางของบริษัท`
- badge `System Bucket`
- ไม่แสดง Customer, Construction status หรือ progress
- Owner สามารถแก้ display name ผ่าน Settings ที่กำหนด ไม่แก้ system identity

### 4.2 Summary Cards

1. `Available to Allocate`
   - ยอดที่สามารถจัดสรรออกได้จริง
   - Owner มีปุ่ม `จัดสรรเงิน`
   - ถ้ายอดเป็น 0 ปุ่ม disabled พร้อมข้อความอธิบาย
2. `Approved — รอจ่าย`
   - Approved Expense Commitments ที่ยังไม่ `PAID`
3. `Paid This Month — จ่ายเดือนนี้`
   - รายจ่าย Operations ที่ `PAID` ภายในเดือนปัจจุบัน

อาจเพิ่ม `Allocated In/Out` เป็น secondary metrics เมื่อมีข้อมูลเพียงพอ แต่ไม่ควรทำให้ summary หลักแน่นเกินไป

### 4.3 Tabs

#### ภาพรวม

- Summary cards
- รายการรายจ่ายล่าสุด
- Allocation ล่าสุด
- Funding Deficit warning ถ้ามี

#### รายจ่าย

- แสดง Input Requests ที่ผูกกับ Operations
- แยก Pending, Approved และ Paid
- ใช้ approval/payment flow ปัจจุบัน
- Allocation ไม่ถูกแสดงเป็น Income/Expense

#### การจัดสรรเงิน

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
Available to Allocate
฿0.00

ยังไม่มีเงินใน Company Operations

[กำหนดยอดเริ่มต้น]  [รับเงินจาก Project]
```

### กำหนดยอดเริ่มต้น

- แสดงเฉพาะ Owner และเฉพาะเมื่อยังไม่มี Initial Opening Balance entry
- Accounting/Admin เป็นผู้เตรียมและตรวจสอบตัวเลขให้ Owner
- Owner เป็นผู้กรอก Amount, เลือกเดือนเริ่มต้น และยืนยันขั้นสุดท้ายในระบบ
- Effective Date ถูกกำหนดเป็นวันที่ 1 ของเดือนที่เลือกโดยอัตโนมัติ
- ต้องกรอก Reason และแสดง Preview ก่อนยืนยัน
- แจ้งชัดเจนว่าเป็นยอดเปิดระบบ ไม่ใช่รายการรับเงินจากลูกค้า
- บันทึกเป็น immutable `OPENING_BALANCE` ledger entry
- หากผิดให้ใช้ Adjustment/Reverse ห้ามแก้หรือลบ record เดิม

### Monthly Roll-forward

Opening Balance ไม่ใช่ยอดที่ Owner ต้องกรอกทุกเดือน ระบบต้องยกยอดให้อัตโนมัติ:

```text
Closing Balance เดือนสิงหาคม
            ↓ อัตโนมัติ
Opening Balance วันที่ 1 กันยายน
```

- Initial Opening Balance กรอกเพียงครั้งแรกตอนเปิดใช้งาน
- วันที่ 1 ของเดือนถัดไป `Monthly Opening = Previous Month Closing`
- การยกยอดรายเดือนไม่สร้าง Income, Expense หรือ Allocation ใหม่
- รายการก่อน Balance Start Date ถูกรวมอยู่ใน Initial Opening Balance และต้องไม่ถูกนำมาคำนวณซ้ำ
- หากต้องแก้ไขยอด ใช้ Adjustment/Reverse พร้อม Audit Trail ไม่แก้ยอดเปิดเดือนโดยตรง

### รับเงินจาก Project

- เปิด Allocation Dialog
- Source ให้ Owner เลือก Active Project ที่มี Available
- Target ล็อกเป็น Company Operations
- แสดงยอดก่อน–หลังทั้งสองฝั่งก่อนยืนยัน

## 6. Allocation UX

### 6.1 จาก Construction Project

เมื่อ Owner กด `จัดสรรเงิน` จาก Project ทั่วไป:

```text
From: SENA Park
To:   Company Operations  ← default selection
```

- Company Operations เป็นปลายทางแรก
- Owner เปลี่ยนเป็น Active Project อื่นได้
- จำนวนสูงสุดคือ Available to Allocate ของ Source
- Projected BOQ Margin ไม่ถูกใช้เป็นเพดาน

### 6.2 จาก Company Operations

เมื่อ Owner กด `จัดสรรเงิน` จาก Operations:

```text
From: Company Operations
To:   เลือก Active Project
```

ใช้สำหรับเติมสภาพคล่องกลับไปยัง Project และอยู่ภายใต้ validation เดียวกัน

### 6.3 Dialog Fields

1. From — locked เมื่อเปิดจาก detail page
2. Available — server-calculated balance
3. To — Active destination selector
4. Amount — numeric/decimal input
5. `ใช้ยอดสูงสุด`
6. Reason — required
7. Before/After Preview
8. `ยืนยันจัดสรร ฿X`

ข้อความบังคับ:

> เป็นการจัดสรรเงินภายในระบบ ไม่ได้ทำรายการโอนผ่านธนาคาร

## 7. User Permissions

| Capability | Owner | Admin | Subcontractor |
|---|---:|---:|---:|
| เห็น Operations Detail | Yes | Yes | No |
| เห็น Available/Commitments | Yes | Yes | No |
| เห็น Allocation History | Yes | Yes | No |
| จัดสรรเงิน | Yes | No | No |
| Reverse Allocation | Yes | No | No |
| กำหนด Opening Balance | Yes | No | No |
| เปลี่ยน display name | Yes | No | No |
| ลบ/Archive Operations | No | No | No |

### Subcontractor Input Policy

Company Operations เป็น Internal-only และไม่มีความสัมพันธ์กับ Subcontractor:

- Subcontractor เห็นเฉพาะ Projects ที่ได้รับมอบหมายให้เข้าไปทำงาน
- Company Operations ต้องไม่ปรากฏใน Project selector ของ Subcontractor
- Subcontractor ส่ง Income หรือ Expense เข้า Operations ไม่ได้
- Subcontractor ไม่เห็นหน้า Operations, Available, Opening Balance, Commitments หรือ Allocation History
- ค่าใช้จ่าย Operations ถูกบันทึกผ่าน Internal Input Flow โดยผู้ใช้ภายในที่ได้รับสิทธิ์; V1 ให้ Owner เป็นผู้ mutation และ Admin/Accounting เตรียม–ตรวจข้อมูลแบบ read-only
- หาก Subcontractor ทำงานให้บริษัท เช่นปรับปรุงสำนักงาน ต้องสร้าง Construction/Internal Work Project จริงและ assign ให้ Subcontractor ห้ามใช้ Company Operations แทน Project

## 8. Loading, Error และ Protection States

- Loading summary/history
- Empty Operations
- Opening Balance required
- Funding Deficit
- Available เท่ากับ 0
- Read-only Admin
- Feature disabled
- Operations bucket missing/configuration error
- Stale balance ระหว่างเปิด Dialog
- Insufficient funds
- Duplicate submit
- Allocation success
- Reverse blocked เพราะ target available ไม่พอ

หาก Operations record หาย ระบบไม่ควรสร้างใหม่จากหน้า UI แบบเงียบ ๆ เพราะอาจเกิด duplicate ให้แสดง configuration error และใช้ bootstrap/recovery process ที่ตรวจสอบได้

## 9. Required User-facing Copy

| จุดใช้งาน | Copy |
|---|---|
| Operations title | `Company Operations` |
| Operations subtitle | `ค่าใช้จ่ายส่วนกลางของบริษัท` |
| System badge | `System Bucket` |
| Available card | `Available to Allocate` / `พร้อมจัดสรร` |
| Zero balance | `ยังไม่มีเงินที่สามารถจัดสรรได้` |
| Deficit | `ยอดที่ต้องเติมเพื่อรองรับภาระผูกพัน` |
| Allocation CTA | `จัดสรรเงิน` |
| Opening CTA | `กำหนดยอดเริ่มต้น` |
| Internal-only notice | `เป็นการจัดสรรเงินภายในระบบ ไม่ได้ทำรายการโอนผ่านธนาคาร` |
| Admin state | `Read only — Owner permission is required` |

## 10. UX Acceptance Criteria

1. Operations อยู่บนสุดในส่วน Company Funds และแยกจาก Construction Projects อย่างชัดเจน
2. ผู้ใช้เข้าใจจากหน้าแรกว่า Operations คือค่าใช้จ่ายส่วนกลาง ไม่ใช่งานก่อสร้าง
3. Operations ไม่มี BOQ, Margin หรือ Progress UI
4. Owner เข้าถึง Allocation ได้ภายในไม่เกินสอง actions จากหน้า Projects
5. Company Operations ถูกเลือกเป็น destination เริ่มต้นเมื่อจัดสรรจาก Construction Project
6. Owner เห็น Before/After Preview ก่อนยืนยัน
7. Admin เห็นข้อมูลครบแต่ไม่มี mutation controls
8. Subcontractor ไม่เห็นหน้า Operations หรือยอดการเงิน
9. Empty/Deficit/Error states มีคำแนะนำที่ดำเนินการต่อได้
10. ลบ/Archive/สร้าง Operations ซ้ำผ่าน UI ไม่ได้
11. Mobile และ keyboard flow ใช้งาน Primary/Reverse flow ได้ครบ
12. Allocation ไม่ถูกนำเสนอว่าเป็น Bank Transfer หรือ Income/Expense

## 11. Activation Inputs

Product/UX decisions เพียงพอสำหรับเริ่ม implementation แล้ว ข้อมูลต่อไปนี้ให้ระบุในขั้นตอนเปิดใช้งาน ไม่จำเป็นต้องทราบตอนเขียนระบบ:

1. จำนวน Initial Opening Balance ที่ Owner จะกรอก
2. เดือนแรกที่เลือกเปิดใช้งาน โดยระบบใช้วันที่ 1 ของเดือนนั้นเป็น Balance Start Date
3. หลักฐานหรือ working paper ที่ Accounting/Admin ใช้เตรียมตัวเลข
4. ช่วง observation บน Demo ก่อน rollout ไป Beta

ค่าตั้งต้นสำหรับการพัฒนาสามารถใช้:

- Display name: `Company Operations`
- Thai subtitle: `ค่าใช้จ่ายส่วนกลางของบริษัท`
- Protected Reserve: 0
- Operations เป็น default allocation destination
- Owner-only mutation และ Admin read-only
- Accounting/Admin เตรียมตัวเลข และ Owner กรอก/ยืนยัน Initial Opening Balance
- Monthly Opening Balance ยกมาจาก Previous Month Closing อัตโนมัติ
- Subcontractor ไม่มี Operations visibility และเลือก/ส่งรายการเข้า Operations ไม่ได้
