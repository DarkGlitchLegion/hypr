#!/usr/bin/env bash
# =====================================================================
# Omarchy-Style Wallpaper Selector for Hyprland
# Keybinding: Super + Ctrl + W
# Scans: ~/.config/hypr/wallpapers/ (jpg, jpeg, png, webp)
# Theme: ~/.config/hypr/rofi/wallpaper.rasi
# =====================================================================

WALLPAPER_DIR="${HOME}/.config/hypr/wallpapers"
ROFI_THEME="${HOME}/.config/hypr/rofi/wallpaper.rasi"
CURRENT_FILE="${HOME}/.config/hypr/state/current_wallpaper"
SET_SCRIPT="${HOME}/.config/hypr/scripts/set-wallpaper.sh"

# Ensure directory exists
if [ ! -d "${WALLPAPER_DIR}" ]; then
    mkdir -p "${WALLPAPER_DIR}"
fi

# Detect current active wallpaper
CURRENT_WALL=""
if [ -f "${CURRENT_FILE}" ]; then
    CURRENT_WALL=$(cat "${CURRENT_FILE}" 2>/dev/null)
fi
if [ -z "${CURRENT_WALL}" ] && [ -f "${HOME}/.config/hypr/hyprpaper/hyprpaper.conf" ]; then
    CURRENT_WALL=$(grep -E "^wallpaper\s*=" "${HOME}/.config/hypr/hyprpaper/hyprpaper.conf" | awk -F, '{print $2}' | xargs)
fi

# Collect supported image files (jpg, jpeg, png, webp)
mapfile -d '' IMAGES < <(find "${WALLPAPER_DIR}" -maxdepth 1 -type f \( -iname "*.png" -o -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.webp" \) -print0 | sort -z)

if [ ${#IMAGES[@]} -eq 0 ]; then
    dunstify -a "Wallpaper" \
             -u normal \
             "No Wallpapers Found" \
             "Place PNG, JPG, or WEBP images in ~/.config/hypr/wallpapers/" 2>/dev/null || true
    exit 0
fi

# Format entries for Rofi with thumbnails and active indicator
generate_menu() {
    for img in "${IMAGES[@]}"; do
        base=$(basename "${img}")
        if [ "${img}" = "${CURRENT_WALL}" ]; then
            label="<span color='#AAAAAA'><b>✔  ${base}</b></span>  <span color='#888888'><i>(Current)</i></span>"
        else
            label="<span color='#D5D5D5'>   ${base}</span>"
        fi
        # Rofi icon metadata: text\0icon\x1fpath
        printf "%s\0icon\x1f%s\n" "${label}" "${img}"
    done
}

CHOSEN_LABEL=$(generate_menu | rofi -dmenu -i -markup-rows -config "${ROFI_THEME}" -p "󰸉  Wallpapers")

if [ -z "${CHOSEN_LABEL}" ]; then
    exit 0
fi

# Match selected label back to the file path
CLEAN_NAME=$(echo "${CHOSEN_LABEL}" | sed -E 's/<[^>]*>//g' | sed -E 's/^[✔ ]*//' | sed -E 's/\(Current\)//' | xargs)

MATCHED_PATH=""
for img in "${IMAGES[@]}"; do
    if [ "$(basename "${img}")" = "${CLEAN_NAME}" ]; then
        MATCHED_PATH="${img}"
        break
    fi
done

if [ -n "${MATCHED_PATH}" ]; then
    "${SET_SCRIPT}" "${MATCHED_PATH}"
fi
