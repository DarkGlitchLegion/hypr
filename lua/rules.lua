-- =====================================================
-- Arch Linux Hyprland Rice — Window & Layer Rules
-- Engine: Hyprland Lua Configuration (v0.57.2+)
-- =====================================================

-- 1. Global Event & Idle Rules
hl.window_rule({
    name = "suppress-maximize-events",
    match = { class = ".*" },
    suppress_event = "maximize",
})

hl.window_rule({
    name = "idle-inhibit-fullscreen",
    match = { class = ".*" },
    idle_inhibit = "fullscreen",
})

-- 2. Floating Dialogs & Utility Windows
hl.window_rule({
    name = "float-pavucontrol",
    match = { class = "pavucontrol" },
    float = true,
    size = { 700, 500 },
    center = true,
})

hl.window_rule({
    name = "float-nm-connection-editor",
    match = { class = "nm-connection-editor" },
    float = true,
})

hl.window_rule({
    name = "float-blueman-manager",
    match = { class = "blueman-manager" },
    float = true,
})

hl.window_rule({
    name = "float-hypr-keybindings",
    match = { class = "hypr-keybindings" },
    float = true,
    size = { 860, 620 },
    center = true,
})

hl.window_rule({
    name = "float-thunar-progress",
    match = { class = "thunar", title = "File Operation Progress" },
    float = true,
})

hl.window_rule({
    name = "float-thunar-confirm",
    match = { class = "thunar", title = "Confirm to replace files" },
    float = true,
})

hl.window_rule({
    name = "float-dialog-open",
    match = { title = "Open File" },
    float = true,
})

hl.window_rule({
    name = "float-dialog-save",
    match = { title = "Save File" },
    float = true,
})

hl.window_rule({
    name = "float-dialog-choose",
    match = { title = "Choose Files" },
    float = true,
})

hl.window_rule({
    name = "float-dialog-branch",
    match = { title = "branchdialog" },
    float = true,
})

-- 3. Application Opacity Customizations
hl.window_rule({
    name = "opacity-kitty",
    match = { class = "kitty" },
    opacity = "0.96 0.90",
})

hl.window_rule({
    name = "opacity-thunar",
    match = { class = "thunar" },
    opacity = "0.98 0.92",
})

hl.window_rule({
    name = "transparent-btop-class",
    match = { class = "btop" },
    opacity = "0.82 0.75",
})

hl.window_rule({
    name = "transparent-btop-title",
    match = { title = "btop" },
    opacity = "0.82 0.75",
})

hl.window_rule({
    name = "transparent-cmatrix-class",
    match = { class = "cmatrix" },
    opacity = "0.75 0.70",
})

hl.window_rule({
    name = "transparent-cmatrix-title",
    match = { title = "cmatrix" },
    opacity = "0.75 0.70",
})

-- 4. Layer Blur Rules (Waybar, Rofi, Notifications)
hl.layer_rule({
    name = "blur-waybar",
    match = { namespace = "waybar" },
    blur = true,
    ignore_alpha = 0.1,
})

hl.layer_rule({
    name = "blur-rofi",
    match = { namespace = "rofi" },
    blur = true,
    ignore_alpha = 0.1,
})

hl.layer_rule({
    name = "blur-notifications",
    match = { namespace = "notifications" },
    blur = true,
    ignore_alpha = 0.1,
})

hl.layer_rule({
    name = "blur-dunst",
    match = { namespace = "dunst" },
    blur = true,
    ignore_alpha = 0.1,
})
