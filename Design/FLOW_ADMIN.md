# Application Flow: Projects-001 Admin Web/Tablet Portal

The application uses a persistent **Left Sidebar Navigation** containing: Dashboard, Projects, Approvals, Insights, and Chat AI.

## 📍 1. Dashboard (Overview)
- **Top Section:** KPI Cards showing Total Budget, Actual Cost, Pending Requests, and Overdue Installments.
- **Middle Section:** Cashflow charts/graphs.
- **Bottom Section:** List of "Risky Projects" and "Recent Actions".

## 📍 2. Projects & BOQ Management
- **Project List:** Table of active projects with a `[+ New Project]` button.
- **Project Detail View:**
  - Shows Comparison Summary (Customer vs Subcontractor BOQ).
  - **Action:** `[Sync BOQ]` button opens a drawer/modal.
  - **BOQ Sync Drawer:** Input field for "Google Sheet URL" -> `[Load Tabs]` -> Checkboxes to select tabs -> `[Queue Sync]` -> Shows a polling progress bar.

## 📍 3. Approvals (Review Queue)
- **List View:** Table of `PENDING_ADMIN` input requests from subcontractors.
- **Detail/Review View (When a request is clicked):**
  - **Left Panel:** OCR Extracted Form fields (editable by admin).
  - **Right Panel:** PDF/Image Preview of the receipt (loaded via signed URL).
  - **Actions (Bottom):** `[Approve]` (Primary), `[Reject]` (Secondary, requires note), and `[Mark as Paid]`.

## 📍 4. Insights (Data Warehouse)
- **Top Bar:** Advanced Filter controls (Project, Source Type, Status, Date Range).
- **Content:** A comprehensive, wide data table showing unified rows (InputRequests, Installments, Transactions).
- **Action:** `[Export CSV/JSON]` button at the top right.

## 📍 5. Chat AI (Financial Assistant)
- **UI:** A conversational interface taking up the main content area.
- **Top Bar:** A dropdown to select an "Optional Project Scope" to narrow the AI's context.
- **Chat Flow:** User asks a question -> AI responds with polished text, data metrics, and suggested next actions.

## 📍 6. User Profile (ข้อมูลส่วนตัวผู้ใช้งาน)
- **Layout:** Minimalist two-column card grid.
- **Left Column (Profile Info):** Large clean avatar circle, Admin/Project Manager Display Name, Employee ID, Email, Role/Permissions Badge (using Muted Teal #4f6f64).
- **Right Column (Security & Activity):** - Action button: `[🔐 Change Password]` opens a clean modal.
  - "Recent Login Sessions" data table showing device, IP address, and status.

## 📍 7. Settings (หน้าตั้งค่าระบบ)
- **Layout:** Vertical Tabbed View (General, Subcontractor KYC, Integrations).
- **Tab 1: General Settings:** Clean toggle switches for system notifications, currency display options, and dark mode preview.
- **Tab 2: Subcontractor KYC Rules:** Form fields to set mandatory fields for Subcontractors when signing up via LINE LIFF (e.g., toggle ON/OFF for Commercial Registration requirement).
- **Tab 3: Integrations & API:** Status indicators and input fields for cloud configurations (Google Firebase Sync status, Google Sheets API Connection, and Vertex AI model versions selection).