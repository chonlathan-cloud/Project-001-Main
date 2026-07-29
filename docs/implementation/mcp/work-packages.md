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
| MCP-200 | Discovery + standard search/fetch | Complete through Phase 4 locally | Inspection and Daily Report stable references join the existing scoped federation |
| MCP-210 | Projects/BOQ/version tools | Complete in Demo | Current, manifest, version, as-of and comparison contracts passed Owner pilot |
| MCP-220 | Users/Access tools | Complete in Demo | Minimized access views and sensitive audit passed Owner pilot |
| MCP-230 | Finance/Payment tools | Complete locally; Demo proof pending | Four tools, exact Decimal contracts, scope/permission tests and readiness metadata |
| MCP-240 | Document Content Gateway | Complete locally; Demo proof pending | Three tools, bounded content, block flag, redaction and injection defenses |
| MCP-250 | Inspection tools | Complete locally; Demo proof pending | Bounded defect list/detail/event reads and opaque document IDs |
| MCP-260 | Daily Report tools | Complete locally; Demo proof pending | Current content, immutable versions and token-free share status |
| MCP-270 | Dashboard/Insights tools | Complete locally; Demo proof pending | Exact scoped totals, calculation metadata and explicit multi-source status |
| MCP-280 | Product Audit tools | Complete locally; Demo view/IAM proof pending | Allowlisted Cloud Logging adapter, mandatory audit and body/prompt omission |
| MCP-300 | Backend internal read contracts | Complete through Phase 4 locally | 27 versioned service-authenticated `/api/v1/internal/mcp/*` routes |
| MCP-301 | MCP Product authorization fields | Complete locally | Fail-closed entitlements, unique OAuth binding, per-call memberships |
| MCP-302 | Owner/Admin settings and revocation | Backend complete; UI/pilot pending | Owner-only mutation endpoints support enable, revoke and unbind |
| MCP-303 | Internal Chat adapter | Not started | Planned after external contracts stabilize |
| MCP-304 | Product citation/document routes | Complete through Phase 4 locally | Product citations, operation references and opaque Document Gateway IDs; no signed URLs |
| MCP-400 | Golden Evaluation Set | Complete through Phase 4 locally | Phase 2, Phase 3 and Phase 4 deterministic evaluators pass at 100% |
| MCP-401 | Contract tests | Complete through repository Phase 4 scope | Backend and MCP suites cover 31 public tools and 27 Backend routes |
| MCP-402 | Authorization/isolation tests | Complete locally; live IAM test pending | Cross-project denial, owner cohort and environment tests pass |
| MCP-403 | Security/redaction tests | Complete through repository Phase 4 scope | Audit filter injection, body/prompt omission, mandatory audit, source failure and existing document controls covered |
| MCP-404 | Performance/failure tests | Phase 4 partial/failure paths covered; live p95 pending | Operations p95 target <=15 seconds requires deployed Demo evidence |
| MCP-405–MCP-409 | Pilots and rollout | Phase 3 Demo complete; Phase 4 pending | Phase 4 needs dedicated audit view/IAM, deployment approval and live evidence |

## Remaining release and later-phase gaps

1. Provision the environment-locked Product Audit bucket/view and grant the MCP
   service identity view access at that exact view; repository code does not make
   this IAM or Logging change.
2. Deploy and collect Phase 4 Owner live evidence, including all ten tools,
   cross-domain sources, audit events, zero leakage/errors and operations p95.
3. Phase 5 curated GCP Operations and Internal Chat adapters remain unimplemented.
