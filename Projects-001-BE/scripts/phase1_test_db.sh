#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${BOQ_TEST_DB_COMPOSE_FILE:-${BACKEND_DIR}/tests/postgres/docker-compose.phase1.yml}"
COMPOSE_PROJECT="${BOQ_TEST_DB_COMPOSE_PROJECT:-projects001_phase1}"
TEST_URL="${BOQ_TEST_DATABASE_URL:-postgresql+asyncpg://phase1:phase1@127.0.0.1:55433/projects001_phase1_test}"
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

alembic() {
  PYTHONDONTWRITEBYTECODE=1 \
    ALEMBIC_DATABASE_URL="${TEST_URL}" \
    "${PYTHON_BIN}" -m alembic -c "${BACKEND_DIR}/alembic.ini" "$@"
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
    echo "${TEST_URL}"
    ;;
  upgrade-empty)
    require_python
    alembic upgrade head
    ;;
  upgrade-current)
    require_python
    PYTHONDONTWRITEBYTECODE=1 TEST_DATABASE_URL="${TEST_URL}" \
      "${PYTHON_BIN}" "${BACKEND_DIR}/tests/postgres/bootstrap_baseline_schema.py"
    alembic stamp 20260915_0000
    alembic upgrade head
    ;;
  check)
    require_python
    alembic check
    ;;
  current)
    require_python
    alembic current
    ;;
  golden)
    require_python
    PYTHONDONTWRITEBYTECODE=1 PHASE0_DATABASE_URL="${TEST_URL}" \
      "${PYTHON_BIN}" "${BACKEND_DIR}/tests/postgres/verify_legacy_budget_golden.py"
    ;;
  verify)
    require_python
    PYTHONDONTWRITEBYTECODE=1 PHASE1_DATABASE_URL="${TEST_URL}" \
      "${PYTHON_BIN}" "${BACKEND_DIR}/tests/postgres/verify_phase1_schema.py"
    ;;
  finance-history)
    require_python
    PYTHONDONTWRITEBYTECODE=1 PHASE1_DATABASE_URL="${TEST_URL}" \
      "${PYTHON_BIN}" "${BACKEND_DIR}/tests/postgres/verify_phase1_finance_history.py"
    ;;
  funds)
    require_python
    PYTHONDONTWRITEBYTECODE=1 PHASE1_DATABASE_URL="${TEST_URL}" \
      "${PYTHON_BIN}" "${BACKEND_DIR}/tests/postgres/verify_phase1_funds.py"
    ;;
  phase5-cutover)
    require_python
    PYTHONDONTWRITEBYTECODE=1 PHASE5_DATABASE_URL="${TEST_URL}" \
      "${PYTHON_BIN}" "${BACKEND_DIR}/tests/postgres/verify_phase5_cutover.py"
    ;;
  *)
    echo "Usage: $0 {up|down|status|url|upgrade-empty|upgrade-current|check|current|golden|verify|finance-history|funds|phase5-cutover}" >&2
    exit 2
    ;;
esac
