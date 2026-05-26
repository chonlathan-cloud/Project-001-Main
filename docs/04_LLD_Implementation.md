### **💻 Phase 4: Low-Level Design (LLD)**
**Project:** Project_001 (The Hybrid Brain for Modern Construction Management)
**Tech Stack:** Python (FastAPI), SQLAlchemy, Pydantic, pgvector, Vertex AI
**📂 1. Project Directory Structure (โครงสร้างโปรเจกต์)**
Uses Domain-Driven Design (DDD) architecture for code cleanliness.

```text
project_001_backend/
├── main.py # Entry point + router registration
├── requirements.txt
└── app/
├── core/database.py # Async engine, session, Base
├── models/
│ ├── boq.py # Project, BOQItem
│ └── finance.py # Installment, Transaction
├── schemas/
│ ├── responses.py # StandardResponse[T]
│ ├── boq_schema.py # ProjectList, BOQTree, SyncBOQ
│ └── bill_schema.py # Extract, Submit, Advance, Approve
├── services/
│ ├── finance_service.py # Net Payable, Split Installment
│ └── ai_service.py # Gemini BOQ parsing, RAG chat
└── api/v1/
├── dashboard.py # R1: KPIs
├── projects.py # R2-3: Projects + BOQ tree
├── bills.py # R4,6: Billing + Admin approval
├── subcontractor.py # R5: Portal + Advance
├── settings.py # R7: Admin settings
└── chat.py # R8: AI Strategic Chat
```


**📝 2. API Contracts & JSON Mock Data (Sent to Frontend team)**
This is the standard JSON structure that Backend will send to Frontend (FE can take this set of JSON to mock variables in Next.js / React to draw screens and wait).

📊 Router 1: Dashboard (Overview)
** GET /api/v1/dashboard/summary
{
  "status": "success",
  "data": {
    "kpis": {
      "total_budget": 15000000.00,
      "actual_cost": 8500000.00,
      "pending_approval_count": 12,
      "overdue_amount": 450000.00,
      "total_profit_margin": "15.2%"
    },
    "monthly_cashflow": [
      { "month": "Jan", "income": 1200000, "expense": 800000 },
      { "month": "Feb", "income": 1500000, "expense": 1100000 },
      { "month": "Mar", "income": 900000, "expense": 1000000 }
    ],
    "recent_actions": [
      { "time": "10 mins ago", "action": "Admin approved bill #INV-001" },
      { "time": "1 hour ago", "action": "Subcontractor A submitted new bill" }
    ]
  }
}

### **📁 Router 2 & 3: Project List & BOQ Tree**
**GET `/api/v1/projects` (Consolidated Project Page)**
(ให้ข้อมูลรายการโปรเจกต์ทั้งหมดที่มีอยู่ในระบบ)

```json
{
  "status": "success",
  "data": [
    {
      "project_id": "uuid-1",
      "name": "Cafe Amazon Flagship",
      "status": "ACTIVE",
      "total_budget": 2500000.00,
      "progress_percent": 45.5
    }
  ]
}
```

**GET `/api/v1/projects/{id}/boq` (Project Detail Page - Tree/Nested Structure)**
(แสดงรายละเอียดงบประมาณแบบลำดับชั้นเพื่อให้ทีมหน้าบ้านนำไปวาดหน้าจอแบบกดขยายได้)

```json
{
  "status": "success",
  "data": {
    "project_name": "Cafe Amazon Flagship",
    "boq_tree": [
      {
        "wbs_level": 1,
        "description": "Electrical and Communication System",
        "total_budget": 597360.00,
        "actual_spent": 200000.00,
        "variance": "+397360.00",
        "children": [
          {
            "wbs_level": 2,
            "description": "LIGHTING FIXTURE",
            "material_budget": 189130.00,
            "labor_budget": 124200.00,
            "children": [
              {
                "wbs_level": 3,
                "description": "Recessed Downlight",
                "qty": 60,
                "unit": "SET",
                "customer_price": 1500.00,
                "subcontractor_price": 1250.00,
                "margin_per_unit": 250.00
              }
            ]
          }
        ]
      }
    ]
  }
}
```

### **🧾 Router 4: Subcontractor Input (Billing Page)**
**POST `/api/v1/bills/extract` (AI OCR result for FE to Auto-fill)**
(ใช้สำหรับสกัดข้อมูลจากรูปภาพใบเสร็จเพื่อกรอกฟอร์มอัตโนมัติ)

```json
{
  "status": "success",
  "data": {
    "receipt_no": "INV-2026-001",
    "date": "2026-03-17",
    "vendor_name": "Thai Construction Materials Store",
    "suggested_expense_type": "MATERIAL",
    "total_amount": 15500.00,
    "items": [
      { "description": "Cement", "qty": 100, "price": 155.00 }
    ]
  }
}
```

### **👷 Router 5: Subcontractor Portal (Personal History)**
**GET `/api/v1/subcontractor/my-bills`**
(ประวัติการวางบิลและรายละเอียดการหักเงินสุทธิ)

```json
{
  "status": "success",
  "data": [
    {
      "bill_id": "uuid-bill-1",
      "date": "2026-03-15",
      "expense_category": "Concrete Work",
      "requested_amount": 50000.00,
      "status": "APPROVED",
      "net_payable": 45000.00,
      "deductions": {
        "vat": 0.00,
        "wht": 1500.00,
        "retention": 2500.00,
        "advance_repayment": 1000.00
      }
    }
  ]
}
```

### **🤖 Router 8: AI Strategic Chat (Intelligence Engine)**
**POST `/api/v1/chat/ask`**

```json
{
  "status": "success",
  "data": {
    "reply": "Based on the data analysis, Subcontractor A generates a better margin in the electrical category at 15%, while Subcontractor B is at 8%. It is recommended to select Subcontractor A for the next phase.",
    "sources": ["BOQ_EE_Project1", "BOQ_EE_Project2"]
  }
}
```

---

### **⚙️ 3. Core Algorithms (Python Backend Logic)**
To provide the Backend team with a visualization of complex logic, here are the **Pseudocode/Python Snippets** for the core features:

**3.1 SQLAlchemy ORM: BOQ Item (Supports WBS & Vector)**
(โครงสร้างโมเดลฐานข้อมูลที่รองรับลำดับชั้นงานและเวกเตอร์ของ AI)

```python
class BOQItem(Base):
    __tablename__ = "boq_items"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"))

    # WBS Hierarchy
    wbs_level = Column(Integer, nullable=False) # 1, 2, 3
    parent_id = Column(UUID(as_uuid=True), ForeignKey("boq_items.id"), nullable=True)

    # Material vs Labor
    material_unit_price = Column(Numeric(15, 2), default=0)
    labor_unit_price = Column(Numeric(15, 2), default=0)

    # AI Vector
    embedding = Column(Vector(768))
```

**3.2 Algorithm: AI Chat with RAG (Router 8)**
(ตรรกะการทำงานของแชทอัจฉริยะที่ใช้ข้อมูลจากฐานข้อมูลมาตอบคำถาม)

```python
def ask_strategic_question(db: Session, question: str, project_id: str = None):
    # 1. Generate embedding from question using Vertex AI
    question_vector = generate_embedding(question)

    # 2. Search DB using pgvector (Cosine Similarity)
    similar_items = db.query(BOQItem).order_by(
        BOQItem.embedding.cosine_distance(question_vector)
    ).limit(10).all()

    # 3. Aggregate Data
    context_data = aggregate_financials(similar_items)

    # 4. Send Context + Question to Gemini 2.0 Flash
    prompt = f"""
    You are a Principal Construction Analyst. Answer the user's question based ONLY on the provided context.
    Context Data: {context_data}
    User Question: {question}
    """
    response = gemini_model.generate_content(prompt)

    return {"reply": response.text, "sources": [item.description for item in similar_items]}
```

**3.3 Algorithm: Split Installment (ซอยงวดงาน)**
(ฟังก์ชันการแยกงวดงานเพื่อรองรับการเบิกเงินล่วงหน้า)

```python
def process_advance_request(db: Session, installment_id: str, advance_percent: float):
    # Use with_for_update() to lock the row and prevent race conditions
    inst = db.query(Installment).filter_by(id=installment_id).with_for_update().first()

    advance_amt = inst.amount * (advance_percent / 100)
    remain_amt = inst.amount - advance_amt

    # Create Advance installment (2.1)
    new_advance = Installment(
        boq_item_id=inst.boq_item_id,
        installment_no=f"{inst.installment_no}.1-ADV",
        amount=advance_amt,
        status="PENDING_ADMIN"
    )
    db.add(new_advance)

    # Update original installment (2.2)
    inst.installment_no = f"{inst.installment_no}.2-REM"
    inst.amount = remain_amt

    db.commit() # SQLAlchemy will automatically rollback if an error occurs
```