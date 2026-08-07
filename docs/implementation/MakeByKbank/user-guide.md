# คู่มือการใช้งาน Forecast Margin Allocation

> เอกสารต้นฉบับภาษาไทยสำหรับนำไปจัดทำคู่มือผู้ใช้งาน

| รายการ | รายละเอียด |
|---|---|
| ฟีเจอร์ | Forecast Margin Allocation / การจัดสรร Margin ที่คาดการณ์ |
| แนวคิด | แต่ละ Project เป็น Bucket และมี Company Operations เป็น Bucket กลางของบริษัท |
| ผู้สร้างและ Reverse รายการ | Owner |
| ผู้ดูข้อมูล | Owner และ Admin |
| วันที่จัดทำ | 7 สิงหาคม 2026 |
| เอกสารอ้างอิง | [Product & UX Plan](plan.md) และ [Implementation Action Plan](actionplan.md) |

## 1. ฟีเจอร์นี้ใช้ทำอะไร

Forecast Margin Allocation ใช้สำหรับวางแผนและจัดสรร Margin ที่คาดการณ์ระหว่าง Project ต่าง ๆ ภายในบริษัท โดยมองแต่ละ Project เป็น “Bucket” หรือ “กระเป๋างบประมาณ”

ตัวอย่างการใช้งาน:

- จัดสรร Margin จาก Project ไปยัง `Company Operations` เพื่อวางแผนค่าใช้จ่ายส่วนกลาง
- จัดสรร Margin จาก `Company Operations` ไปช่วย Project ที่ต้องการงบคาดการณ์เพิ่ม
- จัดสรร Margin จาก Project หนึ่งไปยังอีก Project หนึ่ง
- ตรวจสอบประวัติว่าใครจัดสรร Margin จำนวนเท่าไร เมื่อใด และด้วยเหตุผลใด
- Reverse รายการที่จัดสรรผิด โดยเก็บประวัติเดิมไว้เพื่อการตรวจสอบ

> **ข้อสำคัญ:** ฟีเจอร์นี้เป็นการจัดสรรตัวเลข Forecast ภายในระบบ ไม่ใช่เงินสดจริง ไม่ใช่ยอดบัญชีธนาคาร และไม่ได้ทำรายการโอนเงินผ่านธนาคาร

สถานะรายการการเงินจริง เช่น `Pending`, `Approved` หรือ `Paid` รวมถึงรายรับและรายจ่ายจริง ไม่มีผลต่อ Available Margin ของฟีเจอร์นี้

## 2. สิทธิ์ของผู้ใช้งาน

| ผู้ใช้งาน | ดูยอดและประวัติ | จัดสรร Margin | ตั้ง Opening Forecast Balance | Reverse รายการ |
|---|---:|---:|---:|---:|
| Owner | ได้ | ได้ | ได้ | ได้ |
| Admin / Accounting | ได้ | ไม่ได้ | ไม่ได้ | ไม่ได้ |
| Subcontractor | ไม่ได้ | ไม่ได้ | ไม่ได้ | ไม่ได้ |

Accounting หรือ Admin เป็นผู้จัดเตรียมและตรวจสอบตัวเลข Opening Forecast Balance ส่วน Owner เป็นผู้ตรวจและยืนยันขั้นสุดท้ายในระบบ

## 3. คำศัพท์บนหน้าจอ

| คำบนหน้าจอ | ความหมาย |
|---|---|
| `Forecast Margin` | Margin ที่คาดการณ์ของ Project |
| `Projected BOQ Margin` | Margin ตั้งต้นที่คำนวณจาก Customer BOQ เทียบกับ Subcontractor BOQ |
| `Company Operations` | Bucket กลางสำหรับวางแผนค่าใช้จ่ายส่วนกลางของบริษัท |
| `Opening Forecast Balance` | งบประมาณคาดการณ์ตั้งต้นของ Company Operations ซึ่ง Owner ระบุครั้งแรก |
| `Forecast Allocated In` | Margin ที่ Bucket ได้รับมาจาก Bucket อื่น |
| `Forecast Allocated Out` | Margin ที่ Bucket จัดสรรออกไปยัง Bucket อื่น |
| `Forecast Reserve` | Margin ที่กันสำรองไว้และไม่สามารถจัดสรรออกได้ |
| `Available Margin to Allocate` | Margin คงเหลือสูงสุดที่สามารถจัดสรรออกได้ในขณะนั้น |
| `Margin Allocation Ledger` | ประวัติรายการจัดสรรและ Reverse ที่ตรวจสอบย้อนหลังได้ |
| `Forecast Deficit` | Margin ที่มีอยู่ต่ำกว่ายอดที่เคยจัดสรรออกไปแล้ว |

สูตรที่ระบบใช้คำนวณคือ:

```text
Project ทั่วไป
Available Margin
= Projected BOQ Margin
+ Forecast Allocated In
− Forecast Allocated Out
− Forecast Reserve

Company Operations
Available Margin
= Opening Forecast Balance
+ Forecast Allocated In
− Forecast Allocated Out
− Forecast Reserve
```

ระบบเป็นผู้คำนวณยอดล่าสุดจาก Server ทุกครั้ง ผู้ใช้งานไม่ต้องคำนวณหรือแก้ยอด Available Margin เอง

## 4. การเข้าสู่หน้า Forecast Margin

### 4.1 เปิด Company Operations

1. เข้าสู่ระบบด้วยบัญชี Owner หรือ Admin
2. เลือกเมนู `Projects` จากแถบเมนูด้านซ้าย
3. ไปที่ส่วน `Company Funds` ซึ่งอยู่เหนือรายการ Construction Projects
4. เลือก `Open` บนการ์ด `Company Operations`
5. ระบบจะแสดง Available Margin, Allocated In, Allocated Out และประวัติ Margin Allocation

### 4.2 เปิด Forecast Margin ของ Project

1. ไปที่เมนู `Projects`
2. เลือก Project ที่ต้องการ
3. ในหน้า Project Detail ให้ดูส่วน `FORECAST MARGIN BUCKET`
4. ตรวจสอบการ์ด `Projected BOQ Margin` และ `Available Margin to Allocate`

## 5. การตั้ง Opening Forecast Balance ของ Company Operations

ขั้นตอนนี้ใช้เฉพาะการเปิดใช้งาน Company Operations ครั้งแรก และทำโดย Owner เท่านั้น

1. ให้ Accounting หรือ Admin เตรียมและตรวจสอบตัวเลขงบประมาณคาดการณ์ตั้งต้น
2. ไปที่ `Projects` > `Company Funds`
3. เลือก `Set Opening Forecast Balance`
4. กรอก `Initial Opening Forecast Balance (THB)`
   - กรอกจำนวนเงินได้ไม่เกิน 2 ตำแหน่งทศนิยม
   - หากยังไม่มีงบตั้งต้น ให้กรอก `0.00` อย่างชัดเจน
5. เลือก `Activation month`
   - ระบบจะกำหนดวันที่เริ่มต้นเป็นวันที่ 1 ของเดือนที่เลือกโดยอัตโนมัติ
6. กรอก `Reason` เพื่อระบุที่มาและหลักการจัดเตรียมตัวเลข
7. ตรวจสอบ `Activation Preview`
8. ทำเครื่องหมายยืนยันว่า Accounting/Admin ได้เตรียมและตรวจสอบตัวเลขแล้ว
9. กด `Confirm Opening Forecast Balance`
10. เมื่อสำเร็จ ระบบจะแสดงยอดและวันที่เริ่มใช้งาน

> Opening Forecast Balance เป็นงบประมาณคาดการณ์ ไม่ใช่ยอดเงินสด ยอดธนาคาร หรือรายรับจากลูกค้า และระบบจะเก็บเป็นประวัติที่แก้ไขย้อนหลังโดยตรงไม่ได้

## 6. การจัดสรร Margin จาก Project ไป Company Operations

กรณีนี้เหมาะสำหรับนำ Margin ที่คาดว่าจะได้จาก Project ไปวางแผนเป็นงบดำเนินงานส่วนกลาง

1. เปิด Project ต้นทาง
2. ตรวจสอบ `Projected BOQ Margin` และ `Available Margin to Allocate`
3. กด `Allocate Margin`
4. ตรวจสอบชื่อ Project ในช่อง `From`
5. ที่ช่อง `To` เลือก `Company Operations`
   - ใช้ช่อง Search เพื่อค้นหาปลายทางได้
6. กรอก `Amount (THB)`
   - จำนวนต้องมากกว่า `0.00`
   - จำนวนต้องไม่เกิน Available Margin ของ Project ต้นทาง
   - สามารถเลือก `Use maximum` เพื่อใช้ยอดสูงสุดที่จัดสรรได้
7. กรอก `Reason` ซึ่งเป็นข้อมูลบังคับ
8. กรอก `Reference / note` หากมีเอกสารหรือเลขอ้างอิงภายใน
9. ตรวจสอบส่วน `Available Margin Before / After` ของทั้งต้นทางและปลายทาง
10. กด `Confirm Margin Allocation`
11. เมื่อสำเร็จ ให้ตรวจสอบ Reference และยอดคงเหลือหลังรายการ แล้วกด `Done`

ผลลัพธ์:

- Available Margin ของ Project ต้นทางลดลง
- Forecast Allocated Out ของ Project ต้นทางเพิ่มขึ้น
- Available Margin และ Forecast Allocated In ของ Company Operations เพิ่มขึ้น
- ระบบสร้างรายการใน Margin Allocation Ledger ของทั้งสอง Bucket

## 7. การจัดสรร Margin จาก Company Operations ไปยัง Project

ใช้เมื่อต้องการนำงบคาดการณ์ส่วนกลางไปเพิ่มให้ Project ที่ต้องการความช่วยเหลือ

1. ไปที่ `Projects` > `Company Funds`
2. เปิด `Company Operations`
3. ตรวจสอบ `Available Margin to Allocate`
4. กด `Allocate Margin`
5. เลือก Project ปลายทางในช่อง `To`
6. กรอก Amount, Reason และ Reference/Note ตามต้องการ
7. ตรวจสอบยอด Before / After
8. กด `Confirm Margin Allocation`
9. ตรวจสอบ Reference และยอดหลังรายการ แล้วกด `Done`

หาก Available Margin เป็น `0.00`, ยังไม่ได้ตั้ง Opening Forecast Balance หรือมี Forecast Deficit ปุ่ม Allocate Margin จะไม่สามารถใช้งานได้

## 8. การจัดสรร Margin ระหว่าง Project

1. เปิด Project ที่เป็นต้นทางของ Margin
2. กด `Allocate Margin`
3. ค้นหาและเลือก Project ปลายทาง
4. กรอกจำนวนที่ไม่เกิน Available Margin
5. กรอกเหตุผลและข้อมูลอ้างอิง
6. ตรวจสอบยอด Before / After
7. ยืนยันรายการ

Source และ Target ต้องเป็นคนละ Project และต้องเป็น Bucket ที่ Active อยู่ในระบบ

## 9. การดูประวัติ Margin Allocation

1. เปิด Company Operations หรือ Project ที่ต้องการตรวจสอบ
2. เลื่อนไปที่ส่วน `Margin Allocation Ledger`
3. ตรวจสอบข้อมูลในแต่ละรายการ:
   - `Direction`: Allocated In หรือ Allocated Out
   - `From`: Bucket ต้นทาง
   - `To`: Bucket ปลายทาง
   - `Amount`: จำนวน Margin
   - `Reason`: เหตุผล
   - `Status`: สถานะรายการ
   - `Created by`: ผู้สร้างรายการ
   - `Created at`: วันและเวลา
4. กดไอคอนรูปตาเพื่อดูรายละเอียด Reference/Note และความสัมพันธ์กับรายการ Reverse
5. หากมีรายการจำนวนมาก ให้เลือก `View all Margin Allocations` และ `Load more`

ความหมายของเครื่องหมายจำนวนเงิน:

- เครื่องหมาย `+` หมายถึง Bucket ปัจจุบันได้รับ Margin
- เครื่องหมาย `−` หมายถึง Bucket ปัจจุบันจัดสรร Margin ออก

## 10. การ Reverse รายการที่จัดสรรผิด

ระบบไม่อนุญาตให้แก้ไขหรือลบรายการที่ Posted แล้ว หากจัดสรรผิด Owner ต้องสร้าง Reverse เพื่อคืนยอดในทิศทางตรงกันข้าม

1. ไปที่ `Margin Allocation Ledger`
2. กดไอคอนรูปตาของรายการที่ต้องการ Reverse
3. ตรวจสอบ From, To, Amount, Reason, ผู้สร้าง และวันเวลา
4. ไปที่ส่วน `Reverse Margin Allocation`
5. ตรวจสอบยอดล่าสุดและ Preview การคืน Margin
6. กรอก `Reversal reason`
7. กดปุ่ม `Reverse THB ...`
8. ตรวจสอบประวัติรายการ Reverse ที่ระบบสร้างขึ้น

ผลของการ Reverse:

- ระบบสร้างรายการใหม่ในทิศทางตรงกันข้าม
- รายการเดิมยังคงอยู่เพื่อให้ตรวจสอบย้อนหลังได้
- รายการเดิมและรายการ Reverse จะมีข้อมูลเชื่อมโยงถึงกัน

ระบบจะไม่อนุญาตให้ Reverse หาก Bucket ที่ต้องคืน Margin มียอด Available Margin ไม่เพียงพอ ตัวอย่างเช่น Bucket ปลายทางได้นำ Margin ที่รับมาไปจัดสรรต่อแล้ว

## 11. ตัวอย่างการใช้งาน

Project A มีข้อมูลดังนี้:

```text
Projected BOQ Margin       THB 214,000.00
Forecast Allocated In      THB       0.00
Forecast Allocated Out     THB       0.00
Forecast Reserve           THB       0.00
Available Margin           THB 214,000.00
```

Owner จัดสรร `THB 30,000.00` จาก Project A ไป Company Operations หลังยืนยันรายการ:

```text
Project A
Forecast Allocated Out     THB  30,000.00
Available Margin           THB 184,000.00

Company Operations
Forecast Allocated In      เพิ่มขึ้น THB 30,000.00
Available Margin           เพิ่มขึ้น THB 30,000.00
```

ตัวเลขรายรับจริง รายจ่ายจริง และสถานะการอนุมัติของ Project A จะไม่เปลี่ยนจากรายการนี้

## 12. ข้อความแจ้งเตือนและวิธีแก้ไข

| อาการหรือข้อความ | สาเหตุ | วิธีดำเนินการ |
|---|---|---|
| ปุ่ม `Allocate Margin` กดไม่ได้ | Available Margin เป็น 0, มี Forecast Deficit, Operations ยังไม่เปิดใช้งาน หรือผู้ใช้ไม่มีสิทธิ์ Owner | ตรวจสอบยอดและสิทธิ์ หากเป็น Operations ให้ตั้ง Opening Forecast Balance ก่อน |
| Amount มากกว่ายอดสูงสุด | จำนวนที่กรอกเกิน Available Margin ล่าสุด | ลดจำนวนหรือเลือก `Use maximum` |
| `Reason is required` | ยังไม่ได้กรอกเหตุผล | กรอกเหตุผลทางธุรกิจหรือวัตถุประสงค์ของรายการ |
| ยอดเปลี่ยนระหว่างเปิดหน้าต่าง | มีผู้ใช้อื่นทำรายการหรือ Forecast ถูกคำนวณใหม่ | ตรวจสอบยอดล่าสุดที่ระบบแสดง แล้วกดยืนยันใหม่ |
| ไม่พบ Project ปลายทาง | Project ไม่ Active, ถูก Archive หรือไม่มี Fund Bucket ที่ใช้งานได้ | ตรวจสอบสถานะ Project หรือติดต่อผู้ดูแลระบบ |
| `Read only — Owner permission is required` | เข้าระบบด้วย Admin หรือผู้ใช้ที่ไม่ใช่ Owner | ให้ Owner เป็นผู้ยืนยันรายการ |
| `Forecast Margin Allocation is temporarily disabled` | Environment ปิดการสร้างและ Reverse รายการชั่วคราว | ติดต่อผู้ดูแลระบบ |
| Reverse กดไม่ได้ | รายการถูก Reverse แล้ว หรือ Bucket ที่ต้องคืนยอดมี Available Margin ไม่พอ | ตรวจสอบประวัติและยอดของ Bucket ที่ต้องคืน Margin |
| แสดง `Forecast Deficit` | Forecast base ลดลงจนต่ำกว่ายอดที่จัดสรรออกแล้ว | ตรวจสอบ BOQ/Forecast ล่าสุด รับ Margin เพิ่ม หรือ Reverse รายการที่ยังสามารถคืนได้ |

## 13. แนวทางการกรอก Reason และ Reference

Reason ควรอธิบายวัตถุประสงค์ให้ผู้ตรวจสอบเข้าใจได้โดยไม่ต้องสอบถามเพิ่มเติม เช่น:

- `จัดสรร Margin สำหรับงบค่าใช้จ่ายส่วนกลางเดือนกันยายน 2026`
- `สนับสนุน Project B เนื่องจากต้นทุนวัสดุคาดการณ์เพิ่มขึ้น`
- `ปรับการจัดสรรตามประมาณการ BOQ ฉบับแก้ไขครั้งที่ 3`

Reference/Note สามารถใช้ระบุ:

- เลขที่ Working Paper
- เลขที่เอกสารอนุมัติภายใน
- รอบประชุมหรือวันที่ตัดสินใจ
- หมายเหตุเพิ่มเติมสำหรับ Accounting/Admin

หลีกเลี่ยงเหตุผลที่สั้นเกินไป เช่น `ย้ายเงิน`, `แก้ยอด` หรือ `ตามที่คุย` เพราะไม่เพียงพอสำหรับ Audit Trail

## 14. Checklist ก่อนยืนยันรายการ

- [ ] ตรวจสอบว่าเลือก Source และ Target ถูกต้อง
- [ ] ยืนยันว่าจำนวนไม่เกิน Available Margin ล่าสุด
- [ ] เข้าใจว่ารายการนี้เป็น Forecast และไม่ใช่การโอนเงินจริง
- [ ] กรอก Reason ที่อธิบายวัตถุประสงค์ชัดเจน
- [ ] เพิ่ม Reference/Note หากมีเอกสารประกอบ
- [ ] ตรวจสอบยอด Before / After ของทั้งสอง Bucket
- [ ] หากรายการผิด ให้ใช้ Reverse และห้ามพยายามลบประวัติเดิม

## 15. ภาพประกอบที่แนะนำสำหรับคู่มือฉบับจัดหน้า

1. หน้า Projects พร้อมกรอบเน้นส่วน `Company Funds`
2. หน้า Project Detail พร้อมกรอบเน้น `Projected BOQ Margin` และ `Available Margin to Allocate`
3. หน้าต่าง `Allocate Margin` พร้อมหมายเลขกำกับ From, To, Amount, Reason และ Preview
4. หน้าจอ Success พร้อม Reference Number
5. ตาราง `Margin Allocation Ledger` พร้อมคำอธิบาย Allocated In/Out
6. หน้าต่าง Allocation Detail และส่วน `Reverse Margin Allocation`
7. หน้าต่าง `Set Opening Forecast Balance` สำหรับการเปิดใช้ Company Operations ครั้งแรก

## 16. คำถามที่พบบ่อย

### Allocate Margin คือการโอนเงินจริงหรือไม่

ไม่ใช่ เป็นการจัดสรร Margin ที่คาดการณ์ระหว่าง Bucket ภายในระบบเท่านั้น ไม่มีการเชื่อมต่อหรือสั่งโอนผ่านธนาคาร

### ทำไม Projected BOQ Margin จึงไม่เท่ากับ Available Margin

เพราะ Available Margin รวมยอด Allocated In และหัก Allocated Out กับ Forecast Reserve แล้ว

### สถานะ Paid หรือ Approved ทำให้ Available Margin เปลี่ยนหรือไม่

ไม่เปลี่ยน Actual Cashflow และ Forecast Margin Allocation เป็นคนละส่วนกัน

### Admin สามารถจัดสรรหรือ Reverse ได้หรือไม่

ไม่ได้ Admin ดูยอดและประวัติได้แบบ Read only ส่วน Owner เป็นผู้ยืนยันรายการ

### Subcontractor มองเห็น Company Operations หรือไม่

ไม่เห็น Subcontractor เห็นเฉพาะ Project ที่ตนได้รับมอบหมาย และไม่สามารถส่งรายรับหรือรายจ่ายเข้า Company Operations ได้

### สามารถแก้ไขหรือลบรายการที่ยืนยันแล้วได้หรือไม่

ไม่ได้ รายการที่ Posted แล้วเป็นประวัติถาวร หากผิดต้องใช้ Reverse เพื่อสร้างรายการตรงกันข้ามพร้อมเหตุผล

