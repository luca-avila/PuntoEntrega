#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BUILD_ENV_FILE="${BUILD_ENV_FILE:-$PROJECT_ROOT/.env.build}"
TARGET="all"
PUSH_IMAGES=0

usage() {
  cat <<'USAGE'
Usage: scripts/build_images.sh [all|backend|frontend] [--push]

Builds backend and/or frontend images using .env.build.
USAGE
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
}

require_var() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "$name is required in $BUILD_ENV_FILE"
    exit 1
  fi
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      all|backend|frontend)
        TARGET="$1"
        ;;
      --push)
        PUSH_IMAGES=1
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        echo "Unknown argument: $1"
        usage
        exit 1
        ;;
    esac
    shift
  done
}

build_backend() {
  require_var BACKEND_IMAGE_REF
  echo "==> Building backend image..."
  docker build -t "$BACKEND_IMAGE_REF" "$PROJECT_ROOT/backend"

  if [[ "$PUSH_IMAGES" == "1" ]]; then
    echo "==> Pushing backend image..."
    docker push "$BACKEND_IMAGE_REF"
  fi
}

build_frontend() {
  require_var FRONTEND_IMAGE_REF
  require_var VITE_API_BASE_URL

  echo "==> Building frontend image..."
  docker build \
    --build-arg VITE_API_BASE_URL="$VITE_API_BASE_URL" \
    --build-arg VITE_GOOGLE_MAPS_API_KEY="${VITE_GOOGLE_MAPS_API_KEY:-}" \
    -t "$FRONTEND_IMAGE_REF" \
    "$PROJECT_ROOT/frontend"

  if [[ "$PUSH_IMAGES" == "1" ]]; then
    echo "==> Pushing frontend image..."
    docker push "$FRONTEND_IMAGE_REF"
  fi
}

main() {
  parse_args "$@"
  load_build_env

  case "$TARGET" in
    all)
      build_backend
      build_frontend
      ;;
    backend)
      build_backend
      ;;
    frontend)
      build_frontend
      ;;
  esac

  echo "Image build finished."
}

main "$@"
