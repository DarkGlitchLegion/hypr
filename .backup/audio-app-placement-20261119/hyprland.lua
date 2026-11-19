-- =====================================================
-- Arch Linux Hyprland Rice — Minimal Dark Configuration
-- Engine: Hyprland Lua Configuration (v0.57.2+)
-- Palette: Charcoal #0C0D10 | Slate #17191F | Accent #AAAAAA
-- =====================================================

local homeDir   = os.getenv("HOME")
local configDir = homeDir .. "/.config/hypr"

-- Shared Desktop Environment Context
Desktop = {
    home          = homeDir,
    config        = configDir,
    scripts       = configDir .. "/scripts",
    terminal      = "kitty --config " .. configDir .. "/kitty/kitty.conf",
    fileManager   = "thunar",
    menu          = "rofi -show drun -config " .. configDir .. "/rofi/launcher.rasi",
    controlCenter = configDir .. "/scripts/control-center.sh",
    lockscreen    = "hyprlock -c " .. configDir .. "/hyprlock/hyprlock.conf",
    mainMod       = "SUPER",
}

-- Load Modular Subsystems
dofile(configDir .. "/lua/monitors.lua")
dofile(configDir .. "/lua/autostart.lua")
dofile(configDir .. "/lua/env.lua")
dofile(configDir .. "/lua/appearance.lua")
dofile(configDir .. "/lua/animations.lua")
dofile(configDir .. "/lua/rules.lua")
dofile(configDir .. "/lua/keybinds.lua")
