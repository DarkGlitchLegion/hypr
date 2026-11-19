#!/usr/bin/env bash
# =====================================================================
# Restart Waybar Safely (Super + Shift + R)
# Gracefully restarts Waybar with custom rice configuration
# =====================================================================

CONFIG="${HOME}/.config/hypr/waybar/config.jsonc"
STYLE="${HOME}/.config/hypr/waybar/style.css"

killall -q waybar 2>/dev/null
while pgrep -x waybar >/dev/null; do sleep 0.1; done

if command -v hyprctl >/dev/null 2>&1; then
    hyprctl dispatch "hl.dsp.exec_cmd(\"waybar -c ${CONFIG} -s ${STYLE}\")" >/dev/null 2>&1 || waybar -c "${CONFIG}" -s "${STYLE}" >/dev/null 2>&1 &
else
    waybar -c "${CONFIG}" -s "${STYLE}" >/dev/null 2>&1 &
fi

dunstify -a "Waybar" \
         -u low \
         -i view-refresh \
         "Waybar Reloaded" \
         "Status panel restarted with active configuration." 2>/dev/null || true
