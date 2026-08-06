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
| MCP-280 | Curated GCP Operations tools | Complete in Beta | Six closed-input tools, environment aliases, 30-day operational view, redaction and released qualification |
| MCP-300 | Backend internal read contracts | Complete in Beta | 28 versioned service-authenticated `/api/v1/internal/mcp/*` routes support the qualified 37-tool release |
| MCP-301 | MCP Product authorization fields | Complete in Beta | Fail-closed entitlements, unique OAuth binding, per-call memberships and ChatGPT Owner/Admin qualification passed |
| MCP-302 | Owner/Admin settings and revocation | Complete in Beta | Permission scope, OAuth binding, revoke/unbind and next-call denial passed |
| MCP-303 | Internal Chat adapter | Complete in Demo; shared policy qualified for Beta | Product session and External MCP use the approved shared dashboard/insight services and authorization semantics |
| MCP-304 | Product citation/document routes | Complete through Phase 4 in Demo | Product citations, operation references and opaque Document Gateway IDs; no signed URLs |
| MCP-400 | Golden Evaluation Set | Complete through Phase 5 locally | Phase 2–5 deterministic evaluators pass at 100% |
| MCP-401 | Contract tests | Complete through repository Phase 5 scope | Backend and MCP suites cover 37 public tools and 28 Backend routes |
| MCP-402 | Authorization/isolation tests | Complete in Beta | Owner/Admin, assigned/unassigned project, missing-permission, revoke/unbind and cross-environment cases passed |
| MCP-403 | Security/redaction tests | Complete for Phase 6 | Query bounds, audit pairing and credential/URL/PII/path/UUID/prompt/body leakage checks passed |
| MCP-404 | Performance/failure tests | Complete in Beta | Simple-read and document/operations targets, current error window, audit outage and rollback gates passed |
| MCP-405 | Owner Demo pilot | Complete | Operations, Internal Chat parity, audit, latency and rollback passed for Owner |
| MCP-406 | Admin Demo pilot | Complete | Explicit grant, scoped allow/deny, cross-project denial, unbind and Internal Chat denial passed |
| MCP-407 | Private Plugin test | Complete in Beta | ChatGPT OAuth/CIMD connection, bound compatibility, workflow skill and 37-tool discovery/callability passed |
| MCP-408 | Beta preflight/deploy | Complete | Dedicated identity/log routing, immutable images and final Backend/MCP revisions are live and recorded |
| MCP-409 | Beta controlled rollout | Complete | Owner, selected Admin, revoke/restore, negative cases, audit, performance and rollback gates passed |

## Remaining release and later-phase gaps

Phase 6 is closed. Remaining work is tracked in
[`phase7-publish-readiness-checklist.md`](phase7-publish-readiness-checklist.md):

1. freeze source/build provenance and the final submission candidate;
2. complete publisher identity, public listing, Privacy Policy, Terms and support;
3. prepare a sanitized no-MFA reviewer account and five positive/three negative cases;
4. finish response-minimization, security/privacy, SLO and incident-readiness review;
5. complete domain verification, Portal Tool Scan and explicit internal Go/No-Go;
6. submit for OpenAI review, resolve feedback and publish only after a separate approval.
