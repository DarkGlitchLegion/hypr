#!/usr/bin/env bash

set -euo pipefail

HYPR_DIR="${HOME}/.config/hypr"
CURRENT_FILE="${HYPR_DIR}/current_wallpaper"
HYPRPAPER_CONF="${HYPR_DIR}/hyprpaper.conf"
DEFAULT_WALLPAPER="${HYPR_DIR}/wallpapers/spiderman.png"

save_wallpaper() {
    local path="$1"
    local temp_file

    temp_file=$(mktemp "${CURRENT_FILE}.XXXXXX")
    printf '%s\n' "${path}" > "${temp_file}"
    chmod 644 "${temp_file}"
    mv -f -- "${temp_file}" "${CURRENT_FILE}"
}

wallpaper=""
if [[ -r "${CURRENT_FILE}" ]]; then
    IFS= read -r wallpaper < "${CURRENT_FILE}" || true
fi

if [[ -z "${wallpaper}" ]] || ! wallpaper=$(realpath -e -- "${wallpaper}" 2>/dev/null) || [[ ! -f "${wallpaper}" ]]; then
    wallpaper=$(realpath -e -- "${DEFAULT_WALLPAPER}") || {
        printf 'Wallpaper restore failed: saved wallpaper is unavailable and fallback is missing: %s\n' "${DEFAULT_WALLPAPER}" >&2
        exit 1
    }
    printf 'Saved wallpaper is unavailable; using fallback: %s\n' "${wallpaper}" >&2
    save_wallpaper "${wallpaper}"
fi

if [[ "${wallpaper}" == *$'\n'* ]]; then
    printf 'Wallpaper restore failed: wallpaper paths cannot contain newlines.\n' >&2
    exit 1
fi

config_tmp=$(mktemp "${HYPRPAPER_CONF}.XXXXXX")
trap 'rm -f -- "${config_tmp}"' EXIT
printf 'splash = false\nipc = on\nwallpaper {\n    monitor = *\n    path = %s\n    fit_mode = cover\n}\n' \
    "${wallpaper}" > "${config_tmp}"
chmod 644 "${config_tmp}"
mv -f -- "${config_tmp}" "${HYPRPAPER_CONF}"
trap - EXIT

restart_hyprpaper() {
    local pid
    local running
    local -a pids=()

    mapfile -t pids < <(pgrep -x hyprpaper || true)
    if ((${#pids[@]})); then
        for pid in "${pids[@]}"; do
            kill -TERM "${pid}" || {
                printf 'Wallpaper restore failed: could not stop hyprpaper (PID %s).\n' "${pid}" >&2
                return 1
            }
        done

        for _ in {1..5}; do
            running=0
            for pid in "${pids[@]}"; do
                if kill -0 "${pid}" 2>/dev/null; then
                    running=1
                    break
                fi
            done
            ((running == 0)) && break
            sleep 0.1
        done

        if ((running)); then
            printf 'Wallpaper restore failed: hyprpaper did not stop in time.\n' >&2
            return 1
        fi
    fi

    exec hyprpaper -c "${HYPRPAPER_CONF}"
}

# hyprpaper's control socket is separate from hyprctl; restart from the saved config.
restart_hyprpaper &
daemon_pid=$!
for _ in {1..10}; do
    if ! kill -0 "${daemon_pid}" 2>/dev/null; then
        wait "${daemon_pid}" || exit 1
        printf 'Wallpaper restore failed: hyprpaper did not start.\n' >&2
        exit 1
    fi
    sleep 0.1
done
