# Quickshell/QML desktop shell

Quickshell is the primary bar for this Hyprland rice. The root `shell.qml`
creates one panel per connected display. Modules use Quickshell's Hyprland,
system-tray, process, and IPC APIs; the existing scripts remain the source of
network, audio, battery, notification, Control Center, and power-menu behavior.

## Requirements and startup

- Arch Linux package `quickshell` (provides `qs`); installed Qt 6 runtime
- Hyprland 0.57+ with the native Lua configuration used by this rice
- Existing scripts and Dunst/NetworkManager/PipeWire services as available

The rice installer deploys `quickshell/` to
`~/.config/hypr/quickshell/` and includes Quickshell in the minimal package
profile. Hyprland starts the selected shell through
`scripts/desktop/start-bar.sh`; Quickshell is the default unless the persistent
bar-mode state selects Waybar. The launcher uses an absolute path derived from
the deployed config directory and `qs --no-duplicate`.

The live bar reuses `quick-settings-status.py` for network, audio, microphone,
battery, DND, and security status. It refreshes every five seconds, displays
the active Dunst notification count, opens the existing notification-history
viewer, and opens the existing Control Center from the status cluster. Workspace
switching/occupancy and active-window data come from Quickshell's Hyprland
integration; the tray is event-driven.

`Super+Space` and the bar launcher button open the Quickshell application
launcher. It searches installed desktop entries with subsequence fuzzy matching,
supports keyboard selection, saves favorites and recent queries, accepts
`? words` for a browser search, evaluates safe arithmetic after `=`, and offers
whitelisted actions after `!` (for example `!clipboard` or `!settings`). The
launcher also opens the existing wallpaper,
clipboard, control, and power tools. It does not run arbitrary typed commands.

The launcher’s Settings panel controls bar placement, visible bar modules,
accent color, and animation speed. These preferences are stored atomically in
Quickshell’s per-shell state directory as `settings.json`. The Dashboard panel
shows CPU, memory, storage, and battery metrics; it samples every five seconds
only while open. Both panels are centered on the first connected display.
Volume, microphone, and brightness scripts send event-driven updates to a short
Quickshell OSD and retain Dunst notifications as the fallback when no shell IPC
endpoint is available.

The existing GTK Control Center remains the backend interface for device
operations, and Dunst remains the notification daemon. This avoids a second
network/audio manager or notification daemon while the shell migration
continues. Wallpaper and clipboard selections similarly call the existing
scripts, so their persistence and privacy behavior remain in effect.
The notification button displays Dunst history in a Quickshell panel with
urgency styling, per-item history-pop, clear-all, and the existing DND toggle.

## Recovery and keybinding

Run this command to switch immediately and persistently back to Waybar:

```sh
~/.config/hypr/scripts/desktop/rollback-to-waybar.sh
```

The script hides the running Quickshell panel through its IPC handler, starts
Waybar if it is not already running, and records Waybar as the startup choice.
It does not delete Quickshell or Waybar files. To make Quickshell the default
again after a rollback, remove
`~/.local/state/hypr-rice/bar-mode` and log in again.

`Super+Shift+R` is unchanged as a key chord. It now reloads the selected bar
(Quickshell by default, Waybar after rollback) and reloads Hyprland.
Startup and reload scripts keep the unselected bar hidden or stopped. The
legacy `restart-waybar.sh` entrypoint delegates to the selected shell unless
Waybar fallback mode is explicitly active.

## Structure

- `shell.qml`: screen variants, shared theme/settings/service objects, and
  shell-management IPC.
- `config/`: dimensions, module toggles, scripts path, and theme tokens.
- `services/`: event-driven Hyprland workspace and active-window access.
- `modules/bar/`: panel, workspaces, title, tray, indicators, clock, and
  calendar.
- `modules/launcher/`: application search, favorites, search history, and
  quick links to existing system tools.
- `modules/dashboard/`: on-demand CPU, memory, storage, and battery overview.
- `modules/notifications/`: Dunst-backed history cards, urgency, clear, and DND.
- `modules/osd/`: event-driven volume, microphone, and brightness display.
- `modules/settings/`: persistent bar, accent, and animation preferences.

The shell derives integration paths from its deployed config location, not the
current working directory or repository checkout. Legacy Waybar configuration
and backend scripts remain available for recovery.

## Validation and development

The config targets the installed Quickshell 0.3.2 API. Run a startup check with
`qs --path ~/.config/hypr/quickshell/shell.qml --verbose`; use
`qs ipc --path ~/.config/hypr/quickshell/shell.qml call hyprshell reload` after
editing. On systems with Qt tools, run:

```sh
QML_IMPORT_PATH=/usr/lib/qt6/qml /usr/lib/qt6/bin/qmllint -E quickshell/modules/launcher/Launcher.qml
```

`qmllint` may still report
Quickshell API metadata as incomplete; the runtime loader is the compatibility
check for Quickshell types.

The Control Center, Dunst notification history, wallpaper selector, clipboard
history, and power interface remain script-backed. The current shell does not
yet replace those individual interfaces with native QML panels; it integrates
them through the existing backends.
