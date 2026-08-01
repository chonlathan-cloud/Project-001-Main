# Phase 6 Private Plugin and Beta runbook

Environment: Beta (`project001-489710`, `asia-southeast1`)

This runbook covers MCP-407 through MCP-409. Repository completion is not live
rollout approval. Stop if Phase 5 Demo evidence has any pending gate, if a
Critical/High finding is open, or if the exact Beta identity/resources fail
preflight.

## Roles and contacts

| Duty | Required contact |
|---|---|
| Release owner / incident commander | Current Projects-001 Owner on call |
| Product authorization and user revocation | Product Owner with Settings access |
| OAuth issuer/client operations | Identity-provider administrator |
| GCP deployment, IAM, Logging and rollback | `project001-489710` platform operator |
| Security/privacy assessment | Designated security/privacy reviewer |
| User support | Projects-001 support owner |

Record the named people and reachable incident channel in the private release
ticket before deployment. Do not put personal phone numbers or credentials in
this repository.

## Required Beta profile

| Resource | Exact selector |
|---|---|
| MCP service | `projects-001-mcp-beta` |
| MCP service account | `projects-001-mcp-beta@project001-489710.iam.gserviceaccount.com` |
| Backend | `projects-001-be-beta` |
| Frontend | `projects-001-fe-beta` |
| Cloud SQL | `project-001-beta` |
| Firestore | `prod-beta` |
| Buckets | the five `*-beta` names in `mcp.deploy.beta.example` |
| Product Audit bucket/view | `projects-001-mcp-audit-beta` / `projects-001-mcp-audit-beta-view` |
| Operational bucket/view | `projects-001-mcp-ops-beta` / `projects-001-mcp-ops-beta-view` |
| Product Audit retention/read window | exactly 365 days |
| Operational retention/read window | exactly 30 days |
| Artifact | exact `projects-001-mcp@sha256:<64 hex>` digest that passed Demo |

The Beta identity may have only the exact Backend invoker, log writer, two log
view-accessor grants, and compiled metadata permissions validated by
`deploy_mcp.sh`. It must not have a user-managed key, broad Editor/Owner,
business-data write roles, Secret payload access, BigQuery access, Demo resource
bindings, or access to the excluded SaaS services.

## Release sequence

1. Close every Phase 5 Demo row and attach the named incident contacts.
2. Run the full Backend, MCP, frontend, container, security, evaluation, and
   compatibility suites. Record zero Critical/High findings.
3. Deploy the candidate in Demo, rerun Owner/Admin/revocation/plugin workflows,
   and record the exact Artifact Registry digest—not only a mutable tag.
4. Prepare untracked `mcp.deploy.beta`, `cloudrun-mcp-beta.env.yaml`, and the
   shared `cloudrun-beta.env`. Never commit OAuth secrets or environment files.
5. Set `MCP_PROMOTED_IMAGE_URI` to the approved Demo digest. Run:

   ```bash
   DEPLOY_SHARED_CONFIG=cloudrun-beta.env \
   MCP_DEPLOY_CONFIG=mcp.deploy.beta \
   ./deploy_mcp.sh --preflight-only
   ```

6. After explicit deployment approval, omit `--preflight-only`. The script
   promotes the digest without rebuilding, records the previous revision,
   checks health, verifies unauthenticated MCP initialization returns `401`,
   and prints the rollback command.
7. Keep every Product account disabled. Connect and test one consenting Owner
   with the private plugin, direct/indirect/follow-up/negative cases, all 37
   tool schemas, p95 targets, audit coverage, and no data leakage.
8. Revoke that Owner and prove the next call is denied. Re-enable only after the
   drill is recorded.
9. Add selected Admins one at a time with `mcp_access`, only required domain
   permissions, and assigned-project scope. Repeat the allow/deny/revoke matrix.
10. Stop expansion on any gate failure. Phase 7/public submission remains a
    separate business, privacy, security, and operations decision.

## Rollback

Keep the previous ready Cloud Run revision. Use the exact command printed by the
deployment helper:

```bash
gcloud run services update-traffic projects-001-mcp-beta \
  --project project001-489710 \
  --region asia-southeast1 \
  --to-revisions=PREVIOUS_READY_REVISION=100
```

After rollback, verify `/health`, unauthenticated `/mcp` = `401`, Owner bounded
read, no new `severity>=ERROR`, and no cross-environment access. Database/data
rollback is unnecessary because MCP has no business writes. Restore the
candidate only after a new release decision.

For OAuth rollback, disable the plugin cohort, revoke affected grants, restore
the previously approved issuer/client configuration, and require a new consent
flow. Never make a breaking tool-schema rollback; retain v1 and use additive
fields or a new version.

## OAuth rotation and revocation

1. Create the replacement Beta OAuth client/metadata without removing the
   current client.
2. Validate protected-resource metadata, authorization-server discovery, PKCE,
   `resource`, redirect URI, scope, short-lived token, and Beta environment
   claim with MCP Inspector.
3. Allowlist the replacement client ID in the Beta Backend and run a single
   Owner consent flow.
4. Rebind the Owner's exact issuer/subject, test, then revoke the old grant and
   remove the old client ID.
5. For emergency revocation, disable and unbind Product access first, then
   revoke OAuth and disable/uninstall the workspace plugin.

## Failure runbooks

### Audit outage

- Disable sensitive-document and Product Audit reads; they must fail closed.
- Keep non-sensitive behavior within ADR-0006 and label any partial result.
- Verify the log writer, sink, bucket, view, IAM, quota, and retention without
  reading secret payloads or document bodies.
- Restore audit emission and prove one denied plus one sensitive event before
  reopening the cohort.

### Source outage or partial result

- Do not add a generic SQL, Firestore, GCS, URL, or Logging fallback.
- Return `SOURCE_UNAVAILABLE` or explicit `partial=true` with source warnings.
- Keep Backend business semantics primary and never silently merge conflicts.
- Retry only bounded, idempotent reads; close the incident after freshness and
  accuracy fixtures pass.

### Suspected data exposure

1. Disable the affected Product binding and private-plugin share group.
2. Revoke OAuth grants and rotate compromised credentials/clients through the
   identity-provider process.
3. Preserve minimized audit/security evidence and identify the exact subject,
   time range, tools, and opaque record IDs. Do not copy document bodies into
   the incident ticket.
4. Inspect allowlisted MCP/Backend logs and IAM changes; include no SaaS scope.
5. Notify the release owner and security/privacy reviewer, assess obligations,
   remediate, and require a fresh consent flow before reactivation.

## Support triage

Use the symptom table in the
[Private Plugin user guide](../../User_Manual_MCP_Private_Plugin.md). Start with
protected-resource metadata and OAuth discovery, then Product enablement,
issuer/subject binding, permissions, project assignment, and source status. Do
not solve authorization errors by broadening IAM or returning hidden IDs.

## Data retention and deletion

Beta Product Audit/security events retain allowlisted metadata for 365 days;
operational logs retain 30 days. Business data remains in its authoritative
Product store and follows the Product deletion process. Chat history is
separate. User revocation blocks future reads but does not delete mandatory
audit evidence or content already retained by the approved ChatGPT workspace.

## Release evidence

Use [Phase 6 Beta release evidence](phase6-beta-release-evidence.md). Record
commands, bounded results, revisions, digest, OAuth/client version, cohort,
latency, findings, rollback, and named contacts without tokens, secrets,
prompts, document bodies, signed URLs, or private keys.
