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
| MCP-100 | Service scaffold | Complete locally | `Projects-001-MCP/`; container build passes |
| MCP-101 | Streamable HTTP `/mcp` | Complete locally | protocol and container smoke tests pass; live Inspector pending |
| MCP-102 | Config/environment lock | Complete locally | config tests and deployment fail-closed preflight pass |
| MCP-103 | OAuth validation | Complete locally | JWT/scope vectors pass; live OAuth proof pending |
| MCP-104 | Policy client/enforcement | Complete locally | Backend re-resolves the principal on every policy and data read |
| MCP-105 | Audit/metrics separation | Complete locally | redaction/outage tests pass; Cloud Logging sink/retention pending |
| MCP-106 | Demo service account/IAM | Blocked by live provisioning approval | no repository-only substitute |
| MCP-107 | Demo deploy/preflight | Complete locally | templates/script/smokes ready; real config and deployment approval pending |
| MCP-200 | Discovery + standard search/fetch | Complete for Core Pilot | Bounded Projects/BOQ federated adapter and stable fetch references |
| MCP-210 | Projects/BOQ/version tools | Complete locally | Current, manifest, version, as-of and comparison contracts |
| MCP-220 | Users/Access tools | Complete locally | Minimized project/user access views; sensitive audit required |
| MCP-230–MCP-280 | Later domain tools | Not started | Phases 3–5 in the approved plan |
| MCP-300 | Backend internal read contracts | Complete for Phase 2 scope | Versioned service-authenticated `/api/v1/internal/mcp/*` contracts |
| MCP-301 | MCP Product authorization fields | Complete locally | Fail-closed entitlements, unique OAuth binding, per-call memberships |
| MCP-302 | Owner/Admin settings and revocation | Backend complete; UI/pilot pending | Owner-only mutation endpoints support enable, revoke and unbind |
| MCP-303 | Internal Chat adapter | Not started | Planned after external contracts stabilize |
| MCP-304 | Product citation/document routes | Core citations complete | Project URLs implemented; Document Gateway remains Phase 3 |
| MCP-400 | Golden Evaluation Set | Fixtures complete; live evaluation pending | Owner client run and ≥95% gate not yet evidenced |
| MCP-401 | Contract tests | Complete for repository Phase 2 scope | Backend and MCP suites pass |
| MCP-402 | Authorization/isolation tests | Complete locally; live IAM test pending | Cross-project denial, owner cohort and environment tests pass |
| MCP-403 | Security/redaction tests | Complete for implemented scope | Full document/security suite expands in Phase 3 |
| MCP-404 | Performance/failure tests | Failure/rate-limit paths covered; load baseline pending | p95 target and distributed quota evidence require deployed Demo |
| MCP-405–MCP-409 | Pilots and rollout | Not started | Require explicit live provisioning/deployment approval |

## Remaining backend contract gaps

1. Existing Dashboard, Insight and Finance Admin routes do not consistently
   apply assigned-project scope; their MCP contracts remain unimplemented.
2. Existing financial schemas serialize canonical money as floats.
3. Existing file endpoints return signed URLs/storage keys and are therefore not
   suitable for the Document Content Gateway.
4. Existing Daily Report share-link details are not a status-only MCP contract.
5. No Product Audit query contract/view exists.

Phase 2 closes the access-context, entitlement, project-scope and BOQ version
gaps. The remaining items must be implemented as versioned Backend read
contracts before their dependent domain tools are released.
