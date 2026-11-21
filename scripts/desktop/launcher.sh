#!/usr/bin/env bash
set -euo pipefail

CONFIG_ROOT="${XDG_CONFIG_HOME:-$HOME/.config}/hypr"
STATE_ROOT="${XDG_STATE_HOME:-$HOME/.local/state}/hypr-rice"
MODE_FILE="${STATE_ROOT}/bar-mode"
MODE="quickshell"

if [[ -f "${MODE_FILE}" ]]; then
    IFS= read -r MODE < "${MODE_FILE}"
fi

if [[ "${MODE}" == "quickshell" ]] && command -v qs >/dev/null 2>&1; then
    if qs ipc --path "${CONFIG_ROOT}/quickshell/shell.qml" call hyprshell toggleLauncher >/dev/null 2>&1; then
        exit 0
    fi
fi

exec rofi -show drun -config "${CONFIG_ROOT}/rofi/launcher.rasi"
