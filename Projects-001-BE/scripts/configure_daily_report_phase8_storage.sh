#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-project001-489710}"
BUCKET_NAME="${BUCKET_NAME:-project001-489710-daily-reports-beta}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIFECYCLE_FILE="${SCRIPT_DIR}/../infra/gcp/daily-reports-bucket-lifecycle.json"

if [[ "${PROJECT_ID}" != "project001-489710" ]]; then
  echo "Refusing to update unexpected project: ${PROJECT_ID}" >&2
  exit 2
fi

if [[ "${BUCKET_NAME}" != "project001-489710-daily-reports-beta" ]]; then
  echo "Refusing to update unexpected bucket: ${BUCKET_NAME}" >&2
  exit 2
fi

gcloud storage buckets update "gs://${BUCKET_NAME}" \
  --project="${PROJECT_ID}" \
  --enable-autoclass \
  --autoclass-terminal-storage-class=ARCHIVE \
  --lifecycle-file="${LIFECYCLE_FILE}" \
  --soft-delete-duration=7d \
  --uniform-bucket-level-access \
  --public-access-prevention \
  --update-labels=app=project-001,env=prod-beta

gcloud storage buckets describe "gs://${BUCKET_NAME}" \
  --project="${PROJECT_ID}" \
  --format="yaml(name,location,labels,autoclass,soft_delete_policy,uniform_bucket_level_access,public_access_prevention,lifecycle_config)"
