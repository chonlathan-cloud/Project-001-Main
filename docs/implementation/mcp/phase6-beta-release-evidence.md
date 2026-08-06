# Phase 6 Beta release evidence

Evidence date: 2026-08-06

Environment: Beta (`project001-489710`, `asia-southeast1`)

Release: Product MCP `0.6.0`

Status: **GO — Phase 6 Beta qualification is complete.** The controlled Owner
and Admin qualification, project-scope enforcement, immediate revocation,
negative cases, ChatGPT OAuth/CIMD compatibility, 37-tool discovery/callability,
audit and rollback gates passed. Phase 7 publish-readiness work may begin.

This document retains only release metadata and sanitized results. OAuth tokens,
test-account email addresses, raw project identifiers, request bodies and
private records remain outside the tracked repository.

## Evidence basis

| Evidence type | Source | Recorded result |
|---|---|---|
| Live runtime metadata | Read-only Cloud Run service/revision inspection on 2026-08-06 | Current traffic, Ready state and immutable image digests verified |
| Live bounded observation | Cloud Logging entries after the final Backend revision became ready | Current Backend/MCP revisions returned successful traffic with zero sampled severity-`ERROR` entries |
| ChatGPT acceptance | Release Owner confirmation after reconnecting the Beta Plugin | OAuth, access resolution, project and BOQ workflows passed |
| Controlled authorization suite | Phase 6 Owner/Admin pilot and release tests | Owner/Admin allow/deny, project scope, revoke and negative cases passed |
| Repository qualification | Product MCP release/contract/evaluation suites | Version `0.6.0`, 10 domains and 37 read-only tools passed |

## Final release identity and immutable artifacts

| Component | Qualified release | Immutable image digest | Live state |
|---|---|---|---|
| Backend | `projects-001-be-beta-00019-wwg` | `sha256:45e16147b3a11f620926bad5b369af0ff4292fea8b72752907c127d649491879` | Ready; 100% traffic |
| Product MCP | `projects-001-mcp-beta-00003-p44` | `sha256:99330446496e29de09fe138f0b554ba21c00f14deaca57c730bbaa1ad0ee78f8` | Ready; 100% traffic |

Qualified MCP endpoint:

```text
https://projects-001-mcp-beta-bsrqi3xjcq-as.a.run.app/mcp
```

The Phase 6 golden rollback baseline for any later deployment is the exact pair
`projects-001-be-beta-00019-wwg` and
`projects-001-mcp-beta-00003-p44` with the digests above.

## ChatGPT OAuth and CIMD acceptance

| Client | Identifier used by the qualified release | Result |
|---|---|---|
| MCP Inspector Beta | `wc4ipi5dqC4j9nSuBKL6YWJJojZVOmy1` | Passed |
| ChatGPT Native OAuth client | `tpc_b1XfQAEGyhXACjeQbWt6Bt` | Passed |
| ChatGPT dynamic client metadata (CIMD) | `https://chatgpt.com/oauth/wFY4YkVuvIZ-/client.json` | Passed; this was the missing identifier required by the working ChatGPT connection |

The final Backend revision admits `owner,admin` and includes the qualified
ChatGPT CIMD identifier in `MCP_ALLOWED_CLIENT_IDS`. The real registered Plugin
connection identifier remains outside this tracked evidence.

## Owner qualification

| Scenario | Expected result | Final result |
|---|---|---|
| OAuth and initialization | Authorized Beta Owner completes OAuth and initializes MCP | Passed |
| Current access | `role=owner`, external MCP enabled, all-project access and `mcp_access` resolved from Product authorization | Passed |
| Project discovery | Return only projects currently authorized for the Owner | Passed |
| Project summary | Return the authorized Beta project summary with source/freshness metadata | Passed |
| Current BOQ and version history | Return the current BOQ plus authorized immutable version information | Passed |
| Business-data mutation | No mutation tool is exposed and no business record is changed | Passed |

## Admin scope qualification

The controlled Admin pilot used an active Admin with explicit MCP permissions
and `mcp_all_projects_read=false`.

| Scenario | Expected result | Final result |
|---|---|---|
| Assigned project read | Authorized Admin can read the single assigned project | Passed |
| Unassigned project read | Return `NOT_FOUND_OR_FORBIDDEN` without disclosing whether the record exists | Passed |
| Permission boundary | Finance, sensitive-document, audit and infrastructure reads require their exact Product permissions | Passed |
| Restored membership boundary | Restored project remains readable while the formerly assigned project is denied | Passed |
| State restoration | Original binding, permissions and project membership restored after the pilot | Passed |

## Revocation and negative cases

| Negative case | Expected safe behavior | Final result |
|---|---|---|
| Unauthenticated MCP initialization | HTTP `401` | Passed |
| Revoke and unbind between calls | Immediately subsequent call returns `NOT_FOUND_OR_FORBIDDEN` | Passed |
| Admin guessed or unassigned project ID | Return the same non-enumerating `NOT_FOUND_OR_FORBIDDEN` result | Passed |
| Missing domain permission | Deny before the Product source read | Passed |
| Write/mutation request | No write tool is available; no business mutation occurs | Passed |
| Cross-environment identifier | Deny without reading or disclosing records from another environment | Passed |
| Restore after revoke test | Exact approved binding restores current-access and project-list calls | Passed |

## Tool inventory and workflow compatibility

| Gate | Final evidence | Result |
|---|---|---|
| Tool discovery | 10 approved domains and **37/37 tools** discovered in the qualified ChatGPT/MCP connection | Passed |
| Tool callability | All 37 registered tools are callable under their declared schemas; released direct, indirect, follow-up, negative and boundary workflows passed | Passed |
| Input boundary | Closed schemas reject undeclared or conflicting selectors before Backend access | Passed |
| Read-only boundary | All tools are read-only for business data | Passed |
| Tool annotations | `readOnlyHint=true`, `openWorldHint=false`, `destructiveHint=false` match the published tool behavior | Passed |
| Plugin workflow skill | Projects, BOQ, finance, document, operations, audit and GCP workflows select the intended tools | Passed |

## Performance, audit and operational acceptance

| Gate | Evidence | Result |
|---|---|---|
| Simple-read reliability | 60/60 successful qualification calls | Passed |
| Simple-read p95 | 627 ms against the `<=5s` target | Passed |
| Document/operations ceiling | Representative released workflows completed within the `<=15s` target | Passed by final operator acceptance |
| Sensitive audit pairing | Sensitive reads produced the required start/terminal audit pair; sensitive access remains fail-closed on audit outage | Passed by final release suite |
| Leakage | No sampled token, secret, private key, signed URL, prompt/body or direct target UUID leakage | Passed |
| Current MCP observation | 46 bounded log entries after final Backend readiness; 7 HTTP `200`, one expected unauthenticated `401`, zero severity-`ERROR` | Passed |
| Current Backend observation | 124 bounded revision entries; 37 HTTP `200`, zero severity-`ERROR` | Passed |
| Blocking security findings | No open Critical/High finding accepted for the Phase 6 release | Passed by Release Owner acceptance |

The bounded current-revision observation began at
`2026-08-06T04:42:43Z`, when the final Backend revision was created. It is a
release smoke window, not a replacement for ongoing Phase 7 SLO monitoring.

## Rollback record

The existing Cloud Run rollback/restore procedure was exercised during Phase 6:
the retained previous revisions returned healthy service responses, preserved
the unauthenticated `401` boundary and allowed the candidate revisions to be
restored.

| Purpose | Backend revision | MCP revision | Notes |
|---|---|---|---|
| Phase 6 golden rollback baseline for future releases | `projects-001-be-beta-00019-wwg` | `projects-001-mcp-beta-00003-p44` | Exact ChatGPT-qualified pair; use these as rollback targets after a later deployment |
| Immediate retained previous revisions | `projects-001-be-beta-00018-fv9` | `projects-001-mcp-beta-00002-wxr` | Both Ready; emergency fallback only. Backend `00018` predates the final ChatGPT CIMD allowlist and therefore requires ChatGPT connection requalification if used |

Previous MCP revision `projects-001-mcp-beta-00002-wxr` uses immutable digest
`sha256:35f7e2fe1d6f0de0a6a3be8f8d41a221149df2f669a7a948205b20fbe4c1d15d`.
Backend revision `projects-001-be-beta-00018-fv9` uses the same Backend image
digest as the qualified revision, but its runtime client allowlist does not
contain the final working ChatGPT CIMD identifier.

## Release decision and sign-off

**Decision: GO.** Phase 6 is closed. The qualified Beta release is the immutable
Backend/MCP pair recorded above. Phase 7 may prepare the public listing, legal,
privacy, support, production-readiness and submission-review materials. This GO
does not itself authorize public submission or publication.

| Responsibility | Approver | Decision | Date |
|---|---|---|---|
| Product and Release Owner | Chonlathan Wisetwongsa | **GO — Phase 6 accepted** | 2026-08-06 |
| Technical evidence | Repository qualification plus read-only GCP runtime verification | Complete | 2026-08-06 |
