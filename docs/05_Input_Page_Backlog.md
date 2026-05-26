# Input Page Backlog

รายการนี้สรุปจากสถานะระบบปัจจุบันของ `Projects-001-FE/src/InputPage.jsx` และ flow ที่เชื่อมต่อไปยัง `Approval`

## P0: ต้องทำต่อเพื่อให้ใช้จริงได้

- ทำ OCR จริงแทน mock endpoint `POST /api/v1/input/receipt-extract`
- เพิ่ม auth/role สำหรับ `Input` และ `Approval` เพื่อแยกผู้ยื่นคำขอและ admin
- ผูก approve flow ของ `input_requests` เข้ากับ finance/transaction ถ้าธุรกิจต้องนับเป็นต้นทุนจริง
- เพิ่ม audit trail ว่าใคร submit, review, approve, reject, mark paid
- เพิ่ม signed URL / preview ไฟล์จาก GCS ในหน้า Approval และหน้า Input
- ผูก cron / scheduler สำหรับรัน cleanup `temp_bills` อัตโนมัติใน production

## P1: เพิ่มความถูกต้องของข้อมูลและลดงาน admin

- เพิ่ม validation เชิงธุรกิจให้ครบ เช่น กฎของ `request_type`, บัญชีธนาคาร, และรูปแบบเบอร์โทร
- ทำ duplicate detection ให้แรงขึ้นกว่าเดิม เช่น fuzzy matching ชื่อร้าน/เลขเอกสาร
- ให้หน้า Approval แก้ไขข้อมูล bank account ได้ครบ
- เพิ่ม preview หรือ open receipt จากหน้า Approval เมื่อมีไฟล์แนบจริง
- แยก field ตาม `EXPENSE` / `INCOME` ให้ชัดเจนขึ้น แทนการใช้ฟอร์มชุดเดียว

## P2: ปรับ UX และการทำงานหน้างาน

- ทำ mobile-first layout สำหรับคนหน้างาน
- เพิ่ม draft autosave ก่อน submit
- เพิ่ม searchable project selector
- รองรับหลายไฟล์แนบต่อคำขอ
- เพิ่ม status timeline ในหน้า Input หลัง submit

## P3: Analytics และ workflow ต่อเนื่อง

- ต่อ notification เมื่อคำขอถูก approve/reject/paid
- ทำ SLA / aging dashboard สำหรับคิวอนุมัติ
- เพิ่ม export รายการคำขอเป็น Excel/CSV
- เชื่อมข้อมูล Input เข้ากับ Dashboard/Insights แบบ near real-time
