#!/usr/bin/env bash
# =====================================================================
# Clipboard History Selector (Super + Ctrl + V)
# Supports cliphist with transparent fallback to wl-paste cache
# =====================================================================

ROFI_CONFIG="${HOME}/.config/hypr/rofi/clipboard.rasi"
CACHE_DIR="${HOME}/.cache/hypr_clipboard"
HISTORY_FILE="${CACHE_DIR}/history.txt"
CACHE_PID_FILE="${CACHE_DIR}/daemon.pid"
CLEAR_ACTION="󰆴  Clear All Clipboard History"

# Ensure daemon is running in background if not already active
DAEMON_RUNNING=false
if [ -f "${CACHE_PID_FILE}" ]; then
    DAEMON_PID=$(cat "${CACHE_PID_FILE}" 2>/dev/null)
    if [ -n "${DAEMON_PID}" ] && ps -p "${DAEMON_PID}" -o args= 2>/dev/null | grep -Fq "clipboard-daemon.sh"; then
        DAEMON_RUNNING=true
    fi
fi
if [ "${DAEMON_RUNNING}" != "true" ]; then
    rm -f "${CACHE_PID_FILE}"
    "${HOME}/.config/hypr/scripts/clipboard/clipboard-daemon.sh" >/dev/null 2>&1 &
fi

if command -v cliphist >/dev/null 2>&1; then
    # Mode 1: Official cliphist integration
    CLIPS=$(cliphist list 2>/dev/null)
    if [ -z "${CLIPS}" ]; then
        MENU_ENTRIES="${CLEAR_ACTION}\n<i>(Clipboard history is currently empty)</i>"
    else
        MENU_ENTRIES="${CLEAR_ACTION}\n${CLIPS}"
    fi

    SELECTED=$(echo -e "${MENU_ENTRIES}" | rofi -dmenu -config "${ROFI_CONFIG}" -p "󰅌 Clipboard")
    [ -z "${SELECTED}" ] && exit 0

    if [[ "${SELECTED}" == *"${CLEAR_ACTION}"* ]]; then
        "${HOME}/.config/hypr/scripts/clipboard/clipboard-clear.sh"
        exit 0
    fi

    if [[ "${SELECTED}" == *"empty"* ]]; then
        exit 0
    fi

    # Decode and copy back to clipboard
    echo "${SELECTED}" | cliphist decode | wl-copy
    dunstify -a "Clipboard" -u low -i edit-copy "Clipboard" "Item copied to active clipboard." 2>/dev/null || true

else
    # Mode 2: Integrated Fallback
    mkdir -p "${CACHE_DIR}"
    touch "${HISTORY_FILE}"

    ENTRIES=$(awk -F'|' '{print $2}' "${HISTORY_FILE}" 2>/dev/null)
    if [ -z "${ENTRIES}" ]; then
        MENU_ENTRIES="${CLEAR_ACTION}\n<i>(Clipboard history is empty. Built-in history fallback is active)</i>"
    else
        MENU_ENTRIES="${CLEAR_ACTION}\n${ENTRIES}"
    fi

    SELECTED=$(echo -e "${MENU_ENTRIES}" | rofi -dmenu -config "${ROFI_CONFIG}" -p "󰅌 Clipboard")
    [ -z "${SELECTED}" ] && exit 0

    if [[ "${SELECTED}" == *"${CLEAR_ACTION}"* ]]; then
        "${HOME}/.config/hypr/scripts/clipboard/clipboard-clear.sh"
        exit 0
    fi

    if [[ "${SELECTED}" == *"empty"* ]]; then
        exit 0
    fi

    # Locate the hash corresponding to the preview line
    HASH=$(grep -F "|${SELECTED}" "${HISTORY_FILE}" | head -n 1 | cut -d'|' -f1)
    if [ -n "${HASH}" ] && [ -f "${CACHE_DIR}/${HASH}.txt" ]; then
        cat "${CACHE_DIR}/${HASH}.txt" | wl-copy
        dunstify -a "Clipboard" -u low -i edit-copy "Clipboard" "Item copied to active clipboard." 2>/dev/null || true
    else
        echo -n "${SELECTED}" | wl-copy
    fi
fi
