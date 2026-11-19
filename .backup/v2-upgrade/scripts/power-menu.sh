#!/usr/bin/env bash
# =====================================================
# Omarchy-Style System / Power Menu (Super + Escape)
# Integrates with Rofi, Hyprlock, and Systemd
# =====================================================

ROFI_CONFIG="${HOME}/.config/hypr/rofi/config.rasi"

OPTIONS="󰌾  Lock Screen\n󰤄  Suspend\n󰜉  Reboot\n󰐥  Shutdown\n󰍃  Logout\n󰑓  Reload Desktop"

CHOSEN=$(echo -e "${OPTIONS}" | rofi -dmenu -config "${ROFI_CONFIG}" -p "System")

case "${CHOSEN}" in
    *"Lock Screen"*)
        hyprlock -c "${HOME}/.config/hypr/hyprlock.conf"
        ;;
    *"Suspend"*)
        systemctl suspend
        ;;
    *"Reboot"*)
        systemctl reboot
        ;;
    *"Shutdown"*)
        systemctl poweroff
        ;;
    *"Logout"*)
        hyprctl dispatch exit
        ;;
    *"Reload Desktop"*)
        hyprctl reload && killall -SIGUSR2 waybar
        dunstify -a "System" -u low "Desktop Reloaded" "Hyprland and Waybar have been refreshed."
        ;;
esac
