#!/usr/bin/env bash
# =====================================================================
# Set and Persist Wallpaper for Hyprland (hyprpaper + hyprlock)
# =====================================================================

WALLPAPER="$1"
HYPR_DIR="${HOME}/.config/hypr"
HYPRPAPER_CONF="${HYPR_DIR}/hyprpaper.conf"
HYPRLOCK_CONF="${HYPR_DIR}/hyprlock.conf"
CURRENT_FILE="${HYPR_DIR}/current_wallpaper"

if [ -z "${WALLPAPER}" ] || [ ! -f "${WALLPAPER}" ]; then
    dunstify -a "Wallpaper" -u critical "Wallpaper Error" "File not found: ${WALLPAPER}"
    exit 1
fi

# 1. Save current wallpaper path
echo "${WALLPAPER}" > "${CURRENT_FILE}"

# 2. Update hyprpaper.conf for session persistence across reboots
cat << EOF > "${HYPRPAPER_CONF}"
preload = ${WALLPAPER}
wallpaper = ,${WALLPAPER}
splash = false
ipc = on
EOF

# 3. Synchronize hyprlock.conf background
if [ -f "${HYPRLOCK_CONF}" ]; then
    sed -i "s|path = .*|path = ${WALLPAPER}|" "${HYPRLOCK_CONF}"
fi

# 4. Apply immediately to running hyprpaper instance without restart
if pgrep -x hyprpaper >/dev/null 2>&1; then
    hyprctl hyprpaper preload "${WALLPAPER}" 2>/dev/null
    hyprctl hyprpaper wallpaper ",${WALLPAPER}" 2>/dev/null
    hyprctl hyprpaper unload unused 2>/dev/null
else
    # Start hyprpaper if not already running
    hyprpaper -c "${HYPRPAPER_CONF}" &
fi

# 5. Send confirmation notification with thumbnail
WALL_NAME=$(basename "${WALLPAPER}")
dunstify -a "Wallpaper" \
         -u low \
         -i "${WALLPAPER}" \
         "Wallpaper Changed" \
         "Active: ${WALL_NAME}" 2>/dev/null || true
