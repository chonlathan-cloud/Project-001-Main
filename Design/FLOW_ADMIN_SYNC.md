# Flow Detail: New Project Creation & BOQ Sync Loop

This subsection details the workflow when an Admin clicks `[+ New Project]` and manages the Bill of Quantities (BOQ) synchronization.

## 📱 State 1: The Project Overview & List
- **UI Elements:** A modern data table showing current projects (Project Name, Code, Total Budget, Sync Status).
- **Primary Call-to-Action (CTA):** A prominent button `[+ New Project]` using the Muted Teal (#4f6f64) brand color.

## 📱 State 2: "New Project" Modal / Form
- **Trigger:** Clicking `[+ New Project]`.
- **Form Fields Required:**
  - Project Name (ชื่อโครงการ)
  - Project Code / ID (รหัสโครงการ)
  - Location / Site (สถานที่ก่อสร้าง)
  - Start Date & End Date (ระยะเวลาสัญญา)
- **Actions:** `[Cancel]` (Flat Text) and `[Create & Proceed to BOQ]` (Primary solid button).

## 📱 State 3: Project Detail - The BOQ Control Center
- **Context:** Once a project is created, the user lands on the Project Detail Page.
- **Layout:** Symmetrical split view or clear tab layout:
  - **Tab A:** Customer BOQ (มุมมองฝั่งลูกค้า)
  - **Tab B:** Subcontractor BOQ (มุมมองฝั่งผู้รับเหมาช่วง)
  - **Tab C:** Comparison Summary (หน้าวิเคราะห์ส่วนต่างกำไร/ขาดทุน)
- **Empty State UI:** If no BOQ is synced yet, show an empty state illustration with a clear button: `[🔗 Sync BOQ from Google Sheets]`.

## 📱 State 4: The BOQ Sync Drawer (The Technical Form)
- **Trigger:** Clicking `[Sync BOQ]`. A sleek panel slides out from the right side (Right Drawer).
- **Step-by-Step Interactive Form:**
  1. **Input Field:** Google Sheet URL (ช่องวางลิงก์เอกสาร Google Sheets).
  2. **Action 1:** `[Load Tabs]` Button. Clicking this triggers a mock API call to fetch sheet names.
  3. **Dynamic Selection:** A list of checkboxes appears showing detected tabs (e.g., "🎯 Structure", "⚡ Electrical", "🚰 Plumbing"). User checks the tabs they want to import.
  4. **Action 2:** `[Queue Sync]` Button. 
  5. **Progress Polling State:** The drawer transforms into a loading state showing a custom polling progress bar (e.g., "Parsing row 142/500...") to simulate background processing until successful.