#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-project001-489710}"
DATABASE_ID="${DATABASE_ID:-prod-beta}"

if [[ "${PROJECT_ID}" != "project001-489710" ]]; then
  echo "Refusing to update unexpected project: ${PROJECT_ID}" >&2
  exit 2
fi

if [[ "${DATABASE_ID}" != "prod-beta" ]]; then
  echo "Refusing to update unexpected Firestore database: ${DATABASE_ID}" >&2
  exit 2
fi

create_index() {
  local collection_group="$1"
  shift
  local output
  if output="$(gcloud firestore indexes composite create \
    --project="${PROJECT_ID}" \
    --database="${DATABASE_ID}" \
    --collection-group="${collection_group}" \
    --query-scope=collection \
    --async \
    "$@" 2>&1)"; then
    echo "${output}"
    return 0
  fi
  if [[ "${output}" == *"ALREADY_EXISTS"* || "${output}" == *"already exists"* ]]; then
    echo "Index already exists: ${collection_group}"
    return 0
  fi
  echo "${output}" >&2
  return 1
}

create_index daily_report_submissions \
  --field-config=field-path=project_id,order=ascending \
  --field-config=field-path=status,order=ascending \
  --field-config=field-path=report_date,order=descending

create_index daily_reports \
  --field-config=field-path=project_id,order=ascending \
  --field-config=field-path=status,order=ascending \
  --field-config=field-path=report_date,order=descending

create_index daily_report_notifications \
  --field-config=field-path=audience,order=ascending \
  --field-config=field-path=project_id,order=ascending \
  --field-config=field-path=status,order=ascending \
  --field-config=field-path=created_at,order=descending

create_index project_memberships \
  --field-config=field-path=principal_type,order=ascending \
  --field-config=field-path=principal_id,order=ascending \
  --field-config=field-path=status,order=ascending \
  --field-config=field-path=project_id,order=ascending

create_index daily_report_cycles \
  --field-config=field-path=project_id,order=ascending \
  --field-config=field-path=report_date,order=descending

create_index daily_report_delivery_jobs \
  --field-config=field-path=status,order=ascending \
  --field-config=field-path=updated_at,order=ascending

create_index daily_report_events \
  --field-config=field-path=report_id,order=ascending \
  --field-config=field-path=created_at,order=descending

create_index daily_report_media \
  --field-config=field-path=submission_id,order=ascending \
  --field-config=field-path=created_at,order=ascending

gcloud firestore indexes composite list \
  --project="${PROJECT_ID}" \
  --database="${DATABASE_ID}" \
  --format="table(name.basename(),collectionGroup,queryScope,state)"
