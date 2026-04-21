#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BUILD_ENV_FILE="${BUILD_ENV_FILE:-$PROJECT_ROOT/.env.build}"
TARGET_DIR="${FRONTEND_TARGET_DIR:-/var/www/PuntoEntrega}"
TEMP_CONTAINER="puntoentrega-frontend-artifact-$$"

cleanup() {
  docker rm -f "$TEMP_CONTAINER" >/dev/null 2>&1 || true
}
trap cleanup EXIT

require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    echo "This script must be run with sudo."
    echo "Use: sudo $0"
    exit 1
  fi
}

load_build_env() {
  if [[ ! -f "$BUILD_ENV_FILE" ]]; then
    echo "Build env file not found: $BUILD_ENV_FILE"
    exit 1
  fi

  set -a
  # shellcheck disable=SC1090
  source "$BUILD_ENV_FILE"
  set +a

  if [[ -z "${FRONTEND_IMAGE_REF:-}" ]]; then
    echo "FRONTEND_IMAGE_REF is required in $BUILD_ENV_FILE"
    exit 1
  fi
}

check_paths() {
  mkdir -p "$TARGET_DIR"
}

reload_nginx() {
  if [[ "${SKIP_NGINX_RELOAD:-0}" == "1" ]]; then
    echo "==> Skipping nginx reload."
    return
  fi

  echo "==> Testing nginx config..."
  nginx -t

  echo "==> Reloading nginx..."
  systemctl reload nginx
}

main() {
  require_root
  load_build_env
  check_paths

  cd "$PROJECT_ROOT"

  echo "==> Pulling frontend artifact image..."
  docker pull "$FRONTEND_IMAGE_REF"

  echo "==> Creating temp container..."
  docker create --name "$TEMP_CONTAINER" "$FRONTEND_IMAGE_REF" >/dev/null

  echo "==> Clearing target directory..."
  rm -rf "${TARGET_DIR:?}"/*

  echo "==> Copying dist contents to $TARGET_DIR ..."
  docker cp "$TEMP_CONTAINER":/out/dist/. "$TARGET_DIR"/

  echo "==> Verifying extracted artifact..."
  if [[ ! -f "$TARGET_DIR/index.html" ]]; then
    echo "Deployment failed: $TARGET_DIR/index.html was not found."
    exit 1
  fi

  echo "==> Fixing permissions..."
  chown -R www-data:www-data "$TARGET_DIR"
  find "$TARGET_DIR" -type d -exec chmod 755 {} \;
  find "$TARGET_DIR" -type f -exec chmod 644 {} \;

  reload_nginx

  echo "Frontend deployed successfully."
}

main "$@"
