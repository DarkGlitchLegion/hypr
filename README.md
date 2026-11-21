# Arch Linux Hyprland Rice — Minimal Dark Ecosystem

A developer-focused personal workstation environment built on **Arch Linux**, **Hyprland 0.57.2+ (native Lua engine)**, **Quickshell/QML**, **Rofi Wayland**, and **Dunst**. Waybar is retained as a fallback shell.

Designed around the **Minimal Dark Charcoal palette** (`#0C0D10` background, `#17191F` surface, `#202126` card hover, `#AAAAAA` accent), this ecosystem emphasizes keyboard-driven workflows, zero bloat, and fast hardware integration.

## Installation

Clone the repository and run the single guided installer:

```sh
git clone https://github.com/DarkGlitchLegion/hypr.git
cd hypr
./setup.sh
```

The installer never runs as root, never deletes existing configuration without confirmation, and creates timestamped backups under `~/.local/share/hypr-rice/backups/` before replacing deployed components.

Installation profiles:

- `./setup.sh --minimal`: core Hyprland desktop components.
- `./setup.sh --standard` (default): core, desktop, and hardware utilities.
- `./setup.sh --full`: standard components plus optional convenience tools.

Safety and maintenance options:

```sh
./setup.sh --dry-run
./setup.sh --skip-packages
./setup.sh --backup-only
./setup.sh --restore
./setup.sh --restore /path/to/backup
./setup.sh --symlinks
./setup.sh --yes
```

Package installation is displayed before execution. Unsupported package managers are reported instead of using blind install commands. Package managers currently implemented for missing-package detection and installation are `pacman`, `apt`, and `dnf`; `apt` and `dnf` mappings vary by distribution and repository availability. GPU drivers, kernel settings, bootloaders, and root-level system configuration are never changed automatically.

### Security behavior

- Bluetooth pairing and service authorization require an on-screen Rofi approval from the laptop user. The adapter is pairable/discoverable only for a bounded 120-second window.
- HyprSec container configuration requires an immutable `@sha256:<digest>` image reference. Tag-only references such as `:latest` are rejected.
- Installer restore operations validate backup manifests and destinations, reject symlinks and paths outside rice-owned configuration roots, and display a restore preview before applying changes.

### Updating

Pull repository changes, review the diff, and run `./setup.sh --dry-run` before applying an update. Use `./setup.sh` to merge deployable components into `~/.config/hypr` while preserving existing state JSON files and unrelated files.

### Backup and restore

- `./setup.sh --backup-only` creates a timestamped backup without deploying or installing packages.
- `./setup.sh --restore` restores the latest backup.
- `./setup.sh --restore /path/to/backup` restores a specific backup.
- Restoring automatically creates a safety backup of the current configuration first.

Installation activity is logged to `~/.local/state/hypr-rice/install.log`. Backup manifests and component contents are stored under `~/.local/share/hypr-rice/backups/`.

### Troubleshooting

- Run `./setup.sh --dry-run` to inspect the detected hardware, package plan, and deployment plan without changes.
- Run `scripts/rice validate` after installation to check syntax and configuration references.
- Run `scripts/rice doctor --full` for runtime and dependency diagnostics.
- Do not run `setup.sh` with `sudo`; it intentionally refuses root execution.

---

## Architecture Overview

Hyprland 0.57.2+ runs natively with a modular Lua architecture under `~/.config/hypr/lua/`. Configurations are modularized to prevent configuration drift:

```
~/.config/hypr/
├── hyprland.lua              # Master entrypoint & shared desktop context
├── hyprland.conf             # Compatibility bridge for Hyprland
├── hyprland/                  # Inactive static configs retained for reference
│   └── legacy/
│       ├── animations.conf
│       ├── hypridle.conf
│       ├── keybinds.conf
│       └── windowrules.conf
├── lua/                      # Modular Lua configuration subsystem
│   ├── monitors.lua          # 1:1 native display setup (prevents fractional scaling)
│   ├── autostart.lua         # Background daemons, Polkit, Quickshell, Dunst, etc.
│   ├── env.lua               # Wayland environment variables & cursor synchronization
│   ├── appearance.lua        # Compositor layout, borders, rounding, shadows & blur
│   ├── animations.lua        # Custom quintic & cubic Bezier animation curves
│   ├── rules.lua             # Window rules, dialog centering & layer blur rules
│   ├── app-placement.lua     # Optional app-specific workspace placement rules
│   └── keybinds.lua          # Keyboard shortcuts & window dispatchers
├── quickshell/               # Primary modular Quickshell/QML bar
├── waybar/                   # Retained Waybar fallback
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
│   ├── rice                  # CLI entry point: doctor, validate, snapshot, logs, test
│   ├── rice_maintenance.py   # Diagnostics, safe snapshots, validation, and tests
│   ├── rice_events.py        # Bounded, secret-filtering JSONL activity log
│   ├── idle-manager.py       # Persistent timeout profiles and supervised Hypridle
│   ├── session-presets.py    # Save/apply/restore reversible desktop session bundles
│   ├── audio-menu.sh         # Rofi entry point for the PipeWire audio manager
│   ├── audio-manager.py      # Live sink/source selector and optional HDMI hotplug handling
│   ├── power-profile-menu.sh # AMD P-State power profile switcher & battery health
│   ├── wifi-menu.sh          # Non-blocking network manager
│   ├── bluetooth-menu.sh     # Peripheral management & pairing
│   ├── bluetooth-status.py   # Bluetooth power/connection status helper
│   ├── bluetooth-agent.py    # D-Bus pairing & authentication agent
│   ├── quick-settings.py     # GTK quick-settings popup and live system controls
│   ├── quick-settings-status.py # Shared Quickshell/Waybar connectivity/audio/battery status
│   ├── hyprsec-box.sh        # Rootless Kali container and workspace manager
│   ├── hyprsec-install.sh    # Idempotent HyprSec setup
│   ├── hyprsec-uninstall.sh  # Confirmed container removal; preserves user data
│   ├── wallpaper-selector.sh # Rofi wallpaper thumbnail chooser
│   ├── set-wallpaper.sh      # Hyprpaper IPC reload & Hyprlock persistence
│   ├── clipboard-menu.sh     # Cliphist history browser
│   ├── clipboard-daemon.sh   # Background clipboard listener
│   ├── screenshot.sh         # Grim + Slurp region, window & full capture
│   ├── volume.sh             # PipeWire volume & microphone controller
│   ├── brightness.sh         # Display backlight controller (brightnessctl)
│   ├── notification-toggle.sh# Do Not Disturb toggle
│   ├── apply-gtk-theme.sh    # GTK3/4 Adwaita-dark theme synchronizer
│   ├── start-bar.sh          # Quickshell primary, selectable Waybar fallback
│   ├── restart-bar.sh        # Restart the currently selected shell
│   └── rollback-to-waybar.sh # Switch current/future sessions to Waybar
├── kitty/                    # Kitty terminal emulator configuration
├── dunst/                    # Dunst notification daemon configuration
├── hyprlock/                 # Hyprlock minimalist lockscreen
├── hyprpaper/                # Hyprpaper configuration
│   └── hyprpaper.conf
├── hyprclock/                # Hyprclock configuration
│   └── hyprclock.conf
├── hyprsec/                  # HyprSec defaults, tool catalog, and guide
├── state/                    # Persistent display, idle, session, and wallpaper state
│   ├── current_wallpaper
│   ├── display-preferences.json
│   ├── display-profiles.json
│   ├── idle-settings.json
│   └── session-presets.json
└── wallpapers/               # Curated wallpaper library
```

Root-level compatibility symlinks preserve established paths for legacy configs, Hyprpaper, Hyprclock, and persisted state. The Hyprland entrypoint, scripts, and active Lua modules remain at their established paths.

### Locating and debugging configuration
* **Hyprland startup**: `hyprland.conf` loads `hyprland.lua`, which loads the active modules in `lua/`.
* **Active behavior**: Edit `lua/keybinds.lua`, `lua/appearance.lua`, `lua/animations.lua`, `lua/monitors.lua`, `lua/rules.lua`, or `lua/autostart.lua` for their respective settings. The similarly named files in `hyprland/legacy/` are retained static configs, not the active Lua modules.
* **Bar and menus**: Quickshell modules are in `quickshell/`; Waybar is retained in `waybar/` for recovery; Rofi themes are in `rofi/`.
* **Persisted settings**: Display profiles/preferences, idle settings, session presets, and the saved wallpaper path are in `state/`. Root-level compatibility symlinks keep older references working.
* **Validation**: Run `scripts/rice validate` for config references and syntax checks, or `scripts/rice doctor --full` for broader diagnostics.

### Quickshell/QML shell
Quickshell is the primary Hyprland shell. The native QML UI includes the bar, app launcher, dashboard, settings, notification history, OSD, and a Control Center with network, Bluetooth, audio, displays, idle, screenshots, session presets, clipboard, wallpaper, power, maintenance, and HyprSec pages. <kbd>Super</kbd> + <kbd>C</kbd> or <kbd>Super</kbd> + <kbd>Alt</kbd> + <kbd>Space</kbd> opens the Control Center; <kbd>Super</kbd> + <kbd>K</kbd> opens its searchable keybindings list. Existing scripts continue to perform system operations behind these QML views. Waybar remains an explicit recovery fallback.

<kbd>Super</kbd> + <kbd>Space</kbd> opens the Quickshell application launcher with fuzzy app search, favorites, recent queries, safe browser search (`? words`), arithmetic (`= 2 * (3 + 4)`), and QML Control Center shortcuts. Its dashboard reports CPU, memory, storage, and battery metrics; shell preferences save automatically in Quickshell state. See [quickshell/README.md](./quickshell/README.md) for the QML modules, startup, recovery, and development workflow.

Volume, microphone, and brightness hotkeys show a short Quickshell OSD while its IPC endpoint is available, with Dunst notifications as fallback.

Run [rollback-to-waybar.sh](./scripts/desktop/rollback-to-waybar.sh) to hide Quickshell and switch the current and future sessions to Waybar. `Super+Shift+R` still reloads the bar and Hyprland configuration; it now reloads whichever shell is selected. Review [quickshell/README.md](./quickshell/README.md) for deployment, startup, and recovery details.

---

## Core Features & How to Use Them

### HyprSec Box — Rootless Security Workspace
* **Open**: <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>H</kbd>, or Control Center → HyprSec Box. Change the key in `~/.config/hyprsec/keybind`, then reload Hyprland.
* **Install**: Run `~/.config/hypr/scripts/hyprsec-install.sh` as your regular user. It asks before installing Podman or pulling the Kali Rolling image and preserves existing HyprSec configuration.
* **Isolation**: Rootless Podman, no privileged mode, no host-wide mounts, dropped capabilities, and an internal-only network by default. Only `~/HyprSec/workspace` subdirectories are mounted.
* **Network**: Enable the named rootless bridge explicitly from the menu when package downloads are needed; it requires confirmation. Disable it afterward. The bar's status cluster includes the existing container state indicator; manage the container from Control Center, where network changes require confirmation.
* **Tools and projects**: Manage the curated APT catalog in `~/.config/hyprsec/tools.conf`; package actions happen inside Kali. Create projects under `~/HyprSec/workspace/projects/`. Cleanup is project-scoped and interactive; removing the container preserves workspace files.
* **Configuration and full guide**: See [hyprsec/README.md](./hyprsec/README.md). The default catalog is limited to diagnostics, analysis, development, and reporting tools.

### 1. Rice Control Center (Unified Super-Hub)
* **Hotkey**: <kbd>Super</kbd> + <kbd>C</kbd> or <kbd>Super</kbd> + <kbd>Alt</kbd> + <kbd>Space</kbd>
* **Script**: `~/.config/hypr/scripts/desktop/control-center.sh`
* **What it does**: Provides a centralized keyboard dashboard for the entire desktop.
  * **Rice Health & Diagnostics** is available under System & Performance. It checks Hyprland config/IPC, display watcher count, active monitor geometry for overlaps, workspace state, saved external workspace preference, and commands used by rice features. Choose **Refresh diagnostics** to re-query live state.
  * **Categorized Submenus**:
    * `󰒓 System & Performance`: Rice health diagnostics, process monitor (`btop`), power center, disk usage, desktop/bar reload.
    * `󰤨 Hardware & Connectivity`: Wi-Fi, Bluetooth, PipeWire audio switcher, battery diagnostics.
    * `󰍹 Display & Personalization`: Wallpaper selector, GTK theme synchronization, display info.
    * `󰲋 Developer & Workstation`: VS Code, Kitty, Lazygit, HyprSec Box, tools folder, CMatrix.
    * `󰅇 Productivity & Capture`: Clipboard history, screenshot suite, shortcuts cheatsheet.
    * `󰐥 Session & Power`: Lock screen (Hyprlock), suspend, reboot, poweroff, logout.
  * **Direct Fuzzy Search**: You don't need to navigate submenus—simply type keywords like `wifi`, `audio`, `btop`, `lock`, or `screenshot` to trigger actions immediately from the first screen.

  ### Maintenance Center
  * **Open**: Control Center → **Maintenance Center**. The Rice Diagnostics view is also reachable from System & Performance.
  * **CLI**: Run `~/.config/hypr/scripts/rice doctor`, `doctor --full`, `doctor --module audio`, `validate`, `dependencies --full`, `reload`, or `test`.
  * **Reports**: `rice doctor --report` writes a timestamped report under `~/.local/state/hypr-rice/reports/`; `rice doctor --report PATH` chooses a destination.
  * **Safe repairs**: `rice doctor --fix` offers only a confirmed status refresh for the retained Waybar fallback. It does not edit configs, install packages, or restart services.
  * **Snapshots**: `rice snapshot create`, `list`, `diff ID`, `compare ID OTHER`, `restore ID`, `delete ID`, and `retention N`. Restore previews affected paths, requires confirmation, snapshots the current config first, validates the restored config, and rolls back on validation failure. It can recover from an already-invalid config. Restore is additive: it does not delete files absent from a snapshot. Backups are stored under `~/.local/share/hypr-rice/snapshots/`, with default retention of 10. Display, audio, session-preset, and snapshot-setting changes automatically snapshot their previous saved preferences.
  * **Safe reload**: `rice reload` validates Hyprland and Lua syntax before reloading, then checks Hyprland's reported config errors. Use <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>R</kbd> to reload the selected bar.
  * **Activity**: `rice logs` supports `--module`, `--severity`, `--search`, `--since YYYY-MM-DD`, `--export PATH`, and confirmed `--clear`. JSONL logs rotate at 2 MiB with three retained generations in `~/.local/state/hypr-rice/`.
  * Snapshots exclude `.git`, `.backup`, caches, wallpaper image assets, log files, and common private key/credential filenames. Snapshot restore and manual snapshot deletion always require explicit confirmation. Before manually editing config files, use `rice snapshot create --label pre-manual-edit`.
  * Tests use Python's built-in `unittest`; no new packages are required. The repeatable hardware checklist is in [docs/maintenance-testing.md](./docs/maintenance-testing.md).

  ---

### QML Quick Controls and Control Center
* **Open Quick Controls**: Click the status cluster on the Quickshell bar. Use the Control Center sidebar for network, Bluetooth, audio, display, idle, wallpaper, clipboard, keybinding, screenshot, session, and maintenance views.
* **Device actions**: Wi-Fi networks and known Bluetooth devices are listed in QML. Audio outputs and inputs come from the existing PipeWire backend; select a device and adjust active levels in the Audio page.
* **Other pages**: Display presets preserve the rollback-aware display manager; idle presets preserve the validated timeout manager; wallpaper choices call the existing setter; clipboard history calls the existing clipboard daemon and clear operation.
* **Scripts**: `scripts/desktop/open-hub.sh`, `scripts/hardware/qml-network.py`, `scripts/hardware/qml-bluetooth.py`, and the existing hardware/session backends.

---

### 2. PipeWire Audio Control Center
* **Hotkey**: <kbd>Super</kbd> + <kbd>Ctrl</kbd> + <kbd>A</kbd>
* **Bar Trigger**: Click the Quickshell status cluster, then click the Speaker or Microphone row's icon/text to open the audio manager. The switches toggle mute.
* **Script**: `~/.config/hypr/scripts/hardware/audio-menu.sh`
* **What it does**:
  * Enumerates current PipeWire-Pulse outputs and inputs from JSON, including built-in speakers, HDMI/DisplayPort, Bluetooth, and headsets when exposed by PipeWire.
  * Shows the active route and device-provided description; selecting an output changes the default and moves active streams.
  * The **Set output volume** menu offers 0–100% in 5% steps. The volume hotkeys adjust volume; middle-click opens Pavucontrol's live sliders and per-app routing.
  * Automatic HDMI routing is **off by default**. Enable it from the audio menu; the single autostart watcher selects HDMI/DisplayPort when an audio sink appears and falls back when it disappears.
  * Manual output selection is saved in `~/.config/hypr/audio-preferences.json` and restored at startup or when that output reconnects, provided automatic HDMI routing has not taken precedence.
  * No audio-device names are hardcoded. A connected TV without a PipeWire audio sink is ignored.

### Application Workspace Placement
* Applications, including Firefox, open on the currently active workspace by default.
* The saved external workspace preference is used by Display Manager for HDMI layout only; it does not place application windows.
* Add an app-class-to-workspace rule in [app-placement.lua](./lua/app-placement.lua) only when you want that app forced to a particular workspace.

### Session Presets
* Open **Session Presets** from the Display Manager or Control Center's Display menu.
* Choose **Save current session…** and save a `Work`, `Presentation`, or custom-named preset. A preset records the current connected-monitor layout, each active monitor's workspace, DND state when Dunst is available, and whether a rice-managed idle inhibitor is active.
* Apply a saved preset to switch to that combination. Display changes use the Display Manager's existing confirmation and rollback flow; disconnected or changed monitor setups are rejected rather than partially applied.
* **Restore previous session** returns to the layout, monitor workspaces, notification state, and idle behavior from before the active session preset. Preset definitions persist in `~/.config/hypr/state/session-presets.json`; the temporary restore snapshot lasts for the current login session.
* Session presets and Presentation Mode are mutually exclusive because Presentation Mode already owns a separate reversible display/DND/idle state.

### Screen Timeout and Idle Management
* **Open**: Control Center → **Screen Timeout / Idle Management**. One menu provides timeout presets, the idle toggle, Keep Awake, and detailed action settings.
* **CLI**: `~/.config/hypr/scripts/session/idle-manager.py --menu` (`--quick` remains an alias), `--status`, `--validate`, `--preset "Power Saving"`, `--master off`, `--keep-awake`, or `--resume-idle`.
* **Saved settings**: `~/.config/hypr/state/idle-settings.json`; the idle manager snapshots the previous rice config before changing an existing settings file. Runtime Hypridle config and manager state are generated under `$XDG_RUNTIME_DIR/hypr-rice-idle/`.
* **Profiles**: Balanced (default), Power Saving, Security Focused, Relaxed, Never, and fixed 5–60 minute lock-time profiles. Individual actions can be toggled and set from 15 seconds to 24 hours.
* **Defaults**: Balanced dims at 2 minutes, blanks at 5, locks at 10, powers displays off at 15, and leaves suspend disabled. Power Saving enables suspend at 15 minutes; no other preset enables suspend.
* **Application**: Changes restart only the managed Hypridle process, not Hyprland. The supervisor ensures the rice has only one Hypridle instance and retries/logs daemon failures.
* **Keep awake**: The Screen Timeout / Idle Management menu can temporarily inhibit idle actions. Presentation Mode continues using the existing systemd inhibitor and does not modify saved timeouts. Session Presets capture/restore the rice-managed idle inhibit state.
* **Safety**: If automatic locking is enabled, display power-off is delayed until the session lock is confirmed; suspend runs after locking and display power-off. Manual lock remains independent.
* **Hardware limitation**: Hyprland exposes one DPMS off state, so “Blank screen” and “Turn off display” share the same operation. The earlier enabled timeout is used, adjusted to follow the lock timeout if locking is enabled. Backlight dimming depends on `brightnessctl` and a supported backlight device; the display and action commands are checked before applying.

---

### 3. Power Profiles & Battery Center
* **Bar Trigger**: Open Quick Controls from the Quickshell status cluster, then use the Audio & Display page to select a power profile.
* **Script**: `~/.config/hypr/scripts/session/power-profile-menu.sh`
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
  * Power profile selection is available on the QML Audio & Display page.

---

### 4. Graphical Wi-Fi Manager
* **Hotkey**: <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>S</kbd>
* **Bar Trigger**: Click the Quickshell status cluster, then click the Wi-Fi row's icon/text to open the network manager. The switch toggles the Wi-Fi radio.
* **Script**: `~/.config/hypr/scripts/hardware/wifi-menu.sh`
* **What it does**:
  * Scans nearby Wi-Fi networks in the background (`nmcli --rescan no`) for fast response times.
  * Displays signal strength icons, security state (WPA/WPA2/open), and active connection indicators.
  * The QML Network page includes password entry for secured networks and a rescan control.
  * Includes options to toggle Wi-Fi radio on/off and force an access point rescan.

---

### 5. Graphical Bluetooth Manager & Pairing Agent
* **Hotkey**: <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>B</kbd>
* **Bar Trigger**: Click the Quickshell status cluster, then click the Bluetooth row's icon/text to open the manager. The switch toggles Bluetooth power.
* **Scripts**: `~/.config/hypr/scripts/hardware/bluetooth-menu.sh`, `bluetooth-status.py`, and `bluetooth-agent.py`
* **What it does**:
  * The Quick Settings popup shows whether Bluetooth is powered off (`󰂲`), powered on (`󰂯`), or connected (`󰂱`), and refreshes the state while open.
  * Connects to BlueZ via D-Bus and `bluetoothctl`.
  * Runs a default `KeyboardDisplay` agent and asks for explicit approval on the laptop for pairing and Bluetooth service requests.
  * Approval dialogs use the matching charcoal Rofi theme; pairing mode is visible for three minutes, and agent registration/errors are logged to `~/.local/state/hypr/bluetooth-agent.log`.
  * Lists paired and discovered devices with battery status percentages.
  * Allows connecting, disconnecting, pairing, and unpairing peripherals without launching external GUI tools.

---

### 6. Wallpaper Selector & Persistence Engine
* **Hotkey**: <kbd>Super</kbd> + <kbd>Ctrl</kbd> + <kbd>W</kbd> or <kbd>Super</kbd> + <kbd>Ctrl</kbd> + <kbd>Space</kbd>
* **Scripts**: `~/.config/hypr/scripts/wallpaper/wallpaper-selector.sh` & `set-wallpaper.sh`
* **What it does**:
  * Displays a visual grid of all wallpapers in `~/.config/hypr/wallpapers/` (PNG, JPG, WEBP).
  * Automatically applies the selected image to Hyprpaper via IPC without restarting the daemon.
  * Persists the choice in `~/.config/hypr/state/current_wallpaper` and updates `hyprpaper/hyprpaper.conf`.
  * Automatically synchronizes the lockscreen background in [hyprlock.conf](file:///home/darkglitch/.config/hypr/hyprlock/hyprlock.conf) so lock screen and desktop wallpapers stay consistent.

---

### 7. Clipboard History Manager
* **Hotkey**: <kbd>Super</kbd> + <kbd>Ctrl</kbd> + <kbd>V</kbd>
* **Clear History**: <kbd>Super</kbd> + <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>V</kbd>
* **Scripts**: `~/.config/hypr/scripts/clipboard/clipboard-menu.sh` & `clipboard-daemon.sh`
* **What it does**:
  * Runs a lightweight `wl-paste` listener.
  * Uses `cliphist` when available; otherwise it uses the built-in cache and works without extra packages.
  * Pressing <kbd>Super</kbd> + <kbd>Ctrl</kbd> + <kbd>V</kbd> opens the searchable QML clipboard history.
  * Selecting an entry copies it back to the active clipboard buffer ready for pasting.

---

### 8. Screenshot & Capture Suite
* **Interactive Area**: Press <kbd>Print</kbd>
* **Fullscreen**: Press <kbd>Super</kbd> + <kbd>Print</kbd>
* **Capture Menu**: Press <kbd>Super</kbd> + <kbd>Ctrl</kbd> + <kbd>C</kbd>
* **Script**: `~/.config/hypr/scripts/session/screenshot.sh`
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
* **Quickshell indicators**: The bar shows the displayed-notification count and opens the existing notification-history viewer when clicked. DND remains available through the status cluster and existing keybinding.

---

### 10. Lock Screen & Idle Power Management
* **Instant Lock**: <kbd>Super</kbd> + <kbd>L</kbd> or <kbd>Super</kbd> + <kbd>Ctrl</kbd> + <kbd>L</kbd>
* **Daemons**: `hyprlock`, plus one supervised `hypridle` managed by `scripts/session/idle-manager.py`
* **What it does**:
  * Uses a clean 2D charcoal layout with custom date/time fonts and smooth input dots animations.
  * Idle profiles, individual action timers, and temporary keep-awake controls are available from the Control Center. Balanced is the default; suspend is opt-in.
  * Settings persist in `~/.config/hypr/state/idle-settings.json`. Hypridle is reconfigured without restarting Hyprland.
  * The former `hypridle.conf` is no longer launched directly; the idle manager generates the active Hypridle config in the runtime directory.

---

### 11. GTK Dark Theme & Icon Synchronization
* **Script**: `~/.config/hypr/scripts/desktop/apply-gtk-theme.sh`
* **What it does**:
  * Synchronizes `settings.ini` for GTK 3.0 and GTK 4.0.
  * Applies **Adwaita-dark** theme, **Papirus-Dark** icons, and **Adwaita** 20px cursor.
  * Injects custom CSS into `~/.config/gtk-3.0/gtk.css` so Thunar and GTK dialogs match the charcoal palette (`#0C0D10`).

---

### 12. External Display Manager
* **Hotkey**: <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>M</kbd>
* **Control Center**: Open **Display & Personalization** → **Display Manager**
* **Script**: `~/.config/hypr/scripts/hardware/display-manager.py`
* **Monitor configuration**: [monitors.lua](./lua/monitors.lua) remains the default fallback rule; display changes are applied at runtime and do not rewrite it.
* **Previous limitation**: The fallback rule only selected a preferred mode, and the Control Center's display action only printed monitor information; there was no hotplug watcher, layout UI, or saved profile.
* **What it does**:
  * Reads monitor modes, resolution, refresh rate, scaling, position, and orientation from Hyprland. Detects connector plug/unplug state through the kernel DRM status files without hardcoding individual connector names.
  * Offers Laptop only, External display only, Extend (left/right/above/below), Mirror, and Presentation layouts.
  * Per-monitor controls enable/disable outputs, select a reported resolution/refresh rate, adjust scale and orientation, position relative to another display, or move a display to the top-left primary position.
  * Every manual layout change has a 20-second confirmation window; choosing Keep saves it to `~/.config/hypr/state/display-profiles.json`, while canceling or letting the timer expire restores the previous layout. Presentation layouts are session-only and never overwrite saved normal layouts.
  * Use **Reapply saved layout** to choose and reload a saved profile on demand after changing display settings.
  * A singleton startup watcher listens to Hyprland's monitor IPC events and debounces rapid connect/disconnect events. New displays trigger a Dunst notification with layout choices. It only auto-applies a layout when you explicitly saved that exact connected-monitor combination.
  * Every layout apply is serialized, re-detects connectors before each rule, enables target displays before disabling others, and verifies the resulting state. An unconfirmed change rolls back; a hotplug during confirmation cancels it and restores a safe connected display.
  * On disconnection, the watcher refreshes connector state, enables the internal display if no output remains active, and moves workspaces off unavailable monitors where needed. A singleton lock prevents duplicate listeners and conflicting operations.
  * **Preset-transition root cause fixed**: `hl.monitor` updates an existing monitor rule. The old runtime rule omitted `disabled = false`, so an output disabled by Laptop only remained disabled when later presets tried to re-enable it. The updated rule explicitly sets both `disabled` and `mirror`, clearing inherited state.
  * **External workspace selection**: Extend prompts for a numbered workspace (1–10), an existing named workspace, or a new named workspace. The preference is stored once in `state/display-preferences.json`, applied when extending, and reapplied on reconnect/restart only when both the laptop and an external output are active. The manager does not define a fixed Workspace 3 rule. If the selected workspace is currently active on the laptop, it asks before moving it; creating or activating a workspace on the external monitor restores the previously focused monitor.
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
| <kbd>Super</kbd> + <kbd>Space</kbd> | App Launcher | Opens Quickshell application launcher |
| <kbd>Super</kbd> + <kbd>C</kbd> | Rice Control Center | Opens the unified desktop super-hub |
| <kbd>Super</kbd> + <kbd>Alt</kbd> + <kbd>Space</kbd> | Rice Control Center | Alternative shortcut for Control Center |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>F</kbd> | File Manager | Opens Thunar file manager |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>E</kbd> | Text Editor | Launches VS Code (falls back to Nano in Kitty) |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>T</kbd> | Process Monitor | Opens Btop in transparent Kitty terminal |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>I</kbd> | System Information | Displays Fastfetch in a Kitty terminal |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>M</kbd> | Display Manager | Configure monitor layouts, modes, scaling, and orientation |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>C</kbd> | CMatrix | Matrix digital rain terminal screensaver |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>S</kbd> | Wi-Fi Manager | Opens QML Network page |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>B</kbd> | Bluetooth Manager | Opens QML Network page |

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
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>R</kbd> | Reload Desktop | Reloads the selected bar (Quickshell by default) and Hyprland configuration |
| <kbd>Super</kbd> + <kbd>Ctrl</kbd> + <kbd>A</kbd> | Audio Switcher | Opens PipeWire audio sink and source switcher |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>D</kbd> | Toggle DND | Toggles notification Do Not Disturb mode |
| <kbd>Super</kbd> + <kbd>Ctrl</kbd> + <kbd>N</kbd> | Notification History | Opens QML notification history |
| <kbd>Super</kbd> + <kbd>N</kbd> | Pop Notification | Displays the most recent notification |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>N</kbd> | Dismiss Notifications| Closes all active notification popups |

### Productivity, Capture & Cheatsheets
| Shortcut | Action | Description |
| :--- | :--- | :--- |
| <kbd>Super</kbd> + <kbd>K</kbd> | Shortcuts Menu | Opens searchable QML keybindings page |
| <kbd>Super</kbd> + <kbd>Shift</kbd> + <kbd>K</kbd> | Cheatsheet Window | Opens the QML keybindings page |
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

## Interactive Quickshell Bar

The Quickshell bar provides these mouse interactions; Waybar is retained as a fallback:

| Module | Left-Click | Right-Click | Scroll Wheel |
| :--- | :--- | :--- | :--- |
| **Workspaces** | Activate workspace | — | — |
| **Window title** | — | — | — |
| **Status cluster** | Open the existing Control Center | — | — |
| **Notifications** | Open Dunst notification history | — | — |
| **Clock** | Show/hide calendar | Toggle alternate time format | Change calendar month |
| **System tray** | Activate item | Open item menu | — |
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

# Check retained Waybar fallback configuration JSON
python3 -m json.tool ~/.config/hypr/waybar/config.jsonc > /dev/null
```

### Safe Rollback
If you ever need to restore the configuration back to the pre-modification state:
```bash
cp -r ~/.config/hypr/.backup/phase1-pre/* ~/.config/hypr/
```
