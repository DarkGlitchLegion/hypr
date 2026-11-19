-- =====================================================
-- Arch Linux Hyprland Rice — Appearance & Compositor Settings
-- Engine: Hyprland Lua Configuration (v0.57.2+)
-- Palette: Charcoal #0C0D10 | Slate #17191F | Accent #AAAAAA
-- =====================================================

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
