#!/usr/bin/env bash
set -euo pipefail

STATE_ROOT="${XDG_STATE_HOME:-$HOME/.local/state}/hypr-rice"
MODE_FILE="${STATE_ROOT}/bar-mode"
CONFIG_ROOT="${XDG_CONFIG_HOME:-$HOME/.config}/hypr"

if ! command -v waybar >/dev/null 2>&1; then
    printf 'Waybar is selected but waybar is not installed.\n' >&2
    exit 127
fi

mkdir -p "${STATE_ROOT}"
temporary_mode="$(mktemp "${STATE_ROOT}/.bar-mode.XXXXXX")"
printf 'waybar\n' > "${temporary_mode}"
mv -f -- "${temporary_mode}" "${MODE_FILE}"

if pgrep -u "${UID}" -x waybar >/dev/null 2>&1; then
    exit 0
fi

exec waybar -c "${CONFIG_ROOT}/waybar/config.jsonc" -s "${CONFIG_ROOT}/waybar/style.css"
