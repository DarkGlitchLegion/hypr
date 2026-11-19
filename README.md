# Arch Linux Hyprland Rice — Minimal Dark Ecosystem

A developer-focused personal workstation environment built on **Arch Linux**, **Hyprland 0.57.2+ (native Lua engine)**, **Waybar**, **Rofi Wayland**, and **Dunst**.

Designed around the **Minimal Dark Charcoal palette** (`#0C0D10` background, `#17191F` surface, `#202126` card hover, `#AAAAAA` accent), this ecosystem emphasizes keyboard-driven workflows, zero bloat, and fast hardware integration.

---

## Architecture Overview

Hyprland 0.57.2+ runs natively with a modular Lua architecture under `~/.config/hypr/lua/`. Configurations are modularized to prevent configuration drift:

```
~/.config/hypr/
├── hyprland.lua              # Master entrypoint & shared desktop context
├── hyprland.conf             # Compatibility bridge for Hyprland
├── lua/                      # Modular Lua configuration subsystem
│   ├── monitors.lua          # 1:1 native display setup (prevents fractional scaling)
│   ├── autostart.lua         # Background daemons, Polkit, Waybar, Dunst, etc.
│   ├── env.lua               # Wayland environment variables & cursor synchronization
│   ├── appearance.lua        # Compositor layout, borders, rounding, shadows & blur
│   ├── animations.lua        # Custom quintic & cubic Bezier animation curves
│   ├── rules.lua             # Window rules, dialog centering & layer blur rules
│   └── keybinds.lua          # Keyboard shortcuts & window dispatchers
├── waybar/                   # Waybar status bar
│   ├── config.jsonc          # Modular widgets, PipeWire, power profiles, battery
│   └── style.css             # Minimalist charcoal stylesheet with hover transitions
├── rofi/                     # Rofi Wayland application & control menus
│   ├── launcher.rasi         # Primary app launcher theme
│   ├── command-center.rasi   # Rice Control Center theme
│   ├── audio.rasi            # PipeWire audio switcher theme
│   ├── power-profile.rasi    # Power profile & battery diagnostics theme
│   ├── wifi.rasi             # Graphical Wi-Fi & Bluetooth theme
│   ├── keybindings.rasi      # Searchable shortcut reference modal
│   ├── clipboard.rasi        # Clipboard history manager theme
│   ├── powermenu.rasi        # System session/power dialog theme
│   └── wallpaper.rasi        # Wallpaper visual thumbnail grid
├── scripts/                  # Shell & Python automation utilities
│   ├── control-center.sh     # Rice Control Center super-hub
│   ├── rice-health.py        # Hyprland, display, workspace, and tool diagnostics
│   ├── audio-menu.sh         # PipeWire sink & source switcher (wpctl)
│   ├── power-profile-menu.sh # AMD P-State power profile switcher & battery health
│   ├── wifi-menu.sh          # Non-blocking network manager
│   ├── bluetooth-menu.sh     # Peripheral management & pairing
│   ├── bluetooth-agent.py    # D-Bus pairing & authentication agent
│   ├── wallpaper-selector.sh # Rofi wallpaper thumbnail chooser
│   ├── set-wallpaper.sh      # Hyprpaper IPC reload & Hyprlock persistence
│   ├── clipboard-menu.sh     # Cliphist history browser
│   ├── clipboard-daemon.sh   # Background clipboard listener
│   ├── screenshot.sh         # Grim + Slurp region, window & full capture
│   ├── volume.sh             # PipeWire volume & microphone controller
│   ├── brightness.sh         # Display backlight controller (brightnessctl)
│   ├── notification-toggle.sh# Do Not Disturb toggle & Waybar sync
│   ├── apply-gtk-theme.sh    # GTK3/4 Adwaita-dark theme synchronizer
│   └── restart-waybar.sh     # Clean Waybar restarter
├── kitty/                    # Kitty terminal emulator configuration
├── dunst/                    # Dunst notification daemon configuration
├── hyprlock/                 # Hyprlock minimalist lockscreen
├── hypridle.conf             # Power & idle timeout rules
├── current_wallpaper         # File storing active wallpaper path
└── wallpapers/               # Curated wallpaper library
```

---

## Core Features & How to Use Them

### 1. Rice Control Center (Unified Super-Hub)
* **Hotkey**: <kbd>Super</kbd> + <kbd>C</kbd> or <kbd>Super</kbd> + <kbd>Alt</kbd> + <kbd>Space</kbd>
* **Script**: `~/.config/hypr/scripts/control-center.sh`
* **What it does**: Provides a centralized keyboard dashboard for the entire desktop.
  * **Rice Health & Diagnostics** is available under System & Performance. It checks Hyprland config/IPC, display watcher count, active monitor geometry for overlaps, workspace state, saved external workspace preference, and commands used by rice features. Choose **Refresh diagnostics** to re-query live state.
  * **Categorized Submenus**:
    * `󰒓 System & Performance`: Rice health diagnostics, process monitor (`btop`), power center, disk usage, desktop/Waybar reload.
    * `󰤨 Hardware & Connectivity`: Wi-Fi, Bluetooth, PipeWire audio switcher, battery diagnostics.
    * `󰍹 Display & Personalization`: Wallpaper selector, GTK theme synchronization, display info.
    * `󰲋 Developer & Workstation`: VS Code, Kitty, Lazygit, tools folder, CMatrix.
    * `󰅇 Productivity & Capture`: Clipboard history, screenshot suite, shortcuts cheatsheet.
    * `󰐥 Session & Power`: Lock screen (Hyprlock), suspend, reboot, poweroff, logout.
  * **Direct Fuzzy Search**: You don't need to navigate submenus—simply type keywords like `wifi`, `audio`, `btop`, `lock`, or `screenshot` to trigger actions immediately from the first screen.

---

### 2. PipeWire Audio Control Center
* **Hotkey**: <kbd>Super</kbd> + <kbd>Ctrl</kbd> + <kbd>A</kbd>
* **Waybar Trigger**: Click the **Audio** (`󰕾`) or **Microphone** (`󰍬`) icon in Waybar.
* **Script**: `~/.config/hypr/scripts/audio-menu.sh`
* **What it does**:
  * Auto-detects all available PipeWire audio sinks (Laptop Speakers, HDMI/DisplayPort, Bluetooth headphones).
  * Auto-detects input microphones (Built-in mic, external headset mic).
  * Displays active devices with a `● Active` indicator, volume percentage, and mute status.
  * Clicking any device sets it as the system default sink/source via `wpctl set-default <ID>` and triggers a notification.
  * Includes quick toggles for muting outputs/inputs, raising/lowering volume, and opening `pavucontrol`.

---

### 3. Power Profiles & Battery Center
* **Waybar Trigger**:
  * **Left-Click** on Battery: Opens the interactive Power & Battery Center.
  * **Right-Click** on Battery: Instantly cycles through power profiles (`power-saver` → `balanced` → `performance`).
* **Script**: `~/.config/hypr/scripts/power-profile-menu.sh`
* **What it does**:
  * Interfaces with `powerprofilesctl` to switch AMD P-State CPU governor profiles:
    * **Performance** (`󰓅`): Maximum CPU boost and clocks.
    * **Balanced** (`󰾆`): Standard dynamic frequency scaling.
    * **Power Saver** (`󰌪`): Aggressive throttling for maximum battery longevity.
  * **Hardware Battery Diagnostics**: Inspects `/sys/class/power_supply/BAT0` to calculate:
    * Real-time power draw in Watts (`power_now`).
    * Battery health percentage based on `energy_full` vs `energy_full_design`.
    * Battery cycle count.
  * Includes a **Battery Diagnostic Report** button that triggers a Dunst notification with full hardware and power metrics.
  * Integrated with Waybar's native `power-profiles-daemon` module with live icons.

---

### 4. Graphical Wi-Fi Manager
* **Hotkey**: <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>S</kbd>
* **Waybar Trigger**: Click the **Network** (`󰤨`) widget in Waybar.
* **Script**: `~/.config/hypr/scripts/wifi-menu.sh`
* **What it does**:
  * Scans nearby Wi-Fi networks in the background (`nmcli --rescan no`) for fast response times.
  * Displays signal strength icons, security state (WPA/WPA2/open), and active connection indicators.
  * Selecting an unconfigured network prompts for password entry directly in Rofi.
  * Includes options to toggle Wi-Fi radio on/off and force an access point rescan.

---

### 5. Graphical Bluetooth Manager & Pairing Agent
* **Hotkey**: <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>B</kbd>
* **Waybar Trigger**: Click the **Bluetooth** (`󰂯`) widget in Waybar.
* **Scripts**: `~/.config/hypr/scripts/bluetooth-menu.sh` & `bluetooth-agent.py`
* **What it does**:
  * Connects to BlueZ via D-Bus and `bluetoothctl`.
  * Runs a dedicated background agent (`bluetooth-agent.py`) for automatic pairing, PIN handling, and Dunst notifications.
  * Lists paired and discovered devices with battery status percentages.
  * Allows connecting, disconnecting, pairing, and unpairing peripherals without launching external GUI tools.

---

### 6. Wallpaper Selector & Persistence Engine
* **Hotkey**: <kbd>Super</kbd> + <kbd>Ctrl</kbd> + <kbd>W</kbd> or <kbd>Super</kbd> + <kbd>Ctrl</kbd> + <kbd>Space</kbd>
* **Scripts**: `~/.config/hypr/scripts/wallpaper-selector.sh` & `set-wallpaper.sh`
* **What it does**:
  * Displays a visual grid of all wallpapers in `~/.config/hypr/wallpapers/` (PNG, JPG, WEBP).
  * Automatically applies the selected image to Hyprpaper via IPC without restarting the daemon.
  * Persists the choice in `~/.config/hypr/current_wallpaper` and updates `hyprpaper.conf`.
  * Automatically synchronizes the lockscreen background in [hyprlock.conf](file:///home/darkglitch/.config/hypr/hyprlock/hyprlock.conf) so lock screen and desktop wallpapers stay consistent.

---

### 7. Clipboard History Manager
* **Hotkey**: <kbd>Super</kbd> + <kbd>Ctrl</kbd> + <kbd>V</kbd>
* **Clear History**: <kbd>Super</kbd> + <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>V</kbd>
* **Scripts**: `~/.config/hypr/scripts/clipboard-menu.sh` & `clipboard-daemon.sh`
* **What it does**:
  * Runs a lightweight `wl-paste` listener storing clipboard text and images via `cliphist`.
  * Pressing <kbd>Super</kbd> + <kbd>Ctrl</kbd> + <kbd>V</kbd> opens a fuzzy-searchable history list in Rofi.
  * Selecting an entry copies it back to the active clipboard buffer ready for pasting.

---

### 8. Screenshot & Capture Suite
* **Interactive Area**: Press <kbd>Print</kbd>
* **Fullscreen**: Press <kbd>Super</kbd> + <kbd>Print</kbd>
* **Capture Menu**: Press <kbd>Super</kbd> + <kbd>Ctrl</kbd> + <kbd>C</kbd>
* **Script**: `~/.config/hypr/scripts/screenshot.sh`
* **What it does**:
  * Uses `grim` and `slurp` for Wayland capture.
  * Captured images are automatically saved to `~/Pictures/Screenshots/` with timestamped filenames.
  * Images are simultaneously copied to the Wayland clipboard (`wl-copy`).
  * Triggers a Dunst notification with an interactive thumbnail preview.
  * The menu mode supports Region, Window (auto-detects focused window geometry), Fullscreen, and 5-second delayed capture.

---

### 9. Notification System & Do Not Disturb (DND)
* **Toggle DND**: <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>D</kbd>
* **Notification History**: <kbd>Super</kbd> + <kbd>Ctrl</kbd> + <kbd>N</kbd>
* **Pop Last Notification**: <kbd>Super</kbd> + <kbd>N</kbd>
* **Dismiss All**: <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>N</kbd>
* **Waybar Module**: Displays `󰂚` when notifications are active and `󰂛 DND` when muted. Clicking the module toggles DND mode.

---

### 10. Lock Screen & Idle Power Management
* **Instant Lock**: <kbd>Super</kbd> + <kbd>L</kbd> or <kbd>Super</kbd> + <kbd>Ctrl</kbd> + <kbd>L</kbd>
* **Daemons**: `hyprlock` & `hypridle`
* **What it does**:
  * Uses a clean 2D charcoal layout with custom date/time fonts and smooth input dots animations.
  * **Idle policy** (configured in [hypridle.conf](file:///home/darkglitch/.config/hypr/hypridle.conf)):
    * **4.5 minutes**: Backlight dims to 20% via `brightnessctl`.
    * **5 minutes**: Locks session with `hyprlock`.
    * **6 minutes**: Turns off display backlight (DPMS off). Waking moves/keys turn display back on.
    * **30 minutes**: Suspends laptop to RAM (`systemctl suspend`).

---

### 11. GTK Dark Theme & Icon Synchronization
* **Script**: `~/.config/hypr/scripts/apply-gtk-theme.sh`
* **What it does**:
  * Synchronizes `settings.ini` for GTK 3.0 and GTK 4.0.
  * Applies **Adwaita-dark** theme, **Papirus-Dark** icons, and **Adwaita** 20px cursor.
  * Injects custom CSS into `~/.config/gtk-3.0/gtk.css` so Thunar and GTK dialogs match the charcoal palette (`#0C0D10`).

---

### 12. External Display Manager
* **Hotkey**: <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>M</kbd>
* **Control Center**: Open **Display & Personalization** → **Display Manager**
* **Script**: `~/.config/hypr/scripts/display-manager.py`
* **Monitor configuration**: [monitors.lua](./lua/monitors.lua) remains the default fallback rule; display changes are applied at runtime and do not rewrite it.
* **Previous limitation**: The fallback rule only selected a preferred mode, and the Control Center's display action only printed monitor information; there was no hotplug watcher, layout UI, or saved profile.
* **What it does**:
  * Reads monitor modes, resolution, refresh rate, scaling, position, and orientation from Hyprland. Detects connector plug/unplug state through the kernel DRM status files without hardcoding individual connector names.
  * Offers Laptop only, External display only, Extend (left/right/above/below), Mirror, and Presentation layouts.
  * Per-monitor controls enable/disable outputs, select a reported resolution/refresh rate, adjust scale and orientation, position relative to another display, or move a display to the top-left primary position.
  * Every manual layout change has a 20-second confirmation window; choosing Keep saves it to `~/.config/hypr/display-profiles.json`, while canceling or letting the timer expire restores the previous layout. Presentation layouts are session-only and never overwrite saved normal layouts.
  * Use **Reapply saved layout** to choose and reload a saved profile on demand after changing display settings.
  * A singleton startup watcher listens to Hyprland's monitor IPC events and debounces rapid connect/disconnect events. New displays trigger a Dunst notification with layout choices. It only auto-applies a layout when you explicitly saved that exact connected-monitor combination.
  * Every layout apply is serialized, re-detects connectors before each rule, enables target displays before disabling others, and verifies the resulting state. An unconfirmed change rolls back; a hotplug during confirmation cancels it and restores a safe connected display.
  * On disconnection, the watcher refreshes connector state, enables the internal display if no output remains active, and moves workspaces off unavailable monitors where needed. A singleton lock prevents duplicate listeners and conflicting operations.
  * **Preset-transition root cause fixed**: `hl.monitor` updates an existing monitor rule. The old runtime rule omitted `disabled = false`, so an output disabled by Laptop only remained disabled when later presets tried to re-enable it. The updated rule explicitly sets both `disabled` and `mirror`, clearing inherited state.
  * **External workspace selection**: Extend prompts for a numbered workspace (1–10), an existing named workspace, or a new named workspace. The preference is stored once in `display-preferences.json`, applied when extending, and reapplied on reconnect/restart only when both the laptop and an external output are active. The manager does not define a fixed Workspace 3 rule. If the selected workspace is currently active on the laptop, it asks before moving it; creating or activating a workspace on the external monitor restores the previously focused monitor.
  * Workspace selection and recovery invoke Lua dispatchers through `hyprctl dispatch`; `hyprctl eval` only evaluates Lua and does not execute a returned dispatcher. This prevents a false-success response from leaving the selected workspace unchanged.
  * **External-only overlap fix**: The old apply order enabled the external panel at `(0, 0)` while the laptop panel was still active at `(0, 0)`, and only disabled the laptop afterward. Layouts are now overlap-validated and applied in safe steps: outputs that would collide are temporarily staged beside active monitors, unwanted outputs are disabled while a desired output stays active, then outputs move to their final positions. Each step is re-queried and verified, allowing safe transitions between single-display and extended layouts.
  * Workspace 3 was observed active on HDMI, but the audit found no Workspace 3 rule or command in the active Lua configuration, keybindings, or display scripts. This is Hyprland's runtime workspace-to-monitor association; the original event that created it is not recoverable from the current configuration. Extend now explicitly creates or moves the selected workspace instead of relying on that association.
  * **Mirror safety audit**: The installed build is Hyprland 0.57.2. The matching upstream report describes the renderer crash on 0.56.2; the local coredump reached the same mirror-rendering abort path on 0.57.2. The upstream issue was closed by a moderation bot, not by a code fix, and the latest stable release checked was still 0.57.2. No verified fix commit or newer stable release was found, so mirroring remains fail-closed and no upgrade was performed.
  * **Presentation Mode** offers Extend (external display primary, laptop retained for presenter controls) and External display only. Mirror presentation is offered only when a fixed Hyprland build is verified. Choose DND and idle-blanking protections independently, with both enabled by default. Exit restores the previous connected display layout, exact DND state, and only the idle inhibitor created by Presentation Mode.
  * The Presentation Mode failure was an incomplete implementation: its preset only changed monitor positions and did not manage DND, idle inhibition, or saved pre-presentation state. The updated manager persists session state and exposes a dynamic Start/Exit entry in its existing UI. On unplug, presentation state exits and restores the previous layout where possible.
  * Native mirror mode is blocked on the installed Hyprland 0.57.2 build because the compositor previously aborted in mirror rendering when a mirror target disconnected. Do not try mirroring on that version; use Extend or External only. The recorded coredump confirms Hyprland itself crashed; this recovery code cannot prevent a compositor-level defect from occurring before the disconnect event is handled.
  * Uses existing Python 3, Hyprland, Rofi, and Dunst; it adds no packages or system service.
* **Connect and configure**: Plug in the display, choose a layout from the connection notification or open the manager, then choose **Keep** before the timer expires. Choose the save option to restore that layout on later connections and at startup. Use **Laptop only** to return to the built-in panel; choose **Revert** or let the timer expire to undo an unconfirmed change.
* **Testing**: Mocked transitions and disconnect fallback pass. A connected HDMI display was enabled beside the active laptop panel and then disabled again; the original layout was restored. Physical unplug/replug and workspace migration were not simulated on hardware. Do not perform a live mirror test on Hyprland 0.57.2 because of the compositor crash above.
* **External-only overlap regression**: Simulated laptop-only/external-only/extend transitions and a left-right layout swap passed with no overlapping active monitor rectangles at any intermediate step. Physical HDMI validation was unavailable during this change because `HDMI-A-1` reported disconnected.
* **Presentation validation addendum**: Mocked activation/exit confirms restoration of the saved layout and the original DND state, and cleanup targets only the Presentation Mode idle inhibitor. The no-external-display path makes no changes. Actual idle inhibition and DND behavior still require confirmation in the live session.
* **External workspace testing**: Numbered/named preference validation, explicit assignment, focus preservation, and persistence are covered by mocked IPC checks. Physical HDMI reconnect and restart behavior are documented but still require a hardware/session test.

---

## Master Keybindings Reference

### Application Launchers & Controls
| Shortcut | Action | Description |
| :--- | :--- | :--- |
| <kbd>Super</kbd> + <kbd>Return</kbd> | Open Terminal | Launches Kitty with charcoal theme |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>Return</kbd> | Web Browser | Launches Firefox (Wayland native) |
| <kbd>Super</kbd> + <kbd>Space</kbd> | App Launcher | Opens Rofi application launcher |
| <kbd>Super</kbd> + <kbd>C</kbd> | Rice Control Center | Opens the unified desktop super-hub |
| <kbd>Super</kbd> + <kbd>Alt</kbd> + <kbd>Space</kbd> | Rice Control Center | Alternative shortcut for Control Center |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>F</kbd> | File Manager | Opens Thunar file manager |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>E</kbd> | Text Editor | Launches VS Code (falls back to Nano in Kitty) |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>T</kbd> | Process Monitor | Opens Btop in transparent Kitty terminal |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>I</kbd> | System Information | Displays Fastfetch in a Kitty terminal |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>M</kbd> | Display Manager | Configure monitor layouts, modes, scaling, and orientation |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>C</kbd> | CMatrix | Matrix digital rain terminal screensaver |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>S</kbd> | Wi-Fi Manager | Opens Rofi Wi-Fi manager |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>B</kbd> | Bluetooth Manager | Opens Rofi Bluetooth manager |

### Window Management
| Shortcut | Action | Description |
| :--- | :--- | :--- |
| <kbd>Super</kbd> + <kbd>W</kbd> / <kbd>Super</kbd> + <kbd>Q</kbd> | Close Window | Closes active window |
| <kbd>Super</kbd> + <kbd>T</kbd> / <kbd>Super</kbd> + <kbd>V</kbd> | Toggle Floating | Switches window between tiling and floating |
| <kbd>Super</kbd> + <kbd>F</kbd> | Fullscreen | Clean fullscreen mode (no status bar) |
| <kbd>Super</kbd> + <kbd>Alt</kbd> + <kbd>F</kbd> | Maximize | Maximizes window while keeping status bar |
| <kbd>Super</kbd> + <kbd>P</kbd> | Pseudo Tiling | Toggles pseudo tiling mode |
| <kbd>Super</kbd> + <kbd>J</kbd> | Split Direction | Toggles horizontal vs vertical split in Dwindle |
| <kbd>Super</kbd> + <kbd>G</kbd> | Group Windows | Groups windows into a single tabbed container |
| <kbd>Super</kbd> + <kbd>Alt</kbd> + <kbd>G</kbd> | Ungroup | Moves window out of active group |
| <kbd>Super</kbd> + <kbd>Alt</kbd> + <kbd>Tab</kbd> | Cycle Group | Cycles through tabs in active group |
| <kbd>Super</kbd> + Arrow Keys | Focus Window | Moves focus Left, Right, Up, or Down |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + Arrow Keys | Move Window | Moves/swaps window position |
| <kbd>Super</kbd> + <kbd>=</kbd> / <kbd>-</kbd> | Resize Window | Coarse window resize (+/- 30px) |
| <kbd>Super</kbd> + <kbd>;</kbd> | Shrink Window | Shrinks the focused window by 30px |
| <kbd>Super</kbd> + <kbd>'</kbd> | Enlarge Window | Enlarges the focused window by 30px |
| <kbd>Super</kbd> + Left Mouse Drag | Drag Window | Drags window to float / reposition |
| <kbd>Super</kbd> + Right Mouse Drag | Resize Window | Resizes window via mouse |

### Workspace Management
Workspace shortcuts now cover 1–10 to match the Display Manager; use <kbd>Super</kbd> + <kbd>0</kbd> for workspace 10.

| Shortcut | Action | Description |
| :--- | :--- | :--- |
| <kbd>Super</kbd> + <kbd>1</kbd> .. <kbd>9</kbd>, <kbd>0</kbd> | Switch Workspace | Jumps to workspace 1 through 10; <kbd>0</kbd> selects workspace 10 |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>1</kbd> .. <kbd>9</kbd>, <kbd>0</kbd> | Move to Workspace | Moves focused window to workspace and follows |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>Alt</kbd> + <kbd>1</kbd> .. <kbd>9</kbd>, <kbd>0</kbd> | Move Silently | Moves focused window to workspace without following |
| <kbd>Super</kbd> + <kbd>Tab</kbd> | Next Workspace | Switches to next workspace (`e+1`) |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>Tab</kbd> | Prev Workspace | Switches to previous workspace (`e-1`) |
| <kbd>Super</kbd> + <kbd>Ctrl</kbd> + <kbd>Tab</kbd> | Previous Workspace| Switches to the most recently active workspace |
| <kbd>Super</kbd> + Scroll Wheel | Cycle Workspaces | Scrolls forward/backward through workspaces |

### System & Session Management
| Shortcut | Action | Description |
| :--- | :--- | :--- |
| <kbd>Super</kbd> + <kbd>Escape</kbd> | Power Menu | Opens system session menu (Lock, Suspend, Reboot, Shutdown) |
| <kbd>Super</kbd> + <kbd>L</kbd> / <kbd>Super</kbd> + <kbd>Ctrl</kbd> + <kbd>L</kbd> | Lock Screen | Locks desktop immediately with Hyprlock |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>R</kbd> | Reload Desktop | Restarts Waybar and reloads Hyprland configuration |
| <kbd>Super</kbd> + <kbd>Ctrl</kbd> + <kbd>A</kbd> | Audio Switcher | Opens PipeWire audio sink and source switcher |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>D</kbd> | Toggle DND | Toggles notification Do Not Disturb mode |
| <kbd>Super</kbd> + <kbd>Ctrl</kbd> + <kbd>N</kbd> | Notification History | Opens Rofi notification history viewer |
| <kbd>Super</kbd> + <kbd>N</kbd> | Pop Notification | Displays the most recent notification |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>N</kbd> | Dismiss Notifications| Closes all active notification popups |

### Productivity, Capture & Cheatsheets
| Shortcut | Action | Description |
| :--- | :--- | :--- |
| <kbd>Super</kbd> + <kbd>K</kbd> | Shortcuts Menu | Opens searchable keybindings modal in Rofi |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>K</kbd> | Cheatsheet Window | Launches floating Kitty window with all shortcuts |
| <kbd>Super</kbd> + <kbd>Ctrl</kbd> + <kbd>W</kbd> | Wallpaper Selector | Visual thumbnail wallpaper browser |
| <kbd>Super</kbd> + <kbd>Ctrl</kbd> + <kbd>Space</kbd> | Wallpaper Selector | Alternative shortcut for wallpaper selector |
| <kbd>Super</kbd> + <kbd>Ctrl</kbd> + <kbd>V</kbd> | Clipboard History | Opens clipboard history manager |
| <kbd>Super</kbd> + <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>V</kbd> | Clear Clipboard | Wipes all stored clipboard history |
| <kbd>Print</kbd> | Region Screenshot | Interactive area capture to file & clipboard |
| <kbd>Super</kbd> + <kbd>Print</kbd> | Full Screenshot | Captures entire display to file & clipboard |
| <kbd>Super</kbd> + <kbd>Ctrl</kbd> + <kbd>C</kbd> | Screenshot Menu | Capture menu (Region, Window, Full, Delay) |

### Hardware Media Keys
| Key | Action | Description |
| :--- | :--- | :--- |
| `XF86AudioRaiseVolume` | Volume Up | Raises output volume (+5%) |
| `XF86AudioLowerVolume` | Volume Down | Lowers output volume (-5%) |
| <kbd>Alt</kbd> + `XF86AudioRaiseVolume` | Fine Volume Up | Fine volume adjustment (+1%) |
| <kbd>Alt</kbd> + `XF86AudioLowerVolume` | Fine Volume Down | Fine volume adjustment (-1%) |
| `XF86AudioMute` | Mute Audio | Toggles output audio mute |
| `XF86AudioMicMute` | Mute Microphone | Toggles microphone mute |
| `XF86MonBrightnessUp` | Brightness Up | Raises backlight (+5%) |
| `XF86MonBrightnessDown` | Brightness Down | Lowers backlight (-5%) |
| <kbd>Alt</kbd> + `XF86MonBrightnessUp` | Fine Brightness Up | Fine backlight adjustment (+1%) |
| <kbd>Alt</kbd> + `XF86MonBrightnessDown` | Fine Brightness Down | Fine backlight adjustment (-1%) |
| <kbd>Shift</kbd> + `XF86MonBrightnessUp` | Max Brightness | Sets backlight to 100% |
| <kbd>Shift</kbd> + `XF86MonBrightnessDown` | Min Brightness | Sets backlight to minimum (5%) |

---

## Interactive Waybar Modules

The Waybar status bar at the top of the screen provides direct mouse interactions:

| Module | Left-Click | Right-Click | Scroll Wheel |
| :--- | :--- | :--- | :--- |
| **Workspaces** | Switch to workspace | — | Switch workspace |
| **CPU (``)** | Open Btop monitor | — | — |
| **Memory (``)** | Open Btop monitor | — | — |
| **Network (`󰤨`)** | Open Wi-Fi Manager | — | — |
| **Audio (`󰕾`)** | Open Audio Switcher | Mute / Unmute | Volume +/- |
| **Mic (`󰍬`)** | Open Microphone Selector | Mute / Unmute Mic | Volume +/- |
| **Bluetooth (`󰂯`)** | Open Bluetooth Manager | — | — |
| **Battery (`󰁹`)** | Open Power & Battery Center | Cycle Power Profile | — |
| **Power Profile (`󰓅`/`󰾆`/`󰌪`)** | Shows current active profile | — | — |
| **DND (`󰂚`)** | Toggle Do Not Disturb | — | — |
| **Clock (`󰸗`)** | Show Calendar | Toggle 24h Seconds | Scroll calendar |
| **Power (`󰐥`)** | Open System Power Menu | — | — |

---

## Customization Guide

### Changing Wallpapers
1. Copy any `.png`, `.jpg`, or `.webp` image into `~/.config/hypr/wallpapers/`.
2. Press <kbd>Super</kbd> + <kbd>Ctrl</kbd> + <kbd>W</kbd> to open the thumbnail selector and select your image.
3. Both the desktop and lockscreen will update immediately.

### Adjusting Window Gaps, Rounding & Borders
Edit [appearance.lua](file:///home/darkglitch/.config/hypr/lua/appearance.lua):
```lua
hl.config({
    general = {
        gaps_in = 4,         -- Gap between adjacent tiled windows (px)
        gaps_out = 8,        -- Gap between windows and screen edges (px)
        border_size = 1,     -- Window border width (px)
    },
    decoration = {
        rounding = 8,        -- Window corner radius (px)
        active_opacity = 0.98,
        inactive_opacity = 0.92,
    }
})
```
Press <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>R</kbd> to reload.

### Adding Autostart Applications
Edit [autostart.lua](file:///home/darkglitch/.config/hypr/lua/autostart.lua) and add your command inside the `hl.on("hyprland.start", ...)` block:
```lua
hl.exec_cmd("my-daemon-or-command")
```

### Adding Custom Window or Layer Rules
Edit [rules.lua](file:///home/darkglitch/.config/hypr/lua/rules.lua):
```lua
-- Force an application to float and center
hl.window_rule({
    name = "my-custom-float",
    match = { class = "my-app" },
    float = true,
    size = { 800, 600 },
    center = true,
})
```

---

## Maintenance & Verification

### Verifying Configuration Syntax
Always verify before reloading if you make manual changes:
```bash
# Check Hyprland Lua configuration
XDG_RUNTIME_DIR=/tmp Hyprland --verify-config

# Check Waybar configuration JSON
python3 -m json.tool ~/.config/hypr/waybar/config.jsonc > /dev/null
```

### Safe Rollback
If you ever need to restore the configuration back to the pre-modification state:
```bash
cp -r ~/.config/hypr/.backup/phase1-pre/* ~/.config/hypr/
```
