#!/usr/bin/env bash
set -euo pipefail
CONFIG_ROOT="${XDG_CONFIG_HOME:-$HOME/.config}/hypr"
exec qs ipc --path "${CONFIG_ROOT}/quickshell/shell.qml" call hyprshell toggleNotifications
