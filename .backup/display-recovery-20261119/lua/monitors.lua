-- =====================================================
-- Arch Linux Hyprland Rice — Monitors Configuration
-- Engine: Hyprland Lua Configuration (v0.57.2+)
-- =====================================================

-- 100% native unscaled display (prevents oversized fractional upscaling on 1080p)
hl.monitor({
    output   = "",
    mode     = "preferred",
    position = "auto",
    scale    = 1,
})
