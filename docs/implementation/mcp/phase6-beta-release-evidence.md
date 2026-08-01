# Phase 6 Beta release evidence

Evidence date: 2026-08-01

Environment: Beta (`project001-489710`, `asia-southeast1`)

Status: **Blocked before provisioning/deployment**. Repository work is in
progress/validation, but this file does not authorize a GCP write or rollout.

## Entry gates

| Gate | Evidence | Status |
|---|---|---|
| Phase 5 Demo release | `phase5-demo-release-evidence.md` still contains required pending rows | Blocked |
| Critical/High findings | Attach final security review with zero open Critical/High | Pending |
| Named incident contacts | Record named release, OAuth, GCP, security/privacy and support contacts in private ticket | Pending |
| Tested immutable image | Build Phase 6 in Demo and record exact approved digest | Pending |
| Plugin package | Manifest and bundled workflow skill validate; live ChatGPT app binding intentionally absent | Repository pass / live pending |

## Read-only Beta inventory

Observed 2026-08-01 with bounded metadata reads:

| Resource | Evidence | Status |
|---|---|---|
| Backend | `projects-001-be-beta-00015-rfc` ready | Present |
| Frontend | `projects-001-fe-beta-00016-nww` ready | Present |
| MCP service | No `projects-001-mcp-beta` service returned | Missing |
| MCP service account | Exact `projects-001-mcp-beta@...` describe returned `NOT_FOUND` | Missing |
| Cloud SQL | `project-001-beta`, `asia-southeast1`, `RUNNABLE` | Present |
| Firestore | `prod-beta`, `asia-southeast1`, Firestore Native | Present |
| Storage | All five configured Beta buckets returned | Present; IAM preflight pending |
| Product Audit bucket | Exact `projects-001-mcp-audit-beta` describe returned `NOT_FOUND` | Missing |
| Operational bucket | Exact `projects-001-mcp-ops-beta` describe returned `NOT_FOUND` | Missing |
| Phase 6 image | Registry contains earlier Demo images only; no image contains the uncommitted Phase 6 code | Missing |

No resource was created or modified by this inventory.

## Beta preflight and deployment

| Gate | Required evidence | Status |
|---|---|---|
| Exact environment config | `deploy_mcp.sh --preflight-only` passes with no placeholder/secret in tracked files | Pending |
| Dedicated identity | Exact Beta SA; no key; no broad role; only compiled resource/view access | Blocked: SA missing |
| Audit routing | 365-day bucket, exact sink/view/filter and view IAM | Blocked: bucket missing |
| Operational routing | 30-day bucket, exact sink/view/filter and view IAM | Blocked: bucket missing |
| Image promotion | Exact Demo-tested `@sha256:` digest exists and is selected | Pending |
| Deploy | `projects-001-mcp-beta` healthy; unauthenticated initialize = `401` | Pending |
| Rollback | Previous revision retained; rollback/restore and Owner read verified | Pending |

## Private Plugin compatibility

| Gate | Required evidence | Status |
|---|---|---|
| Developer-mode registration | Stable Beta `/mcp` registered and real `plugin_asdk_app...` ID recorded privately | Pending |
| OAuth | Protected-resource/auth-server metadata, PKCE, scope/resource and Beta claim pass | Pending |
| Package binding | Release copy passes `private_plugin validate --require-bound` | Pending |
| Tool inventory | 37 tools; closed schemas; `Read`/non-destructive/non-open-world annotations | Pending live |
| Workflow skill | Direct, indirect, follow-up, negative and boundary cases select correct tools | Pending live |
| Privacy/consent | Notice acknowledged before linking; external retention understood | Pending |

## Security, quality and performance gates

| Gate | Target | Status |
|---|---:|---|
| Unauthorized/cross-environment access | 0 | Pending |
| Business mutation | 0 | Pending |
| Secret/token/private-key/signed-URL leakage | 0 | Pending |
| Sensitive and denied/security audit coverage | 100% | Pending |
| Finance/version fixture accuracy | 100% | Pending |
| Released evaluation scenarios | >=95% | Pending |
| Simple-read p95 | <=5 seconds | Pending |
| Document/operations p95 | <=15 seconds | Pending |
| Unbounded/unclear partial responses | 0 | Pending |

## Controlled cohort

| Stage | Evidence | Status |
|---|---|---|
| One Owner | Consent, allowed facts, denied scope, audit and next-call revoke | Pending |
| Selected Admin 1 | Assigned-project/domain allow/deny and next-call revoke | Pending |
| Selected Admin 2+ | Add only after previous Admin passes and incident window is clean | Pending |

## Release decision

**NO-GO.** Repository implementation does not close the missing Phase 5 evidence
or absent Beta identity/logging/MCP resources. Provisioning, IAM changes,
deployment, ChatGPT connection registration, and cohort rollout each require
explicit approval and recorded evidence under the runbook.
