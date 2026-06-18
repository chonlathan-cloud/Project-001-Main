# Inspection Feature UX / Flow Draft

เอกสารนี้สรุปแนวทาง UX/flow จาก prototype ใน `Design/New-Feature/Inspection/` เพื่อใช้คุยก่อนลงมือ implement ใน frontend จริง

## 1. Product Positioning

Inspection ควรถูกวางเป็นฟีเจอร์ตรวจงานระดับโครงการ ไม่ใช่ module ลอยแยกจากระบบหลัก

เป้าหมายหลัก:

- ให้ทีมหน้างานปักตำแหน่ง defect / issue บนแปลนหรือ zone ได้เร็ว
- ให้ admin / owner เห็นสถานะงานตรวจ, งานค้าง, ความรุนแรง, ผู้รับผิดชอบ และผลกระทบต่อ handover
- ให้ subcontractor เห็น defect ที่ตัวเองต้องแก้ และส่งหลักฐานกลับมาได้ใน phase ต่อไป
- สร้าง report สำหรับ client, contractor และ management ได้จากข้อมูลเดียวกัน

ตำแหน่งในระบบที่แนะนำ:

- MVP: เพิ่มเป็น local section/tab ภายใน `Project Detail`
- Later: เพิ่ม entry ใน Sidebar ชื่อ `Inspection` เมื่อมี cross-project dashboard แล้ว

เหตุผล: defect ต้องผูกกับ project, zone, plan, subcontractor, BOQ/WBS และ handover status จึงควรเริ่มจาก project context ก่อน

## 2. User Roles

- Owner / Admin: ดูภาพรวมทุกโครงการ, สร้าง inspection, assign งาน, approve close, export report
- Site Inspector: เดินตรวจ, ปัก pin, ถ่ายรูป, ระบุ severity/category, verify หลังแก้ไข
- Subcontractor: เห็นรายการที่ถูก assign, comment, upload รูป after-fix, mark ready for review
- Management / Client: ดู summary และ report แบบอ่านอย่างเดียว

## 3. Information Architecture

แนะนำโครงสร้างหน้าภายใน Project Detail:

```text
Project Detail
├─ BOQ / Compare
├─ Warehouse Records
└─ Inspection
   ├─ Overview
   ├─ Inspect Map
   ├─ Defect Register
   └─ Reports
```


## 4. End-to-End Flow

```text
Project Detail
  ↓
Open Inspection
  ↓
Choose Zone / Floor / Area
  ↓
Open Plan Map
  ↓
Click location or tap Add Defect
  ↓
Fill defect form
  ↓
Save as Open / Assigned
  ↓
Contractor fixes and submits evidence
  ↓
Inspector reviews
  ↓
Resolved or Reopened
  ↓
Report / Handover readiness update
```

## 5. Recommended Screen Flow

### 5.1 Inspection Overview

หน้าสรุปสำหรับ project manager / owner

Content:

- KPI cards: `Total Defects`, `Open`, `Critical`, `Overdue`, `Readiness`
- Severity breakdown: Critical / Major / Minor / Cosmetic
- Category breakdown: Architectural, Electrical, Plumbing, Mechanical, Structural, Finishes
- Contractor performance: open count, overdue count, average closure days
- Handover readiness: projected readiness date and blocker summary

Primary actions:

- `New Inspection`
- `Open Map`
- `Generate Report`

UX rule:

- หน้านี้ควรอ่านได้เร็วเหมือน dashboard งานปฏิบัติการ ไม่ควรเป็น marketing style
- Critical / overdue ต้องมองเห็นทันที

### 5.2 Inspect Map

หน้าหลักสำหรับเดินตรวจงาน

Layout:

- Left/main: floor plan หรือ zone map
- Right panel: zone summary, quick add, selected pin detail
- Top controls: zone selector, status filter, severity filter, upload/replace plan

Core interactions:

- Click/tap บน plan เพื่อเปิด `Add Defect` modal
- Hover/click pin เพื่อดู short detail
- Click pin เพื่อเปิด `Defect Detail Drawer`
- Zoom in/out และ pan สำหรับแปลนขนาดใหญ่
- Filter pin ตาม status, severity, contractor

Add Defect fields:

- Description
- Category
- Severity
- Responsible party / subcontractor
- Due date
- Zone / floor / room
- Coordinate on plan
- Photos / attachments
- Notes
- Optional: BOQ/WBS link

MVP quick add presets:

- Paint touch-up
- Tile/grout incomplete
- Door/window alignment
- Electrical point issue
- Plumbing leak

### 5.3 Defect Register

หน้าตารางสำหรับ tracking และ bulk review

Columns:

- ID
- Photo thumbnail
- Description
- Zone
- Category
- Severity
- Responsible party
- Due date
- Status
- Last updated
- Actions

Filters:

- Search by ID, description, contractor, zone
- Status
- Severity
- Category
- Due/overdue
- Responsible party

Actions:

- Open detail
- Update status
- Assign/reassign
- Delete/void with reason
- Export filtered list

### 5.4 Defect Detail Drawer

ควรเป็น drawer แทน modal เต็มจอ เพื่อให้ผู้ใช้ยังเห็น context จาก map/table

Sections:

- Header: ID, severity, status, due date
- Location: project, zone, room, map coordinate
- Description and category
- Responsible party
- Before photos
- Fix evidence / after photos
- Comments timeline
- Status history
- Action footer

Primary actions by role:

- Inspector/Admin: assign, change due date, verify, reopen, close
- Contractor: comment, upload evidence, mark ready for review
- Read-only user: export/share only

### 5.5 Reports

Report types from prototype are useful and should be kept:

- Client Report: high-level summary, open critical items, selected photos, readiness
- Contractor Report: action list grouped by contractor/trade, due dates, required evidence
- Management Report: progress trend, risk, projected handover, blockers

Report filters:

- Date range
- Zone
- Contractor
- Severity
- Status
- Include/exclude resolved items
- Include photos

Export:

- MVP: browser print / PDF
- Later: saved report snapshot with share link

## 6. Status Model

Prototype ใช้ `Open`, `In Progress`, `Resolved` ซึ่งง่ายและเหมาะสำหรับ mock แต่ระบบจริงควรแยก verification ให้ชัด

MVP ที่แนะนำ:

```text
Open
↓
In Progress
↓
Ready for Review
↓
Resolved
```

Alternative สำหรับ workflow ที่เข้มขึ้น:

```text
Draft
↓
Assigned
↓
In Progress
↓
Ready for Review
↓
Resolved
↘
 Reopened
```

ข้อเสนอ: เริ่ม MVP ด้วย 4 สถานะก่อน แล้วเก็บ `Reopened` เป็น status หรือ event ใน timeline ได้

## 7. Severity Model

ใช้ model จาก prototype ได้:

- Critical: ต้องแก้ทันที กระทบความปลอดภัย/ส่งมอบ
- Major: กระทบคุณภาพหรือการส่งมอบ แต่ยังไม่ใช่ immediate risk
- Minor: งานแก้ทั่วไป
- Cosmetic: งานเก็บรายละเอียด

UX behavior:

- Critical ใช้ red และควรขึ้นก่อนใน list/report
- Overdue + Critical ต้องมี visual priority สูงสุด
- Cosmetic ไม่ควรใช้สี alarm จนรบกวนภาพรวม

## 8. Integration With Current Frontend

จาก frontend ปัจจุบัน:

- Layout หลักใช้ `Sidebar` + `WorkspaceTopbar`
- Project detail route อยู่ที่ `/project/detail/:projectId`
- Existing design tokens หลักอยู่ใน `Projects-001-FE/src/index.css`
- Sidebar มีเมนู `Projects`, `Input`, `Approvals`, `Insights`, `Chat AI`

ข้อเสนอ integration:

- เพิ่ม Inspection เป็น section ภายใน `ProjectDetailPage` ก่อน
- เพิ่ม local tab/action ใน Project Detail แทนเพิ่ม Sidebar item ทันที
- ถ้ามี defect critical/overdue จำนวนมาก ค่อย surface summary ไป Dashboard หรือ Insights ภายหลัง
- ผูก defect กับ `projectId` เป็น mandatory
- Optional links: `subcontractor`, `BOQ/WBS node`, `input request`, `approval/payment` ใน phase หลัง

## 9. Mobile / On-Site UX

การตรวจงานจริงน่าจะเกิดบน tablet/mobile มากกว่า desktop

Mobile requirements:

- Bottom action หรือ sticky `Add Defect`
- Camera upload ต้องอยู่ใน flow แรก ไม่ซ่อนลึก
- Pin tap target ต้องใหญ่พอ
- Defect form ต้องแบ่งเป็น short required fields ก่อน แล้ว detail เพิ่มทีหลังได้
- Offline draft เป็น later phase แต่ควรออกแบบ data model เผื่อไว้

MVP mobile flow:

```text
Project → Inspection → Zone → Add Defect → Take/Upload Photo → Save
```

## 10. MVP Scope

ควรเริ่มด้วย scope นี้:

- Project-level Inspection tab
- Zone/floor selector
- Upload/use plan image
- Add defect pin on map
- Defect register with filters
- Defect detail drawer
- Status update: Open, In Progress, Ready for Review, Resolved
- Photo attachments
- Basic PDF/print report
- Summary KPI cards

ยังไม่ควรเริ่มใน MVP:

- AI recommendation
- Offline sync
- DWG/PDF layer parsing จริง
- Cross-project inspection dashboard
- Contractor self-service portal ถ้ายังไม่มี permission/data model พร้อม
- Automated LINE notification ทุก event

## 11. Open UX Decisions

เรื่องที่ควรคุยก่อนลงมือทำ:

- ใช้ชื่อเมนูว่า `Inspection`, `Defects`, `Punch List`
- Inspection เป็นของ project ทั้งโครงการ
- Subcontractor จะ update status เองได้
- Defect ต้องมีรูปเสมอ
- Zone/room จะมาจาก master data
- Report ต้องใช้ format ภาษาไทย ภาษาอังกฤษ คำที่เป็นคำเฉพาะ
- ต้องมี approve/verify ก่อนปิด defect ทุกครั้ง
- Critical defect จะต้อง block handover readiness โดยอัตโนมัติ 

## 12. Recommended Next Step

ก่อน implement ควรตัดสินใจ 3 เรื่องนี้:

1. Navigation: วาง Inspection เป็น tab ใน Project Detail
2. Status flow: ใช้ 4 สถานะ MVP
3. Actor boundary: subcontractor เห็นและแก้ไขข้อมูลระดับ upload ภาพแจ้ง defect ทำไม่ได้อยู่ อย่างคือ ตรวจรับงานเอง เพราะว่าส่าวนจะเป็นหน้าของ admini or owner only
