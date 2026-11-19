-- =====================================================
-- Arch Linux Hyprland Rice — Minimal Dark Configuration
-- Engine: Hyprland Lua Configuration (v0.57.2+)
-- Palette: Charcoal #0C0D10 | Slate #17191F | Accent #AAAAAA
-- =====================================================

------------------
---- MONITORS ----
------------------
-- 100% native unscaled display (prevents oversized fractional upscaling on 1080p)
hl.monitor({
    output   = "",
    mode     = "preferred",
    position = "auto",
    scale    = 1,
})

---------------------
---- MY PROGRAMS ----
---------------------
local homeDir       = os.getenv("HOME")
local terminal      = "kitty --config " .. homeDir .. "/.config/hypr/kitty/kitty.conf"
local fileManager   = "thunar"
local menu          = "rofi -show drun -config " .. homeDir .. "/.config/hypr/rofi/launcher.rasi"
local commandCenter = homeDir .. "/.config/hypr/scripts/command-center.sh"
local lockscreen    = "hyprlock -c " .. homeDir .. "/.config/hypr/hyprlock/hyprlock.conf"

-------------------
---- AUTOSTART ----
-------------------
hl.on("hyprland.start", function ()
    -- Polkit authentication agent
    hl.exec_cmd("/usr/lib/hyprpolkitagent/hyprpolkitagent")

    -- Waybar status bar
    hl.exec_cmd("waybar -c " .. homeDir .. "/.config/hypr/waybar/config.jsonc -s " .. homeDir .. "/.config/hypr/waybar/style.css")

    -- Dunst notification daemon
    hl.exec_cmd("dunst -config " .. homeDir .. "/.config/hypr/dunst/dunstrc")

    -- Hyprpaper wallpaper daemon
    hl.exec_cmd("hyprpaper -c " .. homeDir .. "/.config/hypr/hyprpaper.conf")

    -- Hypridle power/lock daemon
    hl.exec_cmd("hypridle -c " .. homeDir .. "/.config/hypr/hypridle.conf")

    -- Cursor synchronization across Wayland & XWayland
    hl.exec_cmd("hyprctl setcursor Adwaita 20")
    hl.exec_cmd("gsettings set org.gnome.desktop.interface cursor-theme 'Adwaita'")
    hl.exec_cmd("gsettings set org.gnome.desktop.interface cursor-size 20")

    -- Clipboard history persistence daemon
    hl.exec_cmd(homeDir .. "/.config/hypr/scripts/clipboard-daemon.sh")

    -- Synchronize GTK dark theme & icons for Thunar and GTK apps
    hl.exec_cmd(homeDir .. "/.config/hypr/scripts/apply-gtk-theme.sh")
end)

-------------------------------
---- ENVIRONMENT VARIABLES ----
-------------------------------
hl.env("XDG_CURRENT_DESKTOP", "Hyprland")
hl.env("XDG_SESSION_TYPE", "wayland")
hl.env("XDG_SESSION_DESKTOP", "Hyprland")
hl.env("GDK_BACKEND", "wayland,x11,*")
hl.env("CLUTTER_BACKEND", "wayland")

-- GTK Theme & Dark Scheme Integration
hl.env("GTK_THEME", "Adwaita-dark")

-- Standard Desktop Scaling (1:1, no artificial upscaling)
hl.env("GDK_SCALE", "1")
hl.env("QT_AUTO_SCREEN_SCALE_FACTOR", "0")
hl.env("QT_SCALE_FACTOR", "1")
hl.env("QT_QPA_PLATFORM", "wayland;xcb")
hl.env("QT_WAYLAND_DISABLE_WINDOWDECORATION", "1")

-- Browser native Wayland integration
hl.env("MOZ_ENABLE_WAYLAND", "1")

-- Consistent, standard cursor theme and size (20px)
hl.env("XCURSOR_THEME", "Adwaita")
hl.env("XCURSOR_SIZE", "20")
hl.env("HYPRCURSOR_THEME", "Adwaita")
hl.env("HYPRCURSOR_SIZE", "20")

-----------------------
---- LOOK AND FEEL ----
-----------------------
hl.config({
    general = {
        gaps_in  = 4,
        gaps_out = 8,
        border_size = 1,

        col = {
            active_border   = "rgba(aaaaaaff)",
            inactive_border = "rgba(333333aa)",
        },

        layout = "dwindle",
        resize_on_border = true,
        allow_tearing = false,
    },

    decoration = {
        rounding       = 8,
        active_opacity   = 0.98,
        inactive_opacity = 0.92,

        shadow = {
            enabled      = true,
            range        = 15,
            render_power = 2,
            color        = 0xaa0c0d10,
        },

        blur = {
            enabled   = true,
            size      = 5,
            passes    = 2,
            vibrancy  = 0.1696,
        },
    },

    animations = {
        enabled = true,
    },

    dwindle = {
        preserve_split = true,
        smart_split = false,
    },

    master = {
        new_status = "master",
    },

    misc = {
        force_default_wallpaper = 0,
        disable_hyprland_logo = true,
        disable_splash_rendering = true,
    },

    input = {
        kb_layout = "us",
        follow_mouse = 1,
        sensitivity = 0,

        touchpad = {
            natural_scroll = true,
        },
    },

    cursor = {
        no_hardware_cursors = false,
        sync_gsettings_theme = true,
        enable_hyprcursor = true,
    },

    xwayland = {
        force_zero_scaling = true,
    },
})

--------------------
---- ANIMATIONS ----
--------------------
hl.curve("easeOutQuint",   { type = "bezier", points = { {0.23, 1},    {0.32, 1} } })
hl.curve("easeInOutCubic", { type = "bezier", points = { {0.65, 0.05}, {0.36, 1} } })
hl.curve("linear",         { type = "bezier", points = { {0, 0},       {1, 1}    } })
hl.curve("almostLinear",   { type = "bezier", points = { {0.5, 0.5},   {0.75, 1} } })

hl.animation({ leaf = "windows",     enabled = true, speed = 3.5, bezier = "easeOutQuint" })
hl.animation({ leaf = "windowsIn",   enabled = true, speed = 3.5, bezier = "easeOutQuint" })
hl.animation({ leaf = "windowsOut",  enabled = true, speed = 3.0, bezier = "easeInOutCubic" })
hl.animation({ leaf = "windowsMove", enabled = true, speed = 3.5, bezier = "easeOutQuint" })
hl.animation({ leaf = "fadeIn",      enabled = true, speed = 2.5, bezier = "almostLinear" })
hl.animation({ leaf = "fadeOut",     enabled = true, speed = 2.5, bezier = "almostLinear" })
hl.animation({ leaf = "border",      enabled = true, speed = 4.0, bezier = "easeOutQuint" })
hl.animation({ leaf = "workspaces",  enabled = true, speed = 3.5, bezier = "easeOutQuint" })

---------------------
---- KEYBINDINGS ----
---------------------
local mainMod = "SUPER"
local scripts = homeDir .. "/.config/hypr/scripts"

-- 1. Application Launchers & Command Center
hl.bind(mainMod .. " + RETURN",         hl.dsp.exec_cmd(terminal))
hl.bind(mainMod .. " + SHIFT + RETURN", hl.dsp.exec_cmd("firefox"))
hl.bind(mainMod .. " + SPACE",          hl.dsp.exec_cmd(menu))
hl.bind(mainMod .. " + ALT + SPACE",    hl.dsp.exec_cmd(commandCenter))
hl.bind(mainMod .. " + C",              hl.dsp.exec_cmd(commandCenter))
hl.bind(mainMod .. " + SHIFT + F",      hl.dsp.exec_cmd(fileManager))
hl.bind(mainMod .. " + SHIFT + E",      hl.dsp.exec_cmd("code || kitty --config " .. homeDir .. "/.config/hypr/kitty/kitty.conf -e nano"))
hl.bind(mainMod .. " + SHIFT + T",      hl.dsp.exec_cmd("kitty --config " .. homeDir .. "/.config/hypr/kitty/kitty.conf -e btop"))
hl.bind(mainMod .. " + SHIFT + S",      hl.dsp.exec_cmd("kitty --config " .. homeDir .. "/.config/hypr/kitty/kitty.conf -e nmtui"))

-- 2. Window Management
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
hl.bind(mainMod .. " + equal", hl.dsp.exec_cmd("hyprctl dispatch resizeactive 30 30"),   { repeating = true })
hl.bind(mainMod .. " + minus", hl.dsp.exec_cmd("hyprctl dispatch resizeactive -30 -30"), { repeating = true })

-- Mouse Window Manipulation
hl.bind(mainMod .. " + mouse:272", hl.dsp.window.drag(),   { mouse = true })
hl.bind(mainMod .. " + mouse:273", hl.dsp.window.resize(), { mouse = true })

-- 3. Workspace Management
for i = 1, 5 do
    hl.bind(mainMod .. " + " .. i,               hl.dsp.focus({ workspace = i }))
    hl.bind(mainMod .. " + SHIFT + " .. i,       hl.dsp.window.move({ workspace = i }))
    hl.bind(mainMod .. " + SHIFT + ALT + " .. i, hl.dsp.exec_cmd("hyprctl dispatch movetoworkspacesilent " .. i))
end

-- Workspace Navigation
hl.bind(mainMod .. " + TAB",         hl.dsp.focus({ workspace = "e+1" }))
hl.bind(mainMod .. " + SHIFT + TAB", hl.dsp.focus({ workspace = "e-1" }))
hl.bind(mainMod .. " + CTRL + TAB",  hl.dsp.focus({ workspace = "previous" }))
hl.bind(mainMod .. " + mouse_down",  hl.dsp.focus({ workspace = "e+1" }))
hl.bind(mainMod .. " + mouse_up",    hl.dsp.focus({ workspace = "e-1" }))

-- 4. System Controls & Session
hl.bind(mainMod .. " + ESCAPE",           hl.dsp.exec_cmd(scripts .. "/power-menu.sh"))
hl.bind(mainMod .. " + CTRL + L",         hl.dsp.exec_cmd(lockscreen))
hl.bind(mainMod .. " + L",                hl.dsp.exec_cmd(lockscreen))
hl.bind(mainMod .. " + SHIFT + R",        hl.dsp.exec_cmd(scripts .. "/restart-waybar.sh && hyprctl reload"))
hl.bind(mainMod .. " + CTRL + A",         hl.dsp.exec_cmd("pavucontrol"))
hl.bind(mainMod .. " + SHIFT + D",        hl.dsp.exec_cmd(scripts .. "/notification-toggle.sh"))
hl.bind(mainMod .. " + CTRL + N",         hl.dsp.exec_cmd(scripts .. "/notification-history.sh"))
hl.bind(mainMod .. " + N",                hl.dsp.exec_cmd("dunstctl history-pop"))
hl.bind(mainMod .. " + SHIFT + N",        hl.dsp.exec_cmd("dunstctl close-all"))

-- 5. Productivity & Capture
hl.bind(mainMod .. " + K",                  hl.dsp.exec_cmd(scripts .. "/keybindings-menu.sh"))
hl.bind(mainMod .. " + SHIFT + K",          hl.dsp.exec_cmd(scripts .. "/keybindings-window.sh"))
hl.bind(mainMod .. " + CTRL + W",           hl.dsp.exec_cmd(scripts .. "/wallpaper-selector.sh"))
hl.bind(mainMod .. " + CTRL + SPACE",       hl.dsp.exec_cmd(scripts .. "/wallpaper-selector.sh"))
hl.bind(mainMod .. " + CTRL + V",           hl.dsp.exec_cmd(scripts .. "/clipboard-menu.sh"))
hl.bind(mainMod .. " + CTRL + SHIFT + V",   hl.dsp.exec_cmd(scripts .. "/clipboard-clear.sh"))
hl.bind("Print",                            hl.dsp.exec_cmd(scripts .. "/screenshot.sh region"))
hl.bind(mainMod .. " + Print",              hl.dsp.exec_cmd(scripts .. "/screenshot.sh full"))
hl.bind(mainMod .. " + CTRL + C",           hl.dsp.exec_cmd(scripts .. "/screenshot.sh menu"))

-- 6. Hardware & Multimedia Controls
-- Volume (Normal 5% / Fine 1% on Alt)
hl.bind("XF86AudioRaiseVolume",       hl.dsp.exec_cmd(scripts .. "/volume.sh up 5"),   { locked = true, repeating = true })
hl.bind("XF86AudioLowerVolume",       hl.dsp.exec_cmd(scripts .. "/volume.sh down 5"), { locked = true, repeating = true })
hl.bind("ALT + XF86AudioRaiseVolume", hl.dsp.exec_cmd(scripts .. "/volume.sh up 1"),   { locked = true, repeating = true })
hl.bind("ALT + XF86AudioLowerVolume", hl.dsp.exec_cmd(scripts .. "/volume.sh down 1"), { locked = true, repeating = true })
hl.bind("XF86AudioMute",              hl.dsp.exec_cmd(scripts .. "/volume.sh mute"),   { locked = true, repeating = true })
hl.bind("XF86AudioMicMute",           hl.dsp.exec_cmd(scripts .. "/volume.sh mic"),    { locked = true, repeating = true })

-- Brightness (Normal 5% / Fine 1% on Alt / Min-Max on Shift)
hl.bind("XF86MonBrightnessUp",         hl.dsp.exec_cmd(scripts .. "/brightness.sh up 5"),   { locked = true, repeating = true })
hl.bind("XF86MonBrightnessDown",       hl.dsp.exec_cmd(scripts .. "/brightness.sh down 5"), { locked = true, repeating = true })
hl.bind("ALT + XF86MonBrightnessUp",   hl.dsp.exec_cmd(scripts .. "/brightness.sh up 1"),   { locked = true, repeating = true })
hl.bind("ALT + XF86MonBrightnessDown", hl.dsp.exec_cmd(scripts .. "/brightness.sh down 1"), { locked = true, repeating = true })
hl.bind("SHIFT + XF86MonBrightnessUp",   hl.dsp.exec_cmd(scripts .. "/brightness.sh max"),  { locked = true, repeating = true })
hl.bind("SHIFT + XF86MonBrightnessDown", hl.dsp.exec_cmd(scripts .. "/brightness.sh min"),  { locked = true, repeating = true })

----------------------
---- WINDOW RULES ----
----------------------
hl.window_rule({
    name = "suppress-maximize-events",
    match = { class = ".*" },
    suppress_event = "maximize",
})

hl.window_rule({
    name = "float-pavucontrol",
    match = { class = "pavucontrol" },
    float = true,
})

hl.window_rule({
    name = "float-nm-connection-editor",
    match = { class = "nm-connection-editor" },
    float = true,
})

hl.window_rule({
    name = "float-dialogs",
    match = { title = "Open File" },
    float = true,
})

hl.window_rule({
    name = "float-hypr-keybindings",
    match = { class = "hypr-keybindings" },
    float = true,
})
