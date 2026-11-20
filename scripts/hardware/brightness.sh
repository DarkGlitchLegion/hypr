#!/usr/bin/env bash
# =====================================================
# Omarchy-Style Display Brightness Control for Dunst
# Supports standard steps (5%), fine steps (1%), and min/max
# =====================================================

STEP="${2:-5}"

get_brightness() {
    brightnessctl -m | awk -F, '{print substr($4, 1, length($4)-1)}'
}

notify_brightness() {
    local val
    val=$(get_brightness)
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
