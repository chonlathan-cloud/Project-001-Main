# Phase 6 Beta release evidence

Evidence date: 2026-08-03

Environment: Beta (`project001-489710`, `asia-southeast1`)

Status: **Blocked before provisioning/deployment**. Repository work is in
progress/validation, but this file does not authorize a GCP write or rollout.

## Entry gates

| Gate | Evidence | Status |
|---|---|---|
| Phase 5 Demo release | All required live rows in `phase5-demo-release-evidence.md` are passed with sanitized evidence | Passed |
| Critical/High findings | Attach final security review with zero open Critical/High | Pending |
| Named incident contacts | Record named release, OAuth, GCP, security/privacy and support contacts in private ticket | Pending |
| Tested immutable image | Commit `2415f97` deployed as MCP `0.6.0`; promotion digest `sha256:3aa32fc5cf14e38798e6cdeaba5f0ba04bf6b2276f488015263604da9b5bff97` recorded after Demo validation | Demo passed |
| Plugin package | Manifest and bundled workflow skill validate; an ignored release copy validates as bound without storing or exposing its private app ID in tracked evidence | Demo passed / Beta pending |

## Demo qualification evidence

| Gate | Sanitized evidence | Status |
|---|---|---|
| Candidate | Revision `projects-001-mcp-00013-p9v` reports `0.6.0`, exposes 37 read-only tools and serves 100% traffic | Passed |
| Owner flow | Real ChatGPT Owner connection initialized and completed access, project, finance and BOQ reads through the candidate | Passed |
| Admin and revocation | Phase 5 assigned-project allow/deny and next-call revoke passed; final directory state is unbound and requires a new Owner grant | Passed |
| Bound release copy | Ignored release copy validates with `private_plugin validate --require-bound`; tracked source package remains unbound and shareable | Passed |
| Performance and audit | 6/6 candidate calls succeeded, p95/max 498 ms; sensitive audit pairing 1/1; leakage and unexpected Backend/MCP error matches were zero | Passed |
| Rollback/restore | Prior `0.5.0` revision stayed healthy with unauthenticated initialize `401`; candidate restored to 100% and Owner reads succeeded | Passed |
| Immutable digests | Promotion digest is recorded above; executed Cloud Run platform digest is `sha256:35f7e2fe1d6f0de0a6a3be8f8d41a221149df2f669a7a948205b20fbe4c1d15d` | Passed |

These facts qualify only the Demo image and compatibility package. No Beta
resource, IAM binding, service, traffic or private connection was created or
changed during this qualification.

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
| Phase 6 image | Exact Demo-tested promotion digest is recorded above; it has not been promoted or deployed to Beta | Demo present / Beta pending |

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

**NO-GO for Beta.** Phase 5 Demo evidence and the Phase 6 Demo image/plugin
qualification are complete, but the Beta identity, logging buckets/views and MCP
service remain absent. Beta preflight, digest promotion, deployment, stable
ChatGPT connection registration and cohort rollout each require explicit
approval and recorded evidence under the runbook.
