#!/usr/bin/env bash
# =====================================================
# Clipboard History Entrypoint
# Delegates directly to the new clipboard-menu.sh
# =====================================================

exec "${HOME}/.config/hypr/scripts/clipboard-menu.sh" "$@"
