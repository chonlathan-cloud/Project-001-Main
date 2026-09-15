#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${BACKEND_DIR}/tests/postgres/docker-compose.phase0.yml"
COMPOSE_PROJECT="projects001_phase0"
PHASE0_URL="postgresql+asyncpg://phase0:phase0@127.0.0.1:55432/projects001_phase0_test"
PYTHON_BIN="${BACKEND_DIR}/venv/bin/python"

compose() {
  docker compose -p "${COMPOSE_PROJECT}" -f "${COMPOSE_FILE}" "$@"
}

require_python() {
  if [[ ! -x "${PYTHON_BIN}" ]]; then
    echo "Backend interpreter not found: ${PYTHON_BIN}" >&2
    exit 1
  fi
}

case "${1:-}" in
  up)
    compose up -d --wait
    ;;
  down)
    compose down --remove-orphans
    ;;
  status)
    compose ps
    ;;
  url)
    echo "${PHASE0_URL}"
    ;;
  bootstrap)
    require_python
    PYTHONDONTWRITEBYTECODE=1 \
      PHASE0_DATABASE_URL="${PHASE0_URL}" \
      "${PYTHON_BIN}" "${BACKEND_DIR}/tests/postgres/bootstrap_baseline_schema.py"
    ;;
  fingerprint)
    require_python
    PYTHONDONTWRITEBYTECODE=1 \
      PHASE0_DATABASE_URL="${PHASE0_URL}" \
      "${PYTHON_BIN}" "${BACKEND_DIR}/scripts/schema_preflight.py"
    ;;
  verify)
    require_python
    PYTHONDONTWRITEBYTECODE=1 \
      PHASE0_DATABASE_URL="${PHASE0_URL}" \
      "${PYTHON_BIN}" "${BACKEND_DIR}/tests/postgres/verify_legacy_budget_golden.py"
    ;;
  *)
    echo "Usage: $0 {up|down|status|url|bootstrap|fingerprint|verify}" >&2
    exit 2
    ;;
esac
