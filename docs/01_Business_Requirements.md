### **Phase 1: Detailed Business Logic & Requirements (Version 2.0)**

  * **Project Name:** Project\_001 (The Hybrid Brain for Modern Construction Management)
  * **System Scope:** Single-tenant (Internal Company Use, Multiple Projects)
  * **Core Objective:** Budget management (BOQ), Cash Flow control (AR/AP), and strategic data analysis using AI.

### **👥 1. Actor Profiles, Authentication & Security**

| Actor | Authentication Method | Data Visibility | Key Capabilities |
| :--- | :--- | :--- | :--- |
| **Admin / PM** | Company Email (SSO / Google Workspace) | **Global View:** Can see every project, every BOQ, every bill, and customer financial status. | - Sync BOQ, approve bills, manage contingency budget.<br>- Monitor Overdue Alert Dashboard.<br>- Ask strategic questions to the AI. |
| **Subcontractor** | LINE Login API (via LIFF App) | **Isolated View:** Can see only their own bills, payment status, and their specific work installments. | - Registration (KYC), upload bills.<br>- Request advance payments.<br>- Verify data read by the AI. |

  * **1.1 Zero-Password Login (LINE LIFF):** Subcontractors access the system via the Rich Menu in LINE OA. The system pulls the LINE User ID to bind with the `subcontractor_id` in the database (Firestore).
  * **1.2 KYC & PDPA Compliance:** For first-time access, the system mandates data entry and uploading an "ID Card Photo."
      * **Security Rule:** ID card files are stored in GCS (Google Cloud Storage) in a Private Bucket—strictly no public access.
      * When an Admin needs to view the photo, the system generates a **Signed URL** (temporary link valid for 15 minutes) to comply with PDPA laws.
  * **1.3 Account Recovery:** If a subcontractor loses their phone or changes their LINE account, the Admin can click "Reset LINE Binding" to unbind the old UID, allowing the subcontractor to link their new LINE account to their existing data immediately.

### **💰 2. Billing & Payment Segments**

The system is clearly divided into two sides to manage the company's Cash Flow (Inflow-Outflow).

**Segment A: Subcontractor Side (Accounts Payable / Cost)**

  * **2.1 Dynamic Installment & Advance:** Subcontractors can request an advance payment of up to 50% of the next installment.
      * **Logic:** The system performs an automatic "Split Installment." For example, if Installment 2 is worth 100,000 THB and a 50% Advance is requested, the system splits the record into:
          * Installment 2.1 (Advance) = 50,000 THB (Withdraw now)
          * Installment 2.2 (Remaining) = 50,000 THB (Withdraw upon work completion)
      * **Result:** The total remains exactly 100% of the original BOQ.
  * **2.2 Subcontractor Bill Statuses:**
      * **Draft:** AI has finished reading the bill; awaiting subcontractor confirmation.
      * **Pending:** Subcontractor has submitted the bill; awaiting Admin review.
      * **Advance:** Special status for bills requesting advance payment (awaiting Admin approval).
      * **Approved / Paid:** Admin has approved and transferred funds (the system immediately deducts this amount from the BOQ budget).

**Segment B: Customer Side (Accounts Receivable / Revenue)**

  * **2.3 Customer Billing Statuses:**
      * **Billing:** Currently billing the customer (within the payment due cycle).
      * **Re-billing (Company Financed):** A mock status for cases where the customer is unresponsive or hasn't paid yet, but the company must "pre-pay" cash to the subcontractor. The system records this as "Accounts Receivable" to track that the company is currently carrying this cost.
      * **Accept / Paid:** Customer has completed the payment.
  * **2.4 Overdue Alert System:** Every customer-side bill has a "Due Date" field.
      * The system uses **Cloud Scheduler (Cron Job)** to run a check every midnight. If a bill is overdue and the status is not "Accept," it immediately sends an Alert Notification (highlighted in red) to the Admin Dashboard.

### **3. BOQ & Financial Logic**

  * **3.1 Dual BOQ & Multi-Sheet Ingestion:** One project will have 2 URLs (Customer BOQ and Subcontractor BOQ). Within one URL, the system must support reading Multi-sheets (e.g., AC, SN, EE, Architectural) by automatically looping through each sheet.
  * **3.2 WBS Hierarchy:** The system must understand Parent-Child relationships, such as HVAC Category (Parent) -\> SPLIT TYPE (Child) -\> FCU/CDU (Sub-child). Display and budget calculations must accurately **Roll-up** totals from child to parent.
  * **3.3 Material vs. Labor Split:** The budget for each item is separated into "Material" and "Labor" buckets. When a subcontractor bills, they must specify (or have the AI separate) whether the bill is for materials (e.g., steel purchase) or labor (e.g., worker installment) so the system can deduct from the correct bucket.
  * **3.4 Project-Level Financials:** Overhead (e.g., 12%), Profit, Discount, and 7% VAT on the summary page will not be averaged across line items but will be stored as **"Project Variables"** to calculate the overall project picture.
  * **3.5 Financial Calculation Engine:** The system must calculate the net payment automatically using the equation:
    $$Net Payable = (Base Amount + VAT) - WHT - Advance Deduction - Retention$$
    VAT and WHT rates are pulled dynamically from the subcontractor's profile.
  * **3.6 Unplanned / Extra Work:** If a bill is found that is not in the BOQ, the system categorizes it as "Unplanned / Extra Work." Admins must choose to draw funds from the **Contingency Budget** to pay it, ensuring the project's main Cost Baseline is not distorted.

### **🔄 4. Data Ingestion & AI Workflows**

  * **4.1 BOQ Sync (Zero GAS):** Pulls data from Google Sheets via API -\> Sends it to **Gemini 2.0 Flash** for **Semantic Mapping** (matching column names).
      * **Validation:** If AI confidence is \< 80% -\> Reject immediately.
      * **Versioning:** Always recorded as a new version (**SCD Type 2**); never overwrite old data.
  * **4.2 Subcontractor Billing (Human-in-the-loop):** Upload bill image -\> **Gemini 1.5 Flash (OCR)** extracts data as JSON -\> Auto-fills the form on the Web App. Subcontractors must double-check and correct data before clicking Submit.
  * **4.3 Duplicate Detection:** Checks Receipt No. + Date + Amount. If a duplicate is found, it won't block but will raise a **Red Flag** for Admin review.
  * **4.4 Admin Direct Edit:** Admins can edit bill figures directly for speed (no need to reject and have the subcontractor redo it).
  * **4.5 AI Semantic Matching:** Uses **Vector Search** to match items between Customer BOQ and Subcontractor BOQ (e.g., matching "Downlight Lamp" with "D1 DOWNLIGHT") so management can see the margin for each item immediately.

### **🧠 5. Strategic Intelligence**

  * **5.1 Vector Search (pgvector):** Every item in the BOQ is converted into a **Vector Embedding** for semantic understanding.
  * **5.2 Global Context Analysis:** When an Admin asks strategic questions, the system performs **Data Aggregation** (Group By/Sum) from the database first, then sends the Summary + Vector Context to Gemini for analysis to prevent token overflow and reduce hallucinations.
  * **5.3 RAG for Contracts:** Uses **Document AI** to read employment contracts so the AI can accurately answer questions about payment terms specified in the contract.

### **🛡️ 6. Failure by Design**

  * **6.1 Orphaned Files Cleanup:** Image files in GCS `temp/` that are not approved within 7 days are automatically deleted (Lifecycle Rules).
  * **6.2 AI Backfill:** If Vertex AI is down during vectorization, the system saves it as Plain Text in SQL first and flags it as `needs_embedding = true` for a background job to process later.
  * **6.3 Schema Enforcement:** Every data stream must be validated with **Pydantic** before entering the database. If the type is incorrect, the transaction is rejected immediately.
