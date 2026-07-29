#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHARED_CONFIG_FILE="${DEPLOY_SHARED_CONFIG:-${ROOT_DIR}/cloudrun.env}"
PREFLIGHT_ONLY=false

if [[ "${1:-}" == "--preflight-only" ]]; then
  PREFLIGHT_ONLY=true
elif [[ -n "${1:-}" ]]; then
  echo "Usage: $0 [--preflight-only]"
  exit 2
fi

fail() {
  echo "MCP deployment stopped: $*" >&2
  exit 1
}

[[ -f "${SHARED_CONFIG_FILE}" ]] || fail "missing shared config ${SHARED_CONFIG_FILE}"

set -a
# shellcheck disable=SC1090
source "${SHARED_CONFIG_FILE}"
set +a

shared_name="$(basename "${SHARED_CONFIG_FILE}")"
if [[ -n "${MCP_DEPLOY_CONFIG:-}" ]]; then
  DEPLOY_CONFIG_FILE="${MCP_DEPLOY_CONFIG}"
elif [[ "${shared_name}" == "cloudrun-beta.env" ]]; then
  DEPLOY_CONFIG_FILE="${ROOT_DIR}/mcp.deploy.beta"
else
  DEPLOY_CONFIG_FILE="${ROOT_DIR}/mcp.deploy.demo"
fi

[[ -f "${DEPLOY_CONFIG_FILE}" ]] || fail \
  "missing ${DEPLOY_CONFIG_FILE}; copy the matching mcp.deploy.*.example first"

set -a
# shellcheck disable=SC1090
source "${DEPLOY_CONFIG_FILE}"
set +a

required_vars=(
  GCP_PROJECT_ID
  GCP_REGION
  ARTIFACT_REPO
  MCP_ENVIRONMENT
  MCP_SERVICE_NAME
  MCP_IMAGE_NAME
  MCP_SOURCE_DIR
  MCP_ENV_FILE
  MCP_SERVICE_ACCOUNT
  MCP_BACKEND_SERVICE_NAME
  MCP_CLOUDSQL_INSTANCE
  MCP_FIRESTORE_DATABASE_ID
  MCP_ALLOWED_BUCKETS
  MCP_RESOURCE_URL
  MCP_RATE_LIMIT_PER_MINUTE
)

for variable_name in "${required_vars[@]}"; do
  [[ -n "${!variable_name:-}" ]] || fail "missing ${variable_name}"
done

[[ "${GCP_PROJECT_ID}" == "project001-489710" ]] || fail "unexpected GCP project"
[[ "${GCP_REGION}" == "asia-southeast1" ]] || fail "unexpected GCP region"

case "${MCP_ENVIRONMENT}" in
  demo)
    EXPECTED_APP_ENV="production"
    EXPECTED_MCP_SERVICE="projects-001-mcp"
    EXPECTED_BACKEND_SERVICE="projects-001-be"
    EXPECTED_CLOUDSQL="project001-489710:asia-southeast1:project-001"
    EXPECTED_FIRESTORE="(default)"
    EXPECTED_BUCKETS="kyc_id_cards,temp_bills,perm_bills,project001-489710-work-inspection,project001-489710-daily-reports-demo"
    EXPECTED_AUDIT_BUCKET="projects-001-mcp-audit-demo"
    EXPECTED_AUDIT_SINK="projects-001-mcp-audit-demo-sink"
    EXPECTED_AUDIT_VIEW="projects-001-mcp-audit-demo-view"
    EXPECTED_AUDIT_LOG_VIEW="projects/project001-489710/locations/asia-southeast1/buckets/projects-001-mcp-audit-demo/views/projects-001-mcp-audit-demo-view"
    ;;
  beta)
    EXPECTED_APP_ENV="prod-beta"
    EXPECTED_MCP_SERVICE="projects-001-mcp-beta"
    EXPECTED_BACKEND_SERVICE="projects-001-be-beta"
    EXPECTED_CLOUDSQL="project001-489710:asia-southeast1:project-001-beta"
    EXPECTED_FIRESTORE="prod-beta"
    EXPECTED_BUCKETS="kyc_id_cards-beta,temp_bills-beta,perm_bills-beta,project001-489710-work-inspection-beta,project001-489710-daily-reports-beta"
    EXPECTED_AUDIT_BUCKET="projects-001-mcp-audit-beta"
    EXPECTED_AUDIT_SINK="projects-001-mcp-audit-beta-sink"
    EXPECTED_AUDIT_VIEW="projects-001-mcp-audit-beta-view"
    EXPECTED_AUDIT_LOG_VIEW="projects/project001-489710/locations/asia-southeast1/buckets/projects-001-mcp-audit-beta/views/projects-001-mcp-audit-beta-view"
    ;;
  *) fail "MCP_ENVIRONMENT must be demo or beta" ;;
esac

[[ "${MCP_SERVICE_NAME}" == "${EXPECTED_MCP_SERVICE}" ]] || fail "MCP service mismatch"
[[ "${MCP_BACKEND_SERVICE_NAME}" == "${EXPECTED_BACKEND_SERVICE}" ]] || fail \
  "Backend service mismatch"
[[ "${MCP_CLOUDSQL_INSTANCE}" == "${EXPECTED_CLOUDSQL}" ]] || fail \
  "Cloud SQL mapping mismatch"
[[ "${MCP_FIRESTORE_DATABASE_ID}" == "${EXPECTED_FIRESTORE}" ]] || fail \
  "Firestore mapping mismatch"
[[ "${MCP_ALLOWED_BUCKETS}" == "${EXPECTED_BUCKETS}" ]] || fail \
  "bucket allowlist mismatch"
[[ "${MCP_RESOURCE_URL}" == https://*/mcp ]] || fail \
  "MCP_RESOURCE_URL must be the stable HTTPS /mcp endpoint"
[[ "${MCP_RESOURCE_URL}" != *".invalid"* ]] || fail "replace the placeholder MCP URL"
[[ "${MCP_SERVICE_ACCOUNT}" != *"backend-runtime"* ]] || fail \
  "MCP must use a dedicated service account"
[[ "${MCP_RATE_LIMIT_PER_MINUTE}" =~ ^[0-9]+$ ]] || fail \
  "MCP_RATE_LIMIT_PER_MINUTE must be an integer"
(( MCP_RATE_LIMIT_PER_MINUTE >= 1 && MCP_RATE_LIMIT_PER_MINUTE <= 1000 )) || fail \
  "MCP_RATE_LIMIT_PER_MINUTE must be between 1 and 1000"

MCP_SOURCE_PATH="${ROOT_DIR}/${MCP_SOURCE_DIR}"
MCP_ENV_FILE_PATH="${ROOT_DIR}/${MCP_ENV_FILE}"
[[ -d "${MCP_SOURCE_PATH}" ]] || fail "missing MCP source directory"
[[ -f "${MCP_ENV_FILE_PATH}" ]] || fail \
  "missing ${MCP_ENV_FILE_PATH}; copy the matching cloudrun-mcp*.env.yaml.example first"

if grep -Eiq \
  'project-001-saas|project-001-saas-restore-test|project-saas-001-(be|fe)|bigquery' \
  "${DEPLOY_CONFIG_FILE}" "${MCP_ENV_FILE_PATH}"; then
  fail "configuration references an explicitly excluded resource"
fi

yaml_value() {
  local key="$1"
  awk -v wanted="${key}" '
    $0 ~ "^[[:space:]]*" wanted "[[:space:]]*:" {
      sub("^[[:space:]]*" wanted "[[:space:]]*:[[:space:]]*", "")
      gsub(/^[\047\"]|[\047\"][[:space:]]*$/, "")
      print
      exit
    }
  ' "${MCP_ENV_FILE_PATH}"
}

validate_yaml_value() {
  local yaml_key="$1"
  local expected_value="$2"
  local actual_value
  actual_value="$(yaml_value "${yaml_key}")"
  [[ "${actual_value}" == "${expected_value}" ]] || fail \
    "runtime YAML mismatch for ${yaml_key}"
}

# Keep this compatible with the Bash 3.2 shipped on macOS so preflight can run
# on a clean developer machine without an additional shell dependency.
validate_yaml_value MCP_ENVIRONMENT "${MCP_ENVIRONMENT}"
validate_yaml_value MCP_APP_ENV "${EXPECTED_APP_ENV}"
validate_yaml_value MCP_GCP_PROJECT_ID "${GCP_PROJECT_ID}"
validate_yaml_value MCP_GCP_REGION "${GCP_REGION}"
validate_yaml_value MCP_SERVICE_NAME "${MCP_SERVICE_NAME}"
validate_yaml_value MCP_RESOURCE_URL "${MCP_RESOURCE_URL}"
validate_yaml_value MCP_OAUTH_AUDIENCE "${MCP_RESOURCE_URL}"
validate_yaml_value MCP_BACKEND_SERVICE_NAME "${MCP_BACKEND_SERVICE_NAME}"
validate_yaml_value MCP_CLOUD_SQL_INSTANCE "${MCP_CLOUDSQL_INSTANCE}"
validate_yaml_value MCP_FIRESTORE_DATABASE_ID "${MCP_FIRESTORE_DATABASE_ID}"
validate_yaml_value MCP_ALLOWED_BUCKETS "${MCP_ALLOWED_BUCKETS}"
validate_yaml_value MCP_RATE_LIMIT_PER_MINUTE "${MCP_RATE_LIMIT_PER_MINUTE}"
validate_yaml_value MCP_AUDIT_LOG_VIEW "${EXPECTED_AUDIT_LOG_VIEW}"
validate_yaml_value MCP_AUDIT_READ_MAX_DAYS "90"

for url_key in MCP_OAUTH_ISSUER MCP_OAUTH_JWKS_URL MCP_BACKEND_URL MCP_BACKEND_AUDIENCE; do
  url_value="$(yaml_value "${url_key}")"
  [[ "${url_value}" == https://* ]] || fail "${url_key} must use HTTPS"
  [[ "${url_value}" != *".invalid"* ]] || fail "replace the placeholder ${url_key}"
done

[[ "$(yaml_value MCP_BACKEND_URL)" == "$(yaml_value MCP_BACKEND_AUDIENCE)" ]] || fail \
  "Backend URL and audience must match"
[[ "$(yaml_value MCP_OAUTH_REQUIRED_SCOPES)" == *"mcp:read"* ]] || fail \
  "OAuth scopes must include mcp:read"

echo "MCP config preflight passed for ${MCP_ENVIRONMENT}."

gcloud projects describe "${GCP_PROJECT_ID}" --format='value(projectId)' >/dev/null
gcloud artifacts repositories describe "${ARTIFACT_REPO}" \
  --project "${GCP_PROJECT_ID}" \
  --location "${GCP_REGION}" >/dev/null
gcloud run services describe "${MCP_BACKEND_SERVICE_NAME}" \
  --project "${GCP_PROJECT_ID}" \
  --region "${GCP_REGION}" >/dev/null
gcloud iam service-accounts describe "${MCP_SERVICE_ACCOUNT}" \
  --project "${GCP_PROJECT_ID}" >/dev/null

cloud_sql_name="${MCP_CLOUDSQL_INSTANCE##*:}"
gcloud sql instances describe "${cloud_sql_name}" \
  --project "${GCP_PROJECT_ID}" >/dev/null
gcloud firestore databases describe \
  --database "${MCP_FIRESTORE_DATABASE_ID}" \
  --project "${GCP_PROJECT_ID}" >/dev/null

IFS=',' read -r -a allowed_bucket_items <<< "${MCP_ALLOWED_BUCKETS}"
for bucket_name in "${allowed_bucket_items[@]}"; do
  gcloud storage buckets describe "gs://${bucket_name}" \
    --project "${GCP_PROJECT_ID}" >/dev/null
done

gcloud logging buckets describe "${EXPECTED_AUDIT_BUCKET}" \
  --project "${GCP_PROJECT_ID}" \
  --location "${GCP_REGION}" >/dev/null

audit_view_filter="$(
  gcloud logging views describe "${EXPECTED_AUDIT_VIEW}" \
    --bucket "${EXPECTED_AUDIT_BUCKET}" \
    --project "${GCP_PROJECT_ID}" \
    --location "${GCP_REGION}" \
    --format='value(filter)'
)"
[[ "${audit_view_filter}" == *"${MCP_SERVICE_NAME}"* ]] || fail \
  "audit view filter is not restricted to the MCP service"
[[ "${audit_view_filter}" == *"product_audit"* ]] || fail \
  "audit view filter is not restricted to Product Audit events"

audit_sink_destination="$(
  gcloud logging sinks describe "${EXPECTED_AUDIT_SINK}" \
    --project "${GCP_PROJECT_ID}" \
    --format='value(destination)'
)"
expected_audit_sink_destination="logging.googleapis.com/projects/${GCP_PROJECT_ID}/locations/${GCP_REGION}/buckets/${EXPECTED_AUDIT_BUCKET}"
[[ "${audit_sink_destination}" == "${expected_audit_sink_destination}" ]] || fail \
  "audit sink destination mismatch"

audit_sink_filter="$(
  gcloud logging sinks describe "${EXPECTED_AUDIT_SINK}" \
    --project "${GCP_PROJECT_ID}" \
    --format='value(filter)'
)"
[[ "${audit_sink_filter}" == *"${MCP_SERVICE_NAME}"* ]] || fail \
  "audit sink filter is not restricted to the MCP service"
[[ "${audit_sink_filter}" == *"product_audit"* ]] || fail \
  "audit sink filter is not restricted to Product Audit events"

view_accessor_binding="$(
  gcloud logging views get-iam-policy "${EXPECTED_AUDIT_VIEW}" \
    --bucket "${EXPECTED_AUDIT_BUCKET}" \
    --project "${GCP_PROJECT_ID}" \
    --location "${GCP_REGION}" \
    --flatten='bindings[].members' \
    --filter="bindings.role=roles/logging.viewAccessor AND bindings.members=serviceAccount:${MCP_SERVICE_ACCOUNT}" \
    --format='value(bindings.role)'
)"
[[ "${view_accessor_binding}" == "roles/logging.viewAccessor" ]] || fail \
  "MCP service account lacks exact audit view access"

log_writer_binding="$(
  gcloud projects get-iam-policy "${GCP_PROJECT_ID}" \
    --flatten='bindings[].members' \
    --filter="bindings.role=roles/logging.logWriter AND bindings.members=serviceAccount:${MCP_SERVICE_ACCOUNT}" \
    --format='value(bindings.role)'
)"
[[ "${log_writer_binding}" == "roles/logging.logWriter" ]] || fail \
  "MCP service account lacks logging.logWriter"

echo "MCP live resource preflight passed."

if [[ "${PREFLIGHT_ONLY}" == "true" ]]; then
  exit 0
fi

IMAGE_TAG="${MCP_IMAGE_TAG:-$(git -C "${ROOT_DIR}" rev-parse --short=12 HEAD)}"
IMAGE_URI="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${ARTIFACT_REPO}/${MCP_IMAGE_NAME}:${IMAGE_TAG}"
DOCKER_PLATFORM="${DOCKER_PLATFORM:-linux/amd64}"

previous_revision="$(
  gcloud run revisions list \
    --service "${MCP_SERVICE_NAME}" \
    --project "${GCP_PROJECT_ID}" \
    --region "${GCP_REGION}" \
    --sort-by='~metadata.creationTimestamp' \
    --limit=1 \
    --format='value(metadata.name)' 2>/dev/null || true
)"

echo "Building and pushing ${IMAGE_URI}"
gcloud auth configure-docker "${GCP_REGION}-docker.pkg.dev" --quiet >/dev/null
docker buildx build \
  --platform "${DOCKER_PLATFORM}" \
  --tag "${IMAGE_URI}" \
  --push \
  "${MCP_SOURCE_PATH}"

deploy_args=(
  run deploy "${MCP_SERVICE_NAME}"
  --project "${GCP_PROJECT_ID}"
  --region "${GCP_REGION}"
  --platform managed
  --image "${IMAGE_URI}"
  --service-account "${MCP_SERVICE_ACCOUNT}"
  --allow-unauthenticated
  --env-vars-file "${MCP_ENV_FILE_PATH}"
  --memory "${MCP_MEMORY:-512Mi}"
  --cpu "${MCP_CPU:-1}"
  --min-instances "${MCP_MIN_INSTANCES:-0}"
  --max-instances "${MCP_MAX_INSTANCES:-5}"
)

if [[ -n "${MCP_SECRET_ENV_VARS:-}" ]]; then
  deploy_args+=(--update-secrets "${MCP_SECRET_ENV_VARS}")
fi

gcloud "${deploy_args[@]}"

service_url="$(
  gcloud run services describe "${MCP_SERVICE_NAME}" \
    --project "${GCP_PROJECT_ID}" \
    --region "${GCP_REGION}" \
    --format='value(status.url)'
)"
[[ "${service_url}/mcp" == "${MCP_RESOURCE_URL}" ]] || fail \
  "deployed service URL does not match the OAuth resource URL"

health_status="$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
  "${service_url}/health")"
[[ "${health_status}" == "200" ]] || fail "post-deploy health check failed"

initialize_status="$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
  --request POST \
  --header 'Accept: application/json, text/event-stream' \
  --header 'Content-Type: application/json' \
  --data '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"deploy-smoke","version":"1.0"}}}' \
  "${service_url}/mcp")"
[[ "${initialize_status}" == "401" ]] || fail \
  "unauthenticated initialize did not fail closed"

revision="$(
  gcloud run services describe "${MCP_SERVICE_NAME}" \
    --project "${GCP_PROJECT_ID}" \
    --region "${GCP_REGION}" \
    --format='value(status.latestReadyRevisionName)'
)"

echo "MCP deployed: ${service_url}/mcp"
echo "Ready revision: ${revision}"
if [[ -n "${previous_revision}" ]]; then
  echo "Rollback: gcloud run services update-traffic ${MCP_SERVICE_NAME} --project ${GCP_PROJECT_ID} --region ${GCP_REGION} --to-revisions=${previous_revision}=100"
else
  echo "Rollback reference: no previous revision existed before this deployment."
fi
