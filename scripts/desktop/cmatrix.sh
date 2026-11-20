#!/usr/bin/env bash
# =====================================================================
# Transparent CMatrix Launcher for Hyprland
# Launches cmatrix in a custom styled transparent Kitty window
# =====================================================================

KITTY_CONF="${HOME}/.config/hypr/kitty/kitty.conf"

# Default to asynchronous smooth scroll and bold font if no args given
if [ "$#" -eq 0 ]; then
    ARGS=("-a" "-b")
else
    ARGS=("$@")
fi

exec kitty --class cmatrix \
           --title "cmatrix" \
           --config "${KITTY_CONF}" \
           -e cmatrix "${ARGS[@]}"
