#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
INSTALLER="${SCRIPT_DIR}/scripts/setup/installer.py"

if ! command -v python3 >/dev/null 2>&1; then
    printf 'Error: Python 3 is required. Install python3, then run ./setup.sh again.\n' >&2
    exit 127
fi

if [[ ! -f "${INSTALLER}" ]]; then
    printf 'Error: installer not found: %s\n' "${INSTALLER}" >&2
    exit 1
fi

exec python3 "${INSTALLER}" --repository "${SCRIPT_DIR}" "$@"
