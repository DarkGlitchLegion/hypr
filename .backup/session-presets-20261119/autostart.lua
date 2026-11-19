-- =====================================================
-- Arch Linux Hyprland Rice — Autostart Configuration
-- Engine: Hyprland Lua Configuration (v0.57.2+)
-- =====================================================

hl.on("hyprland.start", function ()
    local config = Desktop.config
    local scripts = Desktop.scripts

    -- Polkit authentication agent
    hl.exec_cmd("/usr/lib/hyprpolkitagent/hyprpolkitagent")

    -- Waybar status bar
    hl.exec_cmd("waybar -c " .. config .. "/waybar/config.jsonc -s " .. config .. "/waybar/style.css")

    -- Dunst notification daemon
    hl.exec_cmd("dunst -config " .. config .. "/dunst/dunstrc")

    -- Restore the saved wallpaper before starting hyprpaper.
    hl.exec_cmd(scripts .. "/restore-wallpaper.sh")

    -- Detect monitor hotplug events and restore explicitly saved display layouts.
    hl.exec_cmd(scripts .. "/display-manager.py --watch")

    -- Watch PipeWire sink hotplug events when optional automatic HDMI routing is enabled.
    hl.exec_cmd(scripts .. "/audio-manager.py --watch")

    -- Hypridle power/lock daemon
    hl.exec_cmd("hypridle -c " .. config .. "/hypridle.conf")

    -- Cursor synchronization across Wayland & XWayland
    hl.exec_cmd("hyprctl setcursor Adwaita 20")
    hl.exec_cmd("gsettings set org.gnome.desktop.interface cursor-theme 'Adwaita'")
    hl.exec_cmd("gsettings set org.gnome.desktop.interface cursor-size 20")

    -- Clipboard history persistence daemon
    hl.exec_cmd(scripts .. "/clipboard-daemon.sh")

    -- Bluetooth pairing & authentication agent (D-Bus)
    hl.exec_cmd(scripts .. "/bluetooth-agent.py")

    -- Synchronize GTK dark theme & icons for Thunar and GTK apps
    hl.exec_cmd(scripts .. "/apply-gtk-theme.sh")
end)
