#!/usr/bin/env bash
# =====================================================================
# PipeWire Audio Control Center for Hyprland
# Switch output sinks (Speakers / HDMI / Bluetooth) & input sources
# Theme: ~/.config/hypr/rofi/audio.rasi
# =====================================================================

ROFI_THEME="${HOME}/.config/hypr/rofi/audio.rasi"
SCRIPTS="${HOME}/.config/hypr/scripts"

notify() {
    local urgency="${1:-low}"
    local icon="${2:-audio-volume-high}"
    local title="$3"
    local msg="$4"
    dunstify -a "Audio" -u "${urgency}" -i "${icon}" "${title}" "${msg}" 2>/dev/null || true
}

# Python helper to parse wpctl status and output menu options
generate_audio_menu() {
    local filter="${1:-all}"
    
    python3 - "${filter}" << 'EOF'
import subprocess, re, sys, html

filter_mode = sys.argv[1] if len(sys.argv) > 1 else "all"

try:
    status_raw = subprocess.check_output(["wpctl", "status"], text=True, stderr=subprocess.DEVNULL)
except Exception:
    status_raw = ""

re_entry = re.compile(r'^\s*[│|├└─ ]*\s*(\*?)\s*(\d+)\.\s+(.*?)(?:\s+\[vol:\s*([0-9.]+)(?:\s+(MUTED))?\])?\s*$')

current_section = None
sinks = []
sources = []

for line in status_raw.splitlines():
    clean = line.strip()
    if 'Sinks:' in clean:
        current_section = 'sinks'
        continue
    elif 'Sources:' in clean:
        current_section = 'sources'
        continue
    elif any(h in clean for h in ['Sink endpoints:', 'Filters:', 'Streams:', 'Video', 'Settings:']):
        current_section = None
        continue

    if current_section in ('sinks', 'sources'):
        m = re_entry.match(line)
        if m:
            is_default = bool(m.group(1))
            dev_id = m.group(2)
            name = m.group(3).strip()
            # Clean trailing extra bracket info if any
            name = re.sub(r'\s+\[.*\]$', '', name)
            vol_str = m.group(4)
            muted = (m.group(5) == 'MUTED')
            vol_pct = int(float(vol_str) * 100) if vol_str else 0
            
            item = {
                'id': dev_id,
                'name': name,
                'default': is_default,
                'vol': vol_pct,
                'muted': muted
            }
            if current_section == 'sinks':
                sinks.append(item)
            else:
                sources.append(item)

def get_sink_icon(name):
    low = name.lower()
    if "hdmi" in low or "displayport" in low:
        return "󰍹"
    elif "bluetooth" in low or "headphone" in low or "wh-" in low or "airpod" in low:
        return "󰋋"
    else:
        return "󰕾"

def format_row(prefix, icon, name, details, tag):
    # Fixed padding format for elegant Rofi display
    left = f"{prefix} {icon}  {name}"
    return f"{tag}|{left}|{details}"

rows = []

if filter_mode in ("all", "outputs"):
    rows.append("HEADER|<span color='#888888'>── Output Sinks (Speakers &amp; Headphones) ──────────────────────────</span>|")
    for s in sinks:
        icon = get_sink_icon(s['name'])
        status_text = f"Muted ({s['vol']}%)" if s['muted'] else f"{s['vol']}%"
        if s['default']:
            label = f"<span color='#AAAAAA'><b>● {icon}  {html.escape(s['name'])}</b></span>"
            details = f"<span color='#A3BE8C'><b>[ACTIVE]</b></span> <span color='#888888'>│</span> <span color='#D5D5D5'>{status_text}</span>"
        else:
            label = f"<span color='#888888'>○ {icon}  {html.escape(s['name'])}</span>"
            details = f"<span color='#D5D5D5'>{status_text}</span>"
        rows.append(f"SINK:{s['id']}:{s['name']}|{label}|{details}")

if filter_mode in ("all", "inputs"):
    rows.append("HEADER|<span color='#888888'>── Input Sources (Microphones) ────────────────────────────────</span>|")
    for src in sources:
        icon = "󰍭" if src['muted'] else "󰍬"
        status_text = f"Muted ({src['vol']}%)" if src['muted'] else f"{src['vol']}%"
        if src['default']:
            label = f"<span color='#AAAAAA'><b>● {icon}  {html.escape(src['name'])}</b></span>"
            details = f"<span color='#A3BE8C'><b>[ACTIVE]</b></span> <span color='#888888'>│</span> <span color='#D5D5D5'>{status_text}</span>"
        else:
            label = f"<span color='#888888'>○ {icon}  {html.escape(src['name'])}</span>"
            details = f"<span color='#D5D5D5'>{status_text}</span>"
        rows.append(f"SOURCE:{src['id']}:{src['name']}|{label}|{details}")

if filter_mode == "all":
    rows.append("HEADER|<span color='#888888'>── Quick Actions ──────────────────────────────────────────────</span>|")
    rows.append("ACTION:toggle-mute|<span color='#AAAAAA'><b>󰝟  Toggle Output Mute</b></span>|<span color='#D5D5D5'>Mute or unmute default sink</span>")
    rows.append("ACTION:toggle-mic|<span color='#AAAAAA'><b>󰍭  Toggle Microphone Mute</b></span>|<span color='#D5D5D5'>Mute or unmute default microphone</span>")
    rows.append("ACTION:vol-up|<span color='#AAAAAA'><b>󰕾  Increase Volume (+5%)</b></span>|<span color='#D5D5D5'>Raise audio output level</span>")
    rows.append("ACTION:vol-down|<span color='#AAAAAA'><b>󰖀  Decrease Volume (-5%)</b></span>|<span color='#D5D5D5'>Lower audio output level</span>")
    rows.append("ACTION:pavucontrol|<span color='#AAAAAA'><b>󰒓  Advanced Audio Mixer</b></span>|<span color='#D5D5D5'>Open Pavucontrol GTK interface</span>")

for r in rows:
    parts = r.split('|')
    tag = parts[0]
    left = parts[1]
    right = parts[2] if len(parts) > 2 else ""
    if tag == "HEADER":
        print(f"{left}")
    else:
        # Include hidden token at the end for matching
        print(f"{left} <span color='#333333'>│</span> {right} \0info\x1f{tag}")
EOF
}

# Handle CLI flags
case "$1" in
    toggle-mute)
        "${SCRIPTS}/volume.sh" mute
        exit 0
        ;;
    toggle-mic)
        "${SCRIPTS}/volume.sh" mic
        exit 0
        ;;
esac

MODE="${1:-all}"
PROMPT="󰕾  Audio Control"
if [ "${MODE}" = "outputs" ]; then
    PROMPT="󰕾  Audio Output"
elif [ "${MODE}" = "inputs" ]; then
    PROMPT="󰍬  Audio Input"
fi

CHOSEN=$(generate_audio_menu "${MODE}" | rofi -dmenu -i -markup-rows -config "${ROFI_THEME}" -p "${PROMPT}")

if [ -z "${CHOSEN}" ]; then
    exit 0
fi

# Extract the selection
if echo "${CHOSEN}" | grep -q "── "; then
    exit 0
fi

case "${CHOSEN}" in
    *"Toggle Output Mute"*)
        "${SCRIPTS}/volume.sh" mute
        ;;
    *"Toggle Microphone Mute"*)
        "${SCRIPTS}/volume.sh" mic
        ;;
    *"Increase Volume"*)
        "${SCRIPTS}/volume.sh" up 5
        ;;
    *"Decrease Volume"*)
        "${SCRIPTS}/volume.sh" down 5
        ;;
    *"Advanced Audio Mixer"*)
        pavucontrol &
        ;;
    *)
        # Check if selection matches a sink or source
        # Extract device name and ID from wpctl status
        CLEAN_NAME=$(echo "${CHOSEN}" | sed -E 's/<[^>]*>//g' | sed -E 's/^[●○][[:space:]]*[^[:space:]]+[[:space:]]+//' | sed -E 's/[[:space:]]*│.*//' | xargs)
        
        # Look up device ID with python
        DEV_INFO=$(python3 - "${CLEAN_NAME}" << 'EOF'
import subprocess, re, sys

query = sys.argv[1].strip()

try:
    status = subprocess.check_output(["wpctl", "status"], text=True, stderr=subprocess.DEVNULL)
except Exception:
    status = ""

re_entry = re.compile(r'^\s*[│|├└─ ]*\s*(\*?)\s*(\d+)\.\s+(.*?)(?:\s+\[vol:\s*([0-9.]+)(?:\s+(MUTED))?\])?\s*$')

current_section = None
found = None

for line in status.splitlines():
    clean = line.strip()
    if 'Sinks:' in clean:
        current_section = 'sink'
        continue
    elif 'Sources:' in clean:
        current_section = 'source'
        continue
    elif any(h in clean for h in ['Sink endpoints:', 'Filters:', 'Streams:', 'Video', 'Settings:']):
        current_section = None
        continue

    if current_section in ('sink', 'source'):
        m = re_entry.match(line)
        if m:
            dev_id = m.group(2)
            name = m.group(3).strip()
            name_clean = re.sub(r'\s+\[.*\]$', '', name)
            if query.lower() in name_clean.lower() or name_clean.lower() in query.lower():
                found = (current_section, dev_id, name_clean)
                break

if found:
    print(f"{found[0]}:{found[1]}:{found[2]}")
EOF
        )

        if [ -n "${DEV_INFO}" ]; then
            DEV_TYPE=$(echo "${DEV_INFO}" | cut -d':' -f1)
            DEV_ID=$(echo "${DEV_INFO}" | cut -d':' -f2)
            DEV_LABEL=$(echo "${DEV_INFO}" | cut -d':' -f3)

            wpctl set-default "${DEV_ID}"
            if [ "${DEV_TYPE}" = "sink" ]; then
                notify "low" "audio-volume-high" "Audio Output Switched" "Default sink: ${DEV_LABEL}"
            else
                notify "low" "microphone-sensitivity-high" "Audio Input Switched" "Default microphone: ${DEV_LABEL}"
            fi
            pkill -RTMIN+10 waybar 2>/dev/null || true
        fi
        ;;
esac
