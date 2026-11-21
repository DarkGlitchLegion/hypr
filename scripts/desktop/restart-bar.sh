#!/usr/bin/env bash
set -euo pipefail

CONFIG_ROOT="${XDG_CONFIG_HOME:-$HOME/.config}/hypr"
SCRIPTS_ROOT="${CONFIG_ROOT}/scripts"
STATE_ROOT="${XDG_STATE_HOME:-$HOME/.local/state}/hypr-rice"
MODE_FILE="${STATE_ROOT}/bar-mode"
MODE="quickshell"

if [[ -f "${MODE_FILE}" ]]; then
    IFS= read -r MODE < "${MODE_FILE}"
fi

case "${MODE}" in
    quickshell)
        if qs ipc --path "${CONFIG_ROOT}/quickshell/shell.qml" show >/dev/null 2>&1; then
            exec qs ipc --path "${CONFIG_ROOT}/quickshell/shell.qml" call hyprshell reload
        fi
        exec "${SCRIPTS_ROOT}/desktop/start-bar.sh"
        ;;
    waybar)
        exec "${SCRIPTS_ROOT}/desktop/restart-waybar.sh"
        ;;
    *)
        printf 'Unknown bar mode "%s" in %s.\n' "${MODE}" "${MODE_FILE}" >&2
        exit 2
        ;;
esac
