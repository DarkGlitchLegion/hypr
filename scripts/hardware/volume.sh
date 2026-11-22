#!/usr/bin/env bash
# =====================================================
# Omarchy-Style Volume Control for Wireplumber / Dunst
# Supports standard steps (5%) and fine 1% adjustments
# =====================================================

STEP="${2:-5}"
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
        dunstify -a "Volume" \
                 -u low \
                 -r 9993 \
                 -i "audio-volume-muted" \
                 "Audio Muted" \
                 "Current level: ${vol}%"
    else
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
            dunstify -a "Microphone" -u low -r 9992 -i "microphone-sensitivity-muted" "Microphone Muted"
        else
            dunstify -a "Microphone" -u low -r 9992 -i "microphone-sensitivity-high" "Microphone Active"
        fi
        refresh_waybar
        ;;
    *)
        echo "Usage: $0 {up [step]|down [step]|mute|mic}"
        exit 1
        ;;
esac
