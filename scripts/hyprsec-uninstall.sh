#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v podman >/dev/null 2>&1; then
    printf 'Podman is not installed; no container could be removed.\n'
    exit 0
fi

"${SCRIPT_DIR}/hyprsec-box.sh" remove
printf 'HyprSec container removal requested. Workspace and configuration were preserved.\n'
