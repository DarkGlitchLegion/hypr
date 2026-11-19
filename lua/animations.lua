-- =====================================================
-- Arch Linux Hyprland Rice — Animations Configuration
-- Engine: Hyprland Lua Configuration (v0.57.2+)
-- =====================================================

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
