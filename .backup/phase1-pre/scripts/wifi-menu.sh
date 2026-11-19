#!/usr/bin/env bash
# =====================================================================
# Graphical Wi-Fi Manager for Hyprland (Rofi + NetworkManager)
# Replaces nmtui with an elegant, modern minimal dark interface
# Theme: ~/.config/hypr/rofi/wifi.rasi
# =====================================================================

ROFI_THEME="${HOME}/.config/hypr/rofi/wifi.rasi"
CACHE_FILE="/tmp/hypr_wifi_cache.json"
PIDFILE="/tmp/hypr_wifi_menu.pid"

# Prevent duplicate menu instances
if [ -f "${PIDFILE}" ]; then
    OLD_PID=$(cat "${PIDFILE}" 2>/dev/null)
    if [ -n "${OLD_PID}" ] && kill -0 "${OLD_PID}" 2>/dev/null; then
        exit 0
    fi
fi
echo "$$" > "${PIDFILE}"
trap 'rm -f "${PIDFILE}"' EXIT

notify() {
    local urgency="${1:-low}"
    local icon="${2:-network-wireless}"
    local title="$3"
    local msg="$4"
    dunstify -a "Network" -u "${urgency}" -i "${icon}" "${title}" "${msg}" 2>/dev/null || true
}

get_wifi_status() {
    nmcli -t -f WIFI general 2>/dev/null || echo "disabled"
}

toggle_wifi() {
    local current
    current=$(get_wifi_status)
    if [ "${current}" = "enabled" ]; then
        nmcli radio wifi off
        notify "low" "network-wireless-offline" "Wi-Fi Disabled" "Wireless radio has been turned off."
    else
        nmcli radio wifi on
        notify "low" "network-wireless" "Wi-Fi Enabled" "Scanning for wireless networks..."
        sleep 1.2
    fi
    pkill -RTMIN+8 waybar 2>/dev/null || true
}

rescan_networks() {
    notify "low" "network-wireless" "Scanning Networks" "Refreshing nearby wireless access points..."
    nmcli device wifi rescan >/dev/null 2>&1 || true
    sleep 1.0
}

# Scan, sort, and cache wireless networks with precise Pango formatting
generate_network_menu() {
    python3 - << 'EOF'
import subprocess, re, html, json

CACHE_FILE = "/tmp/hypr_wifi_cache.json"

try:
    # 1. Fetch saved connections
    raw_saved = subprocess.check_output(
        ["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show"],
        stderr=subprocess.DEVNULL
    ).decode("utf-8", errors="ignore")
    saved_nets = {line.split(":")[0] for line in raw_saved.splitlines() if ":802-11-wireless" in line}

    # 2. Fetch live access points (use cached scan for instantaneous UI response, fallback to active scan if cache empty)
    try:
        raw_scan = subprocess.check_output(
            ["nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY", "device", "wifi", "list", "--rescan", "no"],
            stderr=subprocess.DEVNULL
        ).decode("utf-8", errors="ignore")
        if not raw_scan.strip():
            raw_scan = subprocess.check_output(
                ["nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY", "device", "wifi", "list"],
                stderr=subprocess.DEVNULL
            ).decode("utf-8", errors="ignore")
    except Exception:
        raw_scan = subprocess.check_output(
            ["nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY", "device", "wifi", "list"],
            stderr=subprocess.DEVNULL
        ).decode("utf-8", errors="ignore")

    seen = {}
    for line in raw_scan.splitlines():
        if not line.strip(): continue
        parts = re.split(r"(?<!\\):", line)
        if len(parts) >= 4:
            in_use = (parts[0].strip() == "*")
            ssid = parts[1].replace("\\:", ":").strip()
            signal_str = parts[2].strip()
            signal = int(signal_str) if signal_str.isdigit() else 0
            security = parts[3].strip() if len(parts) > 3 else ""
            if not ssid: continue

            if ssid not in seen:
                seen[ssid] = {
                    "in_use": in_use,
                    "ssid": ssid,
                    "signal": signal,
                    "security": security,
                    "saved": (ssid in saved_nets)
                }
            else:
                if in_use:
                    seen[ssid]["in_use"] = True
                if signal > seen[ssid]["signal"]:
                    seen[ssid]["signal"] = signal
                if not seen[ssid]["security"] and security:
                    seen[ssid]["security"] = security

    # Output control buttons
    print("󰤮  Turn Wi-Fi OFF")
    print("󰑓  Rescan / Refresh Networks")
    print("󰈉  Connect to Hidden Network...")
    print(f"󰋊  Manage Saved Networks ({len(saved_nets)})...")
    print('<span color="#333333">────────────────────────────────────────────────────────────</span>')

    # Sort: Connected first, then highest signal
    sorted_nets = sorted(seen.values(), key=lambda x: (not x["in_use"], -x["signal"]))

    cache = {}

    for net in sorted_nets:
        ssid = net["ssid"]
        escaped_ssid = html.escape(ssid)
        signal = net["signal"]
        sec = net["security"]
        in_use = net["in_use"]
        saved = net["saved"]

        # Signal Icon
        if signal >= 75: sig_icon = "󰤨"
        elif signal >= 50: sig_icon = "󰤥"
        elif signal >= 25: sig_icon = "󰤢"
        else: sig_icon = "󰤟"

        # Security Label
        if not sec or sec == "--":
            sec_badge = '<span color="#EBCB8B">󰌿 Open</span>'
            sec_type = "OPEN"
        else:
            sec_name = "WPA3" if "WPA3" in sec else ("WPA2" if "WPA2" in sec else "WPA")
            sec_badge = f'<span color="#888888">󰌾 {sec_name}</span>'
            sec_type = "SECURED"

        # Construct line
        if in_use:
            line = f'<span color="#A3BE8C"><b>󰄲  {escaped_ssid}</b></span> <span color="#333333">│</span> <span color="#AAAAAA">{sig_icon} {signal}%</span> {sec_badge} <span color="#A3BE8C"><b>[Connected]</b></span>'
        elif saved:
            line = f'<span color="#D5D5D5"><b>{sig_icon}  {escaped_ssid}</b></span> <span color="#333333">│</span> <span color="#888888">{signal}%</span> {sec_badge} <span color="#666666">[Saved]</span>'
        else:
            line = f'<span color="#D5D5D5">{sig_icon}  {escaped_ssid}</span> <span color="#333333">│</span> <span color="#888888">{signal}%</span> {sec_badge}'

        cache[line] = {
            "ssid": ssid,
            "in_use": in_use,
            "saved": saved,
            "security": sec_type,
            "signal": signal
        }
        print(line)

    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)

except Exception as e:
    print(f"Error preparing Wi-Fi list: {e}")
EOF
}

connect_saved() {
    local ssid="$1"
    notify "low" "network-wireless" "Connecting..." "Connecting to saved network: ${ssid}"
    if nmcli connection up id "${ssid}" >/dev/null 2>&1; then
        notify "low" "network-wireless-connected" "Connected" "Successfully connected to ${ssid}."
        pkill -RTMIN+8 waybar 2>/dev/null || true
    else
        notify "critical" "network-wireless-offline" "Connection Failed" "Could not connect to ${ssid}. Re-entering credentials may be required."
    fi
}

connect_open() {
    local ssid="$1"
    notify "low" "network-wireless" "Connecting..." "Connecting to open network: ${ssid}"
    if nmcli device wifi connect "${ssid}" >/dev/null 2>&1; then
        notify "low" "network-wireless-connected" "Connected" "Successfully connected to ${ssid}."
        pkill -RTMIN+8 waybar 2>/dev/null || true
    else
        notify "critical" "network-wireless-offline" "Connection Failed" "Could not connect to open network: ${ssid}."
    fi
}

connect_secured_prompt() {
    local ssid="$1"
    local pass
    pass=$(rofi -dmenu -password -config "${ROFI_THEME}" -p "󰌾 Password" -mesg "Enter WPA passphrase for: <b>${ssid}</b>")
    [ -z "${pass}" ] && return 0

    notify "low" "network-wireless" "Authenticating..." "Connecting to ${ssid}..."
    if nmcli device wifi connect "${ssid}" password "${pass}" >/dev/null 2>&1; then
        notify "low" "network-wireless-connected" "Connected" "Successfully connected to ${ssid}."
        pkill -RTMIN+8 waybar 2>/dev/null || true
    else
        notify "critical" "network-wireless-offline" "Authentication Failed" "Incorrect password or connection timed out for ${ssid}."
    fi
}

connected_network_actions() {
    local ssid="$1"
    local opts="󰅖  Disconnect from ${ssid}\n󰑓  Reconnect to ${ssid}\n󰆴  Forget Saved Network (${ssid})\n󰌌  Back to Network List"
    local act
    act=$(echo -e "${opts}" | rofi -dmenu -config "${ROFI_THEME}" -p "󰄲 ${ssid}" -mesg "Active Wi-Fi Connection Options:")
    [ -z "${act}" ] && return 0

    case "${act}" in
        *"Disconnect"*)
            nmcli connection down id "${ssid}" >/dev/null 2>&1
            notify "low" "network-wireless-offline" "Disconnected" "Disconnected from ${ssid}."
            pkill -RTMIN+8 waybar 2>/dev/null || true
            ;;
        *"Reconnect"*)
            notify "low" "network-wireless" "Reconnecting..." "Re-establishing connection to ${ssid}..."
            nmcli connection up id "${ssid}" >/dev/null 2>&1
            pkill -RTMIN+8 waybar 2>/dev/null || true
            ;;
        *"Forget"*)
            nmcli connection delete id "${ssid}" >/dev/null 2>&1
            notify "low" "edit-delete" "Network Forgotten" "Removed ${ssid} from saved networks."
            pkill -RTMIN+8 waybar 2>/dev/null || true
            ;;
        *"Back"*)
            return 0
            ;;
    esac
}

manage_saved_connections() {
    while true; do
        local raw_saved
        raw_saved=$(nmcli -t -f NAME,TYPE connection show 2>/dev/null | grep ':802-11-wireless' | cut -d':' -f1)
        if [ -z "${raw_saved}" ]; then
            echo -e "<i>(No saved Wi-Fi connections found)</i>\n󰌌  Back" | rofi -dmenu -config "${ROFI_THEME}" -p "󰋊 Saved" >/dev/null
            return 0
        fi

        local menu_list="󰌌  Back to Main Menu\n<span color=\"#333333\">────────────────────────────────────────────────────────────</span>\n"
        while IFS= read -r net; do
            [ -n "${net}" ] && menu_list="${menu_list}󰤨  ${net}\n"
        done <<< "${raw_saved}"

        local chosen
        chosen=$(echo -e "${menu_list}" | rofi -dmenu -markup-rows -config "${ROFI_THEME}" -p "󰋊 Saved Networks" -mesg "Select a saved profile to connect or forget:")
        [ -z "${chosen}" ] && return 0
        [[ "${chosen}" == *"Back"* ]] && return 0
        [[ "${chosen}" == *"──"* ]] && continue

        local target_ssid
        target_ssid=$(echo "${chosen}" | sed -e 's/^󰤨  //' -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
        [ -z "${target_ssid}" ] && continue

        local sub_opts="󰄲  Connect to ${target_ssid}\n󰆴  Delete / Forget Profile\n󰌌  Back"
        local sub_act
        sub_act=$(echo -e "${sub_opts}" | rofi -dmenu -config "${ROFI_THEME}" -p "󰤨 ${target_ssid}" -mesg "Manage Profile: <b>${target_ssid}</b>")
        case "${sub_act}" in
            *"Connect"*)
                connect_saved "${target_ssid}"
                return 0
                ;;
            *"Delete"*)
                nmcli connection delete id "${target_ssid}" >/dev/null 2>&1
                notify "low" "edit-delete" "Profile Deleted" "Removed ${target_ssid} from NetworkManager."
                ;;
            *)
                ;;
        esac
    done
}

connect_hidden_network() {
    local h_ssid
    h_ssid=$(rofi -dmenu -config "${ROFI_THEME}" -p "󰈉 Hidden SSID" -mesg "Enter Hidden Network Name:")
    [ -z "${h_ssid}" ] && return 0

    local sec_choice
    sec_choice=$(echo -e "󰌾  WPA / WPA2 / WPA3 Personal (Secured)\n󰌿  Open Network (No Password)\n󰌌  Cancel" | rofi -dmenu -config "${ROFI_THEME}" -p "󰈉 Security" -mesg "Security Type for <b>${h_ssid}</b>:")
    [ -z "${sec_choice}" ] && return 0
    [[ "${sec_choice}" == *"Cancel"* ]] && return 0

    if [[ "${sec_choice}" == *"Open"* ]]; then
        notify "low" "network-wireless" "Connecting..." "Connecting to hidden open network: ${h_ssid}"
        if nmcli device wifi connect "${h_ssid}" hidden yes >/dev/null 2>&1; then
            notify "low" "network-wireless-connected" "Connected" "Successfully connected to ${h_ssid}."
            pkill -RTMIN+8 waybar 2>/dev/null || true
        else
            notify "critical" "network-wireless-offline" "Connection Failed" "Could not connect to hidden network: ${h_ssid}."
        fi
    else
        local h_pass
        h_pass=$(rofi -dmenu -password -config "${ROFI_THEME}" -p "󰌾 Password" -mesg "Enter WPA passphrase for hidden network: <b>${h_ssid}</b>")
        [ -z "${h_pass}" ] && return 0

        notify "low" "network-wireless" "Authenticating..." "Connecting to hidden network: ${h_ssid}..."
        if nmcli device wifi connect "${h_ssid}" password "${h_pass}" hidden yes >/dev/null 2>&1; then
            notify "low" "network-wireless-connected" "Connected" "Successfully connected to ${h_ssid}."
            pkill -RTMIN+8 waybar 2>/dev/null || true
        else
            notify "critical" "network-wireless-offline" "Connection Failed" "Authentication or association failed for ${h_ssid}."
        fi
    fi
}

main() {
    while true; do
        local status
        status=$(get_wifi_status)

        if [ "${status}" != "enabled" ]; then
            local disabled_opts="󰤨  Wi-Fi is Disabled — Click to Turn ON\n󰌌  Exit"
            local off_choice
            off_choice=$(echo -e "${disabled_opts}" | rofi -dmenu -config "${ROFI_THEME}" -p "󰤮 Wi-Fi" -mesg "Wireless interface is currently disabled.")
            if [[ "${off_choice}" == *"Turn ON"* ]]; then
                toggle_wifi
                continue
            else
                exit 0
            fi
        fi

        # Generate menu entries
        local selection
        selection=$(generate_network_menu | rofi -dmenu -markup-rows -config "${ROFI_THEME}" -p "󰤨 Wi-Fi" -mesg "Select a network or action:")
        [ -z "${selection}" ] && exit 0

        # Action: Turn Wi-Fi Off
        if [[ "${selection}" == *"Turn Wi-Fi OFF"* ]]; then
            toggle_wifi
            continue
        fi

        # Action: Rescan
        if [[ "${selection}" == *"Rescan"* ]]; then
            rescan_networks
            continue
        fi

        # Action: Hidden Network
        if [[ "${selection}" == *"Hidden Network"* ]]; then
            connect_hidden_network
            continue
        fi

        # Action: Manage Saved
        if [[ "${selection}" == *"Manage Saved"* ]]; then
            manage_saved_connections
            continue
        fi

        # Ignore decorative lines
        if [[ "${selection}" == *"──"* ]]; then
            continue
        fi

        # Lookup in cache for exact metadata
        local net_json
        net_json=$(python3 -c "
import json, sys
try:
    with open('${CACHE_FILE}') as f:
        cache = json.load(f)
    item = cache.get(sys.argv[1])
    if item:
        print(json.dumps(item))
except Exception:
    pass
" "${selection}")

        if [ -n "${net_json}" ]; then
            local target_ssid is_active is_saved sec_type
            target_ssid=$(echo "${net_json}" | python3 -c "import sys, json; print(json.load(sys.stdin)['ssid'])")
            is_active=$(echo "${net_json}" | python3 -c "import sys, json; print(json.load(sys.stdin)['in_use'])")
            is_saved=$(echo "${net_json}" | python3 -c "import sys, json; print(json.load(sys.stdin)['saved'])")
            sec_type=$(echo "${net_json}" | python3 -c "import sys, json; print(json.load(sys.stdin)['security'])")

            if [ "${is_active}" = "True" ]; then
                connected_network_actions "${target_ssid}"
                continue
            fi

            if [ "${is_saved}" = "True" ]; then
                local saved_act
                saved_act=$(echo -e "󰄲  Connect to ${target_ssid}\n󰆴  Forget Saved Network\n󰌌  Back" | rofi -dmenu -config "${ROFI_THEME}" -p "󰤨 ${target_ssid}" -mesg "Saved Network Options:")
                case "${saved_act}" in
                    *"Connect"*)
                        connect_saved "${target_ssid}"
                        exit 0
                        ;;
                    *"Forget"*)
                        nmcli connection delete id "${target_ssid}" >/dev/null 2>&1
                        notify "low" "edit-delete" "Network Forgotten" "Removed ${target_ssid} from saved profiles."
                        continue
                        ;;
                    *)
                        continue
                        ;;
                esac
            fi

            if [ "${sec_type}" = "OPEN" ]; then
                connect_open "${target_ssid}"
                exit 0
            else
                connect_secured_prompt "${target_ssid}"
                exit 0
            fi
        else
            # Fallback regex extraction if cache misses
            local fallback_ssid
            fallback_ssid=$(echo "${selection}" | sed -E -e 's/<[^>]+>//g' -e 's/^[[:space:]]*//' -e 's/[│|].*$//' -e 's/^[󰄲󰤨󰤥󰤢󰤟][[:space:]]+//' -e 's/[[:space:]]+$//')
            if [ -n "${fallback_ssid}" ]; then
                connect_secured_prompt "${fallback_ssid}"
                exit 0
            fi
        fi
    done
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
