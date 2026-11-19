-- =====================================================
-- Arch Linux Hyprland Rice — Environment Variables
-- Engine: Hyprland Lua Configuration (v0.57.2+)
-- =====================================================

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
