#!/usr/bin/env bash
set -u

CONFIG_ROOT="${XDG_CONFIG_HOME:-${HOME}/.config}/hypr"

if command -v qs >/dev/null 2>&1 \
    && qs ipc --path "${CONFIG_ROOT}/quickshell/shell.qml" call hyprshell closeFocusedOrOverlay; then
    exit 0
fi

exec hyprctl dispatch killactive
