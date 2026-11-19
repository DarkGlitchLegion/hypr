#!/usr/bin/env bash
# =====================================================================
# Rice Control Center (Unified Desktop Super-Hub)
# Single keyboard-driven dashboard accessing all desktop subsystems
# Hotkey: Super + C / Super + Alt + Space
# Theme: ~/.config/hypr/rofi/command-center.rasi
# =====================================================================

ROFI_THEME="${HOME}/.config/hypr/rofi/command-center.rasi"
SCRIPTS="${HOME}/.config/hypr/scripts"
KITTY_CONF="${HOME}/.config/hypr/kitty/kitty.conf"
LOCK_CONF="${HOME}/.config/hypr/hyprlock/hyprlock.conf"
LAUNCHER_CONF="${HOME}/.config/hypr/rofi/launcher.rasi"

notify() {
    dunstify -a "Control Center" -u low -i "preferences-system" "$1" "$2" 2>/dev/null || true
}

# ---------------------------------------------------------------------
# Top-Level Hub
# ---------------------------------------------------------------------
show_main_hub() {
    cat << 'EOF'
<span color="#AAAAAA"><b>󰒓  [Category] System &amp; Performance      </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Processes, power, storage, desktop reload</span>
<span color="#AAAAAA"><b>󰤨  [Category] Hardware &amp; Connectivity    </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Wi-Fi, Bluetooth, PipeWire audio, battery</span>
<span color="#AAAAAA"><b>󰍹  [Category] Display &amp; Personalization  </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Wallpapers, GTK theme synchronization</span>
<span color="#AAAAAA"><b>󰲋  [Category] Developer &amp; Workstation    </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Code editors, git, pentest suites, terminals</span>
<span color="#AAAAAA"><b>󰅇  [Category] Productivity &amp; Capture     </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Clipboard manager, screenshot suite, shortcuts</span>
<span color="#AAAAAA"><b>󰐥  [Category] Session &amp; Power            </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Lock screen, suspend, reboot, shutdown</span>
<span color="#888888">── Quick Actions ─────────────────────────────────────────────────────────────</span>
<span color="#AAAAAA"><b>󰄲  Application Launcher                  </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Search and launch desktop applications</span>
<span color="#AAAAAA"><b>󰞷  Terminal (Kitty)                      </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Open Kitty terminal emulator</span>
<span color="#AAAAAA"><b>󰍹  Display Manager                       </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Manage connected displays and layouts</span>
<span color="#AAAAAA"><b>󰉋  File Manager (Thunar)                 </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Browse local files and storage</span>
<span color="#AAAAAA"><b>󰈹  Web Browser (Firefox)                 </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Launch default web browser</span>
<span color="#AAAAAA"><b>󰤨  Wi-Fi Network Manager                 </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Scan, connect, and manage Wi-Fi</span>
<span color="#AAAAAA"><b>󰂯  Bluetooth Device Manager              </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Pair and connect Bluetooth peripherals</span>
<span color="#AAAAAA"><b>󰕾  PipeWire Audio Control Center         </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Switch output sinks &amp; microphones</span>
<span color="#AAAAAA"><b>󰓅  Power Profiles &amp; Battery Center       </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Switch power profiles &amp; check battery</span>
<span color="#AAAAAA"><b>󰸉  Wallpaper Selector                    </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Select wallpaper with live preview</span>
<span color="#AAAAAA"><b>󰅇  Clipboard History Manager             </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Search and paste clipboard history</span>
<span color="#AAAAAA"><b>󰹑  Take Screenshot (Region)              </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Select area to capture to clipboard/file</span>
<span color="#AAAAAA"><b>󰌌  Keybindings Reference                 </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Search keyboard shortcuts</span>
<span color="#AAAAAA"><b>󰑓  Reload Hyprland Desktop               </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Refresh Hyprland &amp; Waybar</span>
<span color="#AAAAAA"><b>󰌾  Lock Screen Immediately               </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Lock screen via Hyprlock</span>
EOF
}

# ---------------------------------------------------------------------
# Submenu: System & Performance
# ---------------------------------------------------------------------
show_system_menu() {
    cat << 'EOF'
<span color="#EBCB8B"><b>󰌍  [Back to Control Center]              </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Return to top-level menu</span>
<span color="#AAAAAA"><b>  Process Monitor (Btop)                </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Open transparent resource monitor</span>
<span color="#AAAAAA"><b>󰓅  Power Profiles &amp; Battery Center       </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Switch performance, balanced, power-saver</span>
<span color="#AAAAAA"><b>󰋊  Disk Usage &amp; Storage Overview         </b></span> <span color="#333333">│</span> <span color="#D5D5D5">View local filesystem storage in terminal</span>
<span color="#AAAAAA"><b>󰑓  Restart Waybar                        </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Reload top status bar</span>
<span color="#AAAAAA"><b>󰑓  Reload Hyprland Desktop               </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Refresh Hyprland configuration</span>
<span color="#AAAAAA"><b>󰒓  Hyprland Config Directory             </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Open ~/.config/hypr in Kitty</span>
EOF
}

# ---------------------------------------------------------------------
# Submenu: Hardware & Connectivity
# ---------------------------------------------------------------------
show_hardware_menu() {
    cat << 'EOF'
<span color="#EBCB8B"><b>󰌍  [Back to Control Center]              </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Return to top-level menu</span>
<span color="#AAAAAA"><b>󰤨  Wi-Fi Network Manager                 </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Scan, connect, and disconnect networks</span>
<span color="#AAAAAA"><b>󰂯  Bluetooth Device Manager              </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Pair and manage Bluetooth connections</span>
<span color="#AAAAAA"><b>󰕾  PipeWire Audio Control Center         </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Switch default audio sink and source</span>
<span color="#AAAAAA"><b>󰓅  Power Profiles &amp; Battery Center       </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Battery health &amp; CPU power throttling</span>
<span color="#AAAAAA"><b>󰝟  Toggle Audio Mute                     </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Mute or unmute default output sink</span>
<span color="#AAAAAA"><b>󰍭  Toggle Microphone Mute                </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Mute or unmute default microphone</span>
<span color="#AAAAAA"><b>󰒓  Advanced Mixer (Pavucontrol)          </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Open full GTK audio control panel</span>
EOF
}

# ---------------------------------------------------------------------
# Submenu: Display & Personalization
# ---------------------------------------------------------------------
show_display_menu() {
    cat << 'EOF'
<span color="#EBCB8B"><b>󰌍  [Back to Control Center]              </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Return to top-level menu</span>
<span color="#AAAAAA"><b>󰸉  Wallpaper Selector                    </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Browse and switch desktop wallpapers</span>
<span color="#AAAAAA"><b>󰔎  Synchronize GTK Dark Theme            </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Re-apply Adwaita-dark and icon tokens</span>
<span color="#AAAAAA"><b>󰍹  Display Manager                       </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Manage layouts, resolution, scale, and orientation</span>
<span color="#AAAAAA"><b>󰃠  Set Brightness to 100% (Maximum)      </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Maximize panel backlight</span>
<span color="#AAAAAA"><b>󰃟  Set Brightness to 50%  (Balanced)     </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Set backlight to 50%</span>
<span color="#AAAAAA"><b>󰃞  Set Brightness to 10%  (Minimum)      </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Minimize backlight for dark environments</span>
EOF
}

# ---------------------------------------------------------------------
# Submenu: Developer & Workstation Tools
# ---------------------------------------------------------------------
show_dev_menu() {
    cat << 'EOF'
<span color="#EBCB8B"><b>󰌍  [Back to Control Center]              </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Return to top-level menu</span>
<span color="#AAAAAA"><b>󰞷  Open Terminal (Kitty)                 </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Spawn primary GPU-accelerated terminal</span>
<span color="#AAAAAA"><b>󰨞  Visual Studio Code                    </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Launch code editor</span>
<span color="#AAAAAA"><b>󰊢  Git TUI (Lazygit)                     </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Launch Lazygit in floating terminal</span>
<span color="#AAAAAA"><b>󰉋  File Manager (Thunar)                 </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Browse filesystem and project trees</span>
<span color="#AAAAAA"><b>󱤤  Matrix Screensaver (CMatrix)          </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Transparent terminal digital rain</span>
<span color="#AAAAAA"><b>󰈹  Web Browser (Firefox)                 </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Launch native Wayland browser</span>
<span color="#AAAAAA"><b>󰒃  Security Tools Directory              </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Browse ~/tools in Thunar</span>
EOF
}

# ---------------------------------------------------------------------
# Submenu: Productivity & Capture
# ---------------------------------------------------------------------
show_capture_menu() {
    cat << 'EOF'
<span color="#EBCB8B"><b>󰌍  [Back to Control Center]              </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Return to top-level menu</span>
<span color="#AAAAAA"><b>󰅇  Clipboard History Manager             </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Browse and copy past clipboard entries</span>
<span color="#AAAAAA"><b>󰅇  Wipe Clipboard History                </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Clear all stored clipboard records</span>
<span color="#AAAAAA"><b>󰹑  Region Screenshot                     </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Interactive area selection (grim/slurp)</span>
<span color="#AAAAAA"><b>󰹑  Fullscreen Screenshot                 </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Capture entire active display</span>
<span color="#AAAAAA"><b>󰹑  Screenshot Menu                       </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Open full capture options menu</span>
<span color="#AAAAAA"><b>󰌌  Keybindings Reference (Rofi)          </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Searchable modal shortcut reference</span>
<span color="#AAAAAA"><b>󰌌  Keybindings Cheatsheet (Window)       </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Floating terminal cheatsheet</span>
<span color="#AAAAAA"><b>󰂚  Toggle Do Not Disturb                 </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Pause or unpause desktop notifications</span>
<span color="#AAAAAA"><b>󰍡  Notification History                  </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Browse past notifications</span>
EOF
}

# ---------------------------------------------------------------------
# Submenu: Session & Power
# ---------------------------------------------------------------------
show_session_menu() {
    cat << 'EOF'
<span color="#EBCB8B"><b>󰌍  [Back to Control Center]              </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Return to top-level menu</span>
<span color="#AAAAAA"><b>󰌾  Lock Screen                           </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Lock screen immediately (Hyprlock)</span>
<span color="#AAAAAA"><b>󰤄  Suspend System (Sleep)                </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Suspend to RAM</span>
<span color="#AAAAAA"><b>󰑓  Reload Hyprland Desktop               </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Refresh Hyprland and Waybar</span>
<span color="#AAAAAA"><b>󰍃  Log Out                               </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Exit Hyprland graphical session</span>
<span color="#AAAAAA"><b>󰜉  Reboot System                         </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Restart the computer</span>
<span color="#BF616A"><b>󰐥  Shutdown System                       </b></span> <span color="#333333">│</span> <span color="#D5D5D5">Power off the computer</span>
EOF
}

# ---------------------------------------------------------------------
# Action Dispatcher
# ---------------------------------------------------------------------
handle_action() {
    local item="$1"

    case "${item}" in
        *"[Category] System"*)
            run_menu "system"
            ;;
        *"[Category] Hardware"*)
            run_menu "hardware"
            ;;
        *"[Category] Display"*)
            run_menu "display"
            ;;
        *"[Category] Developer"*)
            run_menu "dev"
            ;;
        *"[Category] Productivity"*)
            run_menu "capture"
            ;;
        *"[Category] Session"*)
            run_menu "session"
            ;;
        *"[Back to Control Center]"*)
            run_menu "main"
            ;;
        *"Application Launcher"*)
            rofi -show drun -config "${LAUNCHER_CONF}" &
            ;;
        *"Terminal (Kitty)"*)
            kitty --config "${KITTY_CONF}" &
            ;;
        *"Display Manager"*)
            "${SCRIPTS}/display-manager.py" &
            ;;
        *"File Manager"*)
            thunar &
            ;;
        *"Web Browser"*)
            firefox &
            ;;
        *"Wi-Fi Network Manager"*)
            "${SCRIPTS}/wifi-menu.sh" &
            ;;
        *"Bluetooth Device Manager"*)
            "${SCRIPTS}/bluetooth-menu.sh" &
            ;;
        *"PipeWire Audio Control Center"*)
            "${SCRIPTS}/audio-menu.sh" &
            ;;
        *"Power Profiles & Battery Center"*)
            "${SCRIPTS}/power-profile-menu.sh" &
            ;;
        *"Process Monitor"*)
            kitty --class btop --title btop --config "${KITTY_CONF}" -e btop &
            ;;
        *"Disk Usage & Storage"*)
            kitty --config "${KITTY_CONF}" -e sh -c "df -hT --exclude-type=tmpfs --exclude-type=devtmpfs; echo ''; read -p 'Press Enter to close...' -r" &
            ;;
        *"Wallpaper Selector"*)
            "${SCRIPTS}/wallpaper-selector.sh" &
            ;;
        *"Synchronize GTK Dark Theme"*)
            "${SCRIPTS}/apply-gtk-theme.sh" &
            notify "GTK Theme Synced" "Applied Adwaita-dark theme configuration."
            ;;
        *"Set Brightness to 100%"*)
            brightnessctl set 100% >/dev/null 2>&1
            notify "Brightness" "Backlight set to 100%"
            ;;
        *"Set Brightness to 50%"*)
            brightnessctl set 50% >/dev/null 2>&1
            notify "Brightness" "Backlight set to 50%"
            ;;
        *"Set Brightness to 10%"*)
            brightnessctl set 10% >/dev/null 2>&1
            notify "Brightness" "Backlight set to 10%"
            ;;
        *"Visual Studio Code"*)
            code &
            ;;
        *"Git TUI (Lazygit)"*)
            kitty --config "${KITTY_CONF}" -e lazygit &
            ;;
        *"Matrix Screensaver"*)
            "${SCRIPTS}/cmatrix.sh" &
            ;;
        *"Security Tools Directory"*)
            if [ -d "${HOME}/tools" ]; then
                thunar "${HOME}/tools" &
            else
                thunar "${HOME}" &
            fi
            ;;
        *"Clipboard History Manager"*)
            "${SCRIPTS}/clipboard-menu.sh" &
            ;;
        *"Wipe Clipboard History"*)
            "${SCRIPTS}/clipboard-clear.sh" &
            ;;
        *"Region Screenshot"*)
            "${SCRIPTS}/screenshot.sh" region &
            ;;
        *"Fullscreen Screenshot"*)
            "${SCRIPTS}/screenshot.sh" full &
            ;;
        *"Screenshot Menu"*)
            "${SCRIPTS}/screenshot.sh" menu &
            ;;
        *"Keybindings Reference (Rofi)"*|*"Keybindings Reference"*)
            "${SCRIPTS}/keybindings-menu.sh" &
            ;;
        *"Keybindings Cheatsheet"*)
            "${SCRIPTS}/keybindings-window.sh" &
            ;;
        *"Toggle Do Not Disturb"*)
            "${SCRIPTS}/notification-toggle.sh" &
            ;;
        *"Notification History"*)
            "${SCRIPTS}/notification-history.sh" &
            ;;
        *"Toggle Audio Mute"*)
            "${SCRIPTS}/volume.sh" mute &
            ;;
        *"Toggle Microphone Mute"*)
            "${SCRIPTS}/volume.sh" mic &
            ;;
        *"Advanced Mixer"*)
            pavucontrol &
            ;;
        *"Restart Waybar"*)
            "${SCRIPTS}/restart-waybar.sh" &
            ;;
        *"Reload Hyprland Desktop"*)
            hyprctl reload && "${SCRIPTS}/restart-waybar.sh" &
            ;;
        *"Hyprland Config Directory"*)
            kitty --config "${KITTY_CONF}" -e sh -c "cd ${HOME}/.config/hypr && ls -la && exec bash" &
            ;;
        *"Lock Screen"*)
            hyprlock -c "${LOCK_CONF}" &
            ;;
        *"Suspend System"*)
            systemctl suspend &
            ;;
        *"Log Out"*)
            hyprctl dispatch exit &
            ;;
        *"Reboot System"*)
            systemctl reboot &
            ;;
        *"Shutdown System"*)
            systemctl poweroff &
            ;;
        "")
            exit 0
            ;;
    esac
}

run_menu() {
    local target="${1:-main}"
    local prompt="󰘳  Control Center"
    local generator

    case "${target}" in
        system)
            prompt="󰒓  System"
            generator="show_system_menu"
            ;;
        hardware)
            prompt="󰤨  Hardware"
            generator="show_hardware_menu"
            ;;
        display)
            prompt="󰍹  Display"
            generator="show_display_menu"
            ;;
        dev)
            prompt="󰲋  Developer"
            generator="show_dev_menu"
            ;;
        capture)
            prompt="󰅇  Capture"
            generator="show_capture_menu"
            ;;
        session)
            prompt="󰐥  Session"
            generator="show_session_menu"
            ;;
        *)
            prompt="󰘳  Control Center"
            generator="show_main_hub"
            ;;
    esac

    local chosen
    chosen=$("${generator}" | rofi -dmenu -i -markup-rows -config "${ROFI_THEME}" -p "${prompt}")
    
    if [ -n "${chosen}" ]; then
        handle_action "${chosen}"
    fi
}

run_menu "$1"
