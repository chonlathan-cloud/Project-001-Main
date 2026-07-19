#!/usr/bin/env bash

set -euo pipefail

PROJECT_ID="${PROJECT_ID:-project001-489710}"
REGION="${REGION:-asia-southeast1}"
SERVICE_NAME="${SERVICE_NAME:-projects-001-be}"
CYCLE_JOB_NAME="${CYCLE_JOB_NAME:-daily-report-cycle-creation-scan}"
DUE_JOB_NAME="${DUE_JOB_NAME:-daily-report-due-action-scan}"
CYCLE_SCHEDULE="${CYCLE_SCHEDULE:-*/15 * * * *}"
DUE_SCHEDULE="${DUE_SCHEDULE:-*/5 * * * *}"
TIME_ZONE="${TIME_ZONE:-Asia/Bangkok}"
SCHEDULER_SERVICE_ACCOUNT="${SCHEDULER_SERVICE_ACCOUNT:-daily-report-scheduler@${PROJECT_ID}.iam.gserviceaccount.com}"

SERVICE_URL="${SERVICE_URL:-$(
  gcloud run services describe "${SERVICE_NAME}" \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --format='value(status.url)'
)}"

if [[ -z "${SERVICE_URL}" ]]; then
  echo "Cloud Run service URL could not be resolved." >&2
  exit 1
fi

CYCLE_URI="${SERVICE_URL}/api/v1/internal/daily-reports/create-due-cycles"
DUE_URI="${SERVICE_URL}/api/v1/internal/daily-reports/scan-due-actions"

if ! gcloud iam service-accounts describe "${SCHEDULER_SERVICE_ACCOUNT}" \
  --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud iam service-accounts create "${SCHEDULER_SERVICE_ACCOUNT%%@*}" \
    --project="${PROJECT_ID}" \
    --display-name="Daily Report Scheduler"
fi

gcloud run services update "${SERVICE_NAME}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --update-env-vars="DAILY_REPORT_SCHEDULER_SERVICE_ACCOUNT=${SCHEDULER_SERVICE_ACCOUNT},DAILY_REPORT_SCHEDULER_AUDIENCE=${SERVICE_URL}"

configure_job() {
  local job_name="$1"
  local schedule="$2"
  local uri="$3"

  if gcloud scheduler jobs describe "${job_name}" \
    --project="${PROJECT_ID}" \
    --location="${REGION}" >/dev/null 2>&1; then
    gcloud scheduler jobs update http "${job_name}" \
      --project="${PROJECT_ID}" \
      --location="${REGION}" \
      --schedule="${schedule}" \
      --time-zone="${TIME_ZONE}" \
      --uri="${uri}" \
      --http-method=POST \
      --oidc-service-account-email="${SCHEDULER_SERVICE_ACCOUNT}" \
      --oidc-token-audience="${SERVICE_URL}" \
      --attempt-deadline=300s
  else
    gcloud scheduler jobs create http "${job_name}" \
      --project="${PROJECT_ID}" \
      --location="${REGION}" \
      --schedule="${schedule}" \
      --time-zone="${TIME_ZONE}" \
      --uri="${uri}" \
      --http-method=POST \
      --oidc-service-account-email="${SCHEDULER_SERVICE_ACCOUNT}" \
      --oidc-token-audience="${SERVICE_URL}" \
      --attempt-deadline=300s
  fi
}

configure_job "${CYCLE_JOB_NAME}" "${CYCLE_SCHEDULE}" "${CYCLE_URI}"
configure_job "${DUE_JOB_NAME}" "${DUE_SCHEDULE}" "${DUE_URI}"

echo "Daily Report cycle scan configured: ${CYCLE_URI}"
echo "Daily Report due-action scan configured: ${DUE_URI}"
