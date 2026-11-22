#!/usr/bin/env bash
set -euo pipefail

CONFIG_ROOT="${XDG_CONFIG_HOME:-$HOME/.config}/hypr"
exec rofi -show drun -config "${CONFIG_ROOT}/rofi/launcher.rasi"
