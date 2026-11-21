#!/usr/bin/env bash
# =====================================================
# Omarchy-Style Volume Control for Wireplumber / Dunst
# Supports standard steps (5%) and fine 1% adjustments
# =====================================================

STEP="${2:-5}"
QUICKSHELL_CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/hypr/quickshell/shell.qml"
BAR_MODE_FILE="${XDG_STATE_HOME:-$HOME/.local/state}/hypr-rice/bar-mode"

show_osd() {
    local title="$1" value="$2" detail="$3" mode="quickshell"
    if [ -f "${BAR_MODE_FILE}" ]; then
        IFS= read -r mode < "${BAR_MODE_FILE}" || true
    fi
    [ "${mode}" = "quickshell" ] || return 1
    command -v qs >/dev/null 2>&1 || return 1
    qs ipc --path "${QUICKSHELL_CONFIG}" call hyprshell showOsd "${title}" "${value}" "${detail}" >/dev/null 2>&1
}

get_volume() {
    # Extract volume as an integer percentage from wpctl output
    wpctl get-volume @DEFAULT_AUDIO_SINK@ | awk '{
        vol = int($2 * 100);
        if ($3 == "[MUTED]") {
            print "muted " vol
        } else {
            print "unmuted " vol
        }
    }'
}

notify_volume() {
    read -r status vol < <(get_volume)
    if [ "${status}" = "muted" ]; then
        if show_osd "Volume" "${vol}" "Muted"; then
            return
        fi
        dunstify -a "Volume" \
                 -u low \
                 -r 9993 \
                 -i "audio-volume-muted" \
                 "Audio Muted" \
                 "Current level: ${vol}%"
    else
        if show_osd "Volume" "${vol}" "Active"; then
            return
        fi
        dunstify -a "Volume" \
                 -u low \
                 -r 9993 \
                 -h int:value:"${vol}" \
                 -i "audio-volume-high" \
                 "Volume: ${vol}%"
    fi
}

refresh_waybar() {
    pkill -RTMIN+7 waybar 2>/dev/null || true
}

case "$1" in
    up)
        wpctl set-volume -l 1.5 @DEFAULT_AUDIO_SINK@ "${STEP}%+"
        notify_volume
        refresh_waybar
        ;;
    down)
        wpctl set-volume @DEFAULT_AUDIO_SINK@ "${STEP}%-"
        notify_volume
        refresh_waybar
        ;;
    mute)
        wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle
        notify_volume
        refresh_waybar
        ;;
    mic)
        wpctl set-mute @DEFAULT_AUDIO_SOURCE@ toggle
        read -r mic_status _ < <(wpctl get-volume @DEFAULT_AUDIO_SOURCE@ | awk '{if ($3 == "[MUTED]") print "muted"; else print "unmuted"}')
        if [ "${mic_status}" = "muted" ]; then
            if ! show_osd "Microphone" "0" "Muted"; then
                dunstify -a "Microphone" -u low -r 9992 -i "microphone-sensitivity-muted" "Microphone Muted"
            fi
        else
            if ! show_osd "Microphone" "100" "Active"; then
                dunstify -a "Microphone" -u low -r 9992 -i "microphone-sensitivity-high" "Microphone Active"
            fi
        fi
        refresh_waybar
        ;;
    *)
        echo "Usage: $0 {up [step]|down [step]|mute|mic}"
        exit 1
        ;;
esac
