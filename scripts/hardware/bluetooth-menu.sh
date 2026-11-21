#!/usr/bin/env bash
# =====================================================================
# Graphical Bluetooth Manager for Hyprland (Rofi + bluetoothctl)
# Theme: ~/.config/hypr/rofi/wifi.rasi
# =====================================================================

ROFI_THEME="${HOME}/.config/hypr/rofi/wifi.rasi"
PIDFILE="/tmp/hypr_bt_menu.pid"

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
    local title="$2"
    local msg="$3"
    dunstify -a "Bluetooth" -u "${urgency}" -i bluetooth "${title}" "${msg}" 2>/dev/null || true
}

refresh_waybar_bluetooth() {
    pkill -RTMIN+9 waybar 2>/dev/null || true
}

log_event() {
    local severity="$1"
    local description="$2"
    python3 "${HOME}/.config/hypr/scripts/core/rice_maintenance.py" event bluetooth "${severity}" "${description}" \
        --category bluetooth >/dev/null 2>&1 || \
        printf 'Bluetooth Manager: could not record activity event: %s\n' "${description}" >&2
}

ensure_agent() {
    if ! pgrep -fa bluetooth-agent.py >/dev/null 2>&1; then
        if command -v hyprctl >/dev/null 2>&1; then
            hyprctl dispatch "hl.dsp.exec_cmd(\"${HOME}/.config/hypr/scripts/hardware/bluetooth-agent.py\")" >/dev/null 2>&1 || \
            nohup python3 "${HOME}/.config/hypr/scripts/hardware/bluetooth-agent.py" >/dev/null 2>&1 &
        else
            nohup python3 "${HOME}/.config/hypr/scripts/hardware/bluetooth-agent.py" >/dev/null 2>&1 &
        fi
    fi
    bluetoothctl pairable on >/dev/null 2>&1 || true
}

is_powered() {
    bluetoothctl show 2>/dev/null | grep -q "Powered: yes"
}

toggle_power() {
    if is_powered; then
        bluetoothctl power off >/dev/null 2>&1
        refresh_waybar_bluetooth
        log_event "info" "Bluetooth radio powered off"
        notify "low" "Bluetooth Disabled" "Bluetooth adapter powered off."
    else
        # 1. Unblock hardware/software RF kill switches
        rfkill unblock bluetooth 2>/dev/null || true
        # 2. Ensure daemon is running
        if command -v systemctl >/dev/null 2>&1; then
            if ! systemctl is-active --quiet bluetooth 2>/dev/null; then
                systemctl start bluetooth 2>/dev/null || true
                sleep 0.3
            fi
        fi
        # 3. Power on adapter
        bluetoothctl power on >/dev/null 2>&1
        sleep 0.4
        ensure_agent
        refresh_waybar_bluetooth

        if is_powered; then
            log_event "info" "Bluetooth radio powered on"
            notify "low" "Bluetooth Enabled" "Bluetooth adapter powered on."
        else
            log_event "error" "Bluetooth radio failed to power on"
            notify "critical" "Bluetooth Error" "Failed to power on Bluetooth. Check rfkill or hardware switch."
        fi
    fi
}

scan_devices() {
    ensure_agent
    notify "low" "Scanning Devices" "Searching for nearby Bluetooth devices for 6 seconds..."
    bluetoothctl --timeout 6 scan on >/dev/null 2>&1 || true
}

device_actions() {
    local mac="$1"
    local name="$2"
    local is_conn="$3"

    local is_paired
    is_paired=$(bluetoothctl info "${mac}" 2>/dev/null | grep -q "Paired: yes" && echo "true" || echo "false")

    local sub_opts
    if [ "${is_conn}" = "true" ]; then
        sub_opts="󰅖  Disconnect from ${name}\n󰆴  Unpair / Remove ${name}\n󰌌  Back"
    elif [ "${is_paired}" = "true" ]; then
        sub_opts="󰄲  Connect to ${name}\n󰆴  Unpair / Remove ${name}\n󰌌  Back"
    else
        sub_opts="󰄲  Pair & Connect to ${name}\n󰆴  Remove Device\n󰌌  Back"
    fi

    local choice
    choice=$(echo -e "${sub_opts}" | rofi -dmenu -config "${ROFI_THEME}" -p "󰂯 ${name}" -mesg "Device: <b>${name}</b> [${mac}]")
    [ -z "${choice}" ] && return 0

    case "${choice}" in
        *"Connect to"*|*"Pair & Connect"*)
            ensure_agent
            bluetoothctl pairable on >/dev/null 2>&1 || true

            if [ "${is_paired}" != "true" ]; then
                notify "normal" "Pairing..." "Initiating pairing with ${name}...\nPlease confirm pairing on your device if prompted."
                # Leave time for the laptop approval dialog and the phone's confirmation.
                if ! timeout 60 bluetoothctl pair "${mac}" >/dev/null 2>&1; then
                    if ! bluetoothctl info "${mac}" 2>/dev/null | grep -q "Paired: yes"; then
                        notify "critical" "Pairing Failed" "Could not complete pairing with ${name}.\nPlease ensure the device is in pairing mode."
                        return 1
                    fi
                fi
                notify "low" "Paired" "Successfully paired with ${name}."
            fi

            if ! bluetoothctl trust "${mac}" >/dev/null 2>&1; then
                notify "critical" "Trust Failed" "Could not authorize future connections from ${name}."
                return 1
            fi

            notify "low" "Connecting..." "Connecting to ${name}..."
            if timeout 10 bluetoothctl connect "${mac}" >/dev/null 2>&1; then
                refresh_waybar_bluetooth
                log_event "info" "Bluetooth device connected"
                notify "low" "Connected" "Connected to ${name}."
            else
                log_event "warning" "Bluetooth connection attempt failed"
                notify "critical" "Connection Failed" "Could not connect to ${name}."
            fi
            ;;
        *"Disconnect"*)
            bluetoothctl disconnect "${mac}" >/dev/null 2>&1
            refresh_waybar_bluetooth
            log_event "info" "Bluetooth device disconnected"
            notify "low" "Disconnected" "Disconnected from ${name}."
            ;;
        *"Unpair"*|*"Remove"*)
            bluetoothctl remove "${mac}" >/dev/null 2>&1
            refresh_waybar_bluetooth
            log_event "info" "Bluetooth paired device removed"
            notify "low" "Device Removed" "Unpaired and removed ${name}."
            ;;
        *)
            ;;
    esac
}

main() {
    ensure_agent

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
        local is_disc
        is_disc=$(bluetoothctl show 2>/dev/null | grep -q "Discoverable: yes" && echo "true" || echo "false")
        local disc_label
        if [ "${is_disc}" = "true" ]; then
            disc_label="󰈉  Pairing Mode: ACTIVE (Visible to others — Click to turn OFF)"
        else
            disc_label="󰈉  Make Computer Discoverable (Pairing Mode - 3 min)"
        fi

        local menu="󰂲  Turn Bluetooth OFF\n${disc_label}\n󰑓  Scan for Nearby Devices (6s)\n<span color=\"#333333\">────────────────────────────────────────────────────────────</span>\n"
        
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
                [ -z "${dname}" ] && dname="Unknown Device"

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
            menu="${menu}<i>(No paired or discovered devices found)</i>\n"
        fi

        local sel
        sel=$(echo -e "${menu}" | rofi -dmenu -markup-rows -config "${ROFI_THEME}" -p "󰂯 Bluetooth" -mesg "Select a Bluetooth device or action:")
        [ -z "${sel}" ] && exit 0

        if [[ "${sel}" == *"Turn Bluetooth OFF"* ]]; then
            toggle_power
            continue
        fi

        if [[ "${sel}" == *"Pairing Mode: ACTIVE"* ]]; then
            bluetoothctl discoverable off >/dev/null 2>&1
            notify "low" "Pairing Mode Disabled" "Computer is no longer discoverable to others."
            continue
        fi

        if [[ "${sel}" == *"Make Computer Discoverable"* ]]; then
            bluetoothctl pairable on >/dev/null 2>&1 || true
            bluetoothctl discoverable on >/dev/null 2>&1 || true
            notify "normal" "Pairing Mode Active" "Computer is visible to other devices for 3 minutes.\nYou can now search and pair from your phone/other device."
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

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
