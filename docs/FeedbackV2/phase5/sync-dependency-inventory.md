# Google Sheets BOQ sync dependency inventory

Inventory was completed before deletion against the committed Phase 4 baseline.

| Surface | Phase 4 dependency | Phase 5 disposition |
| --- | --- | --- |
| Backend routes | `/projects/boq/sync`, `/tabs`, `/sync-batch`, `/sync-jobs/{id}` | Retained only as authenticated actionable 410 compatibility routes |
| Backend runtime | `boq_sync_service.py`, `boq_sync_job_service.py` | Removed after caller/import search |
| Schemas | `SyncBOQ*`, `SheetTabs*` DTOs | Removed; retired routes accept no write payload |
| Gemini | Sheet parsing prompt/function inside `ai_service.py` | Removed; OCR, vector embedding, RAG and answer polishing preserved |
| Configuration | `BOQ_BATCH_SYNC_MAX_TABS`, `VITE_BOQ_BATCH_SYNC_MAX_TABS` | Removed from backend, frontend, Docker and deploy examples |
| Frontend API | sync, tab-preview, batch and job-status helpers | Removed |
| Frontend Projects | Sheet URL/type/tab drawer, polling and retry | Removed; native BOQ is the only BOQ authoring route |
| Settings/Support | Google Sheets integration and BOQ Sync status/help | Removed; Firebase, LINE, Vertex AI and unrelated integrations preserved |
| MCP backend | `boq_sync` processing branch/job-service import | Job import removed; older backend request receives 410 |
| MCP public tool | `get_processing_status` workflow enum/schema | `boq_sync` removed; receipt OCR, daily report and FlowAccount retained |
| Legacy hierarchy helper | Offline legacy fixture/contract utilities | Retained only for historical validation; not imported by runtime write paths |
| Legacy data | `boq_items`, installment/transaction/input relationships | Preserved without expiry, remap, replay, reconciliation or deletion |
| Documentation/prototypes | Older sync-first flow descriptions | Marked superseded by native BOQ and this Phase 5 record |

Post-change startup/import search must find no reference to either removed service. References to `boq_sync` are allowed only in the 410 compatibility branch, retirement tests/evidence, and historical documentation. A generic Cloud Logging workflow filter remains string-based so historical logs can still be searched; it is not an active sync tool.
