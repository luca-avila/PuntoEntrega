#!/usr/bin/env bash
set -Eeuo pipefail

IMAGE_NAME="frontend-image"
TEMP_CONTAINER="frontend-artifact"
FRONTEND_DIR="frontend"
TARGET_DIR="/var/www/PuntoEntrega"

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

check_paths() {
  if [[ ! -d "$FRONTEND_DIR" ]]; then
    echo "Frontend directory not found: $FRONTEND_DIR"
    exit 1
  fi

  if [[ ! -f "$FRONTEND_DIR/Dockerfile" ]]; then
    echo "Dockerfile not found in: $FRONTEND_DIR"
    exit 1
  fi

  mkdir -p "$TARGET_DIR"
}

main() {
  require_root
  check_paths

  echo "==> Building frontend image..."
  docker build -t "$IMAGE_NAME" "$FRONTEND_DIR"

  echo "==> Removing old temp container if it exists..."
  docker rm -f "$TEMP_CONTAINER" >/dev/null 2>&1 || true

  echo "==> Creating temp container..."
  docker create --name "$TEMP_CONTAINER" "$IMAGE_NAME" >/dev/null

  echo "==> Clearing target directory..."
  rm -rf "${TARGET_DIR:?}"/*

  echo "==> Copying dist contents to $TARGET_DIR ..."
  docker cp "$TEMP_CONTAINER":/out/dist/. "$TARGET_DIR"/

  echo "==> Verifying extracted artifact..."
  if [[ ! -f "$TARGET_DIR/index.html" ]]; then
    echo "Deployment failed: $TARGET_DIR/index.html was not found."
    echo "The dist artifact may have been copied incorrectly."
    exit 1
  fi

  echo "==> Fixing permissions..."
  chown -R www-data:www-data "$TARGET_DIR"
  find "$TARGET_DIR" -type d -exec chmod 755 {} \;
  find "$TARGET_DIR" -type f -exec chmod 644 {} \;

  echo "==> Testing nginx config..."
  nginx -t

  echo "==> Reloading nginx..."
  systemctl reload nginx

  echo "✅ Frontend deployed successfully."
}

main "$@"