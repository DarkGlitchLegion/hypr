#!/usr/bin/env bash
# =====================================================================
# Notification DND Status Provider for Waybar (custom/dnd)
# =====================================================================

IS_PAUSED="false"
if command -v dunstctl >/dev/null 2>&1; then
    IS_PAUSED=$(dunstctl is-paused 2>/dev/null || echo "false")
fi

if [ "${IS_PAUSED}" = "true" ]; then
    echo '{"text":"󰂛","tooltip":"Do Not Disturb: ON (Notifications Silenced)","class":"paused","alt":"paused"}'
else
    echo '{"text":"󰂚","tooltip":"Do Not Disturb: OFF (Notifications Active)","class":"active","alt":"active"}'
fi
