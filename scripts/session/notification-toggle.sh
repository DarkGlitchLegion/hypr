#!/usr/bin/env bash
# =====================================================================
# Notification Do Not Disturb (DND) Toggle (Super + Shift + D)
# Controls Dunst pause state and refreshes Waybar DND status indicator
# =====================================================================

if command -v dunstctl >/dev/null 2>&1; then
    dunstctl set-paused toggle 2>/dev/null || true

    IS_PAUSED=$(dunstctl is-paused 2>/dev/null || echo "false")

    # Refresh Waybar custom/dnd module immediately
    pkill -RTMIN+8 waybar 2>/dev/null || true

    if [ "${IS_PAUSED}" = "false" ]; then
        dunstify -a "Notifications" \
                 -u low \
                 -i preferences-system-notifications \
                 "Do Not Disturb: OFF" \
                 "Notifications are now active." 2>/dev/null || true
    fi
fi
