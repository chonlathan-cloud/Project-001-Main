# GCP Read-Only Workflows

Use these patterns for project `project001-489710`. Pass the project flag on every command instead of changing local defaults.

## Command Hygiene

- Use bounded output: `--limit`, `--freshness`, `--format=json`, or focused filters.
- Prefer metadata reads before content reads.
- Do not access Secret Manager payloads with `gcloud secrets versions access`.
- Do not write, deploy, enable APIs, grant IAM, delete resources, upload files, run migrations, or mutate data without explicit user approval.
- Keep `Project-001-saas`, `project-saas-001-be`, and `project-saas-001-fe` out of this repository's architecture analysis unless the user explicitly asks about cross-project SaaS resources.

## Project And API Inventory

```bash
gcloud projects describe project001-489710 --format=json
gcloud services list --enabled --project project001-489710 --format="table(config.name,state)"
gcloud asset search-all-resources --scope=projects/project001-489710 --limit=200 --format=json
```

If Cloud Asset Inventory is unavailable or permission is denied, fall back to service-specific list commands and report the blocker.

## Cloud Run

List services first:

```bash
gcloud run services list --project project001-489710 --platform managed --format=json
```

Describe a selected service:

```bash
gcloud run services describe SERVICE --project project001-489710 --region REGION --format=json
gcloud run revisions list --service SERVICE --project project001-489710 --region REGION --format=json
```

Use the region returned by the service list. If the service is `project-saas-001-be` or `project-saas-001-fe`, treat it as excluded SaaS context.

## Cloud Logging

Use bounded reads. For all Cloud Run logs:

```bash
gcloud logging read 'resource.type="cloud_run_revision"' --project project001-489710 --freshness=1h --limit=50 --format=json
```

For a specific Cloud Run service:

```bash
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="SERVICE"' --project project001-489710 --freshness=1h --limit=50 --format=json
```

For errors only:

```bash
gcloud logging read 'resource.type="cloud_run_revision" AND severity>=ERROR' --project project001-489710 --freshness=24h --limit=100 --format=json
```

## Cloud Build And Artifact Registry

```bash
gcloud builds list --project project001-489710 --limit=20 --format=json
gcloud artifacts repositories list --project project001-489710 --location=asia-southeast1 --format=json
gcloud artifacts docker images list asia-southeast1-docker.pkg.dev/project001-489710/REPOSITORY --include-tags --limit=50 --format=json
```

Do not submit builds or delete images without approval.

## BigQuery

List datasets and tables:

```bash
bq ls --project_id=project001-489710
bq ls --project_id=project001-489710 DATASET
bq show --format=prettyjson project001-489710:DATASET.TABLE
```

Dry-run unfamiliar SQL first:

```bash
bq query --project_id=project001-489710 --nouse_legacy_sql --dry_run 'SELECT ...'
```

Exploratory read queries should include `LIMIT` and avoid wide scans unless the user accepts the cost and scope.

## Firestore

Start with database metadata:

```bash
gcloud firestore databases list --project project001-489710 --format=json
gcloud firestore databases describe --database="(default)" --project project001-489710 --format=json
```

There is no reliable generic CLI command for walking an unknown Firestore collection tree. Use application code, documented collection paths, or specific user-provided paths before reading documents.

## Cloud Storage

```bash
gcloud storage buckets list --project project001-489710 --format=json
gcloud storage buckets describe gs://BUCKET --format=json
gcloud storage ls gs://BUCKET/PREFIX
```

Do not print signed URLs, private object contents, KYC files, receipt payloads, or profile images. Metadata such as object names, size, content type, and timestamps is usually enough for diagnostics.

## Secret Manager

Metadata reads are allowed:

```bash
gcloud secrets list --project project001-489710 --format=json
gcloud secrets describe SECRET --project project001-489710 --format=json
gcloud secrets versions list SECRET --project project001-489710 --format=json
```

Never run `gcloud secrets versions access` unless the user explicitly asks and approves secret access for a specific diagnostic.

## IAM

Read project policy for architecture and permission diagnosis:

```bash
gcloud projects get-iam-policy project001-489710 --format=json
```

When summarizing, group by role and service account. Do not add, remove, or bind roles without explicit approval.

## Document AI

```bash
gcloud documentai processors list --project project001-489710 --location=asia-southeast1 --format=json
gcloud documentai processors describe PROCESSOR_ID --project project001-489710 --location=asia-southeast1 --format=json
```

Correlate OCR issues with Cloud Run logs and GCS metadata. Do not download private receipt files unless the user explicitly asks.

## Vertex AI

```bash
gcloud ai models list --project project001-489710 --region=asia-southeast1 --format=json
gcloud ai endpoints list --project project001-489710 --region=asia-southeast1 --format=json
gcloud ai indexes list --project project001-489710 --region=asia-southeast1 --format=json
```

Compare live resources with backend configuration names such as `VERTEX_AI_MODEL`, `VERTEX_AI_INSIGHT_MODEL`, `VERTEX_AI_RECEIPT_MODEL`, and embedding model settings when those variable names exist in local examples or code.
