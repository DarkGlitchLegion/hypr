#!/usr/bin/env bash
# =====================================================================
# Omarchy-Style Wallpaper Selector for Hyprland
# Keybinding: Super + Ctrl + W
# Scans: ~/.config/hypr/wallpapers/ (jpg, jpeg, png, webp)
# Theme: ~/.config/hypr/rofi/wallpaper.rasi
# =====================================================================

WALLPAPER_DIR="${HOME}/.config/hypr/wallpapers"
ROFI_THEME="${HOME}/.config/hypr/rofi/wallpaper.rasi"
SET_SCRIPT="${HOME}/.config/hypr/scripts/wallpaper/set-wallpaper.sh"

# Ensure directory exists
if [ ! -d "${WALLPAPER_DIR}" ]; then
    mkdir -p "${WALLPAPER_DIR}"
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

# Format entries as thumbnail-only cards. The index returned by Rofi is
# mapped directly back to IMAGES, so filenames never appear in the UI.
generate_menu() {
    for img in "${IMAGES[@]}"; do
        printf "\0icon\x1f%s\n" "${img}"
    done
}

CHOSEN_INDEX=$(generate_menu | rofi -dmenu -i -format i -config "${ROFI_THEME}" -p "󰸉  Wallpapers")

if [ -z "${CHOSEN_INDEX}" ] || [[ ! "${CHOSEN_INDEX}" =~ ^[0-9]+$ ]]; then
    exit 0
fi

MATCHED_PATH="${IMAGES[CHOSEN_INDEX]}"
if [ -n "${MATCHED_PATH}" ]; then
    "${SET_SCRIPT}" "${MATCHED_PATH}"
fi
