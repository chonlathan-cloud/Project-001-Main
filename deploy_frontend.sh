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

FRONTEND_SERVICE_NAME="${FRONTEND_SERVICE_NAME:-Projects-001-FE}"
FRONTEND_IMAGE_NAME="${FRONTEND_IMAGE_NAME:-projects-001-fe}"
FRONTEND_SOURCE_DIR="${ROOT_DIR}/${FRONTEND_SOURCE_DIR:-Projects-001-FE}"
FRONTEND_BUILD_ENV_FILE="${ROOT_DIR}/$(basename "${FRONTEND_BUILD_ENV_FILE:-cloudrun-frontend.build.env}")"
DOCKER_PLATFORM="${DOCKER_PLATFORM:-linux/amd64}"
BACKEND_SERVICE_NAME="${BACKEND_SERVICE_NAME:-Projects-001-BE}"

if [[ ! -d "${FRONTEND_SOURCE_DIR}" ]]; then
  echo "Frontend source directory not found: ${FRONTEND_SOURCE_DIR}"
  exit 1
fi

if [[ ! -f "${FRONTEND_BUILD_ENV_FILE}" ]]; then
  echo "Missing frontend build env file: ${FRONTEND_BUILD_ENV_FILE}"
  echo "Copy cloudrun-frontend.build.env.example to cloudrun-frontend.build.env and fill in your values first."
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "${FRONTEND_BUILD_ENV_FILE}"
set +a

if [[ -z "${VITE_API_BASE_URL:-}" ]]; then
  VITE_API_BASE_URL="$(gcloud run services describe "${BACKEND_SERVICE_NAME}" --region "${GCP_REGION}" --format='value(status.url)')"
  export VITE_API_BASE_URL
fi

REQUIRED_BUILD_VARS=(
  VITE_API_BASE_URL
  VITE_FIREBASE_API_KEY
  VITE_FIREBASE_AUTH_DOMAIN
  VITE_FIREBASE_PROJECT_ID
  VITE_FIREBASE_STORAGE_BUCKET
  VITE_FIREBASE_APP_ID
  VITE_FIREBASE_MESSAGING_SENDER_ID
  VITE_LINE_LIFF_ID
)

for key in "${REQUIRED_BUILD_VARS[@]}"; do
  if [[ -z "${!key:-}" ]]; then
    echo "Missing required frontend build variable: ${key}"
    exit 1
  fi
done

VITE_BOQ_BATCH_SYNC_MAX_TABS="${VITE_BOQ_BATCH_SYNC_MAX_TABS:-3}"
IMAGE_URI="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${ARTIFACT_REPO}/${FRONTEND_IMAGE_NAME}:latest"

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

echo "==> Building and pushing frontend image: ${IMAGE_URI}"
docker buildx build \
  --platform "${DOCKER_PLATFORM}" \
  -t "${IMAGE_URI}" \
  --build-arg "VITE_API_BASE_URL=${VITE_API_BASE_URL}" \
  --build-arg "VITE_FIREBASE_API_KEY=${VITE_FIREBASE_API_KEY}" \
  --build-arg "VITE_FIREBASE_AUTH_DOMAIN=${VITE_FIREBASE_AUTH_DOMAIN}" \
  --build-arg "VITE_FIREBASE_PROJECT_ID=${VITE_FIREBASE_PROJECT_ID}" \
  --build-arg "VITE_FIREBASE_STORAGE_BUCKET=${VITE_FIREBASE_STORAGE_BUCKET}" \
  --build-arg "VITE_FIREBASE_APP_ID=${VITE_FIREBASE_APP_ID}" \
  --build-arg "VITE_FIREBASE_MESSAGING_SENDER_ID=${VITE_FIREBASE_MESSAGING_SENDER_ID}" \
  --build-arg "VITE_LINE_LIFF_ID=${VITE_LINE_LIFF_ID}" \
  --build-arg "VITE_BOQ_BATCH_SYNC_MAX_TABS=${VITE_BOQ_BATCH_SYNC_MAX_TABS}" \
  --push \
  "${FRONTEND_SOURCE_DIR}"

DEPLOY_ARGS=(
  run deploy "${FRONTEND_SERVICE_NAME}"
  --image "${IMAGE_URI}"
  --region "${GCP_REGION}"
  --platform managed
)

if [[ "${FRONTEND_ALLOW_UNAUTHENTICATED:-true}" == "true" ]]; then
  DEPLOY_ARGS+=(--allow-unauthenticated)
else
  DEPLOY_ARGS+=(--no-allow-unauthenticated)
fi

if [[ -n "${FRONTEND_SERVICE_ACCOUNT:-}" ]]; then
  DEPLOY_ARGS+=(--service-account "${FRONTEND_SERVICE_ACCOUNT}")
fi

if [[ -n "${FRONTEND_MEMORY:-}" ]]; then
  DEPLOY_ARGS+=(--memory "${FRONTEND_MEMORY}")
fi

if [[ -n "${FRONTEND_CPU:-}" ]]; then
  DEPLOY_ARGS+=(--cpu "${FRONTEND_CPU}")
fi

if [[ -n "${FRONTEND_MIN_INSTANCES:-}" ]]; then
  DEPLOY_ARGS+=(--min-instances "${FRONTEND_MIN_INSTANCES}")
fi

if [[ -n "${FRONTEND_MAX_INSTANCES:-}" ]]; then
  DEPLOY_ARGS+=(--max-instances "${FRONTEND_MAX_INSTANCES}")
fi

echo "==> Deploying frontend service: ${FRONTEND_SERVICE_NAME}"
gcloud "${DEPLOY_ARGS[@]}"

FRONTEND_URL="$(gcloud run services describe "${FRONTEND_SERVICE_NAME}" --region "${GCP_REGION}" --format='value(status.url)')"
echo "Frontend deployed: ${FRONTEND_URL}"
