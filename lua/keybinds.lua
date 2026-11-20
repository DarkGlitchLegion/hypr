-- =====================================================
-- Arch Linux Hyprland Rice — Keybindings Configuration
-- Engine: Hyprland Lua Configuration (v0.57.2+)
-- Modifier: Super (Windows key)
-- =====================================================

local mainMod       = Desktop.mainMod
local scripts       = Desktop.scripts
local terminal      = Desktop.terminal
local fileManager   = Desktop.fileManager
local menu          = Desktop.menu
local controlCenter = Desktop.controlCenter
local lockscreen    = Desktop.lockscreen
local hyprsecKeybind = "SUPER + SHIFT + H"
local hyprsecKeybindFile = io.open(Desktop.home .. "/.config/hyprsec/keybind", "r")
if hyprsecKeybindFile then
    local configuredKeybind = hyprsecKeybindFile:read("*l")
    hyprsecKeybindFile:close()
    if configuredKeybind and configuredKeybind:match("^[A-Z0-9%s+]+$") then
        hyprsecKeybind = configuredKeybind
    end
end

-- -----------------------------------------------------
-- 1. Application Launchers & Control Center
-- -----------------------------------------------------
hl.bind(mainMod .. " + RETURN",         hl.dsp.exec_cmd(terminal))
hl.bind(mainMod .. " + SHIFT + RETURN", hl.dsp.exec_cmd("firefox"))
hl.bind(mainMod .. " + SPACE",          hl.dsp.exec_cmd(menu))
hl.bind(mainMod .. " + ALT + SPACE",    hl.dsp.exec_cmd(controlCenter))
hl.bind(mainMod .. " + C",              hl.dsp.exec_cmd(controlCenter))
hl.bind(mainMod .. " + SHIFT + F",      hl.dsp.exec_cmd(fileManager))
hl.bind(mainMod .. " + SHIFT + E",      hl.dsp.exec_cmd("code || " .. terminal .. " -e nano"))
hl.bind(mainMod .. " + SHIFT + T",      hl.dsp.exec_cmd("kitty --class btop --title btop --config " .. Desktop.config .. "/kitty/kitty.conf -e btop"))
hl.bind(mainMod .. " + SHIFT + I",      hl.dsp.exec_cmd("kitty --class fastfetch --title fastfetch --hold --config " .. Desktop.config .. "/kitty/kitty.conf -e fastfetch"))
hl.bind(mainMod .. " + SHIFT + M",      hl.dsp.exec_cmd(scripts .. "/hardware/display-manager.py"))
hl.bind(mainMod .. " + SHIFT + C",      hl.dsp.exec_cmd(scripts .. "/desktop/cmatrix.sh"))
hl.bind(mainMod .. " + SHIFT + S",      hl.dsp.exec_cmd(scripts .. "/hardware/wifi-menu.sh"))
hl.bind(mainMod .. " + SHIFT + B",      hl.dsp.exec_cmd(scripts .. "/hardware/bluetooth-menu.sh"))
hl.bind(hyprsecKeybind,                 hl.dsp.exec_cmd(scripts .. "/security/hyprsec-box.sh menu"))

-- -----------------------------------------------------
-- 1b. Genie Effect — Minimize / Restore
-- -----------------------------------------------------
-- Super+M          → genie-minimize active window (warp toward dock/bottom)
-- Super+Alt+M      → genie-restore last minimized window (reverse warp)
-- (Super+Shift+M is kept for display-manager.py — unchanged)
local genie_bin = Desktop.home .. "/.local/bin"
hl.bind(mainMod .. " + M",         hl.dsp.exec_cmd(genie_bin .. "/genie-minimize"))
hl.bind(mainMod .. " + ALT + M",   hl.dsp.exec_cmd(genie_bin .. "/genie-restore"))

-- -----------------------------------------------------
-- 2. Window Management
-- -----------------------------------------------------
hl.bind(mainMod .. " + W",       hl.dsp.window.close())
hl.bind(mainMod .. " + Q",       hl.dsp.window.close())
hl.bind(mainMod .. " + T",       hl.dsp.window.float({ action = "toggle" }))
hl.bind(mainMod .. " + V",       hl.dsp.window.float({ action = "toggle" }))
hl.bind(mainMod .. " + F",       hl.dsp.window.fullscreen(0))
hl.bind(mainMod .. " + ALT + F", hl.dsp.window.fullscreen(1))
hl.bind(mainMod .. " + P",       hl.dsp.window.pseudo())
hl.bind(mainMod .. " + J",       hl.dsp.layout("togglesplit"))

-- Window Grouping (Tabs)
hl.bind(mainMod .. " + G",         hl.dsp.exec_cmd("hyprctl dispatch togglegroup"))
hl.bind(mainMod .. " + ALT + G",   hl.dsp.exec_cmd("hyprctl dispatch moveoutofgroup"))
hl.bind(mainMod .. " + ALT + TAB", hl.dsp.exec_cmd("hyprctl dispatch changegroupactive f"))

-- Directional Focus (Arrow Keys)
hl.bind(mainMod .. " + left",  hl.dsp.focus({ direction = "left" }))
hl.bind(mainMod .. " + right", hl.dsp.focus({ direction = "right" }))
hl.bind(mainMod .. " + up",    hl.dsp.focus({ direction = "up" }))
hl.bind(mainMod .. " + down",  hl.dsp.focus({ direction = "down" }))

-- Move / Swap Windows (Shift + Arrow Keys)
hl.bind(mainMod .. " + SHIFT + left",  hl.dsp.window.move({ direction = "left" }))
hl.bind(mainMod .. " + SHIFT + right", hl.dsp.window.move({ direction = "right" }))
hl.bind(mainMod .. " + SHIFT + up",    hl.dsp.window.move({ direction = "up" }))
hl.bind(mainMod .. " + SHIFT + down",  hl.dsp.window.move({ direction = "down" }))

-- Keyboard Window Resizing
hl.bind(mainMod .. " + semicolon", hl.dsp.window.resize({ x = -30, y = -30, relative = true }), { repeating = true })
hl.bind(mainMod .. " + apostrophe", hl.dsp.window.resize({ x = 30, y = 30, relative = true }), { repeating = true })

-- Mouse Window Manipulation
hl.bind(mainMod .. " + mouse:272", hl.dsp.window.drag(),   { mouse = true })
hl.bind(mainMod .. " + mouse:273", hl.dsp.window.resize(), { mouse = true })

-- -----------------------------------------------------
-- 3. Workspace Management (1 - 10; Super + 0 selects workspace 10)
-- -----------------------------------------------------
for i = 1, 10 do
    local key = tostring(i % 10)
    hl.bind(mainMod .. " + " .. key,               hl.dsp.focus({ workspace = i }))
    hl.bind(mainMod .. " + SHIFT + " .. key,       hl.dsp.window.move({ workspace = i }))
    hl.bind(mainMod .. " + SHIFT + ALT + " .. key, hl.dsp.exec_cmd("hyprctl dispatch movetoworkspacesilent " .. i))
end

-- Workspace Navigation
hl.bind(mainMod .. " + TAB",         hl.dsp.focus({ workspace = "e+1" }))
hl.bind(mainMod .. " + SHIFT + TAB", hl.dsp.focus({ workspace = "e-1" }))
hl.bind(mainMod .. " + CTRL + TAB",  hl.dsp.focus({ workspace = "previous" }))
hl.bind(mainMod .. " + mouse_down",  hl.dsp.focus({ workspace = "e+1" }))
hl.bind(mainMod .. " + mouse_up",    hl.dsp.focus({ workspace = "e-1" }))

-- -----------------------------------------------------
-- 4. System Controls & Hardware
-- -----------------------------------------------------
hl.bind(mainMod .. " + ESCAPE",           hl.dsp.exec_cmd(scripts .. "/session/power-menu.sh"))
hl.bind(mainMod .. " + CTRL + L",         hl.dsp.exec_cmd(lockscreen))
hl.bind(mainMod .. " + L",                hl.dsp.exec_cmd(lockscreen))
hl.bind(mainMod .. " + SHIFT + R",        hl.dsp.exec_cmd(scripts .. "/desktop/restart-waybar.sh && hyprctl reload"))
hl.bind(mainMod .. " + CTRL + A",         hl.dsp.exec_cmd(scripts .. "/hardware/audio-menu.sh"))
hl.bind(mainMod .. " + SHIFT + D",        hl.dsp.exec_cmd(scripts .. "/session/notification-toggle.sh"))
hl.bind(mainMod .. " + CTRL + N",         hl.dsp.exec_cmd(scripts .. "/session/notification-history.sh"))
hl.bind(mainMod .. " + N",                hl.dsp.exec_cmd("dunstctl history-pop"))
hl.bind(mainMod .. " + SHIFT + N",        hl.dsp.exec_cmd("dunstctl close-all"))

-- -----------------------------------------------------
-- 5. Productivity & Capture
-- -----------------------------------------------------
hl.bind(mainMod .. " + K",                  hl.dsp.exec_cmd(scripts .. "/desktop/keybindings-menu.sh"))
hl.bind(mainMod .. " + SHIFT + K",          hl.dsp.exec_cmd(scripts .. "/desktop/keybindings-window.sh"))
hl.bind(mainMod .. " + CTRL + W",           hl.dsp.exec_cmd(scripts .. "/wallpaper/wallpaper-selector.sh"))
hl.bind(mainMod .. " + CTRL + SPACE",       hl.dsp.exec_cmd(scripts .. "/wallpaper/wallpaper-selector.sh"))
hl.bind(mainMod .. " + CTRL + V",           hl.dsp.exec_cmd(scripts .. "/clipboard/clipboard-menu.sh"))
hl.bind(mainMod .. " + CTRL + SHIFT + V",   hl.dsp.exec_cmd(scripts .. "/clipboard/clipboard-clear.sh"))
hl.bind("Print",                            hl.dsp.exec_cmd(scripts .. "/session/screenshot.sh region"))
hl.bind(mainMod .. " + Print",              hl.dsp.exec_cmd(scripts .. "/session/screenshot.sh full"))
hl.bind(mainMod .. " + CTRL + C",           hl.dsp.exec_cmd(scripts .. "/session/screenshot.sh menu"))

-- -----------------------------------------------------
-- 6. Hardware & Multimedia Controls
-- -----------------------------------------------------
-- Volume Controls
hl.bind("XF86AudioRaiseVolume",       hl.dsp.exec_cmd(scripts .. "/hardware/volume.sh up 5"),   { locked = true, repeating = true })
hl.bind("XF86AudioLowerVolume",       hl.dsp.exec_cmd(scripts .. "/hardware/volume.sh down 5"), { locked = true, repeating = true })
hl.bind("ALT + XF86AudioRaiseVolume", hl.dsp.exec_cmd(scripts .. "/hardware/volume.sh up 1"),   { locked = true, repeating = true })
hl.bind("ALT + XF86AudioLowerVolume", hl.dsp.exec_cmd(scripts .. "/hardware/volume.sh down 1"), { locked = true, repeating = true })
hl.bind("XF86AudioMute",              hl.dsp.exec_cmd(scripts .. "/hardware/volume.sh mute"),   { locked = true, repeating = true })
hl.bind("XF86AudioMicMute",           hl.dsp.exec_cmd(scripts .. "/hardware/volume.sh mic"),    { locked = true, repeating = true })

-- Brightness Controls
hl.bind("XF86MonBrightnessUp",         hl.dsp.exec_cmd(scripts .. "/hardware/brightness.sh up 5"),   { locked = true, repeating = true })
hl.bind("XF86MonBrightnessDown",       hl.dsp.exec_cmd(scripts .. "/hardware/brightness.sh down 5"), { locked = true, repeating = true })
hl.bind("ALT + XF86MonBrightnessUp",   hl.dsp.exec_cmd(scripts .. "/hardware/brightness.sh up 1"),   { locked = true, repeating = true })
hl.bind("ALT + XF86MonBrightnessDown", hl.dsp.exec_cmd(scripts .. "/hardware/brightness.sh down 1"), { locked = true, repeating = true })
hl.bind("SHIFT + XF86MonBrightnessUp",   hl.dsp.exec_cmd(scripts .. "/hardware/brightness.sh max"),  { locked = true, repeating = true })
hl.bind("SHIFT + XF86MonBrightnessDown", hl.dsp.exec_cmd(scripts .. "/hardware/brightness.sh min"),  { locked = true, repeating = true })
