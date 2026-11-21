#!/usr/bin/env bash
# =====================================================
# Omarchy-Style Display Brightness Control for Dunst
# Supports standard steps (5%), fine steps (1%), and min/max
# =====================================================

STEP="${2:-5}"
QUICKSHELL_CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/hypr/quickshell/shell.qml"
BAR_MODE_FILE="${XDG_STATE_HOME:-$HOME/.local/state}/hypr-rice/bar-mode"

show_osd() {
    local value="$1" mode="quickshell"
    if [ -f "${BAR_MODE_FILE}" ]; then
        IFS= read -r mode < "${BAR_MODE_FILE}" || true
    fi
    [ "${mode}" = "quickshell" ] || return 1
    command -v qs >/dev/null 2>&1 || return 1
    qs ipc --path "${QUICKSHELL_CONFIG}" call hyprshell showOsd "Brightness" "${value}" "Display" >/dev/null 2>&1
}

get_brightness() {
    brightnessctl -m | awk -F, '{print substr($4, 1, length($4)-1)}'
}

notify_brightness() {
    local val
    val=$(get_brightness)
    if show_osd "${val}"; then
        return
    fi
    dunstify -a "Brightness" \
             -u low \
             -r 9994 \
             -h int:value:"${val}" \
             -i "display-brightness-symbolic" \
             "Brightness: ${val}%"
}

case "$1" in
    up)
        brightnessctl set "${STEP}%+" >/dev/null 2>&1
        notify_brightness
        ;;
    down)
        brightnessctl set "${STEP}%-" >/dev/null 2>&1
        notify_brightness
        ;;
    max)
        brightnessctl set 100% >/dev/null 2>&1
        notify_brightness
        ;;
    min)
        brightnessctl set 5% >/dev/null 2>&1
        notify_brightness
        ;;
    *)
        echo "Usage: $0 {up [step]|down [step]|max|min}"
        exit 1
        ;;
esac
