#!/usr/bin/env bash
set -euo pipefail

CONFIG_ROOT="${XDG_CONFIG_HOME:-$HOME/.config}/hypr"
STATE_ROOT="${XDG_STATE_HOME:-$HOME/.local/state}/hypr-rice"
MODE_FILE="${STATE_ROOT}/bar-mode"
MODE="quickshell"

if [[ -f "${MODE_FILE}" ]]; then
    IFS= read -r MODE < "${MODE_FILE}"
fi

stop_waybar() {
    local pid
    while IFS= read -r pid; do
        [[ "${pid}" =~ ^[0-9]+$ ]] || continue
        kill -TERM "${pid}" 2>/dev/null || true
    done < <(pgrep -u "${UID}" -x waybar || true)
    for attempt in {1..30}; do
        pgrep -u "${UID}" -x waybar >/dev/null 2>&1 || return 0
        sleep 0.1
    done
    printf 'Waybar did not stop; refusing to start Quickshell alongside it.\n' >&2
    return 1
}

case "${MODE}" in
    quickshell)
        if ! command -v qs >/dev/null 2>&1; then
            printf 'Quickshell is selected but qs is not installed.\n' >&2
            exit 127
        fi
        stop_waybar
        exec qs --no-duplicate --daemonize --path "${CONFIG_ROOT}/quickshell/shell.qml"
        ;;
    waybar)
        if ! command -v waybar >/dev/null 2>&1; then
            printf 'Waybar fallback is selected but waybar is not installed.\n' >&2
            exit 127
        fi
        if command -v qs >/dev/null 2>&1; then
            instances="$(qs list --all)"
            if grep -Fq "Config path: ${CONFIG_ROOT}/quickshell/shell.qml" <<< "${instances}"; then
                if ! qs ipc --path "${CONFIG_ROOT}/quickshell/shell.qml" call hyprshell setEnabled false; then
                    printf 'Could not hide Quickshell; Waybar was not started.\n' >&2
                    exit 1
                fi
            fi
        fi
        if pgrep -u "${UID}" -x waybar >/dev/null 2>&1; then
            exit 0
        fi
        exec waybar -c "${CONFIG_ROOT}/waybar/config.jsonc" -s "${CONFIG_ROOT}/waybar/style.css"
        ;;
    *)
        printf 'Unknown bar mode "%s" in %s; expected quickshell or waybar.\n' "${MODE}" "${MODE_FILE}" >&2
        exit 2
        ;;
esac
