#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHARED_CONFIG_FILE="${DEPLOY_SHARED_CONFIG:-${ROOT_DIR}/cloudrun.env}"

if [[ ! -f "${SHARED_CONFIG_FILE}" ]]; then
  echo "Missing shared config: ${SHARED_CONFIG_FILE}"
  echo "Copy cloudrun.env.example to cloudrun.env and fill in your values first."
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "${SHARED_CONFIG_FILE}"
set +a

: "${GCP_PROJECT_ID:?Missing GCP_PROJECT_ID in cloudrun.env}"
: "${GCP_REGION:?Missing GCP_REGION in cloudrun.env}"
: "${ARTIFACT_REPO:?Missing ARTIFACT_REPO in cloudrun.env}"

BACKEND_SERVICE_NAME="${BACKEND_SERVICE_NAME:-Projects-001-BE}"
BACKEND_IMAGE_NAME="${BACKEND_IMAGE_NAME:-projects-001-be}"
BACKEND_SOURCE_DIR="${ROOT_DIR}/${BACKEND_SOURCE_DIR:-Projects-001-BE}"
BACKEND_ENV_FILE="${ROOT_DIR}/$(basename "${BACKEND_ENV_FILE:-cloudrun-backend.env.yaml}")"
DOCKER_PLATFORM="${DOCKER_PLATFORM:-linux/amd64}"

if [[ ! -d "${BACKEND_SOURCE_DIR}" ]]; then
  echo "Backend source directory not found: ${BACKEND_SOURCE_DIR}"
  exit 1
fi

if [[ ! -f "${BACKEND_ENV_FILE}" ]]; then
  echo "Missing backend env file: ${BACKEND_ENV_FILE}"
  echo "Copy cloudrun-backend.env.yaml.example to cloudrun-backend.env.yaml and fill in your values first."
  exit 1
fi

IMAGE_URI="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${ARTIFACT_REPO}/${BACKEND_IMAGE_NAME}:latest"

echo "==> Using GCP project: ${GCP_PROJECT_ID}"
gcloud config set project "${GCP_PROJECT_ID}" >/dev/null

if ! gcloud artifacts repositories describe "${ARTIFACT_REPO}" --location "${GCP_REGION}" >/dev/null 2>&1; then
  echo "==> Creating Artifact Registry repository: ${ARTIFACT_REPO}"
  gcloud artifacts repositories create "${ARTIFACT_REPO}" \
    --repository-format=docker \
    --location="${GCP_REGION}"
fi

echo "==> Configuring docker auth for ${GCP_REGION}-docker.pkg.dev"
gcloud auth configure-docker "${GCP_REGION}-docker.pkg.dev" --quiet >/dev/null

echo "==> Building and pushing backend image: ${IMAGE_URI}"
docker buildx build \
  --platform "${DOCKER_PLATFORM}" \
  -t "${IMAGE_URI}" \
  --push \
  "${BACKEND_SOURCE_DIR}"

DEPLOY_ARGS=(
  run deploy "${BACKEND_SERVICE_NAME}"
  --image "${IMAGE_URI}"
  --region "${GCP_REGION}"
  --platform managed
  --env-vars-file "${BACKEND_ENV_FILE}"
)

if [[ "${BACKEND_ALLOW_UNAUTHENTICATED:-true}" == "true" ]]; then
  DEPLOY_ARGS+=(--allow-unauthenticated)
else
  DEPLOY_ARGS+=(--no-allow-unauthenticated)
fi

if [[ -n "${BACKEND_SERVICE_ACCOUNT:-}" ]]; then
  DEPLOY_ARGS+=(--service-account "${BACKEND_SERVICE_ACCOUNT}")
fi

if [[ -n "${BACKEND_CLOUDSQL_INSTANCE:-}" ]]; then
  DEPLOY_ARGS+=(--add-cloudsql-instances "${BACKEND_CLOUDSQL_INSTANCE}")
fi

if [[ -n "${BACKEND_MEMORY:-}" ]]; then
  DEPLOY_ARGS+=(--memory "${BACKEND_MEMORY}")
fi

if [[ -n "${BACKEND_CPU:-}" ]]; then
  DEPLOY_ARGS+=(--cpu "${BACKEND_CPU}")
fi

if [[ -n "${BACKEND_MIN_INSTANCES:-}" ]]; then
  DEPLOY_ARGS+=(--min-instances "${BACKEND_MIN_INSTANCES}")
fi

if [[ -n "${BACKEND_MAX_INSTANCES:-}" ]]; then
  DEPLOY_ARGS+=(--max-instances "${BACKEND_MAX_INSTANCES}")
fi

echo "==> Deploying backend service: ${BACKEND_SERVICE_NAME}"
gcloud "${DEPLOY_ARGS[@]}"

BACKEND_URL="$(gcloud run services describe "${BACKEND_SERVICE_NAME}" --region "${GCP_REGION}" --format='value(status.url)')"
echo "Backend deployed: ${BACKEND_URL}"
