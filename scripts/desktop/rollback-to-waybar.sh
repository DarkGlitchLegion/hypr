#!/usr/bin/env bash
set -euo pipefail

CONFIG_ROOT="${XDG_CONFIG_HOME:-$HOME/.config}/hypr"
STATE_ROOT="${XDG_STATE_HOME:-$HOME/.local/state}/hypr-rice"
MODE_FILE="${STATE_ROOT}/bar-mode"
SHELL_FILE="${CONFIG_ROOT}/quickshell/shell.qml"
WAYBAR_CONFIG="${CONFIG_ROOT}/waybar/config.jsonc"
WAYBAR_STYLE="${CONFIG_ROOT}/waybar/style.css"
LOG_FILE="${STATE_ROOT}/waybar.log"

if ! command -v waybar >/dev/null 2>&1; then
    printf 'Cannot roll back: Waybar is not installed.\n' >&2
    exit 127
fi

mkdir -p "${STATE_ROOT}"
previous_mode="quickshell"
previous_mode_exists=false
if [[ -f "${MODE_FILE}" ]]; then
    IFS= read -r previous_mode < "${MODE_FILE}"
    previous_mode_exists=true
fi

write_mode() {
    local mode="$1"
    local temporary
    temporary="$(mktemp "${STATE_ROOT}/.bar-mode.XXXXXX")"
    printf '%s\n' "${mode}" > "${temporary}"
    mv -f -- "${temporary}" "${MODE_FILE}"
}

restore_previous_mode() {
    if [[ "${previous_mode_exists}" == true ]]; then
        write_mode "${previous_mode}"
    else
        rm -f -- "${MODE_FILE}"
    fi
}

write_mode waybar
shell_was_running=false
if command -v qs >/dev/null 2>&1; then
    instances="$(qs list --all)"
    if grep -Fq "Config path: ${SHELL_FILE}" <<< "${instances}"; then
        shell_was_running=true
        if ! qs ipc --path "${SHELL_FILE}" call hyprshell setEnabled false; then
            restore_previous_mode
            printf 'Could not hide Quickshell; Waybar was not started.\n' >&2
            exit 1
        fi
    fi
fi

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
        restore_previous_mode
        if [[ "${shell_was_running}" == true ]]; then
            if ! qs ipc --path "${SHELL_FILE}" call hyprshell setEnabled true; then
                printf 'Waybar failed to start and Quickshell could not be re-enabled.\n' >&2
            fi
        fi
        printf 'Waybar failed to start; see %s.\n' "${LOG_FILE}" >&2
        exit 1
    fi
fi

printf 'Waybar is active. Quickshell startup is disabled until bar-mode is changed.\n'
