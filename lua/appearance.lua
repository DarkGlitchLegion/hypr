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
        rounding         = 10,       -- slightly rounder, closer to macOS 11+ window corners
        active_opacity   = 0.98,
        inactive_opacity = 0.92,

        -- macOS-quality drop shadow: soft, deep, offset slightly downward
        shadow = {
            enabled      = true,
            range        = 24,       -- larger penumbra like macOS shadows
            render_power = 3,        -- smoother gradient falloff
            color        = "rgba(0c0d10cc)",   -- #0C0D10 at ~80% — dark charcoal
            offset       = "0 4",    -- subtle downward cast matching macOS light model
        },

        -- Enhanced blur: vivid, layered, low noise — matches macOS vibrancy feel
        blur = {
            enabled        = true,
            size           = 8,      -- larger kernel for smoother frosted-glass look
            passes         = 3,      -- extra pass adds depth without banding
            vibrancy       = 0.20,   -- slightly richer colour pop behind translucent surfaces
            vibrancy_darkness = 0.1,
            noise          = 0.012,  -- fine grain exactly like macOS material noise
            contrast       = 1.05,   -- marginal contrast lift keeps dark palette punchy
            brightness     = 0.95,   -- slight dim so blurred content doesn't wash out
            new_optimizations = true,
            xray           = false,
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
        force_default_wallpaper    = 0,
        disable_hyprland_logo      = true,
        disable_splash_rendering   = true,
        -- Animate window content while resizing (macOS live-resize feel)
        animate_manual_resizes     = true,
        -- Smooth mouse-driven moves
        animate_mouse_windowdragging = true,
        -- Snap focus change to monitor (prevents ghost trails on quick WS switches)
        focus_on_activate          = false,
        -- VFX cursor warping only within current workspace
        mouse_move_enables_dpms    = true,
        -- Prevent flicker when a fullscreen app starts
        enable_swallow             = false,
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
