#!/usr/bin/env bash
# =====================================================
# Floating Terminal Keybindings Cheatsheet Window
# Launches a styled floating Kitty window with pager
# =====================================================

KITTY_CONF="${HOME}/.config/hypr/kitty/kitty.conf"

show_cheatsheet() {
    cat << 'EOF'
 ─────────────────────────────────────────────────────────────────────────────
  ARCH HYPRLAND RICE — KEYBOARD SHORTCUTS
 ─────────────────────────────────────────────────────────────────────────────

  [ LAUNCHER & CONTROL CENTER ]
    Super + Space                Application Launcher (Rofi)
    Super + Alt + Space          Control Center (Desktop Super-Hub)
    Super + C                    Control Center (Alternative)
    Super + Return               Open Terminal (Kitty)
    Super + Shift + Return       Open Web Browser (Firefox)
    Super + Shift + F            Open File Manager (Thunar)
    Super + Shift + E            Open Text Editor (Code / Nano)
    Super + Shift + T            Open Process Monitor (Btop - Transparent)
    Super + Shift + I            Show System Information (Fastfetch)
    Super + Shift + M            Open Display Manager
    Super + Shift + C            Open Matrix Screensaver (CMatrix - Transparent)
    Super + Shift + S            Wi-Fi Network Manager (Rofi)
    Super + Shift + B            Bluetooth Manager (Rofi)

  [ WINDOW MANAGEMENT ]
    Super + W                    Close Focused Window
    Super + Q                    Close Focused Window (Fallback)
    Super + T                    Toggle Tiling / Floating Mode
    Super + V                    Toggle Floating Mode (Fallback)
    Super + F                    Toggle Fullscreen (Clean)
    Super + Alt + F              Toggle Maximize / Full Width
    Super + P                    Toggle Pseudo Tiling
    Super + J                    Toggle Split Direction (Horizontal/Vertical)
    Super + G                    Toggle Window Grouping (Tabs)
    Super + Alt + G              Remove Window from Group
    Super + Alt + Tab            Cycle Windows in Active Group
    Super + Arrow Keys           Move Window Focus (Left, Right, Up, Down)
    Super + Shift + Arrow Keys   Move / Swap Window Position
    Super + ;                    Shrink Focused Window (-30px)
    Super + '                    Enlarge Focused Window (+30px)
    Super + Left Mouse Drag      Move Window
    Super + Right Mouse Drag     Resize Window

  [ WORKSPACE MANAGEMENT ]
    Super + 1 .. 9, 0            Switch to Workspace 1–10 (0 = 10)
    Super + Shift + 1 .. 9, 0    Move Window to Workspace & Follow
    Super + Shift + Alt + 1 .. 9, 0 Move Window to Workspace Silently
    Super + Tab                  Switch to Next Workspace
    Super + Shift + Tab          Switch to Previous Workspace
    Super + Ctrl + Tab           Switch to Former / Recent Workspace
    Super + Mouse Scroll         Cycle Through Workspaces

  [ SYSTEM & NOTIFICATIONS ]
    Super + Escape               Open System / Power Menu (Lock, Suspend, etc.)
    Super + Ctrl + L             Lock Screen Immediately (Hyprlock)
    Super + L                    Lock Screen (Fallback)
    Super + Shift + R            Restart Waybar & Reload Hyprland
    Super + Ctrl + A             Open PipeWire Audio Switcher (Rofi)
    Super + Shift + D            Toggle Do Not Disturb (DND)
    Super + Ctrl + N             Open Notification History Viewer
    Super + N                    Notification History (Pop Last)
    Super + Shift + N            Dismiss All Active Notifications

  [ CLIPBOARD & PRODUCTIVITY ]
    Super + Ctrl + V             Open Clipboard History Manager (Rofi)
    Super + Ctrl + Shift + V     Wipe All Clipboard History
    Super + Ctrl + W             Open Wallpaper Selector (Thumbnail Grid)
    Super + K                    Interactive Keybindings Window (Rofi Modal)
    Super + Shift + K            Terminal Cheatsheet Window
    Print                        Interactive Region Screenshot (Grim + Slurp)
    Super + Print                Fullscreen Screenshot to Clipboard & Disk
    Super + Ctrl + C             Open Screenshot Options Menu

  [ HARDWARE CONTROLS ]
    Volume Up / Down             Adjust Volume (±5% steps)
    Alt + Volume Up / Down       Fine Volume Adjustment (±1% steps)
    Volume Mute / Mic Mute       Toggle Audio / Microphone Mute
    Brightness Up / Down         Adjust Brightness (±5% steps)
    Alt + Brightness Up / Down   Fine Brightness Adjustment (±1% steps)
    Shift + Brightness Up / Down Instant Maximum (100%) / Minimum (5%)

 ─────────────────────────────────────────────────────────────────────────────
  Press 'q' or 'Ctrl+C' to close this window.
 ─────────────────────────────────────────────────────────────────────────────
EOF
}

if [ "$1" = "--inside" ]; then
    show_cheatsheet | less -R -P " Keybindings Cheatsheet (Press q to exit) "
else
    kitty --class "hypr-keybindings" \
          --title "Keybindings Cheatsheet" \
          --config "${KITTY_CONF}" \
          -e "$0" --inside
fi
