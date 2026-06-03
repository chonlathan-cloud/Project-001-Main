# UI/UX Flow: Projects-001 Subcontractor Portal

## 1. Navigation Structure
* Subcontractors use a `ProtectedLayout` with a shared sidebar.
* The subcontractor sidebar navigation contains only two main visible items: `Input` and `Profile`.
* A `Sign Out` action is also available to clear the session.

## 2. Screen: Login Page (`/login`)
* **UI Layout:** A clean centered login card.
* **Actions:** Displays two distinct buttons: "Continue as Admin with Google" and "Continue as Subcontractor with LINE".

## 3. Screen: First-Time Signup & KYC (`/signup`)
* **Trigger:** Shown when a subcontractor logs in via LINE for the first time and requires an account.
* **UI Layout:** A structured onboarding form requiring user identity and banking details.
* **Form Fields:** Inputs for Company/Subcontractor Name, Default Contact Name, Default Phone Number, Tax Identification Number, Default Bank Name, Default Account Number, and Default Account Name.
* **Upload Area:** A specific file dropzone/upload component for the "KYC ID Card Image".

## 4. Screen: Input Page (`/input` - Main Dashboard)
* **Purpose:** The main subcontractor work surface used to submit income or expense requests with a receipt image or PDF.
* **Empty State / Error:** If the user has no assigned projects, disable the project selection and display a prominent warning telling the user to ask Admin to set Assigned Projects.
* **Interaction 1 (Upload):** A dropzone or file picker for receipt files.
* **Interaction 2 (AI OCR):** Upon file selection, show a loading state (simulating AI extraction), then pre-fill empty form fields (Vendor, Receipt number, Date, Amount) and allow the user to review/correct them.
* **Form Layout:** Structured fields for Entry type (`EXPENSE`/`INCOME`), Project, Requester name, Work type (e.g., งานโครงสร้าง, งานสถาปัตย์), Request type, and Amount. Default contact and bank values should be pre-filled automatically.
* **Success State:** After successful submission, display a summary card showing the Request ID, a `PENDING_ADMIN` status badge, and a receipt preview.
* **Warning State:** Display a "Duplicate" warning alert if the system detects a matching Receipt No, Date, and Amount. Show a "Low-Confidence" warning if the OCR needs manual review.

## 5. Screen: Profile Page (`/profile/me`)
* **UI Layout:** A dashboard-style view for personal settings and historical metrics.
* **Header Component:** Displays an Avatar image (or initials) with explicit actions to "Change Photo" or "Use LINE Avatar".
* **Details Section:** Read-only info cards showing Subcontractor name, Contact name, Phone, Tax ID context, LINE UID, Bank account, and Assigned project IDs.
* **Statistics Section:** Metric cards displaying Pending approvals, Approved or paid requests, Total requests, VAT rate, and total Approved amount.
* **Data Visualization:** A request activity chart representing the user's historical input requests.