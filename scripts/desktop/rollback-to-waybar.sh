#!/usr/bin/env bash
set -euo pipefail

CONFIG_ROOT="${XDG_CONFIG_HOME:-$HOME/.config}/hypr"
STATE_ROOT="${XDG_STATE_HOME:-$HOME/.local/state}/hypr-rice"
MODE_FILE="${STATE_ROOT}/bar-mode"
WAYBAR_CONFIG="${CONFIG_ROOT}/waybar/config.jsonc"
WAYBAR_STYLE="${CONFIG_ROOT}/waybar/style.css"
LOG_FILE="${STATE_ROOT}/waybar.log"

if ! command -v waybar >/dev/null 2>&1; then
    printf 'Cannot roll back: Waybar is not installed.\n' >&2
    exit 127
fi

mkdir -p "${STATE_ROOT}"
write_mode() {
    local mode="$1"
    local temporary
    temporary="$(mktemp "${STATE_ROOT}/.bar-mode.XXXXXX")"
    printf '%s\n' "${mode}" > "${temporary}"
    mv -f -- "${temporary}" "${MODE_FILE}"
}

write_mode waybar

if ! pgrep -u "${UID}" -x waybar >/dev/null 2>&1; then
    waybar -c "${WAYBAR_CONFIG}" -s "${WAYBAR_STYLE}" >> "${LOG_FILE}" 2>&1 &
    waybar_pid=$!
    for attempt in {1..30}; do
        if pgrep -u "${UID}" -x waybar >/dev/null 2>&1; then
            break
        fi
        if ! kill -0 "${waybar_pid}" 2>/dev/null; then
            break
        fi
        sleep 0.1
    done
    if ! pgrep -u "${UID}" -x waybar >/dev/null 2>&1; then
        printf 'Waybar failed to start; see %s.\n' "${LOG_FILE}" >&2
        exit 1
    fi
fi

printf 'Waybar is active and selected for future sessions.\n'
