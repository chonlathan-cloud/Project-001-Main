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
| Phases 3–7 | Not started | Follow the approved gates; no cloud promotion was performed |

## Phase 0 artifacts

- [Source-to-tool matrix](source-to-tool-matrix.md)
- [Tool contract rules](tool-contracts-v1.md)
- [Authorization matrix](authorization-matrix.md)
- [Threat model](threat-model.md)
- [Work packages](work-packages.md)
- [Backend Core read contracts v1](backend-core-read-contracts-v1.md)
- ADRs in [`adr/`](adr/)
- Machine-readable tool input schemas in
  `Projects-001-MCP/contracts/tool-input-schemas-v1.json`
- Sanitized evaluation cases in
  `Projects-001-MCP/tests/evals/golden-evaluation-set-v1.json`
- Reproducible Phase 2 evaluator in
  `Projects-001-MCP/tests/evals/phase2_evaluator.py`
- [Demo release evidence](phase2-demo-release-evidence.md)

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

- 45 MCP tests cover protocol metadata/init, OAuth JWT vectors, required scopes,
  environment isolation, Backend service-identity delegation, Product policy,
  Core tool transport, inventory contracts and audit redaction/outage behavior.
- 88 Backend tests cover service identity, entitlement resolution, Owner rollout,
  project-scope sanitation, atomic OAuth bindings, signed cursors, exact BOQ
  money, stable line identity and version comparison.
- Ruff and Python byte-compilation pass.
- The production container builds and runs as a non-root user.
- Container smoke tests return `200` for the public no-data `/health` route and
  `401` plus protected-resource metadata for unauthenticated `/mcp` initialize.
- `deploy_mcp.sh` is syntax-valid and stops before cloud operations when the
  required environment-specific configuration is absent.

No Cloud resources were created or changed as part of repository
implementation.
