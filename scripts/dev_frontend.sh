#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
FRONTEND_ENV_FILE="${FRONTEND_ENV_FILE:-$FRONTEND_DIR/.env}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-5173}"

load_frontend_env() {
  if [[ -f "$FRONTEND_ENV_FILE" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$FRONTEND_ENV_FILE"
    set +a
  fi
}

main() {
  if [[ ! -d "$FRONTEND_DIR" ]]; then
    echo "Frontend directory not found: $FRONTEND_DIR"
    exit 1
  fi

  cd "$FRONTEND_DIR"
  load_frontend_env

  if [[ ! -d node_modules ]]; then
    echo "==> Installing frontend dependencies..."
    npm install
  fi

  echo "==> Starting Vite dev server..."
  exec npm run dev -- --host "$HOST" --port "$PORT"
}

main "$@"
