# Phase 3 repository evidence

Date: 2026-07-29
Scope: Finance, Payment and Document Gateway repository implementation
Cloud state: unchanged

## Outcome

Phase 3 is complete in the repository and ready for an explicitly approved Demo
deployment. MCP version `0.3.0` exposes 21 read-only tools: the 14 Phase 2 tools
plus seven Phase 3 tools. The Backend exposes eight new service-authenticated
read contracts, bringing the internal MCP route set to 20.

## Exit evidence

| Exit criterion | Result | Evidence |
|---|---|---|
| Finance fixtures exact 100% | Pass | Phase 3 evaluator checks exact Decimal strings and arithmetic for G-006/G-007 |
| Sensitive accesses audited 100% | Pass locally | Finance/payment and document-content tools are sensitive; audit outage prevents Backend execution |
| No signed URL, credential or path leakage | Pass | Backend and MCP tests cover payment, metadata, content and share status; credential-like text is redacted |
| Unsupported and large files verified | Pass | MIME, byte, page, extraction-state and external-AI-block paths are covered |
| Prompt injection defense | Pass | Content is labeled untrusted, instruction text is detected, and the evaluator includes an adversarial document |
| Closed input contracts | Pass | All advertised tool schemas set `additionalProperties=false`; unknown fields fail before policy/Backend calls |

## Verification results

- Backend: `100 passed`.
- MCP: `58 passed` (one non-failing Starlette/httpx deprecation warning).
- Phase 3 evaluator: 5/5 cases, `100.0%`, all gates true.
- Ruff: all MCP code/tests and every changed Backend file pass.
- `git diff --check`: pass.
- Production images build as `projects-001-be:phase3-local` and
  `projects-001-mcp:phase3-local`.

The full Backend tree still has eight pre-existing Ruff findings in unrelated
files. They were not changed as part of this Phase 3 scope.

## Implemented boundary

Public MCP tools:

- `get_project_financial_summary`
- `search_financial_records`
- `get_payment`
- `get_payment_document_status`
- `search_documents`
- `get_document_metadata`
- `read_document_content`

The Backend also implements the status-only Daily Report share contract required
by Phase 3. Its public `get_report_share_status` MCP tool remains correctly
scheduled for Phase 4.

## Demo deployment prerequisites

Repository completion does not authorize deployment. Before live Phase 3 proof:

1. Back up the Demo database and apply
   `Projects-001-BE/scripts/migrations/20260729_mcp_document_gateway.sql`.
2. Add the four `MCP_DOCUMENT_*` values to the Demo Backend environment and keep
   `MCP_ALLOWED_ROLES=owner` unless the Admin pilot is separately approved.
3. Deploy Backend first and verify all 20 internal contracts remain
   service-identity-only.
4. Deploy MCP `0.3.0`, then run health, protected-resource, Inspector and direct
   Codex Owner checks.
5. Run the Phase 3 evaluator against sanitized live records and verify Product
   Audit entries for every Finance/payment/document-body access.
6. Confirm no response/log contains a signed URL, object path, credential,
   document body in audit fields, bank reference or FlowAccount secret/ID.

Beta and Phase 4 remain blocked until the approved Demo Phase 3 live evidence is
recorded.
