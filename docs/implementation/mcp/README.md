# Product MCP implementation workspace

This directory contains the execution artifacts for the approved
[`mcp-product-implementation-plan.md`](../mcp-product-implementation-plan.md).
The planning baseline remains immutable; implementation status is tracked here.

## Current tranche

| Phase | Status | Notes |
|---|---|---|
| Phase 0 — contracts and ADRs | Complete | Auth0 compatibility spike proven in Demo; the temporary RFC 9207 response-issuer workaround is recorded in the release evidence |
| Phase 1 — Demo foundation | Complete | Isolated IAM, deployment, OAuth, audit and rollback gates passed in Demo |
| Phase 2 — Core Business Owner Pilot | Complete | All Demo gates passed, including MCP Inspector and direct Codex Owner flows |
| Phase 3 — Finance and Document Gateway | Complete in Demo | Seven public tools and eight Backend contracts deployed; Owner, audit, privacy and latency gates passed |
| Phase 4 — Project Operations and Product Audit | Complete in Demo | Ten tools, 27 Backend contracts, exact audit view, rollback and p95 gates passed |
| Phase 5 — Curated GCP Operations and Internal Chat | Complete in Demo | Operational/IAM, Owner/Admin external-MCP, Internal Chat parity, audit, latency and rollback gates passed |
| Phase 6 — Private Plugin and Beta | Complete in Beta | ChatGPT OAuth/CIMD, 37-tool qualification, Owner/Admin scope, revocation, audit and rollback gates passed; exact revisions/digests are frozen in release evidence |
| Phase 7 — Publish readiness | In progress | Endpoint decision recorded; listing, legal/privacy, reviewer, Portal and explicit approval gates remain |

## Phase 0 artifacts

- [Source-to-tool matrix](source-to-tool-matrix.md)
- [Tool contract rules](tool-contracts-v1.md)
- [Authorization matrix](authorization-matrix.md)
- [Threat model](threat-model.md)
- [Work packages](work-packages.md)
- [Backend Core read contracts v1](backend-core-read-contracts-v1.md)
- [Backend Finance and Document read contracts v1](backend-finance-document-contracts-v1.md)
- [Backend Project Operations and Product Audit contracts v1](backend-project-operations-contracts-v1.md)
- [Backend GCP Operations and Internal Chat contracts v1](backend-gcp-operations-contracts-v1.md)
- ADRs in [`adr/`](adr/)
- Machine-readable tool input schemas in
  `Projects-001-MCP/contracts/tool-input-schemas-v1.json`
- Sanitized evaluation cases in
  `Projects-001-MCP/tests/evals/golden-evaluation-set-v1.json`
- Reproducible Phase 2 evaluator in
  `Projects-001-MCP/tests/evals/phase2_evaluator.py`
- Reproducible Phase 3 evaluator in
  `Projects-001-MCP/tests/evals/phase3_evaluator.py`
- Reproducible Phase 4 and Phase 5 evaluators in
  `Projects-001-MCP/tests/evals/phase4_evaluator.py` and
  `Projects-001-MCP/tests/evals/phase5_evaluator.py`
- Reproducible Phase 6 repository/live-boundary evaluator in
  `Projects-001-MCP/tests/evals/phase6_evaluator.py`
- [Demo release evidence](phase2-demo-release-evidence.md)
- [Phase 3 repository evidence](phase3-repository-evidence.md)
- [Phase 3 Demo release evidence](phase3-demo-release-evidence.md)
- [Phase 4 repository evidence](phase4-repository-evidence.md)
- [Phase 4 Demo release evidence](phase4-demo-release-evidence.md)
- [Phase 5 repository evidence](phase5-repository-evidence.md)
- [Phase 5 Demo release evidence checklist](phase5-demo-release-evidence.md)
- [Phase 6 repository evidence](phase6-repository-evidence.md)
- [Phase 6 Beta release evidence](phase6-beta-release-evidence.md)
- [Phase 7 publish-readiness checklist](phase7-publish-readiness-checklist.md)
- [Phase 6 Beta runbook](phase6-beta-runbook.md)
- [Product MCP privacy notice](phase6-privacy-notice.md)
- [Private Plugin user guide](../../User_Manual_MCP_Private_Plugin.md)

## Guardrails

- The MCP is a separate service and never imports backend source code.
- Business data is read-only. Audit, security logs, metrics and traces are the
  only permitted technical writes.
- The inbound MCP OAuth token is never forwarded to the Product Backend.
- Backend policy is authoritative on every tool call; token roles are hints only.
- No tool accepts an environment, raw SQL, Firestore path, GCS path, log query,
  secret name, or arbitrary URL.
- Missing backend read contracts fail closed instead of falling back to broad
  access.

## Repository verification

- 131 MCP tests cover protocol metadata/init, OAuth vectors, environment
  isolation, Backend delegation, all 37 tool contracts, exact business data,
  Product/operational audit boundaries, GCP allowlists, Admin matrices,
  redaction/outage behavior, private plugin packaging and Beta release policy.
- 114 Backend tests cover service identity, per-call entitlement/revocation,
  project scope, exact shared Chat facts, signed cursors, BOQ/Finance money,
  Document Gateway controls and safe processing status.
- Ruff passes for all MCP code/tests and every changed Backend file. Python
  byte-compilation passes for the changed service and route modules.
- Full Backend Ruff still reports eight pre-existing findings in unrelated
  untouched files; Phase 6 changes no Backend source.
- Both production containers build; the MCP image runs as a non-root user.
- Container smoke tests return `200` for the public no-data `/health` route and
  `401` plus protected-resource metadata for unauthenticated `/mcp` initialize.
- `deploy_mcp.sh` is syntax-valid and stops before cloud operations when the
  required environment-specific configuration is absent.

Repository verification is supplemented by the environment-specific release
evidence above. The final Phase 6 Beta release is the immutable Backend/MCP pair
recorded in `phase6-beta-release-evidence.md`; controlled ChatGPT Owner/Admin,
authorization, revocation, performance, audit and rollback gates passed. Phase 7
publication remains separately gated by the publish-readiness checklist and
explicit business, security/privacy, operations and release approval.
