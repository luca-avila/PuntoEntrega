#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yaml"
BUILD_ENV_FILE="${BUILD_ENV_FILE:-$PROJECT_ROOT/.env.build}"
BACKEND_ENV_FILE="${BACKEND_ENV_FILE:-$PROJECT_ROOT/.env.backend}"
SERVICE_NAME="backend"
WORKER_SERVICE_NAME="worker"
DB_SERVICE_NAME="db"
HEALTHCHECK_URL="${HEALTHCHECK_URL:-http://127.0.0.1:8002/health}"

require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    echo "This script must be run with sudo."
    echo "Use: sudo $0"
    exit 1
  fi
}

check_paths() {
  if [[ ! -f "$COMPOSE_FILE" ]]; then
    echo "docker-compose file not found: $COMPOSE_FILE"
    exit 1
  fi

  if [[ ! -f "$BUILD_ENV_FILE" ]]; then
    echo "Build env file not found: $BUILD_ENV_FILE"
    exit 1
  fi

  if [[ ! -f "$BACKEND_ENV_FILE" ]]; then
    echo "Backend env file not found: $BACKEND_ENV_FILE"
    exit 1
  fi
}

compose() {
  BACKEND_ENV_FILE="$BACKEND_ENV_FILE" docker compose \
    --env-file "$BUILD_ENV_FILE" \
    -f "$COMPOSE_FILE" \
    "$@"
}

healthcheck() {
  echo "==> Running backend health check..."
  for _ in {1..20}; do
    if curl -fsS "$HEALTHCHECK_URL" >/dev/null; then
      echo "Backend health check passed."
      return 0
    fi
    sleep 1
  done

  echo "Backend health check failed: $HEALTHCHECK_URL"
  return 1
}

wait_for_db_health() {
  echo "==> Waiting for database health..."
  local db_container_id
  db_container_id="$(compose ps -q "$DB_SERVICE_NAME")"
  if [[ -z "$db_container_id" ]]; then
    echo "Could not resolve container id for service: $DB_SERVICE_NAME"
    return 1
  fi

  for _ in {1..60}; do
    local health_status
    health_status="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}unknown{{end}}' "$db_container_id")"
    if [[ "$health_status" == "healthy" ]]; then
      echo "Database is healthy."
      return 0
    fi
    sleep 1
  done

  echo "Database did not become healthy in time."
  return 1
}

run_migrations() {
  echo "==> Running database migrations..."
  compose run --rm "$SERVICE_NAME" uv run alembic upgrade head
  echo "Database migrations applied."
}

main() {
  require_root
  check_paths

  cd "$PROJECT_ROOT"

  echo "==> Validating Compose configuration..."
  compose config --quiet

  echo "==> Starting database service..."
  compose up -d "$DB_SERVICE_NAME"
  wait_for_db_health

  run_migrations

  echo "==> Recreating backend and worker containers..."
  compose up -d --force-recreate "$SERVICE_NAME" "$WORKER_SERVICE_NAME"

  healthcheck

  echo "==> Last backend logs:"
  compose logs --tail=50 "$SERVICE_NAME"

  echo "Backend deployed successfully."
}

main "$@"
