#!/usr/bin/env bash
# =====================================================================
# Clipboard History Clear (Super + Ctrl + Shift + V)
# Wipes cliphist and internal cache for privacy and security
# =====================================================================

CACHE_DIR="${HOME}/.cache/hypr_clipboard"

# Clear cliphist database if installed
if command -v cliphist >/dev/null 2>&1; then
    cliphist wipe >/dev/null 2>&1
    rm -rf "${HOME}/.cache/cliphist" 2>/dev/null
fi

# Clear fallback cache
if [ -d "${CACHE_DIR}" ]; then
    find "${CACHE_DIR}" -type f -name "*.txt" -delete 2>/dev/null
    find "${CACHE_DIR}" -type f -name "*.tmp" -delete 2>/dev/null
fi

# Clear active clipboard buffers
if command -v wl-copy >/dev/null 2>&1; then
    wl-copy --clear 2>/dev/null || echo -n "" | wl-copy 2>/dev/null || true
fi

dunstify -a "Clipboard" \
         -u normal \
         -i edit-clear \
         "Clipboard Wiped" \
         "All clipboard history and active buffers have been permanently erased." 2>/dev/null || true
