### **🛠️ Phase 3: Technical Design Document (TDD) - Version 3.0**
**Project:** Project_001 (The Hybrid Brain for Modern Construction Management)
**Architecture:** Serverless Microservices (Cloud Run, Cloud SQL, Firestore)

#### **🗄️ 1. Database Schema Design**
**1.1 Cloud SQL (PostgreSQL + pgvector) - Financial Source of Truth**

**Table: projects**
| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| id | UUID | PRIMARY KEY |
| name | VARCHAR | Project Name |
| project_type | VARCHAR | Project Type (Enum) |
| overhead_percent | DECIMAL | Overhead cost (e.g., 12.00) |
| profit_percent | DECIMAL | Target Profit Margin |
| vat_percent | DECIMAL | Value Added Tax (e.g., 7.00) |
| contingency_budget | DECIMAL | Contingency Budget (Unplanned Work) |
| status | VARCHAR | ACTIVE, COMPLETED |

**Table: boq_items (Supports WBS and Material/Labor)**
| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| id | UUID | PRIMARY KEY |
| project_id | UUID | FOREIGN KEY referencing project |
| boq_type | VARCHAR | CUSTOMER or SUBCONTRACTOR |
| sheet_name | VARCHAR | Sheet Name (e.g., 'AC', 'SN', 'EE') |
| wbs_level | INT | Hierarchy Level (1=Main, 2=Sub, 3=Item) |
| parent_id | UUID | Self-referencing FOREIGN KEY |
| item_no | VARCHAR | Sequence (e.g., '1', '2.1', '-') |
| description | VARCHAR | Item Description |
| qty | DECIMAL | Quantity |
| unit | VARCHAR | Unit of Measurement |
| material_unit_price| DECIMAL | Material unit price |
| labor_unit_price | DECIMAL | Labor unit price |
| total_material | DECIMAL | Total material cost |
| total_labor | DECIMAL | Total labor cost |
| grand_total | DECIMAL | Grand total cost |
| embedding | VECTOR(768) | Vector for Semantic Search |
| valid_from | TIMESTAMP | SCD Type 2: Version Start Date |
| valid_to | TIMESTAMP | SCD Type 2: Version End Date (NULL = Current) |

**Table: installments (Installments and Disbursements)**
| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| id | UUID | PRIMARY KEY |
| boq_item_id | UUID | FOREIGN KEY referencing BOQ Item |
| expense_category | VARCHAR | Category (Concrete, Steel, Paint, etc.) |
| expense_type | VARCHAR | Disbursement Type (Installment, Labor, Material) |
| cost_type | VARCHAR | MATERIAL, LABOR, BOTH |
| installment_no | VARCHAR | No. (e.g., '2', '2.1-ADVANCE') |
| amount | DECIMAL | Amount for the installment |
| status | VARCHAR | LOCKED, PENDING, ADVANCE, APPROVED, etc. |
| due_date | DATE | Payment due date (Customer side) |
| is_overdue | BOOLEAN | Overdue debt alert flag |

**1.2 Firestore (NoSQL) - State & Profile Management**
**Collection: users (Subcontractor Profiles)**
* **doc_id:** (String) Subcontractor ID
* **line_uid:** (String) Used for binding with LINE Login
* **name:** (String) Company/Subcontractor Name
* **tax_id:** (String) Tax Identification Number
* **vat_rate:** (Number) e.g., 0.07 or 0.00
* **wht_rate:** (Number) e.g., 0.03 or 0.01
* **retention_rate:** (Number) Percentage deducted for performance guarantee (e.g., 0.05)
* **bank_account:** (Map) { "bank_name": "KBank", "account_no": "123-4-567", "account_name": "Mr. A" }
* **kyc_gcs_path:** (String) gs://bucket/kyc_id_cards/sub_001.jpg (Private)

Collection: draft_bills (บิลที่รอตรวจสอบ - Human-in-the-loop)
doc_id: (String) Draft ID
subcontractor_id: (String) อ้างอิง User
gcs_temp_path: (String) gs://bucket/temp_bills/bill_123.jpg
ocr_raw_data: (Map/JSON) ข้อมูลดิบที่ Gemini 2.5 flash
status: (String) DRAFT หรือ PENDING_ADMIN

### **🔌 2. API Specifications (Mapped to 7 UI Routers)**
These are the API Endpoints that the Backend must develop so the Frontend can connect them to the 7 functional screens.

* **Router 1: Dashboard (Overall Overview)**
    * **GET `/api/v1/dashboard/summary` (Admin)**
    * **Response:** Sends aggregated KPI data (Total Budget, Actual Cost, Pending Bills, Overdue Amount) and Time-series data (Monthly Income/Expense) for rendering bar charts.

* **Router 2: Project List (Consolidated Project Page)**
    * **GET `/api/v1/projects` (Admin)**
    * **Response:** A list of projects along with calculated percentage of payment progress and status.
    * **POST `/api/v1/boq/sync` (Admin)**
    * **Body:** `{ "project_id": "uuid", "boq_type": "CUSTOMER", "sheet_url": "string" }`
    * **Logic:** Fetch Google Sheet -> Gemini 2.0 analyzes WBS -> Save to Database.

* **Router 3: Project Detail & BOQ**
    * **GET `/api/v1/projects/{id}` (Admin)**
    * **Response:** Basic project information.
    * **GET `/api/v1/projects/{id}/boq` (Admin)**
    * **Response:** BOQ data formatted as Tree/Nested JSON (Parent-Child) with attached Variance values (Customer Price vs. Sub Price) on the same line. This allows the Frontend to render "Card" displays (WBS Level 1) that can be expanded to view internal details.

* **Router 4: Subcontractor Input (Billing Page)**
    * **POST `/api/v1/bills/extract` (Subcontractor)**
    * **Payload:** `file` (Bill Image)
    * **Logic:** Gemini 1.5 performs OCR -> Returns JSON values to the Frontend for "Auto-fill."
    * **POST `/api/v1/bills/submit` (Subcontractor)**
    * **Body:** `{ "expense_category": "Concrete", "expense_type": "Material", "amount": 5000, "bank_account": {...} }`
    * **Logic:** Record to Firestore (Status: `PENDING_ADMIN`).

* **Router 6: Admin Approval (Approval & Status Tracking)**
    * **GET `/api/v1/admin/bills?status=PENDING` (Admin)**
    * **Response:** List of bills awaiting review.
    * **PUT `/api/v1/admin/bills/{id}` (Admin)**
    * **Logic:** **Direct Edit** allowing Admins to modify amount figures or change BOQ categories directly before clicking "Approve."
    * **POST `/api/v1/admin/bills/{id}/approve` (Admin)**
    * **Logic:** Calculate Net Payable -> Record into `transactions` table -> Move image file to `/perm_bills`.

* **Router 7: Settings (Admin Settings)**
    * **GET `/api/v1/settings/subcontractors` (Admin)**
    * **Response:** List of all subcontractor names.
    * **PUT `/api/v1/settings/subcontractors/{id}` (Admin)**
    * **Body:** `{ "vat_rate": 0.07, "wht_rate": 0.03, "retention_rate": 0.05, "name": "..." }`
    * **Logic:** Update profile in Firestore.
    * **POST `/api/v1/settings/subcontractors/{id}/reset-line` (Admin)**
    * **Logic:** Delete the existing `line_uid` to allow the subcontractor to bind a new LINE account.
    * **GET `/api/v1/users/{id}/kyc-image` (Admin)**
    * **Logic:** Generate a Signed URL (15 minutes) for viewing the ID card photo.

### **🤖 Router 8: AI Strategic Chat (Executive Assistant Brain)**
* **POST `/api/v1/chat/ask` (Admin Only)**
* **Function:** Receive questions from executives, search for relevant information (RAG), and have Gemini summarize the answer.
* **Request Body (Frontend must send):**
    ```json
    {
      "message": "Between Subcontractor A and B, who performs better in the electrical category in terms of profit?",
      "project_id": "uuid-1234" // (Optional) Sent if the AI should focus only on the current project.
    }
    ```
* **Backend Logic (Backend must perform):**
    1.  Receive question and perform **Vector Search** in the `boq_items` table (pgvector) to find relevant data.
    2.  Perform **Data Aggregation** (e.g., SUM the amounts for Subcontractor A and B).
    3.  Send the question + summarized data to **Gemini 2.0 Flash**.
    4.  Return the response to the Frontend.
* **Response (Backend sends back):**
    ```json
    {
      "status": "success",
      "data": {
        "reply": "Based on the data analysis, Subcontractor A generates a better margin in the electrical category with a 15% margin, while Subcontractor B is at 8%...",
        "sources": ["BOQ_EE_Project1", "BOQ_EE_Project2"] // Cites sources for reliability.
      }
    }
    ```

### **🔐 3. Security & Environment Variables**
Developers must configure these Environment Variables in Google Secret Manager:

* **DATABASE_URL:** Connection String for PostgreSQL
* **GEMINI_API_KEY:** For calling Vertex AI
* **LINE_CHANNEL_ID & LINE_CHANNEL_SECRET:** For verifying LINE Login
* **FIREBASE_SERVICE_ACCOUNT_JSON:** For accessing Firestore
* **GCS_PRIVATE_BUCKET_NAME:** Bucket name for storing ID card photos (KYC)

🔄 4. Sequence Diagram: Advance Payment (Split Installment Flow)
sequenceDiagram
    participant Admin
    participant API as Cloud Run (Python)
    participant Sheets as Google Sheets API
    participant Gemini as Vertex AI (Gemini 2.0)
    participant DB as Cloud SQL (PostgreSQL)

    Admin->>API: POST /boq/sync (URL)
    API->>Sheets: Get all Sheet names (AC, SN, EE...)
    Sheets-->>API: List of Sheets
    
    loop For each Sheet
        API->>Sheets: Fetch raw rows
        Sheets-->>API: Raw Data (Array of Arrays)
        API->>Gemini: Prompt: "Parse this BOQ. Identify WBS hierarchy (Parent/Child) and split Material/Labor costs."
        Gemini-->>API: Structured JSON (with wbs_level, parent_id)
        API->>API: Pydantic Validation
        API->>DB: INSERT INTO boq_items (SCD Type 2)
    end
    
    API-->>Admin: 200 OK (Sync Completed)

and 

sequenceDiagram
    actor SubCon as Subcontractor (LIFF)
    participant API as FastAPI (Cloud Run)
    participant SQL as Cloud SQL (PostgreSQL)

    SubCon->>API: POST /installments/{id}/advance (50%)
    activate API
    API->>SQL: BEGIN TRANSACTION

    SQL-->>API: Fetch Installment Data (e.g., งวด 2 = 100k)

    alt If amount > allowed limit
        API-->>SubCon: 400 Bad Request (Exceeds 50% limit)
    else Valid Request
        API->>SQL: UPDATE original to 50k (งวด 2.2 Remaining, LOCKED)
        API->>SQL: INSERT new record 50k (งวด 2.1 Advance, PENDING_ADMIN)

        alt DB Error occurs
            API->>SQL: ROLLBACK TRANSACTION
            API-->>SubCon: 500 Internal Server Error
        else Success
            API->>SQL: COMMIT TRANSACTION
            API-->>SubCon: 200 OK (Advance Requested)
        end
    end
    deactivate API