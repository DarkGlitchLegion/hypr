#!/usr/bin/env bash
# =====================================================
# Clipboard History Selector (Super + Ctrl + V)
# Integrates cliphist with Rofi and wl-copy
# =====================================================

ROFI_CONFIG="${HOME}/.config/hypr/rofi/config.rasi"

if command -v cliphist >/dev/null 2>&1; then
    cliphist list | rofi -dmenu -config "${ROFI_CONFIG}" -p "Clipboard" | cliphist decode | wl-copy
else
    # Simple clipboard inspection fallback if cliphist is not yet installed
    CURRENT=$(wl-paste 2>/dev/null)
    if [ -n "${CURRENT}" ]; then
        dunstify -a "Clipboard" -u low "Clipboard Current Content" "${CURRENT}"
    else
        dunstify -a "Clipboard" -u low "Clipboard Empty" "Install cliphist for full history: sudo pacman -S cliphist"
    fi
fi
