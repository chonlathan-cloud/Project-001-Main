# Modify V2 — Native BOQ, Quotations และ Price Database

## 0. สถานะและวิธีใช้เอกสาร

- เจ้าของผลิตภัณฑ์: RAYADEE LIMITED.
- วันที่จัดทำ: 14 กันยายน 2026
- Repository baseline: branch `feature`, commit `8f53197c6cf369b60a5cb2d6771a9bcc7b6b4020` (`add feature alert smooth`). ต้องตรวจ branch/diff อีกครั้งก่อนเริ่ม implementation; ห้ามเปลี่ยนกลับไปใช้ `main` เป็นฐานโดยอัตโนมัติ
- สถานะ: แผนส่งต่อ implementation หลังหารือแนวทางกับผู้ใช้แล้ว **ยังไม่ได้ implement V2**
- Demo/feedback reference: <https://rayadee-boq-hub.thamespbd.chatgpt.site/>
- Existing application reference: <https://projects-001-fe-beta-678310400174.asia-southeast1.run.app/project>
- ข้อกำหนดธุรกิจใน §2 คือข้อสรุปจากการสนทนา ส่วนชื่อ entity/API, precision, locking และลำดับงานคือ **ข้อเสนอทางวิศวกรรมในแผนนี้** ไม่ใช่สิ่งที่มีอยู่แล้วใน repository
- เอกสารนี้อนุญาตให้ agent ทำงานตาม scope BOQ V2 เมื่อได้รับมอบหมาย implementation ไม่ใช่คำสั่ง deploy, แก้ production data, ลบข้อมูล หรือเปลี่ยนสิทธิ์ระบบจริงทันที

ลำดับความสำคัญเมื่อข้อมูลขัดกัน: คำสั่งล่าสุดของผู้ใช้ → ข้อตกลงในแผนนี้ → code/contract ที่ต้องคง compatibility → demo → เอกสาร BOQ เก่า Demo เป็น feedback ของผลิตภัณฑ์นี้ ไม่ใช่ระบบใหม่ที่จะนำมาแทนทั้งแอป และไม่ใช่ข้อบังคับให้คัดลอก defect ของ demo

ก่อนลงมือ อ่าน `AGENTS.md`, `Design/DESIGN.md`, `docs/00_INSTRUCTION.md`, เอกสาร BRD/HLD/TDD/LLD และ code ในพื้นที่ที่จะเปลี่ยน ตรวจ nested instructions และ worktree อย่าทับงานผู้ใช้ เอกสารเก่าที่กำหนด Google Sheets/BOQ สองชุดแยกกันถูกแทนที่เฉพาะส่วน BOQ โดยแผนนี้ ส่วนการเงินและระบบอื่นยังคงเดิม

## 1. ผลลัพธ์ที่ต้องได้

RAYADEE ทำรายการงาน กำหนดราคาขาย ประเมินต้นทุน เปรียบเทียบราคา Supplier/Subcontractor ออกใบเสนอราคา และบันทึกข้อตกลงลูกค้าได้ใน web app เดียว จากนั้นใช้ข้อมูล BOQ ที่สะสมช่วยทำราคาโครงการถัดไปได้เร็วขึ้น โดยไม่ต้องกรอก BOQ ฝั่งลูกค้าและฝั่งต้นทุนซ้ำสองรอบ

หลักการออกแบบ: **หนึ่ง scope งาน → สองมุมราคา → หลายผู้รับผิดชอบต้นทุน → หนึ่งฐานงบประมาณที่เลือกใช้อย่างชัดเจน**

ไม่ใช่การยกเครื่อง Project Management, Accounting, Input/Approval หรือ Customer Portal ทั้งระบบ

## 2. ข้อตกลงธุรกิจที่ต้องรักษา

| ID | ข้อสรุป | ผลต่อ implementation |
| --- | --- | --- |
| D01 | นำ feedback/features ของ demo มา replace BOQ เดิม | ใช้ shell และความสามารถอื่นของ repository ต่อ ไม่ clone ทั้งแอป demo |
| D02 | ทำ BOQ ใน web app เท่านั้น | ถอด Google Sheets URL/tab selection/sync/jobs และ flow ต่อ Sheet |
| D03 | มี Excel export แต่ **ไม่มี import** | ห้ามเพิ่ม Excel/CSV import, supplier price import หรือเปิดช่อง import ซ่อนไว้; ข้อความก่อนหน้าที่เคยขอ import ถูกยกเลิก |
| D04 | กรอก scope ครั้งเดียว มีราคาลูกค้าและต้นทุน | หนึ่งรายการมี quantity/unit/spec และ material/labor ทั้ง sell/cost; มี consolidated/customer/cost views |
| D05 | RAYADEE คุยและตกลงกับลูกค้า แล้วจัดการผู้รับเหมาหลายรายเอง | ไม่เพิ่ม customer-to-subcontractor transaction หรือ portal negotiation |
| D06 | หลาย Supplier/Subcontractor ต่อโครงการ | กำหนด vendor ระดับ cost component; material/labor ของรายการเดียวกันคนละรายได้ |
| D07 | ไม่ต้องรองรับผู้รับเหมาเสนอราคาเหมาทั้งหมวด | หัวหมวดไม่มีราคาเหมา/การกระจาย lump sum; ต้นทุนต้องผูกกับรายการงานจริง |
| D08 | มีต้นทุนประมาณก่อนขาย แล้วมีราคาที่ตกลงกับ vendor ภายหลัง | เก็บ estimate เดิมและประวัติ offer/selection; เปลี่ยนต้นทุนไม่เปลี่ยนราคาลูกค้าอัตโนมัติ |
| D09 | กรอกราคาฝั่งใดก่อนก็ได้ | missing cost ไม่ใช่ 0; ห้ามแสดงกำไรเต็มจำนวนจากต้นทุนที่ยังไม่ทราบ |
| D10 | ใช้รายการ/ราคาที่สะสมช่วยเสนอราคาเร็วขึ้น | Library + price history + explicit promotion/update master; project override ไม่เปลี่ยน master |
| D11 | แยก Revision, Alternative และงานเพิ่ม/ลด | ฐานงบคิดเฉพาะ main revision ที่ตกลงใช้ + accepted change orders; ไม่รวมทุก quotation |
| D12 | เอกสารที่ส่ง/ตกลงแล้วต้องอ้างอิงย้อนหลังได้ | immutable snapshot; แก้โดย revision ใหม่; RAYADEE บันทึก agreement/evidence ภายใน ไม่มี acceptance portal ใหม่ |
| D13 | โครงการจริงเดิมมี 1 โครงการ และผู้ใช้ทำ BOQ ย้อนหลังเองได้ | สร้าง V2 ใน project ID เดิม ไม่ต้องเทียบยอด BOQ เก่า/ใหม่หรือ map ทุกรายการ |
| D14 | ส่วนอื่นของ repository ดีแล้วและต้องคงเดิม | เปลี่ยนเฉพาะจุดเชื่อมแหล่ง BOQ budget; เก็บ finance/history/permissions/workflows เดิม |

คำว่า “2 BOQ” ในเชิงธุรกิจหมายถึงเอกสาร/มุมมองราคาขายกับต้นทุน ไม่ใช่ให้ผู้ใช้สร้าง scope อิสระสองชุด หรือให้ระบบจับคู่ด้วยข้อความเหมือนเดิม

## 3. สิ่งที่ตรวจพบและขอบเขตของหลักฐาน

### 3.1 Demo ที่ใช้เป็น feedback

ตรวจการจัดหมวด/รายการ, quotation หลายชุด, customer/cost views, supplier cost entry, library/price history และ document center รวมถึงการเพิ่ม/คัดลอก/แก้รายการและตรวจ persistence ของตัวอย่าง

สิ่งที่นำมาใช้: native editor, grouping/reorder, library reuse, cost completeness, provenance, quotation workspace, cover/BOQ/payment terms/terms preview และ export workflow

สิ่งที่ต้องแก้หรือทำให้ชัดกว่าตัวอย่าง:

- Demo มี navigation/quotation cards ซ้ำหน้าที่กัน: รวมเป็น revision/alternative selector เดียว ไม่สร้างการเลือกซ้ำหลายจุด
- รายการ sell = 0 และ cost ยังไม่กรอกเคยไม่ถูกนับใน cost coverage: รายการที่อยู่ใน scope ต้องนับตาม component ที่ต้องมีต้นทุน ไม่กรองด้วยยอดขายเป็นบวก
- Library สถานะ draft ไม่ควรถูกสื่อว่าเป็นราคามาตรฐานที่ตรวจสอบแล้ว เพียงเพราะกรอกตัวเลขครบ
- ต้องกำหนด immutable issued/accepted snapshot จริงทั้ง API/DB ไม่ใช่แค่ badge; demo ยังแสดงช่องแก้ไขในสถานะ approved จึงใช้เป็นประเด็นที่ต้องทดสอบ ไม่ใช่ข้อยืนยันว่า backend demo แก้ snapshot ได้
- ห้ามเอา alternatives/revisions มาบวกเป็น project budget; ห้ามนับ subtotal/grand total ซ้ำกับ leaf items
- งวดชำระเงินต้องปิดยอดเศษสตางค์: fixture ยอด 7,752.15 และงวด 30/30/30/10 ต้องเป็น 2,325.65 / 2,325.65 / 2,325.65 / 775.20 ไม่ใช่ 775.22 ในงวดสุดท้าย
- Mobile preview ที่ 390px มี sidebar เบียดเนื้อหา: ใช้ responsive shell เดิมและ editor/detail mode ที่อ่านได้

ข้อจำกัด: ไม่ได้ audit source code/database ของ demo; การกด PDF ไม่ถือว่ายืนยันไฟล์ที่ดาวน์โหลดถูกต้อง และยังไม่ได้ยืนยัน Excel file export ของ demo จึงต้องทดสอบไฟล์จริงใน implementation ห้ามอ้างว่า demo ผ่าน production acceptance แล้ว

### 3.2 Repository/live application

- Baseline `feature` มี Funds/Forecast Margin ซึ่งต้องคงไว้ ต่างจาก checkout `main` ที่เคยตรวจระหว่างการสนทนา
- Live UI มีโครงการจริง `Renovation The Mall` และ Company Funds/Operations แยกกัน ตรวจแบบ read-only ไม่แก้ยอดหรือข้อมูลจริง ไม่ใช้ชื่อ/ID โครงการนี้เป็นเงื่อนไข hardcode
- Project detail มี Forecast Margin, Actual Cashflow, BOQ Comparison, warehouse/execution records และ Inspection; BOQ V2 replace เฉพาะพื้นที่ BOQ และจุดอ่าน budget
- `BOQItem` เดิมเป็น CUSTOMER/SUBCONTRACTOR แยกชุด, SCD2 `valid_from/valid_to`; sync สร้าง row UUID ใหม่ และ readers จับคู่ด้วย sheet/WBS/description ไม่มี native document/revision/catalog model ที่ใช้ได้ครบตาม V2
- เอกสาร `Design/S-BOQ/BOQ_HIERARCHY_CONTRACT.md` อธิบายบาง fields/behavior ที่ยังไม่ครบใน production path ห้ามถือว่า integrated แล้วเพียงเพราะมีเอกสาร/helper/migration
- มี automated tests จริงแล้ว แม้คำอธิบายใน AGENTS เก่าบอกว่าไม่มี: baseline frontend `npm test` ผ่าน 5 tests และ `npm run lint` ผ่าน; ยังไม่รัน build/backend suite สำหรับการจัดทำเอกสารนี้

## 4. ขอบเขตที่เปลี่ยนและสิ่งที่คงเดิม

| Area | เปลี่ยน | คงเดิม/ข้อห้าม |
| --- | --- | --- |
| Project list/create | ปุ่มเปิด/สร้าง BOQ native แทน connect Sheet | project identity, create/rename/filter/navigation, Company Funds |
| Project detail | native BOQ summary/workspace, active baseline, comparison ที่ใช้ shared line IDs | Forecast Margin, Actual Cashflow, warehouse records, Inspection/deep links |
| BOQ | hierarchy/editor, prices/costs/vendors, versioning, export | ไม่แยกกรอก scope สองชุด, ไม่ import |
| Quotations | revision/alternative/change order, document preview, internal acceptance record | ไม่เพิ่ม customer portal หรือ financial payment execution |
| Price Database | canonical items, reference prices, provenance/history/reuse | ไม่ auto-promote/overwrite master, ไม่อ้างเป็น actual cost โดยไร้หลักฐาน |
| Suppliers/Subcontractors | offer/selection และ commercial reference สำหรับ BOQ | identities, onboarding/access และ subcontractor execution flows เดิม |
| Dashboard/Funds/Insights/Chat/MCP | ใช้ active budget source เดียวและแยก budget จาก historical finance | formulas/ledger/actual cashflow/access policies เดิม ยกเว้น explicit V2 unknown-cost protection ใน §11 |
| Input/Approval/OCR/FlowAccount | regression tests; ไม่จำเป็นต้องเพิ่ม BOQ line mapping | การยื่น อนุมัติ จ่าย VAT/accounting readiness/idempotency และ attachments เดิม |
| Settings/Support | ถอดข้อความ/การ์ด Google Sheets สำหรับ BOQ | integration และ settings อื่นทั้งหมด |
| Platform | additive PostgreSQL models/services ใน FastAPI เดิม | React/Vite, auth, deployment topology, GCP infrastructure เดิม |

## 5. Domain และ workflow ที่ต้อง implement

### 5.1 Native BOQ: scope เดียว สองมุมราคา

1. เปิด project เดิม หรือสร้าง project ตาม flow เดิม แล้วเข้า BOQ workspace
2. สร้าง draft quotation/main scope; เพิ่ม work section → category → optional subcategory → item รองรับ item ใต้ category โดยตรง
3. เพิ่มเอง, เลือก library, หรือคัดลอก scope จาก project/revision ที่มีสิทธิ์อ่าน ไม่สร้าง price-history sample ใหม่เพียงเพราะ copy
4. กรอก description/spec/unit/quantity และราคาวัสดุ/แรงงานฝั่งลูกค้า/ต้นทุนในรายการเดียว เลือกแสดง consolidated (default), customer หรือ cost ได้โดยไม่เปลี่ยน underlying scope
5. คำนวณ line/group/document totals และความครบถ้วน; แก้/เพิ่ม/duplicate/reorder/move ได้ใน draft
6. บันทึกและ preview/export แล้ว issue revision; เมื่อมีข้อตกลงให้ผู้มีสิทธิ์บันทึก acceptance ภายใน

ข้อบังคับ hierarchy:

- ใช้ stable logical line ID และ revision-row ID แยกกัน ไม่ใช้ item number/description/array index เป็น identity; reorder/rename ไม่ทำให้ linkage หาย
- Section/category/subcategory เป็น structural nodes ไม่มี editable financial amount; totals derived จาก billable leaves หนึ่งครั้ง
- Item number/display path สร้างจากลำดับได้ แต่ไม่ใช่ foreign key; section metadata ไม่เรียกว่า Google Sheet tab
- ป้องกัน cycle, orphan, parent ข้าม revision/project และการย้าย item ไปใต้ item ที่ไม่อนุญาต
- การเปลี่ยน item เป็น group ต้องไม่ซ่อน/ลบจำนวนเงินเดิมเงียบ ๆ: ให้เลือกย้ายค่าลง child item หรือยืนยันลบข้อมูล draft พร้อมผลกระทบ
- ข้อมูล required/optional/excluded และ free-of-charge ต้อง explicit; excluded item ไม่เข้า budget/coverage ส่วนงานที่ให้ลูกค้าฟรีแต่ยังมีต้นทุนต้องเข้า coverage
- ลบ hard-delete ได้เฉพาะ draft ที่ไม่มี reference ต้องเก็บ lineage ของ issued/accepted items; รองรับ undo ของ draft edit โดยไม่ย้อน audit/accepted history

### 5.2 Cost component และ vendor

- แยก MATERIAL / LABOR ของแต่ละ item; shared scope quantity เป็นค่าเริ่มต้น แต่ component มี quantity/unit/spec ที่ต่างได้โดยแก้ชัดเจน เช่น customer ขาย 1 งาน แต่ material ซื้อ 20 ชิ้น ห้ามเปลี่ยนหน่วยเงียบ ๆ
- เก็บ quantity basis เป็น `INHERITED` หรือ `OVERRIDDEN`: เมื่อ scope quantity เปลี่ยน inherited component ตามค่าใหม่ ส่วน override คงค่าที่ตั้งใจไว้พร้อม visible indicator และ revalidate coverage; offer จำนวนเดิมห้ามยังแสดงครบหลัง required quantity เพิ่ม
- ใช้ states อย่างน้อย `UNKNOWN`, `PRICED`, `NOT_APPLICABLE`; `PRICED` ราคา 0 ต้องตั้งใจกรอกพร้อมเหตุผล ไม่ใช้ null coercion
- สำหรับ V2 นี้ component หนึ่งมี selected vendor/offer ที่ครอบคลุม required quantity ทั้ง component เพียงหนึ่งรายการ การแบ่ง award หลาย vendor/partial quantity ภายใน component ยังไม่ทำ; ผู้ใช้แยก scope item/component ที่มีความหมายชัดเจนใน draft ก่อน ห้าม split/renumber accepted customer scope โดยตรงเพื่อเลี่ยงข้อจำกัดนี้ และห้ามเลือก offer ครึ่งจำนวนแล้วถืออีกครึ่งเป็นต้นทุน 0
- หลาย vendor ต่อ project และ material/labor คนละ vendor รองรับเต็มรูปแบบ ไม่จำกัดจำนวนผู้รับเหมาไว้ที่ 10
- รองรับ supplier ที่ไม่มี login/LINE account ด้วย commercial reference และ optional link ไปยัง identity เดิม อย่าบังคับให้ supplier ทุกรายสมัครเป็นผู้รับเหมาในระบบ
- Manual offer entry: vendor, quotation reference/date/validity, item/component mapping, quantity/unit/spec, rate, discount/included charges, tax basis, attachment และ note
- Compare แสดง coverage, normalized basis, date/validity และความต่าง spec/unit/quantity ก่อนให้เลือก ไม่เฉลี่ยราคาคนละ basis และไม่ auto-select cheapest
- Full coverage ต้องตรง component quantity/unit/spec/included charges ไม่ใช่เพียงตรง customer quantity; เมื่อ basis เปลี่ยนให้ selection เดิมเป็น stale จน reconfirm พร้อมประวัติ ไม่ถือว่ายังคุมต้นทุนใหม่ครบ
- Offer ที่ไม่ถูกเลือก/หมดอายุยังเก็บไว้; การเลือกเกิน validity หรือ non-equivalent spec ต้อง warning และบันทึกเหตุผล ไม่ convert หน่วย/ยืนยันเทียบเท่าเอง
- Offer/offer line ที่ใช้ใน published selection ต้อง immutable/versioned หรือ copy rate/quantity/terms/evidence identity ลง cost snapshot; แก้/ถอน offer โดย revision/event ใหม่ ไม่ PATCH/delete reference จน agreed history หรือไฟล์เก่าเปลี่ยนย้อนหลัง
- Select/replace offer เป็น explicit, authorized, audited action หลัง preview ผลต่อต้นทุน/forecast; ไม่สร้าง PO/payment หรือเปลี่ยน sell price
- RFQ export เลือก scope/component ที่ขอราคา ช่องราคาเว้นว่าง; selected-vendor cost export แสดงเฉพาะงาน/ราคาที่ตกลงกับรายนั้น ไม่เปิดราคาเจ้าอื่น

### 5.3 Estimate, agreed cost และ current forecast

แยกค่าต่อไปนี้ ไม่ใช้ field `cost` เดียวทับทุกช่วงเวลา:

- `original_estimated_cost`: estimate snapshot ของ scope ณ issue revision นั้น; project reporting ใช้ snapshot ของ **issued revision ที่ accepted ใช้จริง** และ accepted CO ที่เกี่ยวข้อง ไม่ใช่ใบเสนอราคาฉบับแรกสุดเสมอไป ถ้ายังไม่ทราบให้คง unknown ใน history เมื่อ accepted แล้ว snapshot นี้ไม่ถูกเติมย้อนหลังให้ดูเหมือนรู้ราคาตั้งแต่แรก
- `agreed_cost`: ต้นทุนที่เลือก/ตกลงกับ vendor แล้ว พร้อม coverage/provenance ไม่อ้างว่าจ่ายเงินจริงแล้ว
- `forecast_cost`: agreed cost ของ component ที่เลือกแล้ว มิฉะนั้นใช้ estimate ล่าสุดที่ผู้มีสิทธิ์ publish; ถ้าไม่มีทั้งสองให้ unknown
- `actual_paid_cost`: ใช้ระบบการเงินจริงเดิมระดับ project ไม่สร้างจาก offer/BOQ และไม่โยนเข้ารายการ BOQ โดยเดา

Current cost plan เป็น versioned internal record แยกจาก immutable customer quotation แยก entered offer, draft selection และ confirmed/published award ให้ชัด การกรอก offer/แก้ working estimate ยังไม่เปลี่ยน Funds จนมี explicit publish/selection confirmation; confirmation อาจอยู่ใน action เดียวกับเลือก offer ได้ ไม่จำเป็นต้องเพิ่ม approval workflow ใหม่

หลัง issue/accept ล็อกเฉพาะ customer snapshot และ cost snapshot ที่ freeze ไว้ ไม่ปิด workspace ทั้งหน้า: owner ยังเปิด working cost plan/offer panel เพื่อกรอกหรือเลือก vendor ภายหลังได้ โดยสิทธิ์/สถานะและผลต่อ forecast ของการ publish แสดงแยกจากเอกสารลูกค้า

ทุกการ publish/award ต้องมี expected version, actor/reason/effective time, audit และคำนวณผลต่อ forecast/deficit ภายใน transaction เดียวกับ source-version update เอกสารต้นทุนที่เคย export อ้างอิง cost-plan version เดิมได้เสมอ

Working cost plan ก่อน acceptance อ้าง draft/issued revision และ scope version ของตัวเองได้ เพื่อทำราคา/รับ offers ก่อนปิดการขาย แต่ยังไม่เป็น operational budget Published cost plan ที่ใช้กับ Funds ต้องอ้าง exact accepted baseline/scope version หากมีงาน CO ใหม่/component ขาด/stale award ให้ required cost เป็น unknown ไม่เติม 0 หรือเอา estimate ของ scope อื่นมาแทน การ activate scope ใหม่ต้องสร้าง/validate corresponding cost-plan version ใน transaction เดียว และเก็บ published plan ก่อนหน้าไว้ดูย้อนหลัง การปรับ effective date ไม่ rewrite historical system snapshots

### 5.4 Quotation lifecycle, alternatives และ change orders

| Concept | ความหมาย | การเข้าฐานงบ |
| --- | --- | --- |
| Draft | แก้ไขได้ ยังไม่ส่ง | ไม่เข้า |
| Issued | เอกสาร snapshot ที่ RAYADEE ส่ง/ออกแล้ว | ยังไม่เข้า จน accepted |
| Revision | แก้ข้อเสนอใน lineage เดิม; revision ใหม่ยังไม่แทนของที่ accepted ทันที | เข้าเฉพาะ revision ที่เลือก accepted/active |
| Alternative | ข้อเสนอทางเลือกในกลุ่มเดียวกัน เช่น spec A/B | เลือกได้หนึ่ง main option ไม่บวก alternatives |
| Accepted | RAYADEE บันทึก agreement ของ revision ที่ issue แล้ว พร้อม evidence | เข้าเมื่อ activate baseline ตามกติกาด้านล่าง |
| Superseded/rejected/withdrawn | เก็บย้อนหลัง ไม่แก้หรือลบ snapshot | ไม่เข้า active baseline |
| Change order | งานเพิ่ม/ลดหลังตกลง main; มี revision/acceptance ของตัวเอง | เข้าเฉพาะ accepted delta ของแต่ละ change order |

- UI ไม่เปิด dropdown ให้ตั้ง status ใดก็ได้; ใช้ transition commands ที่ตรวจ guard ฝั่ง backend
- Issue ตรวจชื่อเอกสาร/project/customer, scope/unit/quantity/sell, calculation/terms และ payment schedule; cost ไม่ครบอนุญาต issue ได้พร้อม warning ไม่บังคับรอ vendor ก่อนเสนอราคา
- Issued และ accepted customer header/scope/rates/terms/rounding policy/doc pages เป็น immutable; project/customer/master edits ภายหลังไม่เปลี่ยนไฟล์เก่า
- Acceptance บันทึก chosen revision, agreed date, actor, recorded timestamp และหลักฐาน/ข้อความอ้างอิง ผู้บันทึกคือ RAYADEE ไม่อ้างว่าลูกค้า sign/กดยอมรับผ่านระบบ
- Default acceptance action activate main/CO ใน transaction เดียวโดยผู้มีสิทธิ์ เว้น manual legacy cutover ที่ให้ preview และยืนยันการเปลี่ยน source ชัดเจน
- หนึ่ง project มี active accepted main เพียงหนึ่ง revision รวม accepted change order revision ล่าสุดของแต่ละ CO หนึ่งครั้ง
- Main revision ใหม่หลังเริ่มงาน **ไม่ทำให้ accepted CO หายหรือถูกนับซ้ำ**: default งานเปลี่ยนใช้ CO; ถ้าจะ rebaseline main ต้อง preview ว่า CO ใด retain หรือถูก absorb เข้า main พร้อม explicit mapping/confirmation ระดับ CO ไม่ใช่การบังคับ map BOQ เก่าไป V2
- Retain/absorb CO ต้องรักษา original-estimate provenance และ vendor obligations/award identities ไม่สร้าง award ซ้ำหรือทำ cost หายเมื่อเปลี่ยน membership; validate baseline + cost-plan lineage และ apply ทั้งชุด atomically ไม่อนุมาน absorption จากยอดเท่ากัน
- CO อ้าง baseline/version และ logical items ที่เพิ่ม/ลด ป้องกัน stale/overlapping deduction, ลดเกิน remaining scope และ double acceptance; conflict ให้แก้ draft ไม่ silently rebase
- Signed delta ใช้ direction `ADD`/`DEDUCT` พร้อม quantity/rate magnitude ไม่ติดลบ เพื่อลดปัญหาเครื่องหมายติดลบซ้ำ; คำนวณ net impact แบบมี calculation policy เดียวกัน
- DEDUCT ฝั่งลูกค้า **ไม่ยกเลิก vendor obligation หรือลด forecast cost อัตโนมัติ**: cost impact ต้องเป็น explicit cost-plan/award adjustment แยกกัน หากยังมีต้นทุนผูกพันของงานที่ถูกลด ให้เก็บเป็น retained component cost ที่อ้าง source component เดิมพร้อมเหตุผลจนมีการปรับ/ยกเลิกจริง ไม่ลบทิ้งเพราะ item ไม่อยู่ใน active customer scope และไม่ reverse actual expenditure
- ยอด main/CO ต้องแสดงทั้งก่อนและหลังเปลี่ยน; ห้ามแก้ published budget ด้วย PATCH ตัวเลขรวมโดยไร้ scope/revision source
- Payment terms ใน quotation เป็นเงื่อนไขเอกสาร **ไม่สร้าง Installment/Transaction/InputPayment อัตโนมัติ**

### 5.5 Price Database และ reuse

- Canonical item: code, name/spec, unit, category/tags, optional metadata ที่ช่วยเทียบงาน, status และ reference-price version ของ material/labor sell/cost
- Search/filter ตาม code/spec/unit/category/source/date; เปิดประวัติจาก item editor ได้ เลือกใช้รายการหรือ reuse หมวด/BOQ จาก project เดิมที่มีสิทธิ์
- Snapshot ค่าเข้า draft; การปรับ draft ไม่แก้ master และ master update ไม่ cascade เข้า draft/issued/accepted โดยอัตโนมัติ การ apply reference ใหม่ทำได้เฉพาะ explicit draft action พร้อม preview
- เก็บ price observations อัตโนมัติเมื่อมี business event เช่น issue, acceptance, publish estimate, supplier offer/award ไม่สร้าง sample ทุก keystroke/autosave
- เก็บ offered sell, accepted sell, estimated cost, offered vendor cost, agreed vendor cost แยกชนิด; actual paid cost มีได้เมื่อมีหลักฐาน allocation จากระบบจริงเท่านั้น ซึ่งการทำ allocation ใหม่ไม่อยู่ใน scope นี้
- ทุก observation มี source project/document/revision/item/component, event/source ID, date, quantity/unit/spec/tax basis, currency, vendor เมื่อเกี่ยวข้อง และ lineage ของการ copy/revise
- Price history เก็บ events ได้ครบ แต่สถิติใช้ distinct underlying business samples ไม่ถือ copy/revision ของโครงการเดียวกันเป็นดีลอิสระ; แสดงจำนวน project/accepted observations และช่วงวันที่ ไม่โชว์ average ไร้บริบท
- “บันทึกเป็นรายการมาตรฐาน” และ “อัปเดตราคาอ้างอิง” ต้องมีมนุษย์ยืนยันพร้อม source/audit; draft/verified/active/outdated/archived แยกจากความครบถ้วนของราคา
- ป้องกัน duplicate code/unit identity และ incompatible unit/spec; ห้าม auto-convert “งาน/เหมา” เป็น ตร.ม. หรือเฉลี่ยคนละหน่วยเพื่อเพิ่ม sample
- Phase นี้ให้ค้น/เทียบ/นำกลับใช้ก่อน AI auto-pricing หรือ model training ยังไม่อยู่ใน scope; เก็บข้อมูลให้เหมาะกับการพัฒนาภายหลังโดยไม่เพิ่ม vector pipeline ใหม่ตอนนี้

## 6. Calculation contract (ข้อเสนอ default สำหรับ implementation)

Backend เป็นผู้คำนวณ authoritative; FE preview และ export ใช้ calculation version เดียวกัน ส่ง decimal เป็น string ไม่ส่ง floating-point money เป็น source of truth

### 6.1 Precision และ line totals

- เสนอ `NUMERIC(20,4)` สำหรับ quantity/unit rates และ `NUMERIC(20,2)` สำหรับ THB totals; เปอร์เซ็นต์รองรับอย่างน้อย 4 decimals ตรวจ overflow/finite/range และห้าม truncation เงียบ ๆ
- ใช้ Decimal และ `ROUND_HALF_UP` 2 decimals ที่ component extended amount: `amount = round(quantity × unit_rate, 2)` จากนั้นรวม material/labor เป็น item total และรวม leaf totals เป็น group/document subtotal
- Structural subtotals เป็น derived display rows เท่านั้น ไม่ส่งกลับไป sum เป็น billable items
- Sell default ใช้ scope quantity; cost ใช้ component quantity ที่ default จาก scope; UI ต้องแสดง basis ต่างกันเมื่อมี override
- Material/labor ที่ not applicable ให้ explicit state; unit price 0 ที่ตั้งใจใช้ไม่เท่ากับ unknown; known-cost subtotal แสดงได้ แต่ full forecast/margin เป็น unknown หากมี required component ไม่ครบ
- Cost completeness แสดง required/priced counts และรายการขาด; ไม่ใช้ยอดขาย > 0 เป็น denominator และไม่ใช้ amount-weighted completeness เมื่อยังไม่รู้ราคาส่วนที่ขาด

### 6.2 Selling adjustments, VAT และ margin

- ขายได้ทั้ง manual rate หรือ helper: markup `sell = cost × (1 + p)`; target margin `sell = cost / (1 − m)` โดย `m < 100%` UI ใช้ชื่อชัดเจน ห้ามเรียก markup ว่า margin
- Helper ใช้เมื่อ cost known และมี explicit apply เท่านั้น ไม่ผูก sell ให้เปลี่ยนตาม cost ตลอดไป
- Document-level overhead/profit markup เป็น optional explicit adjustments ค่าเริ่มต้นของ V2 เป็น 0; หากเสนอใช้ project defaults ต้องให้ยืนยันก่อนนำเข้า draft ไม่คิดซ้ำจาก unit rates อย่างเงียบ ๆ
- เสนอ policy: `S = sum(rounded sell leaf totals)`; overhead/profit adjustments คิดแต่ละรายการจาก S แล้ว round; `B = S + overhead + profit_markup`; discount เลือก fixed หรือ percent of B แบบใดแบบหนึ่ง; `net_sell_ex_vat = B − rounded_discount`; `VAT = round(net_sell_ex_vat × vat_rate, 2)`; `grand_total = net_sell_ex_vat + VAT`
- Snapshot tax rate/basis และ calculation version ต่อ revision ไม่ hardcode VAT 7% ใน runtime จาก test fixture; V2 comparison/reference ใช้ค่าก่อน VAT บน basis ที่ระบุ ไม่เปลี่ยน VAT/WHT/FlowAccount rules ของ actual finance
- หาก vendor ให้ราคารวม VAT ต้องเก็บ original amount/tax basis และ normalized comparison amount โดยเปิดเผยวิธีคำนวณ ห้ามถือ unknown tax basis ว่าเทียบกันได้แล้ว
- Forecast ใช้ `net_sell_ex_vat − forecast_cost_ex_vat`: ฝั่ง sell รวม accepted CO signed deltas ส่วน cost มาจาก compatible published cost plan รวม retained vendor obligations ตาม §5.4 **ไม่หักต้นทุนตาม sell DEDUCT อัตโนมัติ**; ไม่ใช้ customer grand total including VAT เพื่อทำกำไรให้สูงขึ้น
- Margin percent = profit / net sell เมื่อ net sell > 0 และ costs complete; กรณี zero sell ใช้ N/A ไม่หาร 0 ส่วนกำไรติดลบที่คำนวณได้จริงต้องแสดง
- ถ้าแสดง item margin หลัง document discount/charges ให้ allocate adjustment ตามน้ำหนักและลง rounding residual อย่าง deterministic; หากยังไม่ allocate ให้ระบุว่า item margin เป็น before document adjustments ห้ามอ้างว่ารวมตรงกับ project margin
- Contingency/reserve/Funds semantics เดิมคงเดิม ไม่เอา reserve มาหักเป็น vendor cost ซ้ำอีกชั้น

### 6.3 Payment schedule และ fixture

- Percent schedule ต้องรวม 100%; ปัดงวดก่อนสุดท้าย แล้วงวดสุดท้าย = grand total − sum(previous installments); fixed amounts ต้องรวมตรง document total
- Fixture: qty 10, cost 500, sell 700, markup 15%, discount 10%, VAT 7% → item cost 5,000, sell subtotal 7,000, gross item margin 28.5714…%, net sell 7,245, VAT 507.15, grand total 7,752.15
- Copy fixture เป็น qty 20 → grand total 15,504.30 และต้นฉบับต้องไม่เปลี่ยน; payment rounding fixture อยู่ใน §3.1

## 7. Data model และ architecture ที่เสนอ

ใช้ FastAPI + PostgreSQL เดิม แยก domain calculation/state transitions ออกจาก HTTP และ storage ไม่เพิ่ม microservices ตาราง/ไฟล์ต่อไปนี้เป็น logical responsibilities; รวมส่วน one-to-one ที่เหมาะสมได้ ไม่สร้าง abstraction layer เพื่อให้ครบชื่อ

| Logical entity | หน้าที่/invariants |
| --- | --- |
| BOQ document/family | project FK, MAIN/CHANGE_ORDER, alternative group, lineage, readable document number; numbering ไม่ใช้ `count + 1` ที่ชน concurrent create |
| BOQ revision | immutable-on-issue header/terms/pages/calculation policy, state, revision number, optimistic version, creator/issued timestamps |
| BOQ node | revision row ID, stable logical ID, parent/order/type, spec/unit/quantity/sell, catalog/source lineage; composite ownership validation |
| Cost-plan version/components | working/published version, component quantities/states/estimate source, original estimate snapshot, selected offer reference; customer snapshot ไม่ถูก rewrite |
| Vendor offer/offer lines | commercial vendor link, evidence/date/basis, component coverage และ rates; retained unchosen offers |
| Cost selection events | selected/replaced offer, actor/reason/version; หนึ่ง active full-coverage selection ต่อ component |
| Catalog/reference-price versions | canonical identity, lifecycle state, explicit promotion/update audit |
| Price observations | immutable source events + comparable business lineage ไม่ถือทุก revision เป็น independent sample |
| Project budget baseline/members | source LEGACY/V2, one active MAIN + accepted CO membership, published cost version, completeness, activation time/version |
| Agreement/audit/export metadata | acceptance/evidence, transition audit, private artifact URI/hash/audience/source versions; reuse existing shared patterns เมื่อเหมาะสม |

Implementation constraints:

- Preserve `Project`, `BOQItem`, `Installment`, `Transaction`, `InputRequest`, `InputPayment` IDs/FKs เดิม เพิ่ม models/migrations แบบ additive; ไม่บังคับ materialize V2 เป็น CUSTOMER/SUBCONTRACTOR duplicates
- FK/indexes สำหรับ project/revision/parent/order, catalog unit/spec search, vendor date/history และ active baseline lookup; uniqueness สำหรับ revision number, event idempotency, active selections/baseline memberships
- Composite validation ป้องกัน document ของ project A อ้าง component ของ B; hierarchical deletes/updates ต้อง transaction-safe
- Snapshot terms/layout เป็น versioned JSONB ได้ถ้าไม่ต้อง query ทุก field แต่ monetary fields และ relational identities ควร typed/queryable; ไม่เก็บทั้ง domain เป็น opaque JSON blob
- Bulk reads/load options เพื่อเลี่ยง N+1; list price history/quotes paginate และขอ aggregates เป็น batch ไม่โหลดทุก project ทีละ request
- Dedicated internal cost DTO และ client/vendor allowlist DTO; ห้าม serialize ORM ทั้งก้อนแล้วซ่อนด้วย CSS
- Audit เก็บ actor/project/action/entity/version/source/reason/correlation ID; ไม่ log token, attachment content หรือราคาละเอียดใน generic request logs โดยไม่จำเป็น
- ไม่เพิ่ม package ที่ไม่จำเป็น ถ้าต้องเพิ่ม Excel/PDF/decimal dependency ให้เลือก library ที่ maintain และตรวจ official docs/version/license ในตอน implementation; package lock และ bounded resource use ต้องครบ

## 8. API, permissions และ concurrency contracts

### 8.1 Proposed API surface

ใช้ prefix `/api/v1` และ StandardResponse เดิม ชื่อด้านล่างเป็นข้อเสนอใหม่ ต้องลง OpenAPI/tests และปรับ callers พร้อมกัน ไม่อ้างว่า endpoints เหล่านี้มีแล้ว

| Group | Proposed contract |
| --- | --- |
| Workspace/read | `GET /projects/{project_id}/boq-workspace`; list documents/revisions, active source, internal scope/cost completeness |
| Draft | `POST /projects/{project_id}/boq/documents`; `GET/PATCH /boq/revisions/{revision_id}`; atomic batch node/component edits |
| Lifecycle | explicit `validate`, `issue`, `revise`, `create-alternative`, `record-acceptance`, `create-change-order`, `activate-baseline` commands |
| Offers/cost | project-scoped offer CRUD, compare, select/replace, publish-cost-plan commands |
| Library | paginated catalog/search/price-history, explicit promote/update-reference and reuse commands |
| Budget | `GET /projects/{project_id}/budget-summary` backed by shared budget service |
| Exports | `POST /boq/revisions/{revision_id}/exports` with audience/format/vendor/cost-version และ selected node/component IDs หรือ persisted RFQ scope ID; metadata/status/private download |

- Response ใช้ `{ "status": "success", "data": { "status": "DRAFT", ... } }`; lifecycle `status` อยู่ใน `data` เพราะ `src/api.js` reject top-level status ที่ไม่ใช่ `success`
- Reuse `apiRequest` auth/error handling; หากแยก `boqApi.js` ให้ export request helper แบบเล็กที่สุด ไม่สร้าง fetch/auth stack อีกชุด
- Current request helper อ่าน JSON: export ส่ง metadata/download contract หรือใช้ focused binary helper ห้ามเปลี่ยน JSON parser ทั้งระบบเพื่อรองรับ Excel
- API ส่ง null/explicit cost state จริง FE normalizer ห้ามใช้ legacy `toNumber(..., 0)` กับ cost unknown
- Save ใช้ expected version/ETag; validation errors ระบุ node/field; stale version ตอบ 409/412 พร้อม current version และทาง recover ไม่มี last-write-wins เงียบ ๆ
- Autosave debounce/batch ได้ แต่ save indicator ต้องรอ server acknowledgment; issue/export latest draft ต้อง flush save แล้วล็อก revision/version ที่ตั้งใจใช้
- Idempotency key สำหรับ create/copy/issue/accept/activate/select/publish/export และ retry ที่มี side effects ผูก actor/project/command/request hash; key เดิมต่าง payload ต้อง reject
- Export draft ได้เพื่อ review แต่ mark DRAFT และ freeze saved render snapshot/version ก่อน generate ห้ามอ่าน mutable rows ขณะกำลัง stream file
- Domain transition + totals + audit + baseline/version update commit atomically; artifact generation fail ไม่ต้องย้อน acceptance แต่ retry artifact จาก snapshot เดิม

### 8.2 Permission defaults — ไม่ขยาย role โดยปริยาย

| Action | V2 default ตามระบบปัจจุบัน |
| --- | --- |
| Internal project/BOQ read | Owner/Admin ภายใต้ existing project/resource access checks |
| Draft/offer/cost edits, issue, acceptance, baseline activation | Owner เท่านั้น ตาม existing BOQ mutation guard |
| Catalog promotion/reference update | Owner เท่านั้น |
| Export | ผู้มีสิทธิ์อ่าน resource และ audience-specific data; client/vendor format ไม่เท่ากับ anonymous public access |
| Funds mutation | Owner ตาม contract เดิม |
| Customer/subcontractor access management | คง guard เดิมซึ่งบาง action อนุญาต explicit Admin; ห้ามทำให้กลายเป็น owner-only ทั้งระบบ |
| Customer/subcontractor login | คง report/execution access เดิม ไม่ได้รับ internal cost/library/quote access ใหม่ |

Map new action names เป็น capabilities ภายในเพื่อทดสอบได้ แต่ไม่สร้าง role-management feature หรือเปิด Admin authoring เพิ่มเอง หากภายหลังผู้ใช้ต้องการ team drafting ให้ขออนุมัติ matrix แยก ไม่ยกเลิก owner guard ของ Input/Approval/Settings

Enforce server-side ทุก mutation, history/compare/search และ export/download; test cross-project ID substitution และ resource ownership ของ attachments ห้ามใช้การซ่อนปุ่มแทน authorization

### 8.3 Concurrency boundaries

- Lock/order ระหว่าง project baseline, cost plan และ FundBucket ต้องเป็นลำดับเดียวทุก path; explicit baseline/cost publish ต้อง serialize กับ outward allocation
- Existing Funds fingerprint hash จำนวนเงินอย่างเดียวไม่พอ เพิ่ม source kind, baseline ID/version, cost-plan version, completeness และ calculation version เพื่อ detect stale selection แม้ยอดเท่าเดิม
- คำสั่ง accept alternative สองอันพร้อมกันต้องไม่เกิด active MAIN สองตัว; double-click acceptance/CO ไม่เพิ่มงบสองครั้ง
- Supplier selection ระหว่าง owner เปิด allocation form ต้องทำให้ allocation ส่ง stale version ไม่ผ่าน ต้อง refresh/reconfirm ไม่ lock UI ตลอดการกรอก
- Node reorder ใช้ stable IDs และ expected version ไม่ array index; save กับ issue พร้อมกันต้องจบเป็น snapshot ที่ตรง saved version หรือ conflict ไม่ออกเอกสารครึ่งชุด

## 9. Frontend/UI implementation plan

### 9.1 Outcome และ invariants

ผู้ใช้หลักคือทีม RAYADEE ที่ทำราคา โดยตาราง scope + sell/cost และสถานะเอกสารเป็น visual anchor ไม่ใช่ dashboard metric cards การแก้ราคาใน desktop/tablet ต้องเร็ว และ mobile ยังตรวจ/แก้ทีละรายการ/อ่าน preview ได้

UI plan ใช้ `ui-ux-review` และ `Design/DESIGN.md`; Stitch query ในรอบวางแผนติด authentication จึงอ้างอิง demo กับ design tokens/components ใน repo ก่อนเริ่มเขียน UI ให้ query Stitch ตาม AGENTS อีกครั้ง หากยังใช้ไม่ได้ให้ระบุข้อจำกัดและใช้ checked-in design ไม่ออกแบบ shell ใหม่เอง

UI presentation changes ไม่อนุญาตให้แก้ auth, API semantics, validation หรือ state transitions เงียบ ๆ การเปลี่ยน BOQ domain/API ที่จำเป็นได้รับการระบุแยกใน §5–8; business logic/permissions ของ feature อื่นคงเดิม

### 9.2 Layout/actions และ affected components

| Decision | Files/components | Reuse/layout/device/accessibility | Risk และ validation |
| --- | --- | --- | --- |
| REPLACE connect/sync ด้วย open/create BOQ | `ProjectPage.jsx`, `api.js` | ใช้ ProjectCard และ createProject เดิม; ปุ่มหลักตาม existing role; mobile ไม่เพิ่ม card actions แข่งกัน | ห้ามสร้าง project ซ้ำ; test create แล้วเข้า BOQ ของ ID เดิม |
| REPLACE dual-tree compare ด้วย native workspace | `components/BoqWorkbench.jsx`, `ProjectDetailPage.jsx`, new `components/boq/*` | หนึ่ง revision selector, toolbar, dense tree/table, pinned totals; consolidated/customer/cost columns; sticky headings/numeric alignment | ไม่ปิด Funds/Cashflow/Inspection; test shared IDs/reorder/save/conflict/unknown |
| MERGE quotation navigation ซ้ำ | new quotation page/components, `App.jsx`, `Sidebar.jsx`, `WorkspaceTopbar.jsx` | list → workspace/preview; revision/alternative selector เดียว; primary CTA เปลี่ยนตาม lifecycle ไม่แสดงทุก action เป็น primary | ป้องกันเลือกผิด revision; test deep link/reload/back/history |
| EMPHASIZE missing cost และ source | item editor/vendor panel | inline missing indicator + filter; secondary source/date/coverage; ไม่เพิ่ม card ต่อ field | unknown vs 0 ไม่ใช้สีอย่างเดียว; test free item/mixed component coverage |
| MOVE vendor comparison ไว้ใน context งาน | vendor offers panel/export dialog | item/selected-scope panel, semantic comparison table; material/labor basis ชัด | ไม่เพิ่ม supplier-management app ใหม่; test confidentiality/quantity mismatch |
| REPLACE library sample cards ด้วย searchable price workspace | new price database components | table/list + detail history; explicit promote/update action; mobile detail drawer/page | ไม่ auto-update project/master; test permission/lineage/source identity |
| KEEP shared shell และ retained pages | `App.jsx`, `Sidebar.jsx`, `index.css`, admin feedback components | reuse tokens, navigation, confirmation/toast, typography; BOQ CSS scoped | no global retheme; compare retained pages desktop/mobile |
| REMOVE obsolete Sheets copy | `SettingPage.jsx`, `SupportPage.jsx`, topbar | เอาออกเฉพาะ integration entry/copy ที่เกี่ยวกับ BOQ Sheets | ทดสอบ settings customer/subcontractor/access และ integration อื่นยังครบ |

Proposed routes: `/project/detail/:projectId/boq`, `/quotations`, `/quotations/:quotationId`, `/price-database` ภายใน protected internal layout เดิม; `/project` และ `/project/detail/:projectId` คงเดิม Customer report routes ไม่เปลี่ยน

Quotation/BOQ deep link ต้อง pin `revision_id` ด้วย query parameter หรือ nested route และ cost-plan version เมื่อเปิด internal historical view; preserve selection ผ่าน reload/back/preview/export ห้าม link เอกสารเก่ากระโดดไป latest revision/alternative เงียบ ๆ ถ้าไม่มี ID ให้เลือก active revision อย่างชัดเจนแล้ว canonicalize URL

Candidate responsibility files (ไม่ต้องสร้างทุกไฟล์หากรวมแล้ว cohesive กว่า):

```text
Projects-001-FE/src/components/boq/
  BoqWorkspace.jsx, BoqItemsTable.jsx, BoqItemEditor.jsx
  BoqTotalsSummary.jsx, BoqRevisionPicker.jsx, BoqReuseDialog.jsx
  BoqVendorOffersPanel.jsx, BoqExportDialog.jsx
  boqDraftState.js, boqCalculations.js, boq.css
Projects-001-FE/src/components/quotations/
  QuotationWorkspace.jsx, QuotationRevisionComparison.jsx
  QuotationPreview.jsx, QuotationAgreementDialog.jsx, QuotationChangeOrderPanel.jsx
Projects-001-FE/src/components/priceDatabase/
  PriceDatabaseWorkspace.jsx, PriceHistoryPanel.jsx, PriceMasterEditor.jsx
```

### 9.3 Interaction and visual acceptance

- ใช้ existing teal/sand/off-white tokens, Sarabun/Inter และ tabular numbers; divider-first ไม่ซ้อน card ใน card, decorative gradients หรือ oversized metric cards
- Page title/project/revision/status ชัดแต่ไม่แย่งพื้นที่ตาราง; totals เป็น compact summary เดียว มี label before/after VAT และ completeness
- Keyboard: labels, Tab/Shift+Tab, Enter commit, Escape cancel, add/duplicate/delete controls, dialog focus trap/return focus และ visible focus; drag มีคำสั่ง Move up/down / Move to section-category-subcategory ที่ใช้ keyboard ได้ ไม่เกี่ยวกับการสร้าง commercial Alternative
- ใช้ semantic table + native inputs/buttons ก่อน custom ARIA grid; ถ้าเลือก grid ต้อง implement keyboard pattern ครบ ไม่ใส่ role เพียงอย่างเดียว
- Validation inline ผูก input; announcement สั้นสำหรับ save/error ไม่ spam screen reader ทุก keystroke; warning/error ไม่สื่อด้วยสีอย่างเดียว มี contrast ตาม design และ reduced-motion
- States ต้องมี loading, true empty, API failure, read-only, editing, saving, saved version/time, failed save, conflict, offline, unpriced, issued/accepted immutable และ export pending/failed
- ไม่แปลง fetch error เป็น empty BOQ (`getProjectDetailData` เดิมมี catch เป็น null ต้องแยก error); ใช้ BOQ-local error/retry boundary ไม่เพียงลบ catch จน whole-page error ซ่อน Funds/Cashflow/warehouse/Inspection ข้อมูล project และ retained sections ต้องยังใช้งานได้ตาม dependency จริง หาก budget unavailable ให้ fail closed เฉพาะ budget-dependent action ไม่แสดง 0 ปลอม; failed save เก็บ dirty draft และมี retry/copy recovery ก่อน leave
- Desktop 1440px: dense table มี scroll ภายใน; tablet 768/1024px: ซ่อน secondary columns ผ่าน view selector; mobile 390px: collapsed shell, item summary/detail editor และ readable quote preview ไม่ให้ทั้งแอปล้นแนวนอน
- คงการใช้งาน LINE webview/customer reports เดิม; V2 ไม่ย้าย BOQ internal ไป customer/subcontractor view

## 10. Excel/PDF และ document snapshots

| Export audience | เนื้อหา | ต้องไม่รวม |
| --- | --- | --- |
| Customer Excel/PDF | customer/project header, chosen revision/scope, quantities, sell rates/totals, agreed adjustments, VAT, terms/payment schedule และหน้าประกอบที่เลือก | cost, margin, vendor comparisons, internal notes, catalog confidence/internal history |
| Internal cost/consolidated Excel | scope + sell/cost components, estimate/agreed/forecast, completeness, source/vendor และ margin ตามสิทธิ์ | ข้อมูลส่วนตัวหรือ attachment ที่ไม่จำเป็น |
| Vendor RFQ Excel/PDF | เฉพาะ requested scope/spec/unit/qty ของรายนั้น ช่องราคาเว้นว่าง พร้อม reference | customer sell/margin, vendor อื่น/offer อื่น, internal pricing guidance |
| Selected-vendor cost Excel/PDF | เฉพาะงาน/component และ agreed rates ที่เกี่ยวกับรายนั้น พร้อม version/reference | ราคาต้นทุนเจ้าอื่นและราคาขายลูกค้า |

- Excel export เป็นไฟล์ `.xlsx` จริง ไม่ HTML เปลี่ยนนามสกุล; scope hierarchy/units/numeric values/subtotals/tax/Thai text อ่านได้ พิมพ์ได้ และไม่เป็นช่องทาง import กลับ
- Customer export ต้องใช้ allowlisted server serializer ตั้งแต่ query/DTO ห้ามซ่อน cost worksheet/column แล้วถือว่าปลอดภัย; vendor export ต้อง validate vendor scope
- Selected export/RFQ scope ต้อง validate node/component IDs ว่าอยู่ใน revision/project และสิทธิ์ที่ขอจริง แล้ว freeze subset ใน artifact metadata; rerender/retry ไม่เติมรายการที่ไม่ได้เลือกหรืออ่าน latest scope แทน ห้ามรับ cross-revision IDs แม้ description ตรงกัน
- Treat user-entered text เป็น text cell ป้องกัน spreadsheet formula injection (`=`, `+`, `-`, `@` ในข้อความ) โดยไม่ทำให้ numeric values กลายเป็น string ทั้งไฟล์
- Export frozen computed totals; หากมี formulas เพื่อใช้งานสะดวก ต้องมี cached/equivalent displayed values และผลตรง backend ไม่ใช้ Excel recalculation เป็น source of truth
- PDF layout A4: cover/header, detailed BOQ, optional image/visual pages, payment terms, commercial terms และ agreement/signature placeholders ที่เลือกใช้ได้; label ว่า internal recorded agreement ไม่ปลอม digital signature
- กำหนด page order/layout ใน draft, repeat table headers, Thai font embedding, page breaks/no clipped rows, footer revision/page identity; render ไฟล์จริงตรวจหลายหน้า
- ไฟล์ทุกชิ้นผูก revision snapshot, calculation version, audience และ cost-plan version เมื่อมีต้นทุน; internal cost เปลี่ยนแล้ว customer issued artifact เดิมยังเหมือนเดิม
- Private storage/signed downloads ใช้ infrastructure เดิม ตรวจ ownership ก่อนออก URL, limited expiry, safe filenames/MIME/size limits; แยก evidence/export prefix กับ temporary receipt lifecycle เพื่อไม่ให้หลักฐานใบเสนอราคาถูก cleanup แบบ OCR temp files
- ไม่ตั้ง public bucket/URL, ไม่เพิ่ม external delivery/email/LINE ส่งเอกสารอัตโนมัติ; user download/export เองใน scope นี้

## 11. Integration: active budget, Funds และข้อมูลจริงเดิม

### 11.1 One project budget service

เพิ่ม shared budget adapter/service (ชื่อเสนอ `project_budget_service.py`) คืนอย่างน้อย:

`source_kind`, `baseline_id/version`, `main_revision_id`, `accepted_change_order_ids`, `cost_plan_version`, `calculation_version`, `activated_at`, `net_sell_ex_vat`, `original_estimated_cost`, `agreed_cost`, `forecast_cost`, `forecast_margin`, `cost_completeness`, `status`, `as_of`

- LEGACY adapter ใช้พฤติกรรมเดิมของโครงการที่ยังไม่ switch; V2 adapter ใช้ accepted scope/current published cost เท่านั้น Company Operations ไม่มี BOQ และยังใช้ opening forecast balance เดิม
- ไม่มี baseline ให้แสดง draft/not activated ตามจริง ไม่สมมติเป็น accepted revenue; missing cost ต้องมี status และ nullable full forecast ห้ามทำ null → 0 แล้วแสดงกำไร
- ปรับ summary contracts แบบ additive/explicit พร้อม FE/MCP tests; current non-null numeric consumers ต้องได้รับ status handling ก่อนเปิด V2 ห้ามทำ breaking response เงียบ ๆ
- Dashboard/project cards/Funds/Chat/Insights/MCP ต้องอ่าน source เดียวกันและระบุ version; historical query ก่อน cutover ใช้ source ณ เวลานั้น ไม่เอา backdated agreement ไป rewrite report ในอดีต
- Batch budget lookups ไม่ N+1; หนึ่ง summary ต้องมาจาก coherent baseline/cost snapshot แม้มี concurrent publish

### 11.2 Funds: เปลี่ยน source ไม่เปลี่ยน ledger/formula

สูตรเดิมคงไว้เมื่อ forecast known:

```text
raw_available = forecast_base + allocated_in - allocated_out - protected_reserve
available = max(0, raw_available)
deficit = max(0, -raw_available)
```

- Forecast base สำหรับ project ที่ switch แล้ว = V2 forecast margin; actual cashflow ไม่ถูกใช้แทน forecast และไม่ผูกกับ BOQ edit
- ข้อเสนอ safety contract สำหรับ V2: เมื่อ required cost ไม่ครบ ให้แสดง forecast/available ว่า “ยังประเมินไม่ได้” และ reject **new outward allocation** ที่ต้องอาศัย margin นั้น ไม่แสดง available ปลอมเป็น 0 ที่ดูเหมือนประเมินแล้ว
- การยังไม่เลือก vendor ไม่ทำให้ blocked หากมี estimate ครบ; forecast ต้องบอกว่า estimated/partly agreed เพื่อไม่อ้างเป็น final cost
- ไม่ block Actual Payment/Input approval หรือ incoming allocation ที่ผ่าน source-side rules เดิม, ไม่ลบ existing allocation, ไม่ auto-reverse ledger เพราะ cost เปลี่ยน; reversal/correction ที่จำเป็นต้องไม่ถูก blanket unknown-cost gate ปิด ให้รักษา existing correction rules และทดสอบแยก
- เมื่อ publish cost สูงขึ้น/รับ CO งานลดแล้วเกิด deficit ให้แสดง deficit ตามสูตรเดิมพร้อม audit ไม่แก้ย้อนหลังให้ allocations หาย
- Company Operations, opening balance/monthly rollforward, reserve และ transfer/reversal semantics เดิมต้องผ่าน regression tests
- ใช้ source-aware fingerprint และ common locking ตาม §8.3; source ที่ยอดเท่าเดิมแต่ lineage เปลี่ยนก็ต้อง invalidate stale allocation form

### 11.3 Manual replacement โครงการเดิม

1. เปิด existing project เดิม สร้าง V2 draft ผู้ใช้กรอก BOQ ย้อนหลังเองได้ ส่วน finance/execution เดิมทำงานต่อ
2. Legacy เป็น active budget จน owner เตรียม V2 main พร้อม issue/record agreement; agreement date อาจเป็นวันจริงในอดีต แต่ `recorded_at/activated_at` เป็นเวลาในระบบจริง
3. Preview active V2 scope/net sell/cost completeness/forecast และผลต่อ Funds ถ้าต้นทุนไม่ครบต้องยอมรับ status/gating ตาม §11.2 ไม่บังคับให้ยอดตรง BOQ เก่า
4. Owner ยืนยัน cutover transaction: activate V2 baseline, source version, audit/actor/time; retain legacy history/read access และ existing project ID
5. หลัง switch งบอ่านเฉพาะ V2 ไม่บวก legacy; actual finance อ่านประวัติทั้งหมดตาม references เดิม ไม่สร้าง/replay/reapprove payment หรือสร้าง project ใหม่

ไม่ทำ: Excel import สำหรับ migration, automated old→new line mapping, mandatory expense allocation ย้อนหลัง, BOQ amount reconciliation, opening-balance adjustment เพื่อบังคับยอดตรง, delete/truncate legacy rows

ข้อแตกต่างสำคัญ: **ไม่ต้อง reconcile BOQ เก่า/ใหม่ แต่ต้องทดสอบว่าข้อมูลการเงินจริงไม่หาย** การ regression-test จำนวน/IDs/ยอดรายการจริงใน fixture ก่อน/หลัง cutover เป็นงานรักษาข้อมูล ไม่ใช่งานให้ผู้ใช้ตรวจเทียบ BOQ

Critical repository trap: `chat_analytics_service.py` มี historical Installment/Transaction joins ที่กรอง `BOQItem.valid_to IS NULL` ถ้า expire BOQ เก่าทั้งหมดตอน cutover ประวัติการเงินอาจหายจาก Chat/Insights ดังนั้นใช้ explicit source selector ไม่ expire/delete legacy เพื่อซ่อน budget และแยก active budget query ออกจาก historical financial-reference loading แม้ข้อมูล legacy ที่เก่าอยู่แล้วมี `valid_to` ก็ต้องอ่าน finance history ได้

## 12. File-level impact / agent implementation map

Paths ในตารางเป็นไฟล์ที่มีอยู่ ณ baseline; proposed new modules ระบุแยกท้ายตาราง Line numbers เปลี่ยนได้จึงให้ตรวจ function/class อีกครั้ง

| Existing file/path | Required work |
| --- | --- |
| `Projects-001-BE/app/models/boq.py` | Preserve Project/legacy BOQItem; เพิ่ม source metadata ผ่าน migration/model ที่เหมาะสม ไม่ยัด native single-scope กลับ dual legacy tree |
| `Projects-001-BE/app/schemas/boq_schema.py` | แยก legacy read schema จาก native contract; retire sync request/job schemas; IDs/decimal/null correctness |
| `Projects-001-BE/app/api/v1/projects.py` | เปลี่ยน budget readers/project detail adapter; retire sync/tabs/batch/jobs routes; preserve CRUD/access/history |
| `Projects-001-BE/app/services/boq_margin_service.py` | จำกัด legacy helper ใน legacy adapter; V2 ใช้ leaf-only totals กับ explicit source ไม่ sum all roots blindly |
| `Projects-001-BE/app/services/boq_sync_service.py` | Retire Sheets fetch/parser/persist write path หลังถอด callers; preserve stored data/migrations |
| `Projects-001-BE/app/services/boq_sync_job_service.py` | Retire jobs และ integration references แบบครบ dependency graph |
| `Projects-001-BE/app/services/fund_service.py` | ใช้ budget service, V2 unknown status, source fingerprint/locking; preserve ledger/math/Operations |
| `Projects-001-BE/app/api/v1/dashboard.py` | Budget aggregates จาก active source; actual cashflow queries unchanged |
| `Projects-001-BE/app/services/chat_analytics_service.py` | แยก active budget snapshot กับ historical financial FK joins; preserve project/access scoping |
| `Projects-001-BE/app/services/insight_warehouse_service.py` | ปรับ consumption/schema/version ตาม snapshot; ไม่ ingest alternatives เป็น budget หรือ duplicate actuals |
| `Projects-001-BE/app/services/mcp_read_service.py` | V2 current/versions/snapshot/diff/search ผ่าน stable IDs; retain resolvable legacy version refs/history |
| `Projects-001-BE/app/services/mcp_finance_document_service.py` | Active budget source; preserve historical financial joins/document access |
| `Projects-001-BE/app/services/mcp_project_operations_service.py` | เปลี่ยน BOQ budget reads เท่านั้น; preserve execution/daily-report/inspection behavior |
| `Projects-001-BE/app/services/mcp_processing_service.py` | ถอด `boq_sync` import/status branch อย่างเจาะจง ไม่ลบ OCR/daily-report delivery/FlowAccount processing |
| `Projects-001-BE/app/schemas/mcp_schema.py`, `Projects-001-MCP/` | Retire sync workflow/schema/tool contracts ที่เกี่ยวข้อง; update version/current/budget contracts/tests และ caller error ที่ actionable |
| `Projects-001-BE/app/core/config.py`, `Projects-001-BE/.env.example`, `Projects-001-BE/app/api/v1/settings.py` | ถอด BOQ sync-only config (`BOQ_BATCH_SYNC_MAX_TABS`), Google Sheets integration status/copy; preserve shared Google/Gemini/OCR/chat auth/dependencies |
| `Projects-001-BE/app/models/finance.py`, `app/models/input_request.py` | Preservation boundaries: ไม่ rewrite FK, payment history หรือบังคับ BOQ mapping; add regression fixtures ไม่แก้โดยไม่มีเหตุ |
| `Projects-001-FE/src/ProjectPage.jsx` | Remove sync drawer/state/tabs/polling/URL handlers; replace post-create/open action ด้วย native BOQ |
| `Projects-001-FE/src/ProjectDetailPage.jsx`, `src/components/BoqWorkbench.jsx` | Native entry/summary/workspace แทน dual comparison; preserve project finance/execution tabs |
| `Projects-001-FE/src/components/BoqSheetCharts.jsx` | Adapt BOQ-only category aggregation; no sheet/matched-status dependency; accepted source totals |
| `Projects-001-FE/src/api.js` | Retire `syncProjectBoq`, `getProjectBoqTabs`, `syncProjectBoqBatch`, `getProjectBoqSyncJob`; isolate legacy normalizers; add native adapter preserving errors/nulls/response wrapper |
| `Projects-001-FE/src/App.jsx`, `src/components/Sidebar.jsx`, `src/components/WorkspaceTopbar.jsx` | Focused protected routes/nav additions; remove BOQ sync copy; keep existing route guards/customer routes |
| `Projects-001-FE/src/SettingPage.jsx`, `src/SupportPage.jsx` | Remove Sheets-only card/copy, preserve unrelated controls/access rules |
| `Projects-001-FE/src/index.css` | Scoped BOQ styles and obsolete BOQ-only cleanup; no global shell/theme rewrite |
| `Projects-001-FE/package.json` | Add BOQ tests to test discovery; current `npm test` only covers funds/dailyReports globs |
| `docs/01_Business_Requirements.md` through `docs/04_LLD_Implementation.md`, `Design/S-BOQ/` | Mark superseded BOQ contracts/update native behavior and links; preserve finance requirements |

Proposed backend modules: focused `boq_document_service`, `boq_calculation_service`, `boq_cost_service`, `boq_catalog_service`, `boq_export_service`, `project_budget_service`, corresponding router/schemas/models/migrations/tests. Merge appropriately; no separate deployable service required

Sync retirement details:

- Existing `/projects/boq/sync`, `/projects/boq/tabs`, `/projects/boq/sync-batch`, `/projects/boq/sync-jobs/{job_id}` must stop accepting new sync operations after cutover release; return explicit retired/410 contract during compatibility window if old clients can still call, then remove
- Search all imports/callers/jobs/settings/MCP/tool manifests/docs before deleting files; startup/import tests must pass
- Remove BOQ-only env/docs/parser dependencies only if unused elsewhere; do not revoke shared IAM/secrets/Google APIs or remove Gemini/OCR libraries as an incidental cleanup
- Historical migrations/docs can retain “Google Sheets” as history marked retired; production UI/write paths must not continue offering it

## 13. Delivery phases และ verification gates

ทุก phase เป็น implementation ของแผนเดียว ไม่ถือว่า BOQ V2 เสร็จเพียงมี editor; ห้ามเปิด incomplete features ใน live workflow ก่อนผ่าน release gates

### Phase 0 — Baseline and contract lock

- ตรวจ checkout/diff/instructions และ actual callers ตาม §12; record baseline test results โดยไม่แก้ unrelated failures
- เขียน calculation/state/permission/budget response contracts และ fixtures ก่อน UI; verify existing tests discovery และ test database isolation
- Query Stitch/read design sources; ไม่ deploy เปลี่ยน live data หรือเริ่ม cutover จากการอ่านแผน
- Gate: implementation inventory/contract พร้อม ไม่มี unresolved business choice ที่ agent แอบเปลี่ยนเอง หากมี scope ใหม่จริงให้ถามเจ้าของก่อน

### Phase 1 — Additive domain + read compatibility

- Migrations/entities/indexes/state/calculation/audit/version commands; baseline selector default legacy สำหรับ existing projects
- Shared budget service + historical finance separation + consumer readiness/status support รวม Funds lock/fingerprint
- Migration upgrade/startup/legacy contract/finance-preservation tests ผ่าน ก่อนเปิด V2 writes
- Gate: old live workflow ยังทำงานจาก legacy source; ไม่มี V2 totals รั่วเข้า existing reports

### Phase 2 — Native single-entry BOQ

- Create/load/save hierarchy, dual pricing/null completeness, library-independent manual entry, reuse/copy, keyboard/responsive/error/conflict states
- Replace BOQ UI/connect action โดย V2 feature gate ที่ยังคง legacy view ได้ระหว่าง rollout ไม่ลบ history
- Gate: create/edit/reload/copy/reorder + server totals/role checks ผ่าน; draft ไม่เข้า operational budget

### Phase 3 — Quotation lifecycle and exports

- Main/revision/alternative/CO, issue/acceptance/evidence, immutable render snapshots, document numbering/preview, Excel/PDF audience contracts
- Private artifact storage/retry/auth; tests real generated workbooks/PDF rendering/Thai/rounding/confidentiality
- Gate: accepted-only baseline, no alternative double count, draft/issued changes cannot corrupt accepted quotation

### Phase 4 — Vendor cost and Price Database

- Manual offer/compare/select, original estimate/current cost version, full coverage guard, source-aware Funds publish
- Automatic price history + explicit catalog promotion/reference updates + quick reuse; lineages/units/statuses/search pagination
- Gate: new supplier cost affects forecast only after explicit action and never changes accepted sell; reusable history has trustworthy provenance

### Phase 5 — Integrated regression and sync retirement

- Update all budget consumers/MCP contracts, remove Sheets-only UI/config/write paths, retained-page regression and endpoint retirement messages
- End-to-end same-project manual cutover rehearsal in isolated fixtures/test environment; financial history intact; one active baseline and owner controls
- Docs/manuals and release notes explain no import, native BOQ flow, unknown costs, export audiences, legacy history and rollback constraints
- Gate: all §14 tests/checklist pass; any failing/unrun test explicitly recorded, no “complete” claim with critical data/security blocker

### Phase 6 — Controlled production handoff (requires deployment authority)

- Backup/restore readiness for additive migrations, compatibility release first, then enable V2 and let user enter actual BOQ; record runtime flags/config centrally not hardcoded project IDs
- Freeze old sync submissions before activating V2; verify no pending job can overwrite intended active source
- Owner performs documented manual cutover after preview. Do not implement payment replay or BOQ reconciliation as a deployment prerequisite
- Rollback means disable new mutations/restore compatible application version and preserve data. Returning budget source to legacy requires explicit owner decision and impact preview; after accepted V2 changes/allocations it is not safe to silently flip a flag or drop V2 tables
- Monitor save/transition/export failures, conflicts, baseline mismatches, unknown-cost allocations, latency and audit availability with existing observability patterns; no raw confidential payloads

## 14. Required tests and acceptance criteria

### 14.1 New automated behavior matrix

| Area | Required cases |
| --- | --- |
| Hierarchy | direct item/optional subgroup; move/reorder IDs preserved; cycle/cross-project reject; nested subtotal and grand total never counted as leaves |
| Calculation | fractional quantities/rates, Decimal rounding, fixture §6.3, markup vs margin, discount/fixed/percent, tax basis, zero denominator, signed CO and overflow validation |
| Cost completeness | unknown vs explicit zero vs N/A; free customer item still needs cost; one missing component prevents full margin; inherited/overridden quantities after scope edits; unawarded but fully estimated forecast allowed |
| Vendors | multiple vendors/project; different material/labor vendors; quantity/spec/unit mismatch; partial award rejected; changed basis invalidates award; replace award not sum both; expired offer warning/audit |
| Snapshots | edit catalog/customer/project/default/cost after issue cannot mutate customer snapshot/file; authorized post-accept cost editing remains available; revision deep link/reload/export retains exact identity; cost-plan export retains chosen version |
| Lifecycle | draft→issue→accept guards; alternative exclusivity; replacement revision; accepted CO counted once; rejected/unaccepted omitted; rebaseline retains/absorbs CO explicitly; stale/double deduction rejected; sell deduction retains vendor obligations until explicit cost adjustment |
| Budget example | main A 1,000,000 vs alternative B 1,200,000; choose B + accepted ADD 100,000 = 1,300,000, not 2,300,000; later accepted DEDUCT 50,000 = 1,250,000 (all same ex-VAT basis) |
| Persistence/concurrency | duplicate retry create/accept/CO/selection/export; conflicting save/reorder; issue racing save; alternate accept race; cost publish racing allocation; source version changes at equal totals |
| Price history | copy/revision lineage not new independent sample; issue/accept events preserved but distinguish observation kinds; explicit promotion; project override does not change master; unit mismatch/archived source warning |
| Legacy cutover | same project/finance IDs unchanged; new baseline replaces not adds legacy; archived BOQ financial FK history visible to Chat/Insights/MCP; as-of before activation remains legacy |
| Funds | estimated complete forecast, unknown-cost outward gate, incoming allocation and valid reversal/correction unaffected, new CO scope with missing cost becomes unknown, allocation deficit after cost increase, reserve/Operations/monthly rollforward unchanged |
| Access/security | Owner/Admin read vs Owner mutation; cross-project node/offer/accept/export reject; customer/vendor DTO allowlists; private artifacts/evidence ownership; formula injection and file limits |
| Export | real `.xlsx` cells/types/totals/sheets contain no leaked cost for customer/RFQ; selected subset preserved and cross-revision IDs rejected; PDFs A4 Thai/multipage/page order/repeated headings/no clipping; final payment residual exact; retry same snapshot |
| Removal/regression | BOQ endpoint 500 แสดง local error/retry ไม่ซ่อน project finance/execution ทั้งหน้า; retired sync caller contract, backend/MCP startup without sync imports; no import UI/parser/API; OCR/daily report/FlowAccount processing status remains functional |

### 14.2 Existing tests and commands

Frontend from `Projects-001-FE`:

```bash
npm test
npm run lint
npm run build
```

ต้อง update test discovery ให้รวม BOQ/quotation/library tests ใหม่ด้วย มิฉะนั้นผล `npm test` เดิมเพียง 5 tests ไม่ได้ตรวจ V2 Existing `fundMoney.js` exact minor-unit helpers ใช้เป็น reference ได้แต่ไม่รองรับ quantity/rate precision 4 decimals ครบ ห้าม reuse โดยไม่ตรวจ contract

Backend จาก `Projects-001-BE` ใช้ interpreter/environment ที่ repository กำหนดและ **isolated test DB** ไม่ใช่ production `DATABASE_URL`; ตรวจ fixture behavior ก่อนรัน:

```bash
python -m pytest tests/test_fund_service.py tests/test_input_request_access_rules.py tests/test_input_request_payment_rules.py
python -m pytest tests/test_mcp_read_contracts.py tests/test_mcp_phase3_contracts.py tests/test_mcp_phase4_contracts.py tests/test_mcp_phase5_processing.py
python -m pytest tests/test_settings_customers.py tests/test_flowaccount_service.py
```

รัน new BOQ tests แบบ focused ก่อน แล้ว broader BE/MCP suites ตาม touched contract รวม `Projects-001-MCP/tests/contract` และ authorization/security เมื่อแก้ tools/access DTOs ไม่มีการอ้างผลผ่านจนได้ execute จริง บันทึก missing credentials/dependencies/DB fixtures แยกจาก code failures

### 14.3 Browser/UAT checklist

- [ ] Project เดิม → native draft → add item/library → sell/cost → reload/copy/reorder → issue → export → record agreement → active budget
- [ ] Alternative + revision + accepted ADD/DEDUCT เปลี่ยนงบถูกต้อง และเอกสารเก่าเปิดดูได้
- [ ] ใส่ offers หลายราย เลือก material/labor คนละราย ดู estimate vs agreed vs forecast และยืนยัน sell ไม่เปลี่ยน
- [ ] Unknown cost/free item/zero/N/A แสดงครบและไม่ทำกำไรปลอม
- [ ] Price history/reuse เร็วและ source ชัด; promote/update reference ต้องยืนยัน; master ไม่เปลี่ยน project ย้อนหลัง
- [ ] Customer/Internal/RFQ/selected-vendor files ตรวจไฟล์จริงทั้ง numeric accuracy และข้อมูลที่ห้ามเปิดเผย
- [ ] Error/timeout/offline/conflict ไม่ทำ draft หาย; keyboard/focus/read-only states ใช้งานได้
- [ ] Desktop 1440, tablet 768/1024, mobile 390 และ relevant LINE webview retained flows ไม่มี shell regression
- [ ] Project Forecast Margin/Actual Cashflow/warehouse/Inspection, Funds/Operations, Input/Approval/paid records/OCR/FlowAccount, Daily Reports, Insights/Chat/MCP, Settings/access และ customer reports คง behavior
- [ ] Manual legacy cutover ใน test fixture ไม่ต้องยอด BOQ ตรง แต่ history/IDs/actual totals ไม่หาย/เพิ่มซ้ำ
- [ ] Owner/readonly Admin/customer/subcontractor restrictions และ private download authorization ผ่าน

## 15. สิ่งที่ไม่อยู่ใน scope / ห้าม agent เพิ่มเอง

- Google Sheets connection/sync และ Excel/CSV import ทุกรูปแบบ
- Rebuild application shell, replace finance/accounting product, เปลี่ยน Input/Approval/payment rules หรือเพิ่ม mandatory BOQ line mapping
- Category-level lump-sum contractor quote allocation, partial/multiple awards ภายใน component และ procurement/PO automation
- New customer/vendor portal, e-signature, customer acceptance login, auto-send email/LINE quotations
- Team role expansion/Admin BOQ write permission โดยไม่ตกลง matrix เพิ่ม
- Auto-price AI/model training/vector replatform, automatic catalog promotion, auto choose cheapest vendor
- Multi-currency accounting/FX, tax/accounting rule redesign หรือการประมาณราคาจากข้อมูลไม่ comparable; V2 ใช้ THB และเก็บ basis/source ให้ชัด
- Legacy amount reconciliation, automatic historic BOQ recreation, dropping legacy rows, payment replay, mandatory historic expense mapping
- New microservices/GCP architecture/IAM or credential cleanup ที่ไม่จำเป็นต่อ feature และไม่มี authorization แยก

## 16. Definition of done และการส่งต่องาน

V2 เสร็จเมื่อ user ทำ BOQ ขาย/ต้นทุนครั้งเดียวในแอป ออกเอกสาร จัดการ revision/alternative/CO/ราคาผู้รับเหมา และนำข้อมูลกลับใช้เสนอราคาได้จริง โดยทุก budget reader ใช้ active source เดียวและ feature เดิมไม่เสีย ไม่ใช่เพียงหน้า demo ที่แสดงตัวเลขได้

Agent ที่ implement ต้องส่งมอบ:

1. Focused code/migrations/docs พร้อม file-level diff ไม่มี unrelated refactor หรือ secrets
2. สรุป schema/API/calculation/permission/baseline decisions ที่ใช้จริงและข้อแตกต่างจากแผน พร้อมเหตุผล; หากเปลี่ยน business scope ต้องมี user approval ก่อน
3. Test commands/results ที่ execute จริง รวม unrun/failing checks และเหตุผล ไม่ใช้ baseline tests ของแผนนี้แทนผล implementation
4. Screenshots ของ native BOQ/quotation/price library และ representative responsive/error/permission states พร้อม sample customer/vendor/internal export ที่ไม่มีข้อมูลจริงอ่อนไหว
5. Manual cutover/rollback runbook แบบ same-project, no-reconciliation, preserve-history และ release/config/deployment prerequisites
6. Remaining risks/follow-up ที่แยกจาก definition of done ไม่ซ่อน mandatory feature เป็น future work

ความเห็นทางวิศวกรรมหลัก: ลงทุนให้ **scope identity, immutable customer documents, versioned internal costs, explicit budget source และ price provenance** ถูกต้องก่อน สิ่งเหล่านี้ทำให้ UI กรอกง่าย ข้อมูลสะสมเชื่อถือได้ และการเสนอราคาครั้งถัดไปเร็วขึ้น โดยไม่ทำให้โครงการที่กำลังเบิกจ่ายต้องเริ่มใหม่
