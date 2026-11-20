#!/usr/bin/env bash
# =====================================================================
# Laptop Power Profiles & Battery Center for Hyprland
# Switch AMD P-State power profiles & monitor battery health
# Theme: ~/.config/hypr/rofi/power-profile.rasi
# =====================================================================

ROFI_THEME="${HOME}/.config/hypr/rofi/power-profile.rasi"
SCRIPTS="${HOME}/.config/hypr/scripts"

notify() {
    local urgency="${1:-low}"
    local icon="${2:-battery}"
    local title="$3"
    local msg="$4"
    dunstify -a "Power Center" -u "${urgency}" -i "${icon}" "${title}" "${msg}" 2>/dev/null || true
}

get_current_profile() {
    powerprofilesctl get 2>/dev/null || echo "balanced"
}

set_profile() {
    local target="$1"
    local icon="battery"

    if powerprofilesctl set "${target}" 2>/dev/null; then
        case "${target}" in
            performance)
                icon="speedometer"
                notify "normal" "${icon}" "Power Profile: Performance" "Maximum CPU clocks and boost enabled. Higher power consumption."
                ;;
            balanced)
                icon="battery"
                notify "low" "${icon}" "Power Profile: Balanced" "Standard dynamic CPU scaling for daily productivity."
                ;;
            power-saver)
                icon="battery-low"
                notify "low" "${icon}" "Power Profile: Power Saver" "Aggressive frequency throttling and energy conservation."
                ;;
        esac
        # Signal Waybar to refresh
        pkill -RTMIN+8 waybar 2>/dev/null || true
        return 0
    else
        notify "critical" "dialog-error" "Power Profile Error" "Failed to communicate with power-profiles-daemon."
        return 1
    fi
}

cycle_profile() {
    local current
    current=$(get_current_profile)

    case "${current}" in
        power-saver)
            set_profile "balanced"
            ;;
        balanced)
            set_profile "performance"
            ;;
        performance)
            set_profile "power-saver"
            ;;
        *)
            set_profile "balanced"
            ;;
    esac
}

generate_menu() {
    python3 - << 'EOF'
import glob, os, subprocess, html

def read_val(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except Exception:
        return None

# 1. Power Profile
try:
    current_profile = subprocess.check_output(["powerprofilesctl", "get"], text=True, stderr=subprocess.DEVNULL).strip()
except Exception:
    current_profile = "balanced"

# 2. Battery Stats
bats = glob.glob("/sys/class/power_supply/BAT*")
bat_str = "No Battery Detected (AC Desktop)"
health_str = "N/A"
draw_str = ""

if bats:
    b = bats[0]
    cap = read_val(os.path.join(b, "capacity")) or "0"
    stat = read_val(os.path.join(b, "status")) or "Unknown"
    cycles = read_val(os.path.join(b, "cycle_count")) or "0"
    
    # Power Draw
    p_now = read_val(os.path.join(b, "power_now"))
    if p_now and p_now.isdigit():
        watts = float(p_now) / 1000000.0
        draw_str = f"({watts:.1f}W)"
    else:
        c_now = read_val(os.path.join(b, "current_now"))
        v_now = read_val(os.path.join(b, "voltage_now"))
        if c_now and v_now and c_now.isdigit() and v_now.isdigit():
            watts = (float(c_now) * float(v_now)) / 1000000000000.0
            draw_str = f"({watts:.1f}W)"

    # Health
    e_full = read_val(os.path.join(b, "energy_full"))
    e_design = read_val(os.path.join(b, "energy_full_design"))
    if e_full and e_design and e_full.isdigit() and e_design.isdigit() and int(e_design) > 0:
        health_pct = (float(e_full) / float(e_design)) * 100.0
        health_str = f"{health_pct:.0f}%"
    else:
        c_full = read_val(os.path.join(b, "charge_full"))
        c_design = read_val(os.path.join(b, "charge_full_design"))
        if c_full and c_design and c_full.isdigit() and c_design.isdigit() and int(c_design) > 0:
            health_pct = (float(c_full) / float(c_design)) * 100.0
            health_str = f"{health_pct:.0f}%"

    bat_str = f"{os.path.basename(b)}: {cap}% [{stat} {draw_str}] │ Health: {health_str} ({cycles} Cycles)"

profiles = [
    ("performance", "󰓅", "Performance Mode", "Maximum AMD P-State frequency & boost", "#EBCB8B"),
    ("balanced",    "󰾆", "Balanced Mode",    "Standard dynamic performance scaling",    "#AAAAAA"),
    ("power-saver", "󰌪", "Power Saver Mode", "Aggressive throttling for maximum battery", "#A3BE8C"),
]

print(f"<span color='#888888'>── {html.escape(bat_str)} ──</span>")

for p_id, icon, label, desc, color in profiles:
    if p_id == current_profile:
        left = f"<span color='{color}'><b>● {icon}  {label}</b></span>"
        right = f"<span color='#A3BE8C'><b>[ACTIVE]</b></span> <span color='#888888'>│</span> <span color='#D5D5D5'>{desc}</span>"
    else:
        left = f"<span color='#888888'>○ {icon}  {label}</span>"
        right = f"<span color='#D5D5D5'>{desc}</span>"
    print(f"{left} <span color='#333333'>│</span> {right}")

print("<span color='#888888'>── Diagnostics &amp; Power Controls ────────────────────────────────</span>")
print("<span color='#AAAAAA'><b>󰂑  Battery Diagnostic Report       </b></span> <span color='#333333'>│</span> <span color='#D5D5D5'>Display complete battery health in notification</span>")
print("<span color='#AAAAAA'><b>󰌾  Lock Screen Immediately          </b></span> <span color='#333333'>│</span> <span color='#D5D5D5'>Lock desktop session (Hyprlock)</span>")
print("<span color='#AAAAAA'><b>󰤄  Suspend System (Sleep)           </b></span> <span color='#333333'>│</span> <span color='#D5D5D5'>Suspend system to RAM</span>")
EOF
}

show_diagnostic_report() {
    python3 - << 'EOF'
import glob, os, subprocess

bats = glob.glob("/sys/class/power_supply/BAT*")
if not bats:
    msg = "No battery detected on this system."
else:
    b = bats[0]
    def read_val(p):
        try:
            return open(os.path.join(b, p)).read().strip()
        except:
            return "N/A"

    cap = read_val("capacity")
    stat = read_val("status")
    cycles = read_val("cycle_count")
    model = read_val("model_name")
    vendor = read_val("manufacturer")
    tech = read_val("technology")

    p_now = read_val("power_now")
    watts = "N/A"
    if p_now.isdigit():
        watts = f"{float(p_now) / 1000000.0:.2f} W"

    e_full = read_val("energy_full")
    e_design = read_val("energy_full_design")
    health = "N/A"
    if e_full.isdigit() and e_design.isdigit() and int(e_design) > 0:
        health = f"{(float(e_full) / float(e_design)) * 100.0:.1f}% ({int(e_full)//1000}mWh / {int(e_design)//1000}mWh)"

    profile = subprocess.getoutput("powerprofilesctl get")

    msg = f"Battery: {cap}% ({stat})\nPower Draw: {watts}\nHealth: {health}\nCycles: {cycles}\nActive Profile: {profile}\nHardware: {vendor} {model} ({tech})"

subprocess.run(["dunstify", "-a", "Battery Diagnostics", "-u", "normal", "-i", "battery-good", "Battery Health & Hardware Report", msg])
EOF
}

# ---------------------------------------------------------------------
# Execution Dispatcher
# ---------------------------------------------------------------------
case "$1" in
    cycle)
        cycle_profile
        exit 0
        ;;
    set)
        if [ -n "$2" ]; then
            set_profile "$2"
        fi
        exit 0
        ;;
    report)
        show_diagnostic_report
        exit 0
        ;;
esac

CHOSEN=$(generate_menu | rofi -dmenu -i -markup-rows -config "${ROFI_THEME}" -p "󰓅  Power & Battery")

if [ -z "${CHOSEN}" ]; then
    exit 0
fi

case "${CHOSEN}" in
    *"Performance Mode"*)
        set_profile "performance"
        ;;
    *"Balanced Mode"*)
        set_profile "balanced"
        ;;
    *"Power Saver Mode"*)
        set_profile "power-saver"
        ;;
    *"Battery Diagnostic Report"*)
        show_diagnostic_report
        ;;
    *"Lock Screen"*)
        hyprlock -c "${HOME}/.config/hypr/hyprlock/hyprlock.conf" &
        ;;
    *"Suspend System"*)
        systemctl suspend &
        ;;
esac
