#!/usr/bin/env bash
# =====================================================================
# Configure btop for transparency and minimal dark rice theme
# =====================================================================

BTOP_DIR="${HOME}/.config/btop"
mkdir -p "${BTOP_DIR}"

cat << 'EOF' > "${BTOP_DIR}/btop.conf"
# =====================================================================
# btop Configuration — Minimal Dark Transparent Rice
# =====================================================================

# Color theme (matches rice dark palette)
color_theme = "adwaita-dark"

# Disable solid theme background so terminal transparency shines through
theme_background = False

# Enable 24-bit truecolor
truecolor = True

# UI Styling
rounded_corners = True
graph_symbol = "braille"
presets = "cpu:1:default,proc:0:default cpu:0:default,mem:0:default,net:0:default cpu:0:block,net:0:tty"

# Performance update interval in milliseconds
update_ms = 1500

# Process sorting & tree view
proc_sorting = "cpu lazy"
proc_reversed = False
proc_tree = False
proc_colors = True
proc_gradient = True
proc_per_core = False
proc_mem_bytes = True
proc_cpu_graphs = True
proc_info_kernel = False

# CPU box settings
cpu_bottom = False
cpu_single_graph = False
show_uptime = True
check_temp = True
cpu_sensor = "Auto"
show_coretemp = True
cpu_core_map = ""
temp_scale = "celsius"
show_cpu_freq = True

# Memory box
mem_graphs = True
mem_below_net = False
zfs_arc_cached = True
show_swap = True
swap_disk = True
show_disks = True
only_physical = True
use_fstab = True
show_io_stat = True
io_mode = False
io_graph_combined = False
io_graph_percent = False

# Net box
net_download = 100
net_upload = 100
net_auto = True
net_sync = True
net_iface = ""

# Base box sizes
base_10_sizes = False
show_battery = True
selected_battery = "Auto"
show_battery_watts = True
EOF

echo "btop transparent configuration generated at ${BTOP_DIR}/btop.conf"
