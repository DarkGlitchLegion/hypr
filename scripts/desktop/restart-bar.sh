#!/usr/bin/env bash
set -euo pipefail

CONFIG_ROOT="${XDG_CONFIG_HOME:-$HOME/.config}/hypr"
exec "${CONFIG_ROOT}/scripts/desktop/restart-waybar.sh"
