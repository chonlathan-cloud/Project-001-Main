#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

export BOQ_TEST_DB_COMPOSE_FILE="${BACKEND_DIR}/tests/postgres/docker-compose.phase6-pg18.yml"
export BOQ_TEST_DB_COMPOSE_PROJECT="projects001_phase6_pg18"
export BOQ_TEST_DATABASE_URL="postgresql+asyncpg://phase6:phase6@127.0.0.1:55435/projects001_phase6_test"

exec "${SCRIPT_DIR}/phase1_test_db.sh" "$@"
