#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

main() {
  "$SCRIPT_DIR/dev_backend.sh"
  "$SCRIPT_DIR/dev_frontend.sh"
}

main "$@"
