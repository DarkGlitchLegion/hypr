#!/usr/bin/env bash
# =====================================================================
# Hyprlock Ambient Status Provider
# Ultra-lightweight status queries for Hyprlock lock screen
# =====================================================================

MODE="${1:-combined}"

get_battery() {
    BAT_PATH=$(find /sys/class/power_supply/ -name "BAT*" | head -n 1)
    if [ -n "${BAT_PATH}" ] && [ -f "${BAT_PATH}/capacity" ]; then
        CAP=$(cat "${BAT_PATH}/capacity" 2>/dev/null || echo "100")
        STATUS=$(cat "${BAT_PATH}/status" 2>/dev/null || echo "Discharging")
        
        if [ "${STATUS}" = "Charging" ] || [ "${STATUS}" = "Full" ]; then
            ICON="󰂄"
            COLOR="#AAAAAA"
        else
            if [ "${CAP}" -ge 90 ]; then ICON="󰁹"; COLOR="#888888";
            elif [ "${CAP}" -ge 70 ]; then ICON="󰂁"; COLOR="#888888";
            elif [ "${CAP}" -ge 50 ]; then ICON="󰁿"; COLOR="#888888";
            elif [ "${CAP}" -ge 30 ]; then ICON="󰁽"; COLOR="#EBCB8B";
            elif [ "${CAP}" -ge 15 ]; then ICON="󰁻"; COLOR="#EBCB8B";
            else ICON="󰂃"; COLOR="#BF616A";
            fi
        fi
        echo "<span color='${COLOR}'>${ICON} ${CAP}%</span>"
    else
        echo "<span color='#888888'>󰚥 AC</span>"
    fi
}

get_network() {
    # Check if nmcli is available to get connected SSID
    SSID=""
    if command -v nmcli >/dev/null 2>&1; then
        SSID=$(nmcli -t -f active,ssid dev wifi 2>/dev/null | grep '^yes:' | cut -d':' -f2 | head -n 1)
    fi

    if [ -n "${SSID}" ]; then
        echo "<span color='#888888'>󰤨  ${SSID}</span>"
    else
        # Check if any non-loopback interface is operational
        UP_IF=$(ip -br link 2>/dev/null | grep 'UP' | grep -v 'lo' | awk '{print $1}' | head -n 1)
        if [ -n "${UP_IF}" ]; then
            echo "<span color='#888888'>󰈀  Online</span>"
        else
            echo "<span color='#666666'>󰤭  Offline</span>"
        fi
    fi
}

get_user_greeting() {
    USER_NAME=$(whoami)
    HOUR=$(date +%H)
    if [ "${HOUR}" -ge 5 ] && [ "${HOUR}" -lt 12 ]; then
        GREET="Good morning"
    elif [ "${HOUR}" -ge 12 ] && [ "${HOUR}" -lt 18 ]; then
        GREET="Good afternoon"
    elif [ "${HOUR}" -ge 18 ] && [ "${HOUR}" -lt 22 ]; then
        GREET="Good evening"
    else
        GREET="Working late"
    fi
    echo "${GREET}, ${USER_NAME}"
}

case "${MODE}" in
    battery)
        get_battery
        ;;
    network)
        get_network
        ;;
    greeting)
        get_user_greeting
        ;;
    combined)
        BAT=$(get_battery)
        NET=$(get_network)
        echo "${NET}   <span color='#333333'>│</span>   ${BAT}"
        ;;
    *)
        echo ""
        ;;
esac
