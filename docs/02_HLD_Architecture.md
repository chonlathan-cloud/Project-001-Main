### **🏗️ Phase 2: High-Level Design (HLD) Version 2.0**

**Project:** Project\_001 (The Hybrid Brain for Modern Construction Management)

#### **📐 1. System Architecture Diagram**

This diagram illustrates the integration of various components on GCP, clearly categorized into functional layers.
flowchart TD
    %% Actors
    Admin([Admin / PM])
    SubCon([Subcontractor])

    %% Client Layer
    subgraph ClientLayer ["1. Client Layer (Frontend)"]
        WebApp["Admin Web App \n (React / Next.js)"]
        LIFF["LINE LIFF App \n (Subcontractor Portal)"]
    end

    %% API & Compute Layer
    subgraph ComputeLayer ["2. API & Compute Layer (Serverless)"]
        CloudRun["Cloud Run Backend \n (Python / FastAPI)"]
        Scheduler["Cloud Scheduler \n (Cron Jobs)"]
    end

    %% AI & Intelligence Layer
    subgraph AILayer ["3. AI & Intelligence Layer"]
        Gemini15["Vertex AI: Gemini 2.5 Flash \n (OCR & Extraction)"]
        Gemini20["Vertex AI: Gemini 2.5 Flash \n (Semantic & Insights)"]
        DocAI["Document AI \n (Contracts RAG)"]
    end

    %% Data & Persistence Layer
    subgraph DataLayer ["4. Data & Persistence Layer"]
        CloudSQL[(Cloud SQL \n PostgreSQL + pgvector)]
        Firestore[(Firestore \n NoSQL: Users, Drafts)]
        GCS[(Cloud Storage \n Private Buckets)]
    end

    %% Security & Ops
    subgraph SecurityLayer ["5. Security & Operations"]
        IAM[Cloud IAM]
        SecretMgr[Secret Manager]
        FirebaseAuth["Firebase Auth \n (Custom Token)"]
    end

    %% Connections - User to Client
    Admin -->|SSO / Google Workspace| WebApp
    SubCon -->|LINE Login API| LIFF

    %% Connections - Client to Compute
    WebApp -->|"REST API (JWT)"| CloudRun
    LIFF -->|"REST API (JWT)"| CloudRun
    Scheduler -->|Trigger Daily at 00:00| CloudRun

    %% Connections - Compute to AI
    CloudRun -->|gRPC| Gemini15
    CloudRun -->|gRPC| Gemini20
    CloudRun -->|gRPC| DocAI

    %% Connections - Compute to Data
    CloudRun -->|Read/Write Profiles| Firestore
    CloudRun -->|ACID Transactions & Vector| CloudSQL
    CloudRun -->|Upload/Generate Signed URLs| GCS

    %% Connections - Security
    LIFF -.->|Verify LINE UID| FirebaseAuth
    CloudRun -.->|Fetch DB Passwords| SecretMgr
    CloudRun -.->|Enforce Least Privilege| IAM


#### **🛠️ 2. GCP Component Selection & Justification**

To ensure the system supports Business Logic V2.0 securely and cost-effectively, I have designed the following Tech Stack:

| Component | Technology Choice | Justification (Why choose this?) |
| :--- | :--- | :--- |
| **Frontend (Admin)** | React / Next.js | To build complex dashboards for Admins (Global View, BOQ management, bill approval). Hosted on Firebase Hosting. |
| **Frontend (SubCon)** | LINE LIFF App | **Zero-Friction UX:** Subcontractors don't need to download an app or remember passwords. They can access the Web App immediately via the Rich Menu in LINE OA. |
| **Auth Provider** | Firebase Auth | Used for Custom Token Authentication by converting the LINE User ID from LIFF into a Firebase Token for secure backend communication. |
| **Backend API** | Cloud Run (Python/FastAPI) | **Serverless:** Auto-scales to handle traffic spikes during month-end billing. Python is chosen for its superior AI libraries (LangChain) and data validation (Pydantic). |
| **Background Job** | Cloud Scheduler | Acts as a Cron Job to trigger the Cloud Run API every midnight to check for overdue customer bills (AR) and send alerts. |
| **AI Engine** | Vertex AI + Document AI | Vertex AI (Gemini) ensures **Data Privacy** (data is not leaked to train public models). Document AI is added to read "Employment Contracts" for RAG implementation. |
| **Primary DB** | Cloud SQL (PostgreSQL) | **Financial Truth:** Managing finances (Advance, Retention, Split Installments) requires a Relational DB with ACID Transactions to prevent data loss/duplication. Includes **pgvector** for Vector Search. |
| **State DB** | Firestore (NoSQL) | For flexible schema data, such as User Profiles, LINE UID Binding, and "Draft" bill statuses awaiting subcontractor confirmation. |
| **File Storage** | Cloud Storage (GCS) | Divided into 3 main folders:<br>1. `/kyc_id_cards`: 100% Private for ID photos (PDPA).<br>2. `/temp_bills`: Temporary bill storage (7-day auto-deletion).<br>3. `/perm_bills`: Approved bill storage. |

#### **⚙️ 3. Core Technical Workflows**

To illustrate how the Backend (Cloud Run) handles the complexity of Business Logic V2.0:

**Workflow A: KYC & PDPA Compliance (Registration & ID Viewing)**

  * **Upload:** Subcontractor uploads an ID photo via LIFF -\> Cloud Run receives and uploads the file to GCS (`/kyc_id_cards`), configured as a Private Bucket (no direct internet access).
  * **Store Reference:** Cloud Run records only the File Path (e.g., `gs://bucket/kyc/...`) in Firestore.
  * **Secure Viewing:** When an Admin needs to view the ID, Cloud Run uses a Service Account to generate a **Signed URL** (a temporary link valid for 15 minutes). Once expired, the link is immediately inaccessible (100% PDPA Compliant).

**Workflow B: Dynamic Installment & Advance (Splitting Installments)**

  * **Request:** Subcontractor requests a 50% Advance for Installment 2 (e.g., 100,000 THB).
  * **Database Transaction (Cloud SQL):**
    1.  Cloud Run initiates `BEGIN TRANSACTION`.
    2.  Retrieves Installment 2 record and performs the **Split**.
    3.  Creates a new record: Installment 2.1 (Advance) = 50,000 THB (Status: Pending Admin).
    4.  Updates original record: Installment 2.2 (Remaining) = 50,000 THB (Status: Locked).
    5.  `COMMIT TRANSACTION`. (If an error occurs, the system triggers a **Rollback** to 100,000 THB, preventing BOQ data distortion).

**Workflow C: Accounts Receivable & Overdue Alerts (Debt Collection)**

  * **Cron Trigger:** Cloud Scheduler sends a POST request to `/api/v1/cron/check-overdue` at 00:00 AM daily.
  * **Query:** Cloud Run searches Cloud SQL for customer bills where `status != 'Accept'` and `due_date < CURRENT_DATE`.
  * **Action:** If found, Cloud Run updates the flag `is_overdue = true` and sends a Notification (via WebSocket or Firestore) to trigger a Red Alert on the Admin Dashboard the following morning.

#### **🛡️ 4. Security & Failure by Design**

  * **Least Privilege IAM:** Cloud Run uses a Service Account with restricted permissions to read/write only to specified Databases and GCS Buckets, with no access to other GCP resources.
  * **Secret Manager:** Database passwords (PostgreSQL) and API Keys are never hardcoded in the source code; they are retrieved from Secret Manager during Cloud Run's "Cold Start."
  * **Self-Cleaning Storage:** GCS Lifecycle Rules automatically delete temporary files in `/temp_bills`, reducing administrative burden and saving storage costs.
