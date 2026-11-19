#!/usr/bin/env bash
# =====================================================================
# Graphical Bluetooth Manager for Hyprland (Rofi + bluetoothctl)
# Theme: ~/.config/hypr/rofi/wifi.rasi
# =====================================================================

ROFI_THEME="${HOME}/.config/hypr/rofi/wifi.rasi"

notify() {
    local urgency="${1:-low}"
    local title="$2"
    local msg="$3"
    dunstify -a "Bluetooth" -u "${urgency}" -i bluetooth "${title}" "${msg}" 2>/dev/null || true
}

is_powered() {
    bluetoothctl show 2>/dev/null | grep -q "Powered: yes"
}

toggle_power() {
    if is_powered; then
        bluetoothctl power off >/dev/null 2>&1
        notify "low" "Bluetooth Disabled" "Bluetooth adapter powered off."
    else
        bluetoothctl power on >/dev/null 2>&1
        notify "low" "Bluetooth Enabled" "Bluetooth adapter powered on."
        sleep 1.0
    fi
}

scan_devices() {
    notify "low" "Scanning Devices" "Searching for nearby Bluetooth devices for 5 seconds..."
    bluetoothctl --timeout 5 scan on >/dev/null 2>&1 || true
}

device_actions() {
    local mac="$1"
    local name="$2"
    local is_conn="$3"

    local sub_opts
    if [ "${is_conn}" = "true" ]; then
        sub_opts="󰅖  Disconnect from ${name}\n󰆴  Unpair / Remove ${name}\n󰌌  Back"
    else
        sub_opts="󰄲  Connect to ${name}\n󰆴  Unpair / Remove ${name}\n󰌌  Back"
    fi

    local choice
    choice=$(echo -e "${sub_opts}" | rofi -dmenu -config "${ROFI_THEME}" -p "󰂯 ${name}" -mesg "Device: <b>${name}</b> [${mac}]")
    [ -z "${choice}" ] && return 0

    case "${choice}" in
        *"Connect to"*)
            notify "low" "Connecting..." "Connecting to ${name}..."
            if bluetoothctl connect "${mac}" >/dev/null 2>&1; then
                notify "low" "Connected" "Connected to ${name}."
            else
                notify "critical" "Connection Failed" "Could not connect to ${name}."
            fi
            ;;
        *"Disconnect"*)
            bluetoothctl disconnect "${mac}" >/dev/null 2>&1
            notify "low" "Disconnected" "Disconnected from ${name}."
            ;;
        *"Unpair"*)
            bluetoothctl remove "${mac}" >/dev/null 2>&1
            notify "low" "Device Removed" "Unpaired and removed ${name}."
            ;;
        *)
            ;;
    esac
}

main() {
    while true; do
        if ! is_powered; then
            local off_opts="󰂯  Bluetooth is OFF — Click to Turn ON\n󰌌  Exit"
            local choice
            choice=$(echo -e "${off_opts}" | rofi -dmenu -config "${ROFI_THEME}" -p "󰂲 Bluetooth" -mesg "Bluetooth adapter is powered off.")
            if [[ "${choice}" == *"Turn ON"* ]]; then
                toggle_power
                continue
            else
                exit 0
            fi
        fi

        # Header controls
        local menu="󰂲  Turn Bluetooth OFF\n󰑓  Scan for Nearby Devices (5s)\n<span color=\"#333333\">────────────────────────────────────────────────────────────</span>\n"
        
        # Get paired / discovered devices
        local raw_devs
        raw_devs=$(bluetoothctl devices 2>/dev/null)

        if [ -n "${raw_devs}" ]; then
            while IFS= read -r line; do
                local mac
                mac=$(echo "${line}" | awk '{print $2}')
                local dname
                dname=$(echo "${line}" | cut -d' ' -f3-)
                [ -z "${mac}" ] && continue

                local dev_info
                dev_info=$(bluetoothctl info "${mac}" 2>/dev/null)
                local connected
                connected=$(echo "${dev_info}" | grep -q "Connected: yes" && echo "true" || echo "false")
                local paired
                paired=$(echo "${dev_info}" | grep -q "Paired: yes" && echo "true" || echo "false")

                if [ "${connected}" = "true" ]; then
                    menu="${menu}<span color=\"#A3BE8C\"><b>󰂱  ${dname}</b></span> <span color=\"#333333\">│</span> <span color=\"#A3BE8C\">[Connected]</span> [${mac}]\n"
                elif [ "${paired}" = "true" ]; then
                    menu="${menu}<span color=\"#D5D5D5\"><b>󰂯  ${dname}</b></span> <span color=\"#333333\">│</span> <span color=\"#888888\">[Paired]</span> [${mac}]\n"
                else
                    menu="${menu}<span color=\"#888888\">󰂯  ${dname}</span> <span color=\"#333333\">│</span> <span color=\"#666666\">[Discovered]</span> [${mac}]\n"
                fi
            done <<< "${raw_devs}"
        else
            menu="${menu}<i>(No paired devices found)</i>\n"
        fi

        local sel
        sel=$(echo -e "${menu}" | rofi -dmenu -markup-rows -config "${ROFI_THEME}" -p "󰂯 Bluetooth" -mesg "Select a Bluetooth device or action:")
        [ -z "${sel}" ] && exit 0

        if [[ "${sel}" == *"Turn Bluetooth OFF"* ]]; then
            toggle_power
            continue
        fi

        if [[ "${sel}" == *"Scan"* ]]; then
            scan_devices
            continue
        fi

        if [[ "${sel}" == *"──"* ]] || [[ "${sel}" == *"No paired"* ]]; then
            continue
        fi

        # Extract MAC address inside brackets [XX:XX:XX:XX:XX:XX]
        local sel_mac
        sel_mac=$(echo "${sel}" | grep -o '\[[0-9A-Fa-f:]\{17\}\]' | tr -d '[]')
        local sel_name
        sel_name=$(echo "${sel}" | sed -E -e 's/<[^>]+>//g' -e 's/^[󰂱󰂯][[:space:]]+//' -e 's/[│|].*$//' -e 's/[[:space:]]+$//')

        if [ -n "${sel_mac}" ]; then
            local is_active
            is_active=$(echo "${sel}" | grep -q "Connected" && echo "true" || echo "false")
            device_actions "${sel_mac}" "${sel_name}" "${is_active}"
        fi
    done
}

main "$@"
