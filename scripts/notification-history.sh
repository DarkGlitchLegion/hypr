#!/usr/bin/env bash
# =====================================================================
# Notification History Viewer (Super + Ctrl + N)
# Displays Dunst history inside Rofi and allows popping or clearing items
# =====================================================================

ROFI_CONFIG="${HOME}/.config/hypr/rofi/clipboard.rasi"
CLEAR_ACTION="󰆴  Clear Notification History"

if ! command -v dunstctl >/dev/null 2>&1; then
    dunstify -a "Notifications" -u low "Dunst Not Found" "dunstctl is not available." 2>/dev/null || true
    exit 0
fi

# Extract history items using Python
ENTRIES=$(python3 - <<'EOF'
import json, subprocess, sys

try:
    raw = subprocess.check_output(["dunstctl", "history"], stderr=subprocess.DEVNULL).decode('utf-8')
    data = json.loads(raw)
    notifs = data.get("data", [[]])[0]
    
    if not notifs:
        sys.exit(0)
        
    for item in notifs:
        nid = item.get("id", {}).get("data", 0)
        app = item.get("appname", {}).get("data", "System")
        summary = item.get("summary", {}).get("data", "").replace("\n", " ").strip()
        body = item.get("body", {}).get("data", "").replace("\n", " ").strip()
        
        preview = f"{summary}: {body}" if body else summary
        if len(preview) > 90:
            preview = preview[:87] + "..."
            
        print(f"#{nid} | [{app}] {preview}")
except Exception:
    pass
EOF
)

if [ -z "${ENTRIES}" ]; then
    MENU_ENTRIES="${CLEAR_ACTION}\n<i>(Notification history is currently empty)</i>"
else
    MENU_ENTRIES="${CLEAR_ACTION}\n${ENTRIES}"
fi

SELECTED=$(echo -e "${MENU_ENTRIES}" | rofi -dmenu -config "${ROFI_CONFIG}" -p "󰂚 Notifications")
[ -z "${SELECTED}" ] && exit 0

if [[ "${SELECTED}" == *"${CLEAR_ACTION}"* ]]; then
    dunstctl history-clear
    dunstify -a "Notifications" -u low "Notifications Cleared" "Notification history has been cleared." 2>/dev/null || true
    exit 0
fi

if [[ "${SELECTED}" == *"empty"* ]]; then
    exit 0
fi

# Extract the ID: e.g. "#12 | ..."
NID=$(echo "${SELECTED}" | grep -o '^#[0-9]\+' | tr -d '#')
if [ -n "${NID}" ]; then
    dunstctl history-pop "${NID}"
fi
