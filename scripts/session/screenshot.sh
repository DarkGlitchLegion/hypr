#!/usr/bin/env bash
# =====================================================
# Omarchy-Style Screenshot Utility for Hyprland
# Save directory: ~/Pictures/Screenshots
# Tools: grim, slurp, wl-copy, dunstify
# =====================================================

SAVE_DIR="${HOME}/Pictures/Screenshots"
mkdir -p "${SAVE_DIR}"

TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
FILE_PATH="${SAVE_DIR}/screenshot_${TIMESTAMP}.png"

notify_success() {
    local mode="$1"
    dunstify -a "Screenshot" \
             -u low \
             -i "${FILE_PATH}" \
             "Screenshot Taken (${mode})" \
             "Saved to ${FILE_PATH}\nCopied to clipboard."
}

case "$1" in
    region)
        GEOM=$(slurp 2>/dev/null)
        if [ -n "${GEOM}" ]; then
            grim -g "${GEOM}" "${FILE_PATH}"
            wl-copy < "${FILE_PATH}"
            notify_success "Region"
        fi
        ;;
    full)
        sleep 0.2
        grim "${FILE_PATH}"
        wl-copy < "${FILE_PATH}"
        notify_success "Fullscreen"
        ;;
    window)
        # Get active window geometry without requiring jq
        ACTIVE_BOX=$(hyprctl activewindow | awk '
            /at:/ { split($2, at, ","); x=at[1]; y=at[2] }
            /size:/ { split($2, sz, ","); w=sz[1]; h=sz[2] }
            END { if (w && h) printf "%s,%s %sx%s", x, y, w, h }
        ')
        if [ -n "${ACTIVE_BOX}" ]; then
            grim -g "${ACTIVE_BOX}" "${FILE_PATH}"
            wl-copy < "${FILE_PATH}"
            notify_success "Window"
        else
            dunstify -a "Screenshot" -u normal "Screenshot Failed" "No active window detected."
        fi
        ;;
    delayed)
        dunstify -a "Screenshot" -t 5000 "Capturing in 5 seconds..."
        sleep 5
        "$0" full
        ;;
    menu|"")
        exec qs ipc --path "${HOME}/.config/hypr/quickshell/shell.qml" call hyprshell openHub capture
        ;;
    *)
        echo "Usage: $0 {region|full|window|menu}"
        exit 1
        ;;
esac
