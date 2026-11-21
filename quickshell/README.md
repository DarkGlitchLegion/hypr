# Quickshell and QML desktop shell

Quickshell is the primary graphical shell for this Hyprland setup. The existing
Waybar configuration remains available as a recovery option. The QML shell
owns the bar, launcher, dashboard, settings, notification history, OSD, and
Control Center. System operations stay in the existing scripts and are called
with argument arrays from QML.

## Start and recover

Hyprland starts the selected bar with `scripts/desktop/start-bar.sh`. The
default is Quickshell. To return to Waybar, run:

```sh
~/.config/hypr/scripts/desktop/rollback-to-waybar.sh
```

Remove `~/.local/state/hypr-rice/bar-mode` and log in again to select
Quickshell. `Super+Shift+R` reloads the selected bar and Hyprland.

## QML modules

- `shell.qml`: shared settings/theme/services and IPC used by Hyprland binds.
- `config/`: design tokens and persistent preferences.
- `services/`: event-driven Hyprland workspace and window information.
- `modules/bar/`: workspace indicator, active title, tray, status, clock, and
  launcher-free bar controls.
- `modules/launcher/`: app search, favorites, history, calculator, web search,
  and QML Control Center shortcuts.
- `modules/controlcenter/`: overview plus controls, network, audio, displays,
  idle management, screenshots, HyprSec, system, maintenance, developer tools,
  session presets, wallpapers, clipboard, keybindings, power, and settings.
- `modules/notifications/`: Dunst-backed history, urgency, dismiss, clear, and
  DND controls.
- `modules/dashboard/`, `modules/settings/`, and `modules/osd/`: system
  metrics, shell preferences, and hardware feedback.

`Super+C` and `Super+Alt+Space` toggle the full Control Center. Clicking the
bar's status cluster toggles a separate, compact Quick Controls panel aligned
with the bar; clicking the cluster again or pressing Escape closes it. Neither
panel uses an in-panel close button. Existing menu entry scripts such as
`control-center.sh`, `keybindings-menu.sh`, `wallpaper-selector.sh`,
`clipboard-menu.sh`, and `power-menu.sh` now open the corresponding QML page.
Other shortcuts are documented in the searchable Keybindings page (`Super+K`).
`Super+W` and `Super+Q` close the active shell overlay first, and close the
focused application window when no overlay is open.

The wallpaper and clipboard pages use the established wallpaper setter,
clipboard daemon, and clipboard-clear operation. Audio, network, Bluetooth,
and display views use existing system tools or small JSON/action bridges.
Display layouts still use the transactional display manager and rollback
behavior. Dunst remains the notification daemon; Quickshell does not start a
second one.

Settings, wallpaper favorites, and recent wallpaper choices are written to
Quickshell state. Paths are derived from the deployed config directory. Missing
hardware tools produce empty device lists or normal command failures rather
than blocking shell startup.
Wi-Fi and Bluetooth actions now report pending/completed/failure state and
refresh their device lists when each command exits; audio slider updates are
coalesced while dragging to avoid spawning a process for every pointer event.

## Validation and development

Use `qs --path ~/.config/hypr/quickshell/shell.qml --verbose` to inspect startup
and `qs ipc --path ~/.config/hypr/quickshell/shell.qml show` to inspect IPC.
The code targets the installed Quickshell 0.3.2 API. `qmllint` can report
unresolved Quickshell-specific types because its standalone metadata does not
include all compositor types; verify actual loading with Quickshell as well.

The bar creates one panel per screen. Overlay panels use the primary screen and
remain independent of monitor-specific window management. Wallpaper and
clipboard backends keep their existing persistence and privacy behavior.

Interactive overlays use on-demand Wayland layer-shell keyboard focus, and
only one modal overlay is active at a time. This avoids competing popup grabs
when opening the launcher or Control Center from Hyprland keybindings.
