#!/usr/bin/env bash
# =====================================================================
# Clipboard Daemon for Hyprland
# Supports cliphist with transparent fallback to wl-paste cache
# =====================================================================

CACHE_DIR="${HOME}/.cache/hypr_clipboard"
HISTORY_FILE="${CACHE_DIR}/history.txt"
PID_FILE="${CACHE_DIR}/daemon.pid"

mkdir -p "${CACHE_DIR}"

# Check for single instance
if [ -f "${PID_FILE}" ]; then
    OLD_PID=$(cat "${PID_FILE}")
    if ps -p "${OLD_PID}" >/dev/null 2>&1; then
        exit 0
    fi
fi
echo "$$" > "${PID_FILE}"

cleanup() {
    rm -f "${PID_FILE}"
    kill $(jobs -p) 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# If cliphist is available, use official cliphist listeners
if command -v cliphist >/dev/null 2>&1; then
    wl-paste --type text --watch cliphist store &
    wl-paste --type image --watch cliphist store &
    wait
else
    # Robust fallback: capture unique text entries using wl-paste
    touch "${HISTORY_FILE}"
    wl-paste --watch bash -c '
        CACHE_DIR="${HOME}/.cache/hypr_clipboard"
        HISTORY_FILE="${CACHE_DIR}/history.txt"
        CONTENT=$(wl-paste 2>/dev/null)
        [ -z "${CONTENT}" ] && exit 0

        # Collapse multi-line to single preview representation
        PREVIEW=$(echo "${CONTENT}" | tr "\n\r\t" "   " | sed -e "s/[[:space:]]\+/ /g" -e "s/^[[:space:]]//" | cut -c1-120)
        [ -z "${PREVIEW}" ] && exit 0

        HASH=$(echo -n "${CONTENT}" | sha256sum | cut -d" " -f1)
        ITEM_FILE="${CACHE_DIR}/${HASH}.txt"
        echo -n "${CONTENT}" > "${ITEM_FILE}"

        TMP_HIST="${CACHE_DIR}/history.tmp"
        echo "${HASH}|${PREVIEW}" > "${TMP_HIST}"
        if [ -f "${HISTORY_FILE}" ]; then
            grep -v "^${HASH}|" "${HISTORY_FILE}" 2>/dev/null | head -n 99 >> "${TMP_HIST}"
        fi
        mv "${TMP_HIST}" "${HISTORY_FILE}"
    ' &
    wait
fi
