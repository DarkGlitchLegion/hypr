#!/usr/bin/env bash
# =====================================================================
# Hyprland Keybindings Reference Window (Super + K)
# Renders a dedicated, styled modal window with fuzzy search
# Shows Shortcut on the left and Function Description on the right
# Pressing Enter on any item executes the corresponding action.
# =====================================================================

ROFI_THEME="${HOME}/.config/hypr/rofi/keybindings.rasi"

generate_list() {
    cat << 'EOF'
<span color="#888888">[Launcher ]</span>  <span weight="bold" color="#AAAAAA">Super + Space               </span> <span color="#333333">│</span>  <span color="#D5D5D5">Application Launcher (Rofi)</span>
<span color="#888888">[Command  ]</span>  <span weight="bold" color="#AAAAAA">Super + Alt + Space         </span> <span color="#333333">│</span>  <span color="#D5D5D5">Control Center (Desktop Super-Hub)</span>
<span color="#888888">[Command  ]</span>  <span weight="bold" color="#AAAAAA">Super + C                   </span> <span color="#333333">│</span>  <span color="#D5D5D5">Control Center (Alternative)</span>
<span color="#888888">[App      ]</span>  <span weight="bold" color="#AAAAAA">Super + Return              </span> <span color="#333333">│</span>  <span color="#D5D5D5">Open Terminal (Kitty)</span>
<span color="#888888">[App      ]</span>  <span weight="bold" color="#AAAAAA">Super + Shift + Return      </span> <span color="#333333">│</span>  <span color="#D5D5D5">Open Web Browser (Firefox)</span>
<span color="#888888">[App      ]</span>  <span weight="bold" color="#AAAAAA">Super + Shift + F           </span> <span color="#333333">│</span>  <span color="#D5D5D5">Open File Manager (Thunar)</span>
<span color="#888888">[App      ]</span>  <span weight="bold" color="#AAAAAA">Super + Shift + E           </span> <span color="#333333">│</span>  <span color="#D5D5D5">Open Text Editor (Code / Nano)</span>
<span color="#888888">[App      ]</span>  <span weight="bold" color="#AAAAAA">Super + Shift + T           </span> <span color="#333333">│</span>  <span color="#D5D5D5">Open Process Monitor (Btop - Transparent)</span>
<span color="#888888">[App      ]</span>  <span weight="bold" color="#AAAAAA">Super + Shift + C           </span> <span color="#333333">│</span>  <span color="#D5D5D5">Open Matrix Screensaver (CMatrix - Transparent)</span>
<span color="#888888">[App      ]</span>  <span weight="bold" color="#AAAAAA">Super + Shift + S           </span> <span color="#333333">│</span>  <span color="#D5D5D5">Wi-Fi Network Manager (Rofi)</span>
<span color="#888888">[App      ]</span>  <span weight="bold" color="#AAAAAA">Super + Shift + B           </span> <span color="#333333">│</span>  <span color="#D5D5D5">Bluetooth Manager (Rofi)</span>
<span color="#888888">[Window   ]</span>  <span weight="bold" color="#AAAAAA">Super + W                   </span> <span color="#333333">│</span>  <span color="#D5D5D5">Close Focused Window</span>
<span color="#888888">[Window   ]</span>  <span weight="bold" color="#AAAAAA">Super + Q                   </span> <span color="#333333">│</span>  <span color="#D5D5D5">Close Focused Window (Alt)</span>
<span color="#888888">[Window   ]</span>  <span weight="bold" color="#AAAAAA">Super + T                   </span> <span color="#333333">│</span>  <span color="#D5D5D5">Toggle Tiling / Floating Window</span>
<span color="#888888">[Window   ]</span>  <span weight="bold" color="#AAAAAA">Super + V                   </span> <span color="#333333">│</span>  <span color="#D5D5D5">Toggle Floating Window (Alt)</span>
<span color="#888888">[Window   ]</span>  <span weight="bold" color="#AAAAAA">Super + F                   </span> <span color="#333333">│</span>  <span color="#D5D5D5">Toggle Fullscreen</span>
<span color="#888888">[Window   ]</span>  <span weight="bold" color="#AAAAAA">Super + Alt + F             </span> <span color="#333333">│</span>  <span color="#D5D5D5">Toggle Maximize / Full Width</span>
<span color="#888888">[Window   ]</span>  <span weight="bold" color="#AAAAAA">Super + P                   </span> <span color="#333333">│</span>  <span color="#D5D5D5">Toggle Pseudo Tiling</span>
<span color="#888888">[Window   ]</span>  <span weight="bold" color="#AAAAAA">Super + J                   </span> <span color="#333333">│</span>  <span color="#D5D5D5">Toggle Split Direction (Dwindle)</span>
<span color="#888888">[Window   ]</span>  <span weight="bold" color="#AAAAAA">Super + G                   </span> <span color="#333333">│</span>  <span color="#D5D5D5">Toggle Window Grouping (Tabs)</span>
<span color="#888888">[Window   ]</span>  <span weight="bold" color="#AAAAAA">Super + Alt + G             </span> <span color="#333333">│</span>  <span color="#D5D5D5">Remove Window from Group</span>
<span color="#888888">[Window   ]</span>  <span weight="bold" color="#AAAAAA">Super + Alt + Tab           </span> <span color="#333333">│</span>  <span color="#D5D5D5">Cycle Windows in Active Group</span>
<span color="#888888">[Window   ]</span>  <span weight="bold" color="#AAAAAA">Super + Arrow               </span> <span color="#333333">│</span>  <span color="#D5D5D5">Move Window Focus (Directional)</span>
<span color="#888888">[Window   ]</span>  <span weight="bold" color="#AAAAAA">Super + Shift + Arrow       </span> <span color="#333333">│</span>  <span color="#D5D5D5">Move / Swap Window in Direction</span>
<span color="#888888">[Window   ]</span>  <span weight="bold" color="#AAAAAA">Super + Equal (=)           </span> <span color="#333333">│</span>  <span color="#D5D5D5">Increase Window Size (+30px)</span>
<span color="#888888">[Window   ]</span>  <span weight="bold" color="#AAAAAA">Super + Minus (-)           </span> <span color="#333333">│</span>  <span color="#D5D5D5">Decrease Window Size (-30px)</span>
<span color="#888888">[Workspace]</span>  <span weight="bold" color="#AAAAAA">Super + 1..5                </span> <span color="#333333">│</span>  <span color="#D5D5D5">Jump to Workspace 1–5</span>
<span color="#888888">[Workspace]</span>  <span weight="bold" color="#AAAAAA">Super + Shift + 1..5        </span> <span color="#333333">│</span>  <span color="#D5D5D5">Move Window to Workspace &amp; Follow</span>
<span color="#888888">[Workspace]</span>  <span weight="bold" color="#AAAAAA">Super + Shift + Alt + 1..5  </span> <span color="#333333">│</span>  <span color="#D5D5D5">Move Window to Workspace Silently</span>
<span color="#888888">[Workspace]</span>  <span weight="bold" color="#AAAAAA">Super + Tab                 </span> <span color="#333333">│</span>  <span color="#D5D5D5">Jump to Next Workspace</span>
<span color="#888888">[Workspace]</span>  <span weight="bold" color="#AAAAAA">Super + Shift + Tab         </span> <span color="#333333">│</span>  <span color="#D5D5D5">Jump to Previous Workspace</span>
<span color="#888888">[Workspace]</span>  <span weight="bold" color="#AAAAAA">Super + Ctrl + Tab          </span> <span color="#333333">│</span>  <span color="#D5D5D5">Jump to Former / Recent Workspace</span>
<span color="#888888">[System   ]</span>  <span weight="bold" color="#AAAAAA">Super + Escape              </span> <span color="#333333">│</span>  <span color="#D5D5D5">Open System / Power Menu</span>
<span color="#888888">[System   ]</span>  <span weight="bold" color="#AAAAAA">Super + Ctrl + L            </span> <span color="#333333">│</span>  <span color="#D5D5D5">Lock Screen (Hyprlock)</span>
<span color="#888888">[System   ]</span>  <span weight="bold" color="#AAAAAA">Super + Shift + R           </span> <span color="#333333">│</span>  <span color="#D5D5D5">Restart Waybar &amp; Reload Desktop</span>
<span color="#888888">[System   ]</span>  <span weight="bold" color="#AAAAAA">Super + Ctrl + A            </span> <span color="#333333">│</span>  <span color="#D5D5D5">PipeWire Audio Switcher (Rofi)</span>
<span color="#888888">[Clipboard]</span>  <span weight="bold" color="#AAAAAA">Super + Ctrl + V            </span> <span color="#333333">│</span>  <span color="#D5D5D5">Open Clipboard History Manager</span>
<span color="#888888">[Clipboard]</span>  <span weight="bold" color="#AAAAAA">Super + Ctrl + Shift + V    </span> <span color="#333333">│</span>  <span color="#D5D5D5">Wipe All Clipboard History</span>
<span color="#888888">[Style    ]</span>  <span weight="bold" color="#AAAAAA">Super + Ctrl + W            </span> <span color="#333333">│</span>  <span color="#D5D5D5">Wallpaper Selector (Thumbnail Grid)</span>
<span color="#888888">[Notif    ]</span>  <span weight="bold" color="#AAAAAA">Super + Shift + D           </span> <span color="#333333">│</span>  <span color="#D5D5D5">Toggle Do Not Disturb (DND)</span>
<span color="#888888">[Notif    ]</span>  <span weight="bold" color="#AAAAAA">Super + Ctrl + N            </span> <span color="#333333">│</span>  <span color="#D5D5D5">Open Notification History Menu</span>
<span color="#888888">[Notif    ]</span>  <span weight="bold" color="#AAAAAA">Super + N                   </span> <span color="#333333">│</span>  <span color="#D5D5D5">Pop Last Notification from History</span>
<span color="#888888">[Notif    ]</span>  <span weight="bold" color="#AAAAAA">Super + Shift + N           </span> <span color="#333333">│</span>  <span color="#D5D5D5">Dismiss All Active Notifications</span>
<span color="#888888">[Capture  ]</span>  <span weight="bold" color="#AAAAAA">Print                       </span> <span color="#333333">│</span>  <span color="#D5D5D5">Interactive Area Screenshot (Grim+Slurp)</span>
<span color="#888888">[Capture  ]</span>  <span weight="bold" color="#AAAAAA">Super + Print               </span> <span color="#333333">│</span>  <span color="#D5D5D5">Fullscreen Screenshot to Clipboard &amp; Disk</span>
<span color="#888888">[Capture  ]</span>  <span weight="bold" color="#AAAAAA">Super + Ctrl + C            </span> <span color="#333333">│</span>  <span color="#D5D5D5">Open Screenshot Options Menu</span>
<span color="#888888">[Hardware ]</span>  <span weight="bold" color="#AAAAAA">XF86AudioRaiseVolume        </span> <span color="#333333">│</span>  <span color="#D5D5D5">Volume Up (+5%)</span>
<span color="#888888">[Hardware ]</span>  <span weight="bold" color="#AAAAAA">Alt + XF86AudioRaiseVolume  </span> <span color="#333333">│</span>  <span color="#D5D5D5">Fine Volume Up (+1%)</span>
<span color="#888888">[Hardware ]</span>  <span weight="bold" color="#AAAAAA">XF86AudioLowerVolume        </span> <span color="#333333">│</span>  <span color="#D5D5D5">Volume Down (-5%)</span>
<span color="#888888">[Hardware ]</span>  <span weight="bold" color="#AAAAAA">Alt + XF86AudioLowerVolume  </span> <span color="#333333">│</span>  <span color="#D5D5D5">Fine Volume Down (-1%)</span>
<span color="#888888">[Hardware ]</span>  <span weight="bold" color="#AAAAAA">XF86AudioMute               </span> <span color="#333333">│</span>  <span color="#D5D5D5">Toggle Audio Mute</span>
<span color="#888888">[Hardware ]</span>  <span weight="bold" color="#AAAAAA">XF86AudioMicMute            </span> <span color="#333333">│</span>  <span color="#D5D5D5">Toggle Microphone Mute</span>
<span color="#888888">[Hardware ]</span>  <span weight="bold" color="#AAAAAA">XF86MonBrightnessUp         </span> <span color="#333333">│</span>  <span color="#D5D5D5">Brightness Up (+5%)</span>
<span color="#888888">[Hardware ]</span>  <span weight="bold" color="#AAAAAA">Alt + XF86MonBrightnessUp   </span> <span color="#333333">│</span>  <span color="#D5D5D5">Fine Brightness Up (+1%)</span>
<span color="#888888">[Hardware ]</span>  <span weight="bold" color="#AAAAAA">XF86MonBrightnessDown       </span> <span color="#333333">│</span>  <span color="#D5D5D5">Brightness Down (-5%)</span>
<span color="#888888">[Hardware ]</span>  <span weight="bold" color="#AAAAAA">Alt + XF86MonBrightnessDown </span> <span color="#333333">│</span>  <span color="#D5D5D5">Fine Brightness Down (-1%)</span>
<span color="#888888">[Hardware ]</span>  <span weight="bold" color="#AAAAAA">Shift + XF86MonBrightnessUp </span> <span color="#333333">│</span>  <span color="#D5D5D5">Maximum Brightness (100%)</span>
<span color="#888888">[Hardware ]</span>  <span weight="bold" color="#AAAAAA">Shift + XF86MonBrightnessDwn</span> <span color="#333333">│</span>  <span color="#D5D5D5">Minimum Brightness (5%)</span>
EOF
}

CHOSEN=$(generate_list | rofi -dmenu -i -markup-rows -config "${ROFI_THEME}" -p "󰌌  Keybindings")

if [ -z "${CHOSEN}" ]; then
    exit 0
fi

# Execute corresponding function if activated
case "${CHOSEN}" in
    *"Super + Space"*)
        rofi -show drun -config "${HOME}/.config/hypr/rofi/launcher.rasi" &
        ;;
    *"Super + Alt + Space"*|*"Super + C"*)
        "${HOME}/.config/hypr/scripts/command-center.sh" &
        ;;
    *"Super + Return"*)
        kitty --config "${HOME}/.config/hypr/kitty/kitty.conf" &
        ;;
    *"Super + Shift + Return"*)
        firefox &
        ;;
    *"Super + Shift + F"*)
        thunar &
        ;;
    *"Super + Shift + E"*)
        code &
        ;;
    *"Super + Shift + T"*)
        kitty --class btop --title btop --config "${HOME}/.config/hypr/kitty/kitty.conf" -e btop &
        ;;
    *"Super + Shift + C"*)
        "${HOME}/.config/hypr/scripts/cmatrix.sh" &
        ;;
    *"Super + Shift + S"*)
        "${HOME}/.config/hypr/scripts/wifi-menu.sh" &
        ;;
    *"Super + Shift + B"*)
        "${HOME}/.config/hypr/scripts/bluetooth-menu.sh" &
        ;;
    *"Super + W"*|*"Super + Q"*)
        hyprctl dispatch killactive
        ;;
    *"Super + T"*|*"Super + V"*)
        hyprctl dispatch togglefloating
        ;;
    *"Super + F"*)
        hyprctl dispatch fullscreen 0
        ;;
    *"Super + Alt + F"*)
        hyprctl dispatch fullscreen 1
        ;;
    *"Super + P"*)
        hyprctl dispatch pseudo
        ;;
    *"Super + J"*)
        hyprctl dispatch togglesplit
        ;;
    *"Super + G"*)
        hyprctl dispatch togglegroup
        ;;
    *"Super + Alt + G"*)
        hyprctl dispatch moveoutofgroup
        ;;
    *"Super + Alt + Tab"*)
        hyprctl dispatch changegroupactive f
        ;;
    *"Super + Escape"*)
        "${HOME}/.config/hypr/scripts/power-menu.sh" &
        ;;
    *"Super + Ctrl + L"*|*"Super + L"*)
        hyprlock -c "${HOME}/.config/hypr/hyprlock/hyprlock.conf" &
        ;;
    *"Super + Shift + R"*)
        "${HOME}/.config/hypr/scripts/restart-waybar.sh" && hyprctl reload
        ;;
    *"Super + Ctrl + A"*)
        "${HOME}/.config/hypr/scripts/audio-menu.sh" &
        ;;
    *"Super + Ctrl + Shift + V"*)
        "${HOME}/.config/hypr/scripts/clipboard-clear.sh" &
        ;;
    *"Super + Ctrl + V"*)
        "${HOME}/.config/hypr/scripts/clipboard-menu.sh" &
        ;;
    *"Super + Ctrl + W"*|*"Super + Ctrl + Space"*)
        "${HOME}/.config/hypr/scripts/wallpaper-selector.sh" &
        ;;
    *"Super + Shift + D"*)
        "${HOME}/.config/hypr/scripts/notification-toggle.sh" &
        ;;
    *"Super + Ctrl + N"*)
        "${HOME}/.config/hypr/scripts/notification-history.sh" &
        ;;
    *"Super + N"*)
        dunstctl history-pop
        ;;
    *"Super + Shift + N"*)
        dunstctl close-all
        ;;
    *"Print"*)
        if [[ "${CHOSEN}" == *"Super + Print"* ]]; then
            "${HOME}/.config/hypr/scripts/screenshot.sh" full &
        elif [[ "${CHOSEN}" == *"Ctrl + C"* ]]; then
            "${HOME}/.config/hypr/scripts/screenshot.sh" menu &
        else
            "${HOME}/.config/hypr/scripts/screenshot.sh" region &
        fi
        ;;
esac
