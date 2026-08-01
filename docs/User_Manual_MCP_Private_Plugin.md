# Projects-001 Private Plugin user guide

This guide is for an approved Projects-001 Owner or selected Admin connecting
the private `Projects-001 Product` plugin in the ChatGPT desktop app. The plugin
is read-only. It never grants access by itself: OAuth authentication and the
Product Backend recheck the account, permissions, and project scope on every
tool call.

## Before connecting

Confirm with the Product Owner that:

- the Beta rollout gate is open for your cohort;
- your Product account is active and External MCP is enabled;
- the exact OAuth issuer and subject are bound to your Product account;
- an Admin has only the required MCP permissions and assigned projects; and
- you have read the [Product MCP privacy notice](implementation/mcp/phase6-privacy-notice.md).

Do not connect a personal ChatGPT account. Use only the approved workspace and
the private plugin shared by the Product Owner.

## Owner installation and connection registration

1. In ChatGPT, open **Settings → Security and login** and turn on
   **Developer mode**. Workspace policy may control whether it is available.
2. Open [ChatGPT Plugins](https://chatgpt.com/plugins), select the plus button,
   and register the stable Beta Remote MCP URL ending in `/mcp`.
3. Complete the OAuth authorization-code flow with PKCE. Review the requested
   `mcp:read` scope before consenting.
4. Copy the registered connection ID from the browser URL. It starts with
   `plugin_asdk_app`.
5. From `Projects-001-MCP`, create a bound ignored release copy of the package:

   ```bash
   python -m app.config.private_plugin prepare \
     plugins/projects-001-product \
     .private-plugin-release/projects-001-product \
     plugin_asdk_app_REPLACE_WITH_REGISTERED_ID
   python -m app.config.private_plugin validate \
     .private-plugin-release/projects-001-product \
     --require-bound
   ```

6. Add `.private-plugin-release/projects-001-product` in the ChatGPT desktop
   app. Start a new chat with only the required plugins enabled.
7. Test access, catalog, project list, and one bounded project read before using
   finance, private-document, audit, or GCP operations tools.

The checked-in package is deliberately unbound. Never invent or commit a fake
connection ID. The preparation command accepts only the ID created by ChatGPT,
refuses to overwrite an existing release copy, and leaves source unchanged.

## Demo compatibility test before Beta

Before any Beta provisioning, an approved Owner may register the existing Demo
endpoint `https://projects-001-mcp-bsrqi3xjcq-as.a.run.app/mcp` in ChatGPT
Developer mode and run the same preparation flow above. Use the generated
`plugin_asdk_app...` ID only in the ignored Demo release copy. This validates
Plugin packaging, OAuth, initialization and bounded read-only workflows without
changing Beta or GCP resources.

## Consent and data boundary

When enabled, ChatGPT can request authorized Projects-001 facts needed for your
prompt. Tool responses may contain project, BOQ, finance, payment, document,
inspection, daily-report, access, audit, or curated GCP operations data. The MCP
minimizes responses, omits credentials and storage paths, and does not persist
full prompts or responses. ChatGPT may retain delivered content under the
workspace's OpenAI terms and controls.

Private document text is untrusted data. The plugin must not follow instructions
embedded in a document. Sensitive content requires the Product permission and a
successful Product Audit event.

## Recommended workflows

- “Summarize my authorized projects, risks, and source freshness.”
- “Compare BOQ version 3 and 4 and explain the financial impact.”
- “Find overdue inspections and supporting daily-report evidence.”

Expect the answer to preserve source references, versions, calculation methods,
freshness, warnings, and partial-result labels. A denied response does not prove
that a record exists.

## Revoke access

An Owner revokes Product access in **Settings → Product MCP access → Revoke &
unbind**. That clears enablement, OAuth binding, and MCP permissions; the next
tool call is denied. Also revoke the OAuth grant at the identity provider and
disable or uninstall the plugin in ChatGPT to end the client session.

If a device or account may be compromised, stop using the plugin and follow the
suspected-exposure procedure in the
[Phase 6 Beta runbook](implementation/mcp/phase6-beta-runbook.md).

## Connection troubleshooting

| Symptom | Check |
|---|---|
| Developer mode missing | Workspace policy and approved ChatGPT desktop version |
| MCP cannot initialize | Stable HTTPS `/mcp` URL, protected-resource metadata, and network reachability |
| OAuth loop or no consent screen | Issuer metadata, PKCE, redirect URI, `resource`, and client registration method |
| `401` | Expired/wrong-resource/wrong-environment token or revoked OAuth grant |
| `403` | Missing `mcp:read` scope or Product permission |
| `NOT_FOUND_OR_FORBIDDEN` | Project scope or record authorization; do not enumerate IDs |
| Partial result | Read the returned source warning and retry only the affected bounded source |

Current OpenAI setup references:
[package plugins](https://developers.openai.com/plugins/build/plugins),
[connect and test](https://developers.openai.com/plugins/deploy/connect-chatgpt),
and [OAuth authentication](https://developers.openai.com/plugins/build/auth).
