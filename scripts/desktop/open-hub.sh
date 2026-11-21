#!/usr/bin/env bash
set -euo pipefail

CONFIG_ROOT="${XDG_CONFIG_HOME:-$HOME/.config}/hypr"
PAGE="${1:-home}"
case "${PAGE}" in
    home|controls|network|audio|display|idle|capture|security|system|maintenance|developer|presets|wallpaper|clipboard|keys|power|settings) ;;
    *) echo "Unknown QML control center page: ${PAGE}" >&2; exit 2 ;;
esac

exec qs ipc --path "${CONFIG_ROOT}/quickshell/shell.qml" call hyprshell openHub "${PAGE}"
