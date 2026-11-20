#!/usr/bin/env bash
# =====================================================================
# Set and Persist Wallpaper for Hyprland (hyprpaper + hyprlock)
# =====================================================================

WALLPAPER="$1"
HYPR_DIR="${HOME}/.config/hypr"
HYPRLOCK_DIR_CONF="${HYPR_DIR}/hyprlock/hyprlock.conf"
CURRENT_FILE="${HYPR_DIR}/state/current_wallpaper"
RESTORE_SCRIPT="${HYPR_DIR}/scripts/restore-wallpaper.sh"

if [ -z "${WALLPAPER}" ] || ! WALLPAPER=$(realpath -e -- "${WALLPAPER}" 2>/dev/null) || [ ! -f "${WALLPAPER}" ]; then
    dunstify -a "Wallpaper" -u critical "Wallpaper Error" "File not found: ${WALLPAPER}" 2>/dev/null || true
    exit 1
fi

if [[ "${WALLPAPER}" == *$'\n'* ]]; then
    dunstify -a "Wallpaper" -u critical "Wallpaper Error" "Wallpaper paths cannot contain newlines." 2>/dev/null || true
    exit 1
fi

mkdir -p "${HYPR_DIR}"
state_tmp=$(mktemp "${CURRENT_FILE}.XXXXXX") || exit 1
trap 'rm -f -- "${state_tmp}"' EXIT
printf '%s\n' "${WALLPAPER}" > "${state_tmp}" || exit 1
chmod 644 "${state_tmp}" || exit 1
mv -f -- "${state_tmp}" "${CURRENT_FILE}" || exit 1
trap - EXIT

# Keep the lock screen background in sync with the selected desktop wallpaper.
if [ -f "${HYPRLOCK_DIR_CONF}" ]; then
    sed -i "s|path = .*|path = ${WALLPAPER}|" "${HYPRLOCK_DIR_CONF}"
fi

if ! "${RESTORE_SCRIPT}"; then
    dunstify -a "Wallpaper" -u critical "Wallpaper Error" "Saved ${WALLPAPER}, but could not apply it." 2>/dev/null || true
    exit 1
fi

WALL_NAME=$(basename "${WALLPAPER}")
dunstify -a "Wallpaper" \
         -u low \
         -i "${WALLPAPER}" \
         "Wallpaper Changed" \
         "Active: ${WALL_NAME}" 2>/dev/null || true
