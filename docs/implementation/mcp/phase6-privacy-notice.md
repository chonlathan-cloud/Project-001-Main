# Product MCP privacy notice

Status: Phase 6 Beta notice; requires Product/legal approval before controlled
Beta rollout.

## Purpose and controller

Projects-001 Product MCP gives approved workspace users read-only access to the
Projects-001 records they are already authorized to view. The Product Owner
controls Product access, scopes, and revocation. OpenAI/ChatGPT processes the
content delivered to the user's approved workspace under that workspace's
applicable terms and privacy controls.

## Data that may be processed

Depending on the user's request and Product permissions, bounded responses may
include:

- project and membership metadata;
- BOQ versions and exact financial/payment facts;
- document metadata and authorized bounded extraction text;
- inspection and daily-report facts;
- dashboard calculations, source health, and processing status;
- minimized Product Audit or curated application-error metadata.

The MCP does not request a full ChatGPT conversation, raw location, passwords,
API keys, MFA/OTP values, payment-card data, arbitrary GCS paths, signed URLs,
Secret Manager payloads, raw SQL, or raw Cloud Logging queries.

## Minimization and access control

- OAuth requires the coarse `mcp:read` scope; Product permissions remain the
  final authority.
- The Backend re-resolves active status, external-MCP enablement, role,
  permissions, and project scope for every tool call.
- Tools use closed inputs, bounded lists/content, and allowlisted sources.
- Sensitive document access is audited and fails closed when mandatory audit
  emission is unavailable.
- Responses omit credentials, tokens, storage paths, signed URLs, prompts, full
  response bodies, and unnecessary internal identifiers.

## Logging and retention

Product MCP does not persist full prompts or full responses. Product Audit and
security events contain allowlisted metadata only. Retention is:

- Demo Product Audit/security: 90 days;
- Beta Product Audit/security: 365 days;
- operational error logs: 30 days; and
- non-PII service metrics: up to 13 months under the implementation plan.

ChatGPT conversation retention is separate from Product MCP logging and is
governed by the approved workspace configuration and OpenAI terms.

## Consent and revocation

Before linking, the user must see the requested OAuth scope and this notice.
The Owner records the exact OAuth issuer/subject binding in Product Settings.
The Owner can use **Revoke & unbind** to clear Product enablement, binding, and
permissions; the next MCP tool call is denied. The OAuth grant and ChatGPT
plugin installation should also be revoked/disabled to end client-side access.

## Data correction, deletion, and incidents

Business-record correction or deletion must use the authorized Product
workflow; the MCP cannot mutate records. Product Audit retention is governed by
the fixed environment policy and should not be selectively shortened to hide an
event. For suspected disclosure, disable the affected Product binding and
plugin cohort, revoke OAuth, preserve minimized audit evidence, and follow the
[Phase 6 Beta runbook](phase6-beta-runbook.md).

This notice implements the minimization, explicit-consent, and least-privilege
principles in OpenAI's
[plugin guidelines](https://developers.openai.com/plugins/app-guidelines) and
[security and privacy guide](https://developers.openai.com/plugins/guides/security-privacy).
