#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-project001-489710}"
ALERT_EMAIL="${ALERT_EMAIL:-${1:-}}"
CHANNEL_DISPLAY_NAME="RAYADEE Daily Report Operations"
SERVICE_FILTER='resource.type="cloud_run_revision" AND resource.labels.service_name=~"^projects-001-be(-beta)?$"'

if [[ "${PROJECT_ID}" != "project001-489710" ]]; then
  echo "Refusing to update unexpected project: ${PROJECT_ID}" >&2
  exit 2
fi

upsert_metric() {
  local metric_name="$1"
  local description="$2"
  local log_filter="$3"
  if gcloud logging metrics describe "${metric_name}" \
    --project="${PROJECT_ID}" >/dev/null 2>&1; then
    gcloud logging metrics update "${metric_name}" \
      --project="${PROJECT_ID}" \
      --description="${description}" \
      --log-filter="${log_filter}"
  else
    gcloud logging metrics create "${metric_name}" \
      --project="${PROJECT_ID}" \
      --description="${description}" \
      --log-filter="${log_filter}"
  fi
}

upsert_metric daily_report_scheduler_failures \
  "Daily Report Scheduler failures." \
  "${SERVICE_FILTER} AND jsonPayload.event=\"daily_report_scheduler_failure\""
upsert_metric daily_report_line_delivery_failures \
  "Daily Report customer LINE delivery failures." \
  "${SERVICE_FILTER} AND jsonPayload.event=\"daily_report_line_delivery_failed\""
upsert_metric daily_report_subcontractor_notification_failures \
  "Daily Report subcontractor LINE notification failures." \
  "${SERVICE_FILTER} AND (jsonPayload.event=\"daily_report_notification_failed\" OR jsonPayload.event=\"subcontractor_line_notification_failed\")"
upsert_metric daily_report_upload_failures \
  "Daily Report upload or upload-finalization failures." \
  "${SERVICE_FILTER} AND (jsonPayload.event=\"daily_report_upload_failed\" OR jsonPayload.event=\"daily_report_upload_finalization_failed\")"
upsert_metric daily_report_webhook_signature_rejections \
  "Rejected customer LINE webhook signatures." \
  "${SERVICE_FILTER} AND jsonPayload.event=\"line_webhook_signature_rejected\""
upsert_metric daily_report_rate_limit_rejections \
  "Requests rejected by the RAYADEE endpoint rate limiter." \
  "${SERVICE_FILTER} AND jsonPayload.event=\"rate_limit_exceeded\""
upsert_metric daily_report_server_errors \
  "Unhandled or HTTP 5xx Daily Report backend errors." \
  "${SERVICE_FILTER} AND (jsonPayload.event=\"request_unhandled_exception\" OR (jsonPayload.event=\"request_completed\" AND jsonPayload.status_code>=500))"

if [[ -z "${ALERT_EMAIL}" ]]; then
  echo "Metrics configured. Set ALERT_EMAIL and run again to configure email alerts."
  exit 0
fi

if [[ "${ALERT_EMAIL}" != *@*.* ]]; then
  echo "ALERT_EMAIL does not look like a valid email address." >&2
  exit 2
fi

CHANNEL_NAME="$(gcloud alpha monitoring channels list \
  --project="${PROJECT_ID}" \
  --filter="displayName=\"${CHANNEL_DISPLAY_NAME}\" AND labels.email_address=\"${ALERT_EMAIL}\"" \
  --format="value(name)" \
  --limit=1)"
if [[ -z "${CHANNEL_NAME}" ]]; then
  CHANNEL_NAME="$(gcloud alpha monitoring channels create \
    --project="${PROJECT_ID}" \
    --display-name="${CHANNEL_DISPLAY_NAME}" \
    --description="Shared Admin operations channel for RAYADEE Daily Report failures." \
    --type=email \
    --channel-labels="email_address=${ALERT_EMAIL}" \
    --user-labels=app=project-001,env=prod-beta \
    --format="value(name)")"
fi

create_policy() {
  local display_name="$1"
  local metric_name="$2"
  local threshold="$3"
  local alignment_period="$4"
  local existing_policy
  existing_policy="$(gcloud alpha monitoring policies list \
    --project="${PROJECT_ID}" \
    --filter="displayName=\"${display_name}\"" \
    --format="value(name)" \
    --limit=1)"
  if [[ -n "${existing_policy}" ]]; then
    gcloud alpha monitoring policies update "${existing_policy}" \
      --project="${PROJECT_ID}" \
      --enabled \
      --set-notification-channels="${CHANNEL_NAME}" \
      --update-user-labels=app=project-001,env=prod-beta
    return 0
  fi
  gcloud alpha monitoring policies create \
    --project="${PROJECT_ID}" \
    --display-name="${display_name}" \
    --condition-display-name="${display_name}" \
    --condition-filter="resource.type=\"cloud_run_revision\" AND metric.type=\"logging.googleapis.com/user/${metric_name}\"" \
    --aggregation="{\"alignmentPeriod\":\"${alignment_period}\",\"perSeriesAligner\":\"ALIGN_SUM\",\"crossSeriesReducer\":\"REDUCE_SUM\"}" \
    --duration=0s \
    --if="> ${threshold}" \
    --trigger-count=1 \
    --combiner=OR \
    --notification-channels="${CHANNEL_NAME}" \
    --user-labels=app=project-001,env=prod-beta \
    --documentation="RAYADEE Daily Report beta failure. Check Cloud Run logs using the request ID and event fields; do not copy tokens or signed URLs into incident notes."
}

create_policy "RAYADEE Daily Report - Scheduler failure" daily_report_scheduler_failures 0 300s
create_policy "RAYADEE Daily Report - LINE delivery failure" daily_report_line_delivery_failures 0 300s
create_policy "RAYADEE Daily Report - Subcontractor notification failures" daily_report_subcontractor_notification_failures 2 300s
create_policy "RAYADEE Daily Report - Upload failure" daily_report_upload_failures 0 300s
create_policy "RAYADEE Daily Report - Webhook signature spike" daily_report_webhook_signature_rejections 5 300s
create_policy "RAYADEE Daily Report - Rate-limit spike" daily_report_rate_limit_rejections 50 300s
create_policy "RAYADEE Daily Report - Server error" daily_report_server_errors 0 300s

echo "Daily Report metrics and alerts are configured for ${ALERT_EMAIL}."
