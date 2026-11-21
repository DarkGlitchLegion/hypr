-- =====================================================
-- Arch Linux Hyprland Rice — Autostart Configuration
-- Engine: Hyprland Lua Configuration (v0.57.2+)
-- =====================================================

hl.on("hyprland.start", function ()
    local config = Desktop.config
    local scripts = Desktop.scripts

    -- Continuously sample the active route so traffic totals persist while the popup is closed.
    hl.exec_cmd(scripts .. "/hardware/network-traffic.py --watch")

    -- Polkit authentication agent
    hl.exec_cmd("/usr/lib/hyprpolkitagent/hyprpolkitagent")

    -- Start the selected bar (Quickshell by default, Waybar after rollback).
    hl.exec_cmd(scripts .. "/desktop/start-bar.sh")

    -- Dunst notification daemon
    hl.exec_cmd("dunst -config " .. config .. "/dunst/dunstrc")

    -- Restore the saved wallpaper before starting hyprpaper.
    hl.exec_cmd(scripts .. "/wallpaper/restore-wallpaper.sh")

    -- Battery notifier through SMS notifications
    hl.exec_cmd(scripts .. "/session/battery-notifier.sh")

    -- Detect monitor hotplug events and restore explicitly saved display layouts.
    hl.exec_cmd(scripts .. "/hardware/display-manager.py --watch")

    -- Watch PipeWire sink hotplug events when optional automatic HDMI routing is enabled.
    hl.exec_cmd(scripts .. "/hardware/audio-manager.py --watch")

    -- One supervised Hypridle instance uses persistent Rice idle settings.
    hl.exec_cmd(scripts .. "/session/idle-manager.py --supervise")

    -- Cursor synchronization across Wayland & XWayland
    hl.exec_cmd("hyprctl setcursor Adwaita 20")
    hl.exec_cmd("gsettings set org.gnome.desktop.interface cursor-theme 'Adwaita'")
    hl.exec_cmd("gsettings set org.gnome.desktop.interface cursor-size 20")

    -- Clipboard history persistence daemon
    hl.exec_cmd(scripts .. "/clipboard/clipboard-daemon.sh")

    -- Bluetooth pairing & authentication agent (D-Bus)
    hl.exec_cmd(scripts .. "/hardware/bluetooth-agent.py")

    -- Synchronize GTK dark theme & icons for Thunar and GTK apps
    hl.exec_cmd(scripts .. "/desktop/apply-gtk-theme.sh")

    -- Genie Effect plugin — load after Hyprland is fully started.
    -- Silently skips if the .so is missing (before first build or after a Hyprland update).
    local genie_so = Desktop.home .. "/.local/share/hypr-genie/genie.so"
    local f = io.open(genie_so, "r")
    if f then
        f:close()
        hl.exec_cmd("hyprctl plugin load " .. genie_so)
    end
end)
