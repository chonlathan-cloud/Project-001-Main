# Phase 6.5: Subcontractor Portal Mobile Responsive Plan

Status: Complete — demo and physical-device acceptance testing passed
Decision date: 2026-07-19  
Completion date: 2026-07-19
Implementation type: Responsive React web and LIFF optimization  
Native application: Out of scope  

Implementation progress (2026-07-19):

- Shared mobile header and off-canvas subcontractor navigation implemented.
- Daily Report camera/gallery evidence flow, previews, upload states, and mobile step actions implemented.
- Input camera/gallery capture, stacked workflow, mobile line items, on-demand preview, review sheet, and sticky submit implemented.
- Profile desktop inline grids replaced with responsive sections and mobile touch targets.
- Existing API calls, permissions, validation, and backend behavior preserved.
- Frontend lint and production build pass.
- Google Stitch could not be queried because the connector requires authentication; the checked-in RAYADEE design and Daily Report mockup were used as the implementation reference.
- Demo deployment, iPhone LINE, Android LINE, customer portal, and desktop regression checks passed.
- Upload recovery, session states, permissions, Thai content, customer acknowledgement, and report-linked questions passed.
- No critical or high-priority defects remain open.

## 1. Decision Summary

The entire subcontractor portal must work well on mobile devices before Phase 7 begins.

The work covers:

- Daily Report: `/daily-reports/me`
- Input: `/input`
- Profile: `/profile/me`
- Subcontractor Sidebar
- Workspace Topbar
- Shared responsive layout, navigation, form, upload, feedback, and error states

The work does not create:

- An iOS or Android native application
- A separate mobile backend
- A Progressive Web App installation flow
- Full offline operation
- New business rules or API contracts
- A redesign of the Admin/Owner portal

Desktop behavior must remain available and must not regress.

## 2. Why This Is a Release Gate

Subcontractors enter the portal from a LINE Rich Menu and are expected to perform site work from mobile phones. Mobile support is therefore part of the primary product experience, not an optional enhancement.

The current implementation includes responsive breakpoints, but the result is mostly a stacked desktop interface. Important mobile problems remain:

- The shared content area retains the desktop sidebar offset.
- The mobile sidebar becomes a large page section instead of a compact navigation control.
- Workspace headers consume too much vertical space in a LINE webview.
- Daily Report keeps desktop cards, hierarchy, and action placement.
- Input combines a dense form and document preview designed around a large screen.
- Profile contains inline multi-column layout styles that cannot adapt cleanly.
- Long forms do not consistently provide a reachable mobile primary action.
- Camera, upload, retry, keyboard, safe-area, and weak-network behavior require explicit mobile treatment.

Phase 7 scheduling and reminders should not direct subcontractors into a workflow that is not ready for their primary devices.

## 3. Product Goals

### 3.1 Primary goals

- Make every subcontractor route usable from a LINE in-app browser.
- Support normal use from 320px through 430px wide mobile viewports.
- Preserve the existing RAYADEE identity and business terminology.
- Reduce unnecessary scrolling and duplicated page chrome.
- Make primary actions obvious and reachable with one hand.
- Make required information and validation understandable in Thai.
- Make uploads recoverable on unstable mobile networks.
- Preserve the same permissions, APIs, and server-side validation.
- Keep desktop layouts functional at larger breakpoints.

### 3.2 Usability targets

- No horizontal page scrolling at supported widths.
- Daily Report normal path can be completed in approximately three minutes.
- Input can be completed without desktop-style side-by-side panels.
- Profile information can be reviewed and edited without zooming.
- Primary controls have at least a 44px touch target.
- Form fields use a mobile-safe font size to avoid unwanted iOS zoom.
- Sticky controls respect the device safe area and mobile keyboard.
- Users can recover from a failed upload without restarting the form.

## 4. Experience Principles

### 4.1 Responsive web, not a simulated native app

The portal remains one React web application. Mobile layouts should feel intentional, but they must not imitate operating-system navigation or introduce native-app assumptions.

### 4.2 LINE webview first

The primary environment is the LINE in-app browser. Safari and Chrome remain supported secondary environments.

### 4.3 One task per mobile screen

Large desktop sections should become focused mobile sections. Progressive disclosure should hide advanced or conditional fields until they are relevant.

### 4.4 Bottom space belongs to the current task

The primary action for a form should remain reachable near the bottom safe area. Global navigation must not compete with form submission controls.

### 4.5 Preserve source data and backend rules

Responsive work may reorganize how fields are presented, but it must not change:

- Required fields
- Permission checks
- Project assignments
- Submission state transitions
- Payment/input request rules
- Profile approval rules
- Upload ownership or storage rules

## 5. Responsive Contract

### 5.1 Viewport ranges

```text
Mobile compact: 320px-374px
Mobile standard: 375px-430px
Tablet/intermediate: 431px-1023px
Desktop: 1024px and above
```

Responsive rules should be content-driven. These ranges define the required testing matrix, not a requirement to create four separate implementations.

### 5.2 Mobile layout requirements

- `main-content` must have no desktop sidebar offset.
- Page width must remain within the visual viewport.
- Content must respect `env(safe-area-inset-top)` and `env(safe-area-inset-bottom)`.
- Interactive controls must remain usable when the software keyboard is open.
- Fixed or sticky elements must not cover validation messages or final fields.
- Tables must convert to mobile cards or controlled horizontal regions.
- Dialogs must become mobile sheets or full-width dialogs where appropriate.
- Text, images, and controls must not depend on hover.
- Focus states and screen-reader labels must remain available.

## 6. Mobile Information Architecture

### 6.1 Subcontractor shell

Recommended mobile shell:

- Compact sticky topbar
- RAYADEE identity
- Current route title
- Menu button opening an off-canvas sheet
- Navigation links for Daily Report, Input, and Profile
- Account identity and Sign Out inside the menu sheet
- No permanent desktop sidebar
- No large date pill or descriptive paragraph on every mobile page

A permanent bottom navigation is not recommended for the first implementation because it would compete with Daily Report and Input sticky action bars inside the limited LINE webview height.

### 6.2 Daily Report mobile flow

Keep the existing three-step business flow but present it as three focused mobile screens.

#### Step 1: Work and evidence

- Compact project/date context
- Camera-first action
- Secondary gallery/file action
- Photo previews
- Per-file waiting, uploading, uploaded, failed, and retry states
- Work summary
- Work areas
- Manpower
- Progress
- Weather

#### Step 2: Site check and tomorrow plan

- Large touch-friendly Safety, Quality, Schedule, Material, and Customer Decision controls
- Calm normal/no-issue path
- Conditional issue details
- Severity selection only when an issue exists
- Tomorrow plan
- Clear draft-saved state

#### Step 3: Review and submit

- Compact project/date summary
- Work summary
- Evidence thumbnails and upload state
- Issue summary
- Tomorrow plan
- Missing-required-information links returning to the relevant step
- Sticky Submit for Review action
- Dedicated submitted-success state

History should move into a compact “My Reports” view or collapsible section instead of extending the form page.

### 6.3 Input mobile flow

The current desktop form/preview composition should become a guided vertical workflow.

Recommended sequence:

1. Select income/expense request type.
2. Capture or upload the receipt/document.
3. Review OCR status and extracted information.
4. Complete project, requester, vendor, date, category, and payment fields.
5. Review line items as mobile cards.
6. Open document preview on demand in a full-width viewer.
7. Review the submission summary in a mobile sheet.
8. Submit and show a dedicated success state.

Mobile rules:

- Document preview is collapsed by default.
- Preview must never force the form into a narrow side-by-side column.
- Line-item tables become stacked editable cards.
- Long option lists use full-width controls.
- Receipt capture and gallery selection are visually distinct.
- OCR processing, failure, retry, and manual-entry states are explicit.
- The final Submit action remains reachable above the safe area.

### 6.4 Profile mobile flow

The Profile page should become a single-column account workspace.

Recommended section order:

1. Identity and access status
2. Contact information
3. Company information
4. Assigned projects
5. Bank/payment information where applicable
6. Documents/KYC status where applicable
7. Recent activity or account metadata
8. Sign Out

Mobile rules:

- Replace inline multi-column layout styles with responsive classes.
- Use expandable sections for secondary information.
- Keep Edit/Save/Cancel actions close to the section being edited.
- Avoid showing empty desktop statistics cards without useful mobile value.
- Clearly distinguish editable information from approval-controlled information.
- Preserve privacy treatment for bank and KYC information.

## 7. Work Packages

### 7.1 Phase 6.5A: Baseline and approved mobile specification

Tasks:

- Restore Stitch access and inspect the latest design system before implementation.
- Use the checked-in Daily Report mobile mockup as the workflow reference.
- Capture current screenshots at 320px, 360px, 390px, 430px, 768px, and desktop.
- Record overflow, keyboard, navigation, upload, and dialog defects.
- Prepare mobile wireframes for Shell, Daily Report, Input, and Profile.
- Confirm Thai mobile copy and field priority.
- Define shared spacing, touch-target, field, sheet, header, and sticky-action patterns.

Exit criteria:

- Mobile wireframes are approved for all in-scope routes.
- Desktop elements to preserve are identified.
- No unresolved mobile navigation or field-priority decisions remain.

### 7.2 Phase 6.5B: Shared subcontractor shell

Tasks:

- Remove the desktop sidebar offset on mobile.
- Convert Sidebar into an accessible off-canvas mobile menu.
- Create a compact subcontractor Topbar.
- Remove duplicated page title/description content.
- Add safe-area handling.
- Prevent background scrolling while the menu is open.
- Ensure navigation closes after route changes.
- Keep desktop Sidebar and Topbar unchanged at desktop width.

Exit criteria:

- Daily Report, Input, and Profile open at full mobile width.
- Navigation and Sign Out are reachable without horizontal scrolling.
- No content is hidden behind the topbar or device safe area.
- Keyboard and orientation changes do not break the shell.
- Desktop shell regression checks pass.

### 7.3 Phase 6.5C: Daily Report mobile experience

Tasks:

- Implement the focused three-step mobile presentation.
- Make project/date context compact.
- Add camera-first and gallery actions.
- Show media thumbnails and per-file state.
- Preserve successful uploads when another file fails.
- Add retry and remove controls.
- Add draft-saved feedback.
- Use progressive disclosure for issues.
- Add sticky step actions.
- Add missing-field navigation.
- Add dedicated submitted and changes-requested states.
- Move history out of the long form flow.

Exit criteria:

- A subcontractor can create, save, submit, and resubmit from a mobile LINE webview.
- At least one photo is visibly uploaded before submission.
- A failed upload can be retried without recreating the report.
- The normal report path meets the completion-time target.
- Submitted reports become read-only.
- Desktop Daily Report still works.

### 7.4 Phase 6.5D: Input mobile experience

Tasks:

- Convert the desktop form/preview layout into a vertical mobile workflow.
- Provide mobile receipt capture and gallery selection.
- Make OCR processing and retry states visible.
- Convert line-item rows to mobile cards.
- Move document preview into an on-demand full-width view.
- Convert the review dialog to a mobile sheet.
- Add a sticky final action without covering fields.
- Validate long Thai labels, currency values, and error messages.

Exit criteria:

- Income and expense requests can be completed at 320px width.
- Receipt capture, OCR, manual correction, review, and submit work in LINE.
- No line-item field requires horizontal page scrolling.
- Preview can be opened and closed without losing form state.
- Desktop Input behavior remains available.

### 7.5 Phase 6.5E: Profile mobile experience

Tasks:

- Replace inline grid styles with responsive layout classes.
- Reorder profile sections for subcontractor priorities.
- Make edit actions section-specific and touch-friendly.
- Stack identity, project, contact, company, bank, and document information.
- Add compact loading, empty, error, and approval-controlled states.
- Confirm long names, project lists, phone numbers, and bank information wrap safely.

Exit criteria:

- Profile content is readable and editable without zooming.
- Assigned-project information is clear.
- Approval-controlled fields are not presented as freely editable.
- Sensitive information remains protected.
- Desktop Profile behavior does not regress.

### 7.6 Phase 6.5F: Accessibility, resilience, and device QA

Tasks:

- Test keyboard-only navigation where supported.
- Test screen-reader labels and focus order.
- Confirm 44px touch targets.
- Confirm visible focus and validation states.
- Test Thai text scaling and long content.
- Test slow, interrupted, and resumed uploads.
- Test refresh and LIFF close/reopen behavior.
- Test iOS and Android software keyboards.
- Test portrait orientation at all supported widths.
- Test actual LINE in-app browsers on iPhone and Android.
- Run frontend lint and production build.
- Run desktop regression checks for all modified pages.

Exit criteria:

- No critical mobile usability or accessibility defects remain.
- No horizontal page scrolling exists in supported flows.
- Upload and draft recovery behavior is verified.
- LINE mobile beta flow passes on iPhone and Android.
- Desktop regression checks pass.

## 8. Frontend Architecture Guidance

Implementation should reuse existing APIs and business state.

Recommended structure:

- Keep API functions in `src/api.js` unchanged unless a separately approved requirement is discovered.
- Separate shared workflow state from desktop/mobile presentation when the current component is too tightly coupled.
- Prefer responsive components and shared primitives over duplicate route implementations.
- Use mobile-specific components only when desktop markup cannot provide a clear accessible reading order.
- Replace layout-related inline styles with named responsive classes.
- Keep permission and role decisions outside presentation components.
- Do not use viewport width as an authorization or data-selection decision.

Potential shared UI primitives:

- `SubcontractorMobileHeader`
- `SubcontractorNavigationSheet`
- `MobileStickyActions`
- `MobileSectionCard`
- `MobileProgressHeader`
- `MobileUploadPicker`
- `MobileFileStatus`
- `MobileReviewSheet`
- `ResponsiveFieldGrid`

Names are provisional and must be reconciled with existing component conventions before implementation.

## 9. Expected File Areas

Likely frontend areas:

- `Projects-001-FE/src/App.jsx`
- `Projects-001-FE/src/components/Sidebar.jsx`
- `Projects-001-FE/src/components/WorkspaceTopbar.jsx`
- `Projects-001-FE/src/index.css`
- `Projects-001-FE/src/DailyReportsPage.jsx`
- `Projects-001-FE/src/components/dailyReports/SubcontractorDailyReportWorkspace.jsx`
- `Projects-001-FE/src/daily-reports.css`
- `Projects-001-FE/src/InputPage.jsx`
- `Projects-001-FE/src/components/InputLineItemsEditor.jsx`
- `Projects-001-FE/src/ProfilePage.jsx`
- New shared subcontractor responsive components under `Projects-001-FE/src/components/`

Out-of-scope areas:

- `Projects-001-BE/`
- Firestore collections
- GCS bucket architecture
- LINE Messaging API delivery logic
- Admin/Owner review UI
- Customer portal UI

## 10. State and Failure Requirements

Every in-scope mobile page must define:

- Initial loading
- Empty state
- Inline validation
- Network failure
- Retry
- Session expired
- Permission denied
- Save in progress
- Save successful
- Submit in progress
- Submit successful
- Submit failed

Upload surfaces must additionally define:

- Selected locally
- Waiting to upload
- Uploading
- Uploaded
- Unsupported type
- File too large
- Failed
- Retry available
- Removed

## 11. Mobile Test Matrix

### 11.1 Required viewport coverage

- 320px compact phone
- 360px Android baseline
- 375px iPhone baseline
- 390px modern iPhone
- 430px large phone
- 768px tablet boundary
- 1024px desktop boundary

### 11.2 Required environments

- LINE in-app browser on iPhone
- LINE in-app browser on Android
- Safari on iPhone
- Chrome on Android
- Desktop Chrome

### 11.3 Required end-to-end subcontractor flows

#### Daily Report

- Open from Rich Menu
- Select project/date
- Capture a photo
- Add work information
- Complete the quick check
- Add an issue
- Review and submit
- Recover from failed media upload
- Open submitted status
- Open Changes Requested and resubmit

#### Input

- Open Input
- Capture/upload receipt
- Wait for OCR
- Correct extracted values
- Add/edit/remove line items
- Open document preview
- Review and submit
- Recover from OCR or network failure

#### Profile

- Open Profile
- Review access status
- Review assigned projects
- Edit allowed contact/company information
- Review protected fields
- Save and reload
- Sign out

## 12. Acceptance Criteria

Phase 6.5 is complete only when:

- All three subcontractor routes work from 320px through 430px.
- No supported flow has horizontal page scrolling.
- Sidebar is replaced by usable mobile navigation.
- Topbar is compact and does not duplicate page content.
- Daily Report normal path can be completed in approximately three minutes.
- Camera and gallery photo selection work in LINE.
- Failed media uploads can be retried.
- Input document preview does not compress the form.
- Input line items are usable without a desktop table.
- Profile inline desktop grids are removed from the mobile reading order.
- Primary actions remain reachable with the mobile keyboard open.
- Safe-area insets are respected.
- Thai labels and validation messages do not overflow.
- Session, permission, error, loading, and success states are verified.
- iPhone LINE and Android LINE beta tests pass.
- Desktop Daily Report, Input, Profile, Sidebar, and Topbar regression tests pass.
- Frontend lint and production build pass.

## 13. Delivery and Rollout

Recommended rollout:

1. Approve mobile wireframes.
2. Implement and verify the shared shell.
3. Implement Daily Report mobile UX.
4. Implement Input mobile UX.
5. Implement Profile mobile UX.
6. Run device and desktop regression QA.
7. Deploy to the demo environment.
8. Test with a real subcontractor account on iPhone and Android.
9. Resolve critical and high-priority defects.
10. Deploy to beta.
11. Mark Phase 6.5 complete.
12. Begin Phase 7.

Rollback must preserve:

- Existing desktop routes
- Existing backend/API behavior
- Existing saved drafts and uploaded files
- Existing LINE login configuration

## 14. Phase Gate

Phase 7 must not begin until the Phase 6.5 acceptance criteria pass in the demo environment and the critical mobile flows pass on at least one iPhone and one Android device inside LINE.

Scheduling and reminder work may be prepared separately, but reminders must not be activated for subcontractors until the mobile portal is ready.

Gate result: passed on 2026-07-19. Phase 7 may begin.

## 15. Completion Record

- Shared shell, Daily Report, Input, Profile, customer portal, and Thai customer report passed.
- iPhone LINE and Android LINE acceptance flows passed.
- Camera, gallery, upload retry, submission, review, publication, acknowledgement, and questions passed.
- Desktop regression checks passed.
- Frontend lint and production build passed.
- Google Stitch authentication remains a tooling limitation and is not a Phase 6.5 release blocker.

No native-application decisions are required for this phase.
