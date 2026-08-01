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
| MCP-402 | Authorization/isolation tests | External-MCP live matrix passed; 3 Admin rows remain | Cross-project, six-tool allow, missing-permission denial and next-call disablement passed; explicit grant, unbind and Internal Chat denial remain |
| MCP-403 | Security/redaction tests | Complete through repository Phase 5 scope | Operational query bounds and credential/URL/PII/path/UUID redaction join prior controls |
| MCP-404 | Performance/failure tests | Demo passed; Beta p95 pending | Demo operations p95, audit and rollback gates passed; Beta still requires deployed live evidence |
| MCP-405 | Owner Demo pilot | External-MCP Phase 5 pass; Internal Chat evidence pending | All six operations tools, audit, latency and rollback passed for Owner |
| MCP-406 | Admin Demo pilot | External-MCP matrix passed; 3 rows pending | Allow/deny, cross-project and next-call disablement passed; explicit grant, unbind and Internal Chat denial remain |
| MCP-407 | Private Plugin test | Repository package complete; live test pending | Valid manifest, registered-app binder and bundled workflow skill; Beta connection ID not created |
| MCP-408 | Beta preflight/deploy | Preflight hardened; provisioning/deploy blocked | Exact SA/digest/365-day audit gates implemented; Beta MCP identity/service/log buckets absent |
| MCP-409 | Beta controlled rollout | Not started | Requires Phase 5 closure, Beta deploy, Owner pilot, revoke drill, then selected Admins |

## Remaining release and later-phase gaps

1. Close the seven remaining Phase 5 Demo rows: four Internal Chat consistency
   checks plus Admin explicit grant, unbind and Internal Chat denial.
2. Build and retest Phase 6 in Demo, then record the exact approved image digest.
3. Provision the missing Beta MCP service account, MCP service, 365-day Product
   Audit bucket/sink/view, 30-day operational bucket/sink/view and exact IAM.
4. Run the exact Beta preflight, deploy only after approval, and test rollback.
5. Register/bind/test the private plugin and run the Beta Owner → revoke →
   selected Admin rollout under `phase6-beta-runbook.md`.
