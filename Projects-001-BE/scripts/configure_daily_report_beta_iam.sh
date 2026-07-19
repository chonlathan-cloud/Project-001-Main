#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-project001-489710}"
REGION="${REGION:-asia-southeast1}"
SERVICE_NAME="${SERVICE_NAME:-projects-001-be-beta}"
SERVICE_ACCOUNT_NAME="${SERVICE_ACCOUNT_NAME:-backend-runtime-beta}"
SERVICE_ACCOUNT="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
GCS_BUCKETS="${GCS_BUCKETS:-kyc_id_cards-beta,project001-489710-work-inspection-beta,project001-489710-daily-reports-beta}"
SECRET_NAMES="${SECRET_NAMES:-}"

if [[ "${PROJECT_ID}" != "project001-489710" ]]; then
  echo "Refusing to update unexpected project: ${PROJECT_ID}" >&2
  exit 2
fi

if [[ "${SERVICE_NAME}" != "projects-001-be-beta" ]]; then
  echo "Refusing to update unexpected Cloud Run service: ${SERVICE_NAME}" >&2
  exit 2
fi

if [[ -z "${SECRET_NAMES}" ]]; then
  echo "SECRET_NAMES is empty; no IAM or Cloud Run changes were made." >&2
  echo "Set every comma-separated Secret Manager reference used by the beta backend." >&2
  exit 2
fi

if ! gcloud iam service-accounts describe "${SERVICE_ACCOUNT}" \
  --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud iam service-accounts create "${SERVICE_ACCOUNT_NAME}" \
    --project="${PROJECT_ID}" \
    --display-name="Projects-001 beta backend runtime"
fi

for role in \
  roles/aiplatform.user \
  roles/cloudsql.client \
  roles/cloudtasks.enqueuer \
  roles/datastore.user; do
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="${role}" \
    --condition=None \
    --quiet
done

IFS=',' read -r -a bucket_names <<< "${GCS_BUCKETS}"
for bucket_name in "${bucket_names[@]}"; do
  gcloud storage buckets add-iam-policy-binding "gs://${bucket_name}" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role=roles/storage.objectUser
done

IFS=',' read -r -a secret_names <<< "${SECRET_NAMES}"
for secret_name in "${secret_names[@]}"; do
  gcloud secrets add-iam-policy-binding "${secret_name}" \
    --project="${PROJECT_ID}" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role=roles/secretmanager.secretAccessor
done

gcloud iam service-accounts add-iam-policy-binding "${SERVICE_ACCOUNT}" \
  --project="${PROJECT_ID}" \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role=roles/iam.serviceAccountTokenCreator

gcloud run services update "${SERVICE_NAME}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --service-account="${SERVICE_ACCOUNT}"

echo "Beta backend now uses ${SERVICE_ACCOUNT}."
echo "Verify every beta flow before removing any role from the shared backend-runtime identity."
