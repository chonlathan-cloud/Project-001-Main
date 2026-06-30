---
name: gcp-project001-ops
description: "Read-only Google Cloud operations diagnostics for project project001-489710. Use when Codex needs to inspect this repository's GCP architecture, resource inventory, Cloud Run services, Cloud Logging entries, BigQuery datasets, Firestore databases, Cloud Storage buckets, Secret Manager metadata, IAM policy, Artifact Registry, Document AI processors, Vertex AI resources, or safe bounded gcloud/bq diagnostics. Exclude Cloud SQL instance Project-001-saas and Cloud Run services project-saas-001-be/project-saas-001-fe because they belong to another project/repository."
---

# GCP Project001 Ops

## Defaults

Use project `project001-489710` and local `gcloud` CLI authentication. Keep all operations read-only unless the user explicitly asks for a write/deploy action and approves it. Prefer passing `--project project001-489710` or `--project_id project001-489710` instead of changing local `gcloud` defaults.

Never print, store, or request service account keys, Firebase private keys, `.env` secrets, access tokens, credential JSON contents, Secret Manager payloads, signed URLs, or full connection strings. Redact secrets before showing command output to the user.

Start diagnostics by confirming local CLI context:

```bash
gcloud config get-value project
gcloud auth list
```

A different active `gcloud` default project is acceptable when every diagnostic command passes `--project project001-489710`.

## Scope Boundaries

Treat this skill as the GCP read-only architecture lens for this repository. In scope: Cloud Run, Cloud Logging, Cloud Build metadata, Artifact Registry, Cloud Storage, BigQuery, Firestore, Secret Manager metadata, IAM policy reads, Document AI, Vertex AI, enabled APIs, and general project inventory.

Do not treat these resources as part of this project's architecture unless the user explicitly redirects:

- Cloud SQL instance `Project-001-saas`
- Cloud Run service `project-saas-001-be`
- Cloud Run service `project-saas-001-fe`

Those SaaS resources belong to another project/repository. If they appear in command output, call out that they are excluded context instead of using them as evidence for this project.

## Quick Inventory

Use the helper script when broad discovery is useful. It prints safe commands by default:

```bash
python .codex/skills/gcp-project001-ops/scripts/gcp_project001_readonly.py inventory
```

Run commands only when local credentials permit read-only access and the user task needs live data:

```bash
python .codex/skills/gcp-project001-ops/scripts/gcp_project001_readonly.py inventory --execute
```

For exact command patterns by service, read `references/gcp-readonly-workflows.md` before running diagnostics outside the helper script.

## Diagnostic Workflow

1. Confirm the user's request is read-only. If it implies deploy, create, update, delete, enable, IAM mutation, data export, or database writes, stop and ask for explicit approval.
2. Inspect local app configuration from examples and code before relying on live cloud state. Prefer `.env.example` over real `.env` files.
3. Inventory the relevant resource family with bounded output.
4. Describe only the selected resource after it is identified.
5. For logs, always use a bounded window such as `--freshness=1h` and `--limit=50`; never stream indefinitely unless the user asks.
6. For BigQuery, list datasets/tables first. Use `--dry_run` for unfamiliar SQL and add `LIMIT` to exploratory queries.
7. Summarize findings with concrete resource names, regions, timestamps, and blockers. Do not include secrets or raw credential material.

## Escalation Rules

Read-only commands are acceptable when local credentials permit them. Before any create/update/delete/deploy/enable command, pause and ask for explicit user approval. This includes `gcloud run deploy`, `gcloud services enable`, IAM changes, Secret Manager version access, Firestore writes, BigQuery table writes, bucket mutations, Cloud SQL changes, and Redis/Memorystore updates.
