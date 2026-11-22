#!/usr/bin/env bash
# =====================================================================
# Hyprland Command Center (Compatibility Bridge)
# Forwarding directly to the enhanced Control Center
# =====================================================================
exec "${HOME}/.config/hypr/scripts/desktop/control-center.sh" "$@"
