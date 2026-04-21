#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

main() {
  "$SCRIPT_DIR/deploy_backend.sh"
  "$SCRIPT_DIR/deploy_frontend.sh"
}

main "$@"
