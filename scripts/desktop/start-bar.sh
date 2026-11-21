#!/usr/bin/env bash
set -euo pipefail

CONFIG_ROOT="${XDG_CONFIG_HOME:-$HOME/.config}/hypr"
STATE_ROOT="${XDG_STATE_HOME:-$HOME/.local/state}/hypr-rice"
MODE_FILE="${STATE_ROOT}/bar-mode"
MODE="quickshell"

if [[ -f "${MODE_FILE}" ]]; then
    IFS= read -r MODE < "${MODE_FILE}"
fi

case "${MODE}" in
    quickshell)
        if ! command -v qs >/dev/null 2>&1; then
            printf 'Quickshell is selected but qs is not installed.\n' >&2
            exit 127
        fi
        exec qs --no-duplicate --daemonize --path "${CONFIG_ROOT}/quickshell/shell.qml"
        ;;
    waybar)
        if ! command -v waybar >/dev/null 2>&1; then
            printf 'Waybar fallback is selected but waybar is not installed.\n' >&2
            exit 127
        fi
        exec waybar -c "${CONFIG_ROOT}/waybar/config.jsonc" -s "${CONFIG_ROOT}/waybar/style.css"
        ;;
    *)
        printf 'Unknown bar mode "%s" in %s; expected quickshell or waybar.\n' "${MODE}" "${MODE_FILE}" >&2
        exit 2
        ;;
esac
