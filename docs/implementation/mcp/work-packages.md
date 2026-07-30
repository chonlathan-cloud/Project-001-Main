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
| MCP-200 | Discovery + standard search/fetch | Complete through Phase 4 in Demo | Inspection and Daily Report stable references join the existing scoped federation |
| MCP-210 | Projects/BOQ/version tools | Complete in Demo | Current, manifest, version, as-of and comparison contracts passed Owner pilot |
| MCP-220 | Users/Access tools | Complete in Demo | Minimized access views and sensitive audit passed Owner pilot |
| MCP-230 | Finance/Payment tools | Complete in Demo | Four tools, exact Decimal contracts, scope/permission tests and readiness metadata |
| MCP-240 | Document Content Gateway | Complete in Demo | Three tools, bounded content, block flag, redaction and injection defenses |
| MCP-250 | Inspection/Daily Report tools | Complete in Demo | Bounded defects, current/history reports, opaque document IDs and token-free share status |
| MCP-260 | Dashboard/Insights tools | Complete in Demo | Exact scoped totals, calculation metadata and explicit multi-source status |
| MCP-270 | Product Audit tools | Complete in Demo | Allowlisted Cloud Logging adapter, mandatory audit and body/prompt omission |
| MCP-280 | Curated GCP Operations tools | Complete locally; Demo proof pending | Six closed-input tools, environment aliases, 30-day operational view and redaction |
| MCP-300 | Backend internal read contracts | Complete through Phase 5 locally | 28 versioned service-authenticated `/api/v1/internal/mcp/*` routes |
| MCP-301 | MCP Product authorization fields | Complete locally | Fail-closed entitlements, unique OAuth binding, per-call memberships |
| MCP-302 | Owner/Admin settings and revocation | Complete locally; Demo Admin proof pending | Owner UI/API supports permission scope, OAuth binding, revoke and unbind |
| MCP-303 | Internal Chat adapter | Complete locally; Demo consistency proof pending | Current Product session calls exact shared dashboard/insight services |
| MCP-304 | Product citation/document routes | Complete through Phase 4 in Demo | Product citations, operation references and opaque Document Gateway IDs; no signed URLs |
| MCP-400 | Golden Evaluation Set | Complete through Phase 5 locally | Phase 2–5 deterministic evaluators pass at 100% |
| MCP-401 | Contract tests | Complete through repository Phase 5 scope | Backend and MCP suites cover 37 public tools and 28 Backend routes |
| MCP-402 | Authorization/isolation tests | Complete locally; live IAM/Admin test pending | Cross-project, environment, six-tool Admin matrix and next-call revocation pass |
| MCP-403 | Security/redaction tests | Complete through repository Phase 5 scope | Operational query bounds and credential/URL/PII/path/UUID redaction join prior controls |
| MCP-404 | Performance/failure tests | Phase 5 repository failure paths covered; live p95 pending | Operations p95 target <=15 seconds requires deployed Demo evidence |
| MCP-405–MCP-409 | Pilots and rollout | Phase 4 Demo complete; Phase 5 pending | Phase 5 needs operational view/IAM, Owner live proof, Admin pilot and revocation evidence |

## Remaining release and later-phase gaps

1. Provision the 30-day environment-locked operational bucket/sink/view, exact
   view IAM and approved Product metadata permissions; repository code does not
   make these cloud changes.
2. Deploy and collect Phase 5 Owner evidence for all six tools plus exact
   Internal/External Chat consistency, then run the selected Admin matrix and
   immediate revocation proof.
3. Phase 6 Private Plugin and Beta rollout remain blocked until the Phase 5 Demo
   evidence is passed.
