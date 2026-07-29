# Product MCP work packages

Status reflects repository work only. A package that needs live OAuth, IAM,
Cloud Run, or pilot evidence is not complete until that external evidence exists.

| ID | Work package | Status | Evidence / dependency |
|---|---|---|---|
| MCP-001 | Source-to-tool matrix | Complete | `source-to-tool-matrix.md` |
| MCP-002 | Tool schemas v1 | Complete | `contracts/tool-input-schemas-v1.json` |
| MCP-003 | Common response/error schemas | Complete | MCP `app/schemas/common.py` |
| MCP-004 | Authorization matrix | Complete | `authorization-matrix.md` + tests |
| MCP-005 | Threat model | Complete | `threat-model.md` |
| MCP-006 | Delegation ADR | Complete | ADR-0001 |
| MCP-007 | Auth provider ADR | Complete for SDK/provider baseline | ADR-0002; managed IdP selection remains a live spike |
| MCP-100 | Service scaffold | Complete in Demo | Separate non-root MCP service deployed and rollback-tested in Phase 1 |
| MCP-101 | Streamable HTTP `/mcp` | Complete in Demo | Protocol, container smoke and live Inspector initialization passed |
| MCP-102 | Config/environment lock | Complete in Demo | Fail-closed environment checks and deployment preflight passed |
| MCP-103 | OAuth validation | Complete in Demo | JWT/scope vectors and direct Codex Authorization Code + PKCE passed |
| MCP-104 | Policy client/enforcement | Complete in Demo | Backend re-resolves the principal on every policy and data read |
| MCP-105 | Audit/metrics separation | Complete for Owner pilot | Live sensitive audit/redaction and outage behavior passed |
| MCP-106 | Demo service account/IAM | Complete for Owner pilot | Dedicated identity and least-privilege evidence recorded in Phase 2 release evidence |
| MCP-107 | Demo deploy/preflight | Complete for Owner pilot | Demo deploy, smoke and rollback evidence recorded |
| MCP-200 | Discovery + standard search/fetch | Complete through Phase 3 locally | Finance/document adapters inherit domain permission and audit policy |
| MCP-210 | Projects/BOQ/version tools | Complete in Demo | Current, manifest, version, as-of and comparison contracts passed Owner pilot |
| MCP-220 | Users/Access tools | Complete in Demo | Minimized access views and sensitive audit passed Owner pilot |
| MCP-230 | Finance/Payment tools | Complete locally; Demo proof pending | Four tools, exact Decimal contracts, scope/permission tests and readiness metadata |
| MCP-240 | Document Content Gateway | Complete locally; Demo proof pending | Three tools, bounded content, block flag, redaction and injection defenses |
| MCP-250–MCP-280 | Later domain tools | Not started | Phases 4–5 in the approved plan |
| MCP-300 | Backend internal read contracts | Complete through Phase 3 locally | 20 versioned service-authenticated `/api/v1/internal/mcp/*` routes |
| MCP-301 | MCP Product authorization fields | Complete locally | Fail-closed entitlements, unique OAuth binding, per-call memberships |
| MCP-302 | Owner/Admin settings and revocation | Backend complete; UI/pilot pending | Owner-only mutation endpoints support enable, revoke and unbind |
| MCP-303 | Internal Chat adapter | Not started | Planned after external contracts stabilize |
| MCP-304 | Product citation/document routes | Complete through Phase 3 locally | Product citations plus opaque Document Gateway metadata; no signed URLs |
| MCP-400 | Golden Evaluation Set | Complete through Phase 3 locally | Phase 2 and Phase 3 deterministic evaluators pass; Phase 3 live run pending |
| MCP-401 | Contract tests | Complete through repository Phase 3 scope | Backend and MCP suites cover 21 public tools and eight new Backend routes |
| MCP-402 | Authorization/isolation tests | Complete locally; live IAM test pending | Cross-project denial, owner cohort and environment tests pass |
| MCP-403 | Security/redaction tests | Complete through repository Phase 3 scope | Credential/path leakage, block, prompt injection, size/MIME and audit outage covered |
| MCP-404 | Performance/failure tests | Failure/rate-limit paths covered; load baseline pending | p95 target and distributed quota evidence require deployed Demo |
| MCP-405–MCP-409 | Pilots and rollout | Phase 2 Owner complete; Phase 3 pending | Phase 3 deployment requires separate approval and live evidence |

## Remaining backend contract gaps

1. Dashboard and Insight MCP contracts remain Phase 4 work.
2. Inspection and Daily Report public MCP tools remain Phase 4 work; only their
   bounded file metadata adapters and share-status Backend boundary exist now.
3. No Product Audit query contract/view exists.

Phase 3 closes the Finance, Payment, Document Gateway and share-status Backend
gaps. Remaining items must be implemented as versioned Backend read contracts
before their dependent Phase 4/5 tools are released.
