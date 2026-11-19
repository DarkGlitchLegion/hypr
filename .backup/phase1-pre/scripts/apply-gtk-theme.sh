#!/usr/bin/env bash
# =====================================================================
# Apply Minimal Dark GTK Theme for Thunar & Desktop Applications
# Palette: Charcoal #0C0D10 | Surface #17191F | Slate #202126 | Accent #AAAAAA
# =====================================================================

GTK3_DIR="${HOME}/.config/gtk-3.0"
GTK4_DIR="${HOME}/.config/gtk-4.0"

mkdir -p "${GTK3_DIR}" "${GTK4_DIR}"

# 1. SETTINGS.INI (GTK3 & GTK4)
cat << 'EOF' > "${GTK3_DIR}/settings.ini"
[Settings]
gtk-theme-name=Adwaita-dark
gtk-icon-theme-name=Papirus-Dark
gtk-font-name=JetBrainsMono Nerd Font 10
gtk-cursor-theme-name=Adwaita
gtk-cursor-theme-size=20
gtk-toolbar-style=GTK_TOOLBAR_BOTH_HORIZ
gtk-toolbar-icon-size=GTK_ICON_SIZE_LARGE_TOOLBAR
gtk-button-images=1
gtk-menu-images=1
gtk-enable-event-sounds=0
gtk-enable-input-feedback-sounds=0
gtk-xft-antialias=1
gtk-xft-hinting=1
gtk-xft-hintstyle=hintslight
gtk-xft-rgba=rgb
gtk-application-prefer-dark-theme=1
EOF

cp "${GTK3_DIR}/settings.ini" "${GTK4_DIR}/settings.ini"

# 2. GTK.CSS (Custom Charcoal & Accent Styling for Thunar & GTK Apps)
cat << 'EOF' > "${GTK3_DIR}/gtk.css"
/* =====================================================================
 * Minimalist Dark Theme for GTK3 & Thunar
 * Palette: Charcoal #0C0D10 | Surface #17191F | Slate #202126
 * Accent: #AAAAAA | Foreground: #D5D5D5 | Border: #333333
 * ===================================================================== */

@define-color theme_bg_color #0C0D10;
@define-color theme_fg_color #D5D5D5;
@define-color theme_base_color #0C0D10;
@define-color theme_text_color #D5D5D5;
@define-color theme_selected_bg_color #202126;
@define-color theme_selected_fg_color #FFFFFF;
@define-color insensitive_bg_color #17191F;
@define-color insensitive_fg_color #666666;
@define-color insensitive_base_color #0C0D10;
@define-color theme_unfocused_bg_color #0C0D10;
@define-color theme_unfocused_fg_color #888888;
@define-color theme_unfocused_base_color #0C0D10;
@define-color theme_unfocused_selected_bg_color #202126;
@define-color theme_unfocused_selected_fg_color #D5D5D5;
@define-color borders #333333;
@define-color unfocused_borders #202126;
@define-color warning_color #EBCB8B;
@define-color error_color #BF616A;
@define-color success_color #A3BE8C;

/* Window Background */
window,
.background {
    background-color: #0C0D10;
    color: #D5D5D5;
}

/* Headerbar & Main Toolbars */
headerbar,
toolbar,
.toolbar {
    background-color: #17191F;
    border-bottom: 1px solid #333333;
    color: #D5D5D5;
}

headerbar .title,
headerbar label {
    color: #D5D5D5;
    font-weight: bold;
}

/* Thunar Window Container */
.thunar,
window.thunar {
    background-color: #0C0D10;
    color: #D5D5D5;
}

/* Thunar Sidebar (Shortcuts & Folder Tree) */
.thunar .sidebar,
.thunar .sidebar treeview,
.thunar .sidebar .view,
treeview.sidebar {
    background-color: #17191F;
    color: #888888;
    border-right: 1px solid #202126;
}

.thunar .sidebar treeview:hover,
.thunar .sidebar .view:hover {
    color: #D5D5D5;
}

.thunar .sidebar treeview:selected,
.thunar .sidebar .view:selected,
.thunar .sidebar row:selected {
    background-color: #202126;
    color: #FFFFFF;
    border-left: 2px solid #AAAAAA;
}

/* Thunar Main File Grid & Detailed View */
.thunar .view,
.thunar treeview,
.thunar iconview,
ThunarIconView,
ThunarStandardView {
    background-color: #0C0D10;
    color: #D5D5D5;
}

/* Selected Items in Main View */
.thunar .view:selected,
.thunar treeview:selected,
.thunar iconview:selected,
.thunar .view row:selected {
    background-color: #202126;
    color: #FFFFFF;
    border: 1px solid #AAAAAA;
    border-radius: 4px;
}

/* Path Bar & Breadcrumbs */
.thunar path-bar button,
.thunar .path-bar button,
path-bar button {
    background-color: #202126;
    color: #D5D5D5;
    border: 1px solid #333333;
    border-radius: 4px;
    padding: 3px 8px;
    margin: 2px;
}

.thunar path-bar button:hover,
path-bar button:hover {
    background-color: #333333;
    color: #FFFFFF;
    border-color: #AAAAAA;
}

.thunar path-bar button:checked,
path-bar button:checked {
    background-color: #AAAAAA;
    color: #0C0D10;
    font-weight: bold;
}

/* Text Inputs & Search Bars */
entry,
.entry {
    background-color: #17191F;
    color: #D5D5D5;
    border: 1px solid #333333;
    border-radius: 6px;
    padding: 4px 8px;
}

entry:focus,
.entry:focus {
    border-color: #AAAAAA;
    background-color: #202126;
}

/* Action Buttons */
button {
    background-color: #17191F;
    color: #D5D5D5;
    border: 1px solid #202126;
    border-radius: 4px;
    padding: 4px 8px;
}

button:hover {
    background-color: #202126;
    border-color: #333333;
    color: #FFFFFF;
}

button:active,
button:checked {
    background-color: #AAAAAA;
    color: #0C0D10;
}

/* Statusbar */
statusbar,
.thunar statusbar {
    background-color: #17191F;
    border-top: 1px solid #202126;
    color: #888888;
    font-size: 11px;
}

/* Scrollbars */
scrollbar {
    background-color: transparent;
}

scrollbar slider {
    background-color: #202126;
    border-radius: 4px;
    min-width: 6px;
    min-height: 6px;
    border: 1px solid #333333;
}

scrollbar slider:hover {
    background-color: #AAAAAA;
}

scrollbar slider:active {
    background-color: #D5D5D5;
}

/* Separators */
separator {
    background-color: #202126;
    min-width: 1px;
    min-height: 1px;
}

/* Popovers & Context Menus */
popover,
menu,
.menu {
    background-color: #17191F;
    border: 1px solid #333333;
    border-radius: 6px;
    padding: 4px;
    color: #D5D5D5;
}

menuitem,
.menuitem {
    padding: 4px 8px;
    border-radius: 4px;
}

menuitem:hover,
.menuitem:hover {
    background-color: #202126;
    color: #FFFFFF;
}
EOF

cp "${GTK3_DIR}/gtk.css" "${GTK4_DIR}/gtk.css"

# 3. GSETTINGS DESKTOP INTERFACE
if command -v gsettings >/dev/null 2>&1; then
    gsettings set org.gnome.desktop.interface gtk-theme 'Adwaita-dark' 2>/dev/null || true
    gsettings set org.gnome.desktop.interface color-scheme 'prefer-dark' 2>/dev/null || true
    gsettings set org.gnome.desktop.interface icon-theme 'Papirus-Dark' 2>/dev/null || true
    gsettings set org.gnome.desktop.interface font-name 'JetBrainsMono Nerd Font 10' 2>/dev/null || true
    gsettings set org.gnome.desktop.interface cursor-theme 'Adwaita' 2>/dev/null || true
    gsettings set org.gnome.desktop.interface cursor-size 20 2>/dev/null || true
fi

echo "Minimal dark GTK theme configured for Thunar and desktop applications."
