# BOQ Hierarchy Contract

Phase 1 audit artifact for BOQ sync and BOQ Workbench display.

## Scope

This contract defines how synced BOQ rows must become a display-ready WBS tree for Customer, Subcontractor, and Compare views.

The immediate validation target is sheet `SN`, BOQ type `CUSTOMER`, using `Design/S-BOQ/S-BOQ.json` and the provided Google Sheet screenshot as the reference.

Google Stitch status: Stitch MCP was queried during the audit, but both project and design-system reads returned `Auth required`. UI work should continue from local `Design/DESIGN.md` and existing BOQ Workbench conventions until Stitch auth is available.

## Current Findings

- Backend already has hierarchy fields on `BOQItem`: `raw_wbs_level`, `display_wbs_level`, `row_type`, `hierarchy_status`, `source_row_index`, and `sort_order`.
- Backend already has `app/services/boq_hierarchy.py`, which classifies rows as `SYSTEM`, `GROUP`, `ITEM`, or `TOTAL`.
- Backend project BOQ API already returns `row_type`, hierarchy status, source row index, sort order, and display budgets.
- Frontend `api.js` already sanitizes hierarchy fields into `rowType`, `hierarchyStatus`, `sourceRowIndex`, `sortOrder`, `rawWbsLevel`, and `displayWbsLevel`.
- Frontend `BoqWorkbench.jsx` already has row-type display, quality badges, and default expansion for Level 1 parents.
- The current SN sample order is not the original sheet order. In `S-BOQ.json`, `วาล์ว (VALVE) ทองเหลือง` appears before `ระบบน้ำเสีย` and `ระบบน้ำดี`, which prevents reliable parent inference from the sample alone.
- The SN sample has `parent_id` values but does not include matching row `id` values, so the sample cannot resolve parent references directly.
- The SN sample does not include `TOTAL - SN`, `TOTAL - 1`, or `TOTAL - 2`, but these rows must be visible in the final UI.

## Required Row Contract

Each persisted and API-returned BOQ row should expose these fields:

| Field | Requirement |
| --- | --- |
| `key` / `id` | Stable row identifier returned to the frontend. |
| `sheet_name` | Sheet tab, e.g. `SN`. |
| `boq_type` | `CUSTOMER` or `SUBCONTRACTOR`. |
| `source_row_index` | Original Google Sheet row index. Required for deterministic hierarchy inference. |
| `sort_order` | Display order after parsing. Usually follows `source_row_index`; may be adjusted only by explicit normalization rules. |
| `raw_wbs_level` | WBS level emitted by parser/Gemini/template parser before correction. |
| `display_wbs_level` | Corrected WBS level used by UI. |
| `wbs_level` | Should match `display_wbs_level` for backward compatibility. |
| `row_type` | `SYSTEM`, `GROUP`, `ITEM`, or `TOTAL`. |
| `hierarchy_status` | `OK`, or pipe-separated quality flags such as `INFERRED_PARENT|RAW_LEVEL_MISMATCH`. |
| `parent_id` | Database parent relationship. API may return only nested `children`, but persisted data must store the parent. |
| `item_no` | BOQ item number when present. |
| `description` | Display label. |
| `qty`, `unit` | Detail values when present. |
| material/labor/total fields | Own budget values and display rollups. |
| `children` | Recursive API payload. |

## Row Type Rules

`SYSTEM`
- Top-level system/discipline separator.
- Any description beginning with `ระบบ` must be Level 1 across all sheets.
- Numeric top-level item numbers such as `1`, `2`, `3` may also indicate Level 1 when the row is a section header.
- Example: `ระบบน้ำเสีย (SIOL WATER)`, `ระบบน้ำดี (COLD WATER)`.

`GROUP`
- Mid-level work package under a system.
- Pipe, valve, pump, equipment, and other work group rows are Level 2 when they organize detail rows.
- Example: `ท่อน้ำเสีย PVC CLASS 13.5`, `ท่อประปา PPR (PN 20)`, `วาล์ว (VALVE) ทองเหลือง`.

`ITEM`
- Leaf/detail BOQ row.
- Rows with unit, quantity, unit price, material total, labor total, or grand total are Level 3 unless a sheet-specific rule says otherwise.
- Example: `ขนาด Æ 2"`, `ACCESSORIES & FITTING`, `HANGER & SUPPORT`, `STOP VALVE Æ 1/2"`.

`TOTAL`
- Summary row that must remain visible in the UI.
- Sheet totals are Level 1 summary rows.
- Section totals are Level 2 summary rows under their related system.
- Example: `TOTAL - SN`, `TOTAL - 1`, `TOTAL - 2`.

## Parent Resolution Rules

1. Prefer a valid parser parent reference only if it points to an existing row in the same sync result.
2. If a valid parent reference is unavailable, infer parent from the original sheet order, not from post-processed summary order.
3. For `SYSTEM`, parent must be `null`.
4. For `GROUP`, parent must be the latest matching Level 1 `SYSTEM`.
5. For `ITEM`, parent must be the latest matching Level 2 `GROUP`.
6. For section `TOTAL - n`, parent must be the `SYSTEM` with `item_no = n`.
7. For sheet `TOTAL - SN`, parent must be `null`.
8. If the parser output order has summary rows before detail rows, backend normalization must restore the original sheet display order before parent inference.
9. If a parent is inferred, set `hierarchy_status` to include `INFERRED_PARENT`.
10. If raw parser level differs from corrected display level, set `hierarchy_status` to include `RAW_LEVEL_MISMATCH`.
11. If no safe parent can be determined, keep the row visible and set `PARENT_MISSING`.

## SN Customer Expected Tree

The Phase 1 fixture is `Design/S-BOQ/sn-customer-hierarchy.contract.json`.

Expected visible hierarchy:

```text
SN / CUSTOMER
- ระบบน้ำเสีย (SIOL WATER) [SYSTEM, Level 1]
  - ท่อน้ำเสีย PVC CLASS 13.5 [GROUP, Level 2]
    - ขนาด Æ 2" [ITEM, Level 3]
    - ACCESSORIES & FITTING [ITEM, Level 3]
    - HANGER & SUPPORT [ITEM, Level 3]
  - TOTAL - 1 [TOTAL, Level 2]

- ระบบน้ำดี (COLD WATER) [SYSTEM, Level 1]
  - ท่อประปา PPR (PN 20) [GROUP, Level 2]
    - ขนาด Æ 1/2" [ITEM, Level 3]
    - ACCESSORIES & FITTING [ITEM, Level 3]
    - HANGER & SUPPORT [ITEM, Level 3]
  - วาล์ว (VALVE) ทองเหลือง [GROUP, Level 2]
    - STOP VALVE Æ 1/2" [ITEM, Level 3]
    - GATE VALVE Æ 1/2" [ITEM, Level 3]
    - SOLENOID VALVE Æ 1/2" [ITEM, Level 3]
    - ACCESSORIES & FITTING [ITEM, Level 3]
    - มิเตอร์น้ำประปา ø1/2" [ITEM, Level 3]
  - TOTAL - 2 [TOTAL, Level 2]

- TOTAL - SN [TOTAL, Level 1]
```

Rows such as `ปั๊มน้ำอัตโนมัติ` are not part of the expected visible SN tree for this fixture because the user-defined target Level 2 set contains only wastewater pipe, PPR pipe, and brass valve. If a future sheet includes pump detail rows, it should become a normal Level 2 `GROUP` under `ระบบน้ำดี`.

## Acceptance Criteria For Later Phases

- SN Customer tree exactly matches the fixture hierarchy.
- `ระบบน้ำเสีย` and `ระบบน้ำดี` are Level 1 parents.
- `ท่อน้ำเสีย PVC CLASS 13.5`, `ท่อประปา PPR (PN 20)`, and `วาล์ว (VALVE) ทองเหลือง` are Level 2 groups.
- Detail rows are Level 3 items under the correct group.
- `TOTAL - SN`, `TOTAL - 1`, and `TOTAL - 2` are visible.
- UI shows `display_wbs_level`, `row_type`, and quality badges.
- Search finds parent rows, child rows, and total rows.
- Sheet filter `SN` keeps the full matching branch visible.
- Compare view preserves hierarchy for Customer-only, Subcontractor-only, and matched rows.
- Backend validation must fail or warn if a sheet loses TOTAL rows during sync.

## Phase 2 Risks To Address

- Current sample order can make parent inference wrong if the backend uses post-processed order instead of original sheet order.
- Summary fallback can place summary rows before detail rows. That is useful for total validation but unsafe for display hierarchy unless the original row order is preserved.
- `parent_id` cannot be audited from `S-BOQ.json` unless row IDs are included in the sample or the API returns nested children.
- Rows with zero totals and no children should be handled explicitly: visible if they are `SYSTEM`, `GROUP` with later children, or `TOTAL`; otherwise hidden or flagged as an empty reference row.
