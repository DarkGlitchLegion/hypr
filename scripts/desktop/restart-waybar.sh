#!/usr/bin/env bash
# =====================================================================
# Restart the selected bar, keeping this compatibility entrypoint safe.
# =====================================================================

CONFIG_ROOT="${XDG_CONFIG_HOME:-$HOME/.config}/hypr"
STATE_ROOT="${XDG_STATE_HOME:-$HOME/.local/state}/hypr-rice"
CONFIG="${CONFIG_ROOT}/waybar/config.jsonc"
STYLE="${CONFIG_ROOT}/waybar/style.css"
MODE_FILE="${STATE_ROOT}/bar-mode"
MODE="quickshell"

if [[ -f "${MODE_FILE}" ]]; then
    IFS= read -r MODE < "${MODE_FILE}"
fi

if [[ "${MODE}" != "waybar" ]]; then
    exec "${CONFIG_ROOT}/scripts/desktop/restart-bar.sh"
fi

while IFS= read -r pid; do
    [[ "${pid}" =~ ^[0-9]+$ ]] || continue
    kill -TERM "${pid}"
done < <(pgrep -u "${UID}" -x waybar || true)

for attempt in {1..30}; do
    pgrep -u "${UID}" -x waybar >/dev/null 2>&1 || break
    sleep 0.1
done
if pgrep -u "${UID}" -x waybar >/dev/null 2>&1; then
    printf 'Waybar did not stop; refusing to start a duplicate instance.\n' >&2
    exit 1
fi

mkdir -p "${STATE_ROOT}"
waybar -c "${CONFIG}" -s "${STYLE}" >> "${STATE_ROOT}/waybar.log" 2>&1 &
waybar_pid=$!
for attempt in {1..30}; do
    pgrep -u "${UID}" -x waybar >/dev/null 2>&1 && break
    if ! kill -0 "${waybar_pid}" 2>/dev/null; then
        break
    fi
    sleep 0.1
done
if ! pgrep -u "${UID}" -x waybar >/dev/null 2>&1; then
    printf 'Waybar failed to restart; see %s/waybar.log.\n' "${STATE_ROOT}" >&2
    exit 1
fi

dunstify -a "Bar" -u low -i view-refresh "Waybar Reloaded" "Fallback status panel restarted." 2>/dev/null || true
