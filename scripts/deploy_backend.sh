#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yaml"
SERVICE_NAME="backend"
HEALTHCHECK_URL="http://127.0.0.1:8002/health"

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
}

healthcheck() {
  echo "==> Running backend health check..."
  for i in {1..20}; do
    if curl -fsS "$HEALTHCHECK_URL" >/dev/null; then
      echo "✅ Backend health check passed."
      return 0
    fi
    sleep 1
  done

  echo "❌ Backend health check failed: $HEALTHCHECK_URL"
  return 1
}

main() {
  require_root
  check_paths

  cd "$PROJECT_ROOT"

  echo "==> Building backend image..."
  docker compose -f "$COMPOSE_FILE" build "$SERVICE_NAME"

  echo "==> Recreating backend container..."
  docker compose -f "$COMPOSE_FILE" up -d --force-recreate "$SERVICE_NAME"

  healthcheck

  echo "==> Last backend logs:"
  docker compose -f "$COMPOSE_FILE" logs --tail=50 "$SERVICE_NAME"

  echo "✅ Backend deployed successfully."
}

main "$@"