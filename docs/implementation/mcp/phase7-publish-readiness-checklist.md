# Phase 7 Publish Readiness Checklist

Status: **In progress**

Started: 2026-08-06

Scope: Prepare Projects-001 Product MCP for OpenAI Plugin review and a later
explicit publish decision. Phase 6 Beta qualification is complete; Phase 7 does
not authorize submission, production mutation or public publication until the
approval gates in this checklist are signed.

## 1. Current release baseline

- [x] Phase 6 release decision is `GO` in
      [`phase6-beta-release-evidence.md`](./phase6-beta-release-evidence.md).
- [x] Product MCP release is `0.6.0`.
- [x] Backend golden revision is `projects-001-be-beta-00019-wwg` at immutable
      digest `sha256:45e16147b3a11f620926bad5b369af0ff4292fea8b72752907c127d649491879`.
- [x] MCP golden revision is `projects-001-mcp-beta-00003-p44` at immutable
      digest `sha256:99330446496e29de09fe138f0b554ba21c00f14deaca57c730bbaa1ad0ee78f8`.
- [x] 37 read-only tools across 10 domains passed Phase 6 discovery and
      callability checks.
- [x] The golden Backend/MCP pair is recorded as the rollback baseline for any
      Phase 7 deployment.
- [ ] Record the source commit/build provenance that produced both immutable
      images in the private release ticket.
- [ ] Freeze tool names, schemas, annotations and skill instructions for the
      submission candidate; any later change requires re-test and **Scan Tools**.

## 2. Endpoint decision

Decision `P7-ENDPOINT-001`:

```text
URL type: Universal
MCP URL: https://projects-001-mcp-beta-bsrqi3xjcq-as.a.run.app/mcp
Custom domain: Deferred until a later business decision
```

- [x] Keep the existing public HTTPS Cloud Run endpoint for the initial Phase 7
      preparation and draft work.
- [x] Use **Universal**, because one fixed MCP URL currently serves all approved
      users and organizations.
- [x] Buying/configuring a custom domain is deferred and is not required to
      start the checklist.
- [ ] Before **Submit for Review**, the Product and Security owners must certify
      that this endpoint is the production service, not a testing endpoint, and
      that it meets the public support/SLO commitments. The current `beta` name
      makes this an explicit final-submission gate.
- [ ] Keep the endpoint publicly reachable for the whole review period.
- [ ] Implement and validate the exact domain-verification response at
      `/.well-known/openai-apps-challenge` when the Portal issues its token; the
      route must return only that token.
- [ ] Re-run OAuth metadata, PKCE, `resource`, issuer/audience and CIMD checks
      against the exact submitted URL.
- [ ] Record an endpoint-change policy. If origin or tool metadata changes,
      reassess domain verification, authentication, tests and Tool Scan.

## 3. Publisher and Platform access

- [ ] Choose the public publisher name: verified individual or verified
      business.
- [ ] Complete the matching identity verification in OpenAI Platform
      organization settings.
- [ ] Confirm the submitting account has `api.apps.write`.
- [ ] Confirm reviewers/status owners have `api.apps.read`.
- [ ] Record the OpenAI Platform organization ID and responsible owner in the
      private release ticket, not in this repository.

## 4. Public listing package

- [ ] Final Plugin name is customer-facing and production-ready.
- [ ] Short description is concise and within Portal limits.
- [ ] Long description accurately describes read-only project, BOQ, finance,
      document and operations workflows.
- [ ] Developer/publisher identity exactly matches the verified identity.
- [ ] Select final category.
- [ ] Prepare production logo and brand assets.
- [ ] Publish a public HTTPS website URL.
- [ ] Publish a public HTTPS support URL.
- [ ] Publish a public HTTPS Privacy Policy URL.
- [ ] Publish a public HTTPS Terms of Service URL.
- [ ] Confirm all listing claims match actual tools, permissions and supported
      workflows.
- [ ] Prepare no more than three high-value starter prompts and validate them on
      the submitted candidate.

## 5. Authentication and reviewer environment

- [x] Phase 6 ChatGPT OAuth and CIMD compatibility passed.
- [x] Qualified ChatGPT CIMD identifier is recorded without OAuth secrets.
- [ ] Create a dedicated reviewer/demo account that does not expose real
      customer or Beta pilot data.
- [ ] Reviewer sign-in must not require MFA, SMS, email confirmation, private
      network access or manual administrator intervention.
- [ ] Provide stable, non-expiring review credentials through the Portal's
      private review field only.
- [ ] Seed deterministic sanitized projects, BOQ versions, finance summaries,
      documents and operations data needed by every submitted test case.
- [ ] Verify the reviewer account has only the minimum permissions required for
      the documented workflows.
- [ ] Test account disable/revoke and deletion procedures.

## 6. Tools, skills and response review

- [x] All 37 tools are read-only for business data.
- [x] Baseline annotations are `readOnlyHint=true`, `openWorldHint=false` and
      `destructiveHint=false`.
- [ ] Audit every tool name, description, input schema and output structure for
      clarity and exact behavioral alignment.
- [ ] Add output schemas where they materially improve reviewer/model
      understanding.
- [ ] Audit all tool responses for data minimization. Remove unnecessary
      request IDs, trace/session IDs, internal account IDs, timestamps,
      telemetry, debug payloads and logging metadata.
- [ ] Confirm no tool returns tokens, secrets, signed URLs, raw credentials,
      internal storage paths or undisclosed personal-data fields.
- [ ] Confirm sensitive-document reads remain permission-gated, bounded,
      redacted and mandatory-audited.
- [ ] Confirm no tool requests or reconstructs a complete ChatGPT conversation.
- [ ] Validate the bundled workflow skill and every referenced file/asset.
- [ ] Run the Portal **Scan Tools** action and review all discovered tools,
      imported skills, domains, warnings and errors.
- [ ] Fix every blocking validation error, deploy the approved fix, re-run the
      full affected test scope and scan again.

## 7. Privacy, legal and user control

- [x] Internal Beta privacy notice exists in
      [`phase6-privacy-notice.md`](./phase6-privacy-notice.md).
- [ ] Convert the notice into a public Privacy Policy reviewed for the intended
      countries/regions.
- [ ] Disclose every category of personal/user-related data collected,
      processed or returned, its purpose and legal basis where applicable.
- [ ] Disclose data recipients/processors, including OpenAI/ChatGPT and relevant
      Projects-001 infrastructure providers.
- [ ] Publish retention timelines and deletion procedures.
- [ ] Document access, correction, deletion and consent-withdrawal controls.
- [ ] Publish Terms of Service covering eligibility, acceptable use, service
      limitations and support boundaries.
- [ ] Confirm restricted data is neither requested nor returned.
- [ ] Complete final PDPA/privacy review and record approval.

## 8. Support, revocation and operations

- [x] Phase 6 immediate revoke/unbind behavior passed.
- [x] Phase 6 rollback and restoration procedure passed.
- [ ] Publish user instructions for connection, consent, disconnection and
      revocation.
- [ ] Publish support intake instructions and support response targets.
- [ ] Name primary and backup contacts for Release, OAuth, GCP, Security/Privacy
      and Customer Support in the private release ticket.
- [ ] Review Beta evidence and set public SLOs for availability, simple reads,
      document/operations reads and incident response.
- [ ] Configure ongoing availability, latency, OAuth-failure and error-rate
      monitoring for the submitted revisions.
- [ ] Complete a clean observation window for the final submission candidate.
- [ ] Re-run rollback/restore after any Phase 7 deployment or runtime-config
      change.
- [ ] Exercise OAuth client/issuer rotation, audit outage, source outage and
      suspected-data-exposure runbooks.
- [ ] Define public deprecation and incident-communication procedures.

## 9. Reviewer test package

Prepare test cases that require no internal company context.

### Positive cases — minimum five

- [ ] P-01: List only the reviewer's authorized projects.
- [ ] P-02: Summarize one project with sources and freshness.
- [ ] P-03: Return the current BOQ version and budget summary.
- [ ] P-04: Compare two deterministic BOQ versions.
- [ ] P-05: Summarize overdue inspections and related daily-report evidence.
- [ ] For each positive case, record the prompt, expected tool/skill sequence,
      expected result shape and exact sanitized fixture requirements.

### Negative cases — minimum three

- [ ] N-01: Request an unassigned project; expect
      `NOT_FOUND_OR_FORBIDDEN` without record enumeration.
- [ ] N-02: Request a business-data mutation; expect no write action and a clear
      read-only boundary.
- [ ] N-03: Use a revoked/unbound account; expect immediate denial.
- [ ] For each negative case, record the prompt/scenario, expected refusal or
      safe fallback and why the Plugin must not complete the action.

### Final test execution

- [ ] Run all submitted cases on every supported ChatGPT/Codex surface selected
      for publication.
- [ ] Confirm the provided reviewer account can reproduce every case without
      additional setup.
- [ ] Record exact expected versus actual results and resolve every mismatch.
- [ ] Confirm results contain no irrelevant personal identifiers or debug data.

## 10. Submission Portal

- [ ] Create the Plugin draft at `https://platform.openai.com/plugins` using
      **With MCP**.
- [ ] Complete Info, MCP, Skills, Prompts, Testing and Global sections.
- [ ] Enter the selected Universal MCP URL and reviewer-ready auth details.
- [ ] Complete domain verification.
- [ ] Run **Scan Tools** after the final deployment and confirm zero blocking
      errors.
- [ ] Select only countries/regions where product, support and legal terms are
      ready.
- [ ] Prepare release notes explaining the initial release, reviewer data and
      any setup expectations.
- [ ] Complete policy attestations only after all listing, server, skill, test
      and availability information is verified.
- [ ] Capture the immutable release candidate and final evidence snapshot before
      submission.

## 11. Required approval gates

All rows must be approved before **Submit for Review**.

| Gate | Required decision | Approver | Status |
|---|---|---|---|
| Product/business packaging | Audience, countries, support model and pricing/product packaging accepted | Product/Business Owner | Pending |
| Endpoint | Existing Cloud Run endpoint explicitly accepted as production, or replacement endpoint qualified | Product + Operations | Pending |
| Security | No open Critical/High; auth, tool hints, data minimization and incident controls approved | Security Owner | Pending |
| Privacy/legal | Public Privacy Policy, Terms, retention/deletion and regional availability approved | Privacy/Legal Owner | Pending |
| Operations | SLO, monitoring, on-call, support and rollback readiness approved | Operations Owner | Pending |
| Release | Exact revision/digest, Portal scan, tests and release notes accepted | Release Owner | Pending |

Submission does not equal publication. After OpenAI approves the Plugin, the
Product, Security/Privacy and Release owners must make a second explicit
**Publish** decision.

## 12. Recommended Phase 7 work packages

These IDs extend the implementation-plan checklist; they are recommendations
for tracking and are not existing OpenAI identifiers.

| ID | Work package | Done when |
|---|---|---|
| MCP-410 | Freeze Phase 6 release | Candidate revisions, digests, provenance and rollback baseline are locked |
| MCP-411 | Publisher/listing package | Verified publisher, listing copy, assets and four public URLs are ready |
| MCP-412 | Privacy/security/support package | Public policies, response audit, support and incident controls are approved |
| MCP-413 | Reviewer environment and tests | Sanitized no-MFA account plus five positive/three negative cases pass |
| MCP-414 | Portal draft and validation | Domain verified; Tools/Skills scan has zero blocking errors |
| MCP-415 | Internal Go/No-Go | All approval-gate rows are signed |
| MCP-416 | Review and publish | Review feedback resolved and explicit publish approval recorded |

## 13. Exit criteria

Phase 7 is complete only when:

- all required checklist items are checked;
- the exact production endpoint and immutable release candidate are frozen;
- reviewer credentials and all submitted tests pass;
- Portal validation and Tool Scan have no blocking errors;
- Business, Endpoint, Security, Privacy/Legal, Operations and Release gates are
  approved;
- OpenAI review is approved; and
- a separate explicit publish decision is recorded.

## Official references

- [Submit plugins](https://developers.openai.com/plugins/deploy/submission)
- [MCP server review requirements](https://developers.openai.com/plugins/deploy/app-review)
- [Plugin guidelines](https://developers.openai.com/plugins/app-guidelines)
- [Plugin submission errors](https://developers.openai.com/plugins/deploy/submission-errors)

