#!/usr/bin/env bash
# =====================================================================
# Hyprland Command Center
# Quick access to all desktop controls, settings, and tools
# Theme: ~/.config/hypr/rofi/command-center.rasi
# =====================================================================

ROFI_THEME="${HOME}/.config/hypr/rofi/command-center.rasi"
SCRIPTS="${HOME}/.config/hypr/scripts"

generate_commands() {
    cat << 'EOF'
<span color="#AAAAAA"><b>󰄲  Application Launcher       </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Search and launch desktop apps</span>
<span color="#AAAAAA"><b>󰞷  Terminal (Kitty)           </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Open Kitty terminal emulator</span>
<span color="#AAAAAA"><b>󰉋  File Manager (Thunar)      </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Browse local files and storage</span>
<span color="#AAAAAA"><b>󰈹  Web Browser (Firefox)      </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Launch default web browser</span>
<span color="#AAAAAA"><b>󰸉  Wallpaper Selector         </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Choose wallpaper with live thumbnails</span>
<span color="#AAAAAA"><b>󰅇  Clipboard History          </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Search, select and paste copied items</span>
<span color="#AAAAAA"><b>󰌌  Keybindings Reference      </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Search and run keyboard shortcuts</span>
<span color="#AAAAAA"><b>󰂚  Toggle Do Not Disturb      </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Mute or unmute desktop notifications</span>
<span color="#AAAAAA"><b>󰍡  Notification History       </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Browse past system notifications</span>
<span color="#AAAAAA"><b>󰑓  Restart Waybar             </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Reload top status bar</span>
<span color="#AAAAAA"><b>󰑓  Reload Hyprland Desktop    </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Refresh Hyprland configuration</span>
<span color="#AAAAAA"><b>󰒓  Hyprland Configuration     </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Open ~/.config/hypr/ in terminal</span>
<span color="#AAAAAA"><b>󰌾  Lock Screen                </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Lock screen immediately (Hyprlock)</span>
<span color="#AAAAAA"><b>󰐥  Power &amp; Session Menu       </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Lock, Suspend, Reboot, or Shutdown</span>
EOF
}

CHOSEN=$(generate_commands | rofi -dmenu -i -markup-rows -config "${ROFI_THEME}" -p "󰘳  Command Center")

if [ -z "${CHOSEN}" ]; then
    exit 0
fi

case "${CHOSEN}" in
    *"Application Launcher"*)
        rofi -show drun -config "${HOME}/.config/hypr/rofi/launcher.rasi" &
        ;;
    *"Terminal (Kitty)"*)
        kitty --config "${HOME}/.config/hypr/kitty/kitty.conf" &
        ;;
    *"File Manager"*)
        thunar &
        ;;
    *"Web Browser"*)
        firefox &
        ;;
    *"Wallpaper Selector"*)
        "${SCRIPTS}/wallpaper-selector.sh" &
        ;;
    *"Clipboard History"*)
        "${SCRIPTS}/clipboard-menu.sh" &
        ;;
    *"Keybindings Reference"*)
        "${SCRIPTS}/keybindings-menu.sh" &
        ;;
    *"Toggle Do Not Disturb"*)
        "${SCRIPTS}/notification-toggle.sh" &
        ;;
    *"Notification History"*)
        "${SCRIPTS}/notification-history.sh" &
        ;;
    *"Restart Waybar"*)
        "${SCRIPTS}/restart-waybar.sh" &
        ;;
    *"Reload Hyprland Desktop"*)
        hyprctl reload && "${SCRIPTS}/restart-waybar.sh" &
        ;;
    *"Hyprland Configuration"*)
        kitty --config "${HOME}/.config/hypr/kitty/kitty.conf" -e sh -c "cd ${HOME}/.config/hypr && ls -la && exec bash" &
        ;;
    *"Lock Screen"*)
        hyprlock -c "${HOME}/.config/hypr/hyprlock/hyprlock.conf" &
        ;;
    *"Power &"*)
        "${SCRIPTS}/power-menu.sh" &
        ;;
esac
