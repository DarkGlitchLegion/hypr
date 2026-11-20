#!/usr/bin/env python3
"""
Quick Settings Popup for Hyprland
GNOME-inspired, dark, rounded, minimalist.
Uses GTK3 + gtk-layer-shell for proper Wayland overlay positioning.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import GLib, Gtk, GtkLayerShell, Pango  # noqa: E402

# ── Paths ──────────────────────────────────────────────────────────────────────
HOME = Path.home()
SCRIPTS = HOME / ".config" / "hypr" / "scripts"
LOCK_FILE = Path(tempfile.gettempdir()) / "hypr-quick-settings.lock"

# ── Colour palette (matches existing rice) ────────────────────────────────────
CSS = """
* {
    font-family: "JetBrainsMono Nerd Font", monospace;
    font-size: 11px;
    font-weight: 500;
}

window {
    background: transparent;
}

#qs-root {
    background-color: rgba(12, 13, 16, 0.96);
    border: 1px solid #2a2b30;
    border-radius: 12px;
    padding: 14px;
    min-width: 320px;
}

/* ── Section headers ── */
.section-label {
    font-size: 10px;
    font-weight: 700;
    color: #555560;
    letter-spacing: 1px;
    margin-top: 10px;
    margin-bottom: 4px;
    padding-left: 2px;
}

/* ── Toggle rows ── */
.toggle-row {
    background-color: #17191F;
    border: 1px solid #202126;
    border-radius: 8px;
    padding: 6px 10px;
    margin: 2px 0;
    transition: all 0.15s ease;
}

.toggle-row:hover {
    background-color: #202126;
    border-color: #333340;
}

.toggle-label {
    color: #D5D5D5;
    font-size: 11px;
}

.toggle-sub {
    color: #666672;
    font-size: 10px;
}

/* ── GTK Switch ── */
switch {
    min-height: 18px;
    min-width: 36px;
    border-radius: 9px;
    background-color: #333340;
    border: none;
    outline: none;
    box-shadow: none;
    transition: background-color 0.2s ease;
}

switch:checked {
    background-color: #AAAAAA;
}

switch slider {
    min-height: 14px;
    min-width: 14px;
    border-radius: 7px;
    background-color: #D5D5D5;
    border: none;
    box-shadow: none;
    margin: 2px;
}

switch:checked slider {
    background-color: #0C0D10;
}

/* ── Sliders ── */
.slider-row {
    padding: 4px 10px;
    margin: 2px 0;
}

.slider-icon {
    color: #888888;
    font-size: 13px;
    min-width: 20px;
}

scale {
    min-height: 20px;
}

scale trough {
    background-color: #202126;
    border-radius: 4px;
    min-height: 4px;
}

scale trough highlight {
    background-color: #AAAAAA;
    border-radius: 4px;
}

scale slider {
    background-color: #D5D5D5;
    border-radius: 50%;
    min-height: 14px;
    min-width: 14px;
    border: none;
    box-shadow: none;
    margin: -5px;
    transition: background-color 0.1s ease;
}

scale slider:hover {
    background-color: #FFFFFF;
}

/* ── Stat tiles ── */
.stat-grid {
    margin: 4px 0;
}

.stat-tile {
    background-color: #17191F;
    border: 1px solid #202126;
    border-radius: 8px;
    padding: 8px 10px;
    margin: 2px;
    min-width: 70px;
    transition: all 0.15s ease;
}

.stat-tile:hover {
    background-color: #202126;
    border-color: #333340;
}

.stat-icon {
    color: #AAAAAA;
    font-size: 14px;
    font-weight: 400;
}

.stat-value {
    color: #D5D5D5;
    font-size: 12px;
    font-weight: 600;
}

.stat-name {
    color: #555560;
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 0.5px;
}

/* ── Action buttons ── */
button.action-btn {
    background-image: none;
    background-color: #17191F;
    border: 1px solid #202126;
    border-radius: 8px;
    color: #D5D5D5;
    font-size: 11px;
    padding: 8px 10px;
    margin: 2px;
    transition: all 0.15s ease;
    outline: none;
    box-shadow: none;
}

button.action-btn label.action-label {
    color: #D5D5D5;
}

.action-icon {
    color: #AAAAAA;
    font-size: 14px;
}

button.action-btn:hover {
    background-image: none;
    background-color: #202126;
    border-color: #333340;
}

button.action-btn:hover label.action-label {
    color: #D5D5D5;
}

button.action-btn:active {
    background-image: none;
    background-color: #202126;
}

/* ── Security badge ── */
.sec-running {
    color: #A3BE8C;
}

.sec-stopped {
    color: #888888;
}

.sec-unavailable {
    color: #BF616A;
}

/* ── Divider ── */
.qs-divider {
    background-color: #202126;
    min-height: 1px;
    margin: 8px 0;
}

/* ── Clock in header ── */
.qs-clock {
    color: #D5D5D5;
    font-size: 20px;
    font-weight: 600;
}

.qs-date {
    color: #666672;
    font-size: 10px;
}
"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def run_bg(cmd: list[str]) -> None:
    """Fire-and-forget a shell command (non-blocking)."""
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)


def run_out(cmd: list[str], timeout: float = 2.0) -> str:
    """Run a command and return stdout, or '' on failure."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception:
        return ""


def refresh_waybar() -> None:
    subprocess.run(
        ["pkill", "-RTMIN+7", "waybar"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def _read_sys(path: str) -> Optional[str]:
    try:
        return Path(path).read_text().strip()
    except Exception:
        return None


# ── System data ───────────────────────────────────────────────────────────────

def get_cpu_usage() -> int:
    try:
        import psutil
        return int(psutil.cpu_percent(interval=0.3))
    except Exception:
        return 0


def get_ram_usage() -> tuple[int, float, float]:
    """Returns (percent, used_GiB, total_GiB)."""
    try:
        import psutil
        m = psutil.virtual_memory()
        return int(m.percent), m.used / 1e9, m.total / 1e9
    except Exception:
        return 0, 0.0, 0.0


def get_cpu_temp() -> Optional[float]:
    """Read AMD k10temp Tctl (°C)."""
    # hwmon5 = k10temp on this machine; walk to be safe
    for hw in Path("/sys/class/hwmon").glob("hwmon*"):
        name = _read_sys(str(hw / "name"))
        if name and "k10temp" in name:
            raw = _read_sys(str(hw / "temp1_input"))
            if raw and raw.isdigit():
                return float(raw) / 1000.0
    return None


def get_gpu_temp() -> Optional[float]:
    """Read amdgpu edge temp (°C)."""
    for hw in Path("/sys/class/hwmon").glob("hwmon*"):
        name = _read_sys(str(hw / "name"))
        if name and "amdgpu" in name:
            raw = _read_sys(str(hw / "temp1_input"))
            if raw and raw.isdigit():
                return float(raw) / 1000.0
    return None


def get_battery() -> dict:
    import glob
    bats = glob.glob("/sys/class/power_supply/BAT*")
    if not bats:
        return {"present": False}
    b = bats[0]
    cap = int(_read_sys(f"{b}/capacity") or 0)
    status = _read_sys(f"{b}/status") or "Unknown"
    p_now = _read_sys(f"{b}/power_now")
    watts = None
    if p_now and p_now.isdigit():
        watts = float(p_now) / 1_000_000.0
    # Health
    e_full = _read_sys(f"{b}/energy_full")
    e_design = _read_sys(f"{b}/energy_full_design")
    health = None
    if e_full and e_design and e_full.isdigit() and e_design.isdigit() and int(e_design) > 0:
        health = (float(e_full) / float(e_design)) * 100.0
    return {
        "present": True,
        "capacity": cap,
        "status": status,
        "watts": watts,
        "health": health,
    }


def get_volume() -> tuple[int, bool]:
    """Returns (volume_percent, is_muted)."""
    out = run_out(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"])
    if not out:
        return 0, False
    parts = out.split()
    vol = int(float(parts[1]) * 100) if len(parts) >= 2 else 0
    muted = "[MUTED]" in out
    return vol, muted


def get_mic_muted() -> bool:
    out = run_out(["wpctl", "get-volume", "@DEFAULT_AUDIO_SOURCE@"])
    return "[MUTED]" in out


def get_brightness() -> int:
    out = run_out(["brightnessctl", "-m"])
    if out:
        parts = out.split(",")
        if len(parts) >= 4:
            pct = parts[3].rstrip("%")
            try:
                return int(pct)
            except ValueError:
                pass
    return 50


def get_network() -> dict:
    wifi_enabled = run_out(["nmcli", "radio", "wifi"], timeout=3) == "enabled"
    out = run_out(["nmcli", "-t", "-f", "ACTIVE,SSID,SIGNAL", "dev", "wifi"], timeout=3)
    if wifi_enabled:
        for line in out.splitlines():
            parts = line.split(":")
            if len(parts) >= 3 and parts[0] == "yes":
                ssid = parts[1]
                sig = parts[2] if len(parts) > 2 else "?"
                return {
                    "enabled": True,
                    "connected": True,
                    "ssid": ssid,
                    "signal": sig,
                }
    return {
        "enabled": wifi_enabled,
        "connected": False,
        "ssid": "",
        "signal": "",
    }


def get_bluetooth() -> dict:
    out = run_out(["bluetoothctl", "show"], timeout=3)
    powered = "Powered: yes" in out
    if not powered:
        return {"powered": False, "connected": False, "device": ""}
    dev_out = run_out(["bluetoothctl", "devices", "Connected"], timeout=3)
    devices = [
        ln.partition(" ")[2].partition(" ")[2].strip()
        for ln in dev_out.splitlines()
        if ln.startswith("Device ")
    ]
    return {
        "powered": True,
        "connected": bool(devices),
        "device": devices[0] if devices else "",
    }


def get_dnd() -> bool:
    """True = DND on (paused)."""
    out = run_out(["dunstctl", "is-paused"])
    return out == "true"


def get_power_profile() -> str:
    return run_out(["powerprofilesctl", "get"]) or "balanced"


def get_hyprsec() -> dict:
    out = run_out(
        [str(SCRIPTS / "hyprsec-box.sh"), "waybar-status"], timeout=5
    )
    try:
        d = json.loads(out)
        return d
    except Exception:
        return {"text": "󰒃 Sec: unavailable", "class": "unavailable", "tooltip": ""}


# ── Quick Settings Window ─────────────────────────────────────────────────────

class QuickSettings(Gtk.Window):

    def __init__(self) -> None:
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self._closing = False

        # Apply CSS
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_screen(
            self.get_screen(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        # Layer shell configuration — anchor to top-right, below bar
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.TOP)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, True)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, 46)   # below 32px bar + 6+8 margin
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.RIGHT, 8)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.ON_DEMAND)
        GtkLayerShell.set_namespace(self, "hypr-quick-settings")

        self.set_decorated(False)
        self.set_resizable(False)
        self.set_app_paintable(True)

        # Transparent background support
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)

        # Connect events
        self.connect("key-press-event", self._on_key_press)
        self.connect("delete-event", self._on_close)

        # Build UI
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.set_name("qs-root")
        self.add(root)

        self._build_header(root)
        self._loading_label = Gtk.Label(label="Loading quick settings…")
        self._loading_label.set_margin_top(18)
        self._loading_label.set_margin_bottom(18)
        root.pack_start(self._loading_label, False, False, 0)
        self._status_widgets = {}
        self._updating_status = False
        self._refreshing = False
        self._stats_refresh_id = 0

        self.show_all()

        # Request focus so Escape works
        self.present()
        GLib.timeout_add(50, self._grab_focus)

        self._refresh_id = 0
        threading.Thread(target=self._load_panel_data, daemon=True).start()

    # ── Focus ──────────────────────────────────────────────────────────────

    def _grab_focus(self) -> bool:
        self.grab_focus()
        return False

    # ── Close ──────────────────────────────────────────────────────────────

    def _close(self) -> None:
        if self._closing:
            return
        self._closing = True
        if self._refresh_id:
            GLib.source_remove(self._refresh_id)
        if self._stats_refresh_id:
            GLib.source_remove(self._stats_refresh_id)
        LOCK_FILE.unlink(missing_ok=True)
        self.destroy()
        Gtk.main_quit()

    def _on_key_press(self, _widget, event) -> bool:
        from gi.repository import Gdk
        if event.keyval == Gdk.KEY_Escape:
            self._close()
            return True
        return False

    def _on_close(self, *_args) -> bool:
        self._close()
        return True

    def _load_panel_data(self) -> None:
        try:
            data = self._collect_panel_data()
        except Exception as exc:
            print(f"Failed to load quick settings: {exc}", file=sys.stderr)
            GLib.idle_add(self._show_load_error, str(exc))
            return

        GLib.idle_add(self._populate_panel, data)

    def _show_load_error(self, message: str) -> bool:
        if not self._closing:
            self._loading_label.set_text(f"Unable to load quick settings: {message}")
        return False

    def _populate_panel(self, data: dict) -> bool:
        if self._closing:
            return False

        root = self.get_child()
        root.remove(self._loading_label)
        self._add_divider(root)
        self._build_connectivity(root, data["network"], data["bluetooth"])
        self._add_divider(root)
        self._build_audio(root, data["volume"], data["mic_muted"],
                          data["brightness"], data["dnd"])
        self._add_divider(root)
        self._build_power(root, data["battery"], data["profile"])
        self._add_divider(root)
        self._build_system(root, data["cpu"], data["ram"], data["cpu_temp"],
                           data["gpu_temp"], data["security"])
        self._add_divider(root)
        self._build_actions(root)
        self.show_all()
        self._refresh_id = GLib.timeout_add_seconds(1, self._refresh_panel)
        self._stats_refresh_id = GLib.timeout_add_seconds(3, self._refresh_stats)
        return False

    # ── UI Helpers ─────────────────────────────────────────────────────────

    def _section_label(self, text: str) -> Gtk.Label:
        lbl = Gtk.Label(label=text, xalign=0)
        lbl.get_style_context().add_class("section-label")
        return lbl

    def _add_divider(self, parent: Gtk.Box) -> None:
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.get_style_context().add_class("qs-divider")
        parent.pack_start(sep, False, False, 0)

    def _toggle_row(self, icon: str, label: str, sublabel: str,
                    active: bool, on_toggle=None, on_click=None,
                    status_key: Optional[str] = None) -> Gtk.Box:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        row.get_style_context().add_class("toggle-row")

        icon_lbl = Gtk.Label(label=icon)
        icon_lbl.get_style_context().add_class("stat-icon")
        icon_lbl.set_xalign(0.5)
        icon_lbl.set_size_request(22, -1)

        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        main_lbl = Gtk.Label(label=label, xalign=0)
        main_lbl.get_style_context().add_class("toggle-label")
        text_box.pack_start(main_lbl, False, False, 0)
        if sublabel:
            sub_lbl = Gtk.Label(label=sublabel, xalign=0)
            sub_lbl.get_style_context().add_class("toggle-sub")
            sub_lbl.set_ellipsize(Pango.EllipsizeMode.END)
            sub_lbl.set_max_width_chars(28)
            text_box.pack_start(sub_lbl, False, False, 0)

        content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        content.pack_start(icon_lbl, False, False, 0)
        content.pack_start(text_box, True, True, 0)
        if on_click is not None:
            click_area = Gtk.EventBox()
            click_area.set_visible_window(False)
            click_area.add(content)
            click_area.connect(
                "button-press-event",
                lambda _widget, event: self._handle_row_click(on_click, event),
            )
            row.pack_start(click_area, True, True, 0)
        else:
            row.pack_start(content, True, True, 0)

        switch = None
        if on_toggle is not None:
            sw = Gtk.Switch()
            sw.set_active(active)
            sw.connect("notify::active", self._on_switch_changed, on_toggle)
            sw.set_valign(Gtk.Align.CENTER)
            row.pack_end(sw, False, False, 0)
            switch = sw

        if status_key is not None:
            self._status_widgets[status_key] = {
                "icon": icon_lbl,
                "label": main_lbl,
                "sublabel": sub_lbl if sublabel else None,
                "switch": switch,
            }

        return row

    def _handle_row_click(self, callback, event) -> bool:
        if event.button == 1:
            callback()
            return True
        return False

    def _on_switch_changed(self, switch, _property, callback) -> None:
        if not self._updating_status:
            callback(switch.get_active())

    def _slider_row(self, icon: str, value: int, on_change=None) -> Gtk.Box:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.get_style_context().add_class("slider-row")

        icon_lbl = Gtk.Label(label=icon)
        icon_lbl.get_style_context().add_class("slider-icon")
        row.pack_start(icon_lbl, False, False, 0)

        scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        scale.set_value(max(0, min(100, value)))
        scale.set_draw_value(False)
        scale.set_hexpand(True)
        if on_change:
            scale.connect("value-changed", lambda s: on_change(int(s.get_value())))
        row.pack_start(scale, True, True, 0)

        val_lbl = Gtk.Label(label=f"{value}%")
        val_lbl.get_style_context().add_class("toggle-sub")
        val_lbl.set_size_request(32, -1)
        val_lbl.set_xalign(1.0)
        row.pack_end(val_lbl, False, False, 0)

        self._vol_label = val_lbl  # may be overwritten; that's fine
        return row, scale, val_lbl  # type: ignore[return-value]

    # ── Header: Clock + Date ───────────────────────────────────────────────

    def _build_header(self, parent: Gtk.Box) -> None:
        hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)

        time_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._clock_lbl = Gtk.Label(xalign=0)
        self._clock_lbl.get_style_context().add_class("qs-clock")
        self._date_lbl = Gtk.Label(xalign=0)
        self._date_lbl.get_style_context().add_class("qs-date")
        time_box.pack_start(self._clock_lbl, False, False, 0)
        time_box.pack_start(self._date_lbl, False, False, 0)
        hdr.pack_start(time_box, True, True, 0)

        parent.pack_start(hdr, False, False, 0)
        self._update_clock()
        GLib.timeout_add_seconds(1, self._update_clock)

    def _update_clock(self) -> bool:
        now = time.strftime("%H:%M")
        date = time.strftime("%A, %B %-d")
        self._clock_lbl.set_text(now)
        self._date_lbl.set_text(date)
        return not self._closing

    # ── Connectivity ───────────────────────────────────────────────────────

    def _build_connectivity(self, parent: Gtk.Box, net: dict,
                            bt: dict) -> None:
        parent.pack_start(self._section_label("CONNECTIVITY"), False, False, 0)

        # Wi-Fi row
        if net["connected"]:
            wifi_sub = f"{net['ssid']}  {net['signal']}%" if net["signal"] else net["ssid"]
            wifi_icon = "󰤨"
        elif net["enabled"]:
            wifi_sub = "On · not connected"
            wifi_icon = "󰤨"
        else:
            wifi_sub = "Off"
            wifi_icon = "󰤭"

        wifi_row = self._toggle_row(
            wifi_icon, "Wi-Fi", wifi_sub, net["enabled"],
            on_toggle=self._toggle_wifi,
            on_click=lambda: self._launch(str(SCRIPTS / "wifi-menu.sh")),
            status_key="wifi",
        )
        wifi_row.set_tooltip_text("Click switch to toggle • Click label to manage networks")
        parent.pack_start(wifi_row, False, False, 0)

        # Bluetooth row
        if bt["connected"]:
            bt_icon = "󰂱"
            bt_sub = bt["device"] or "Connected"
        elif bt["powered"]:
            bt_icon = "󰂯"
            bt_sub = "On · no device connected"
        else:
            bt_icon = "󰂲"
            bt_sub = "Off"

        bt_row = self._toggle_row(
            bt_icon, "Bluetooth", bt_sub, bt["powered"],
            on_toggle=self._toggle_bluetooth,
            on_click=lambda: self._launch(str(SCRIPTS / "bluetooth-menu.sh")),
            status_key="bluetooth",
        )
        parent.pack_start(bt_row, False, False, 0)

    def _toggle_wifi(self, active: bool) -> None:
        def _do():
            if active:
                run_out(["nmcli", "radio", "wifi", "on"], timeout=4)
            else:
                run_out(["nmcli", "radio", "wifi", "off"], timeout=4)
            GLib.idle_add(self._refresh_live_status)
        threading.Thread(target=_do, daemon=True).start()

    def _toggle_bluetooth(self, active: bool) -> None:
        def _do():
            if active:
                subprocess.run(["rfkill", "unblock", "bluetooth"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                run_out(["bluetoothctl", "power", "on"], timeout=4)
            else:
                run_out(["bluetoothctl", "power", "off"], timeout=4)
            GLib.idle_add(self._refresh_live_status)
        threading.Thread(target=_do, daemon=True).start()

    # ── Audio ──────────────────────────────────────────────────────────────

    def _build_audio(self, parent: Gtk.Box, volume: tuple[int, bool],
                     mic_muted: bool, brightness: int, dnd: bool) -> None:
        parent.pack_start(self._section_label("AUDIO"), False, False, 0)

        vol, muted = volume

        # Volume slider
        vol_icon = "󰝟" if muted else ("󰕿" if vol < 33 else ("󰖀" if vol < 66 else "󰕾"))
        v_row, v_scale, v_lbl = self._slider_row(vol_icon, vol,
                                                   on_change=self._on_volume_change)
        self._vol_scale = v_scale
        self._vol_lbl_widget = v_lbl
        parent.pack_start(v_row, False, False, 0)

        # Mute + Mic row
        mute_row = self._toggle_row(
            "󰝟" if muted else "󰕾", "Speaker",
            "Muted" if muted else f"{vol}%",
            not muted, on_toggle=self._toggle_mute,
            on_click=lambda: self._launch(str(SCRIPTS / "audio-menu.sh")),
            status_key="speaker",
        )
        parent.pack_start(mute_row, False, False, 0)

        mic_row = self._toggle_row(
            "󰍭" if mic_muted else "󰍬", "Microphone",
            "Muted" if mic_muted else "Active",
            not mic_muted, on_toggle=self._toggle_mic,
            on_click=lambda: self._launch(str(SCRIPTS / "audio-menu.sh")),
            status_key="microphone",
        )
        parent.pack_start(mic_row, False, False, 0)

        # Brightness slider
        b_row, b_scale, b_lbl = self._slider_row("󰃞", brightness,
                                                   on_change=self._on_brightness_change)
        self._bri_scale = b_scale
        self._bri_lbl_widget = b_lbl
        b_row_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        bri_hdr = Gtk.Label(label="DISPLAY", xalign=0)
        bri_hdr.get_style_context().add_class("section-label")
        parent.pack_start(bri_hdr, False, False, 0)
        parent.pack_start(b_row, False, False, 0)

        # DND toggle
        dnd_row = self._toggle_row(
            "󰂛" if dnd else "󰂚", "Do Not Disturb",
            "Notifications silenced" if dnd else "Notifications active",
            dnd, on_toggle=self._toggle_dnd, status_key="dnd"
        )
        parent.pack_start(dnd_row, False, False, 0)

    def _on_volume_change(self, val: int) -> None:
        def _do():
            subprocess.run(
                ["wpctl", "set-volume", "-l", "1.5", "@DEFAULT_AUDIO_SINK@", f"{val}%"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            GLib.idle_add(refresh_waybar)
        self._vol_lbl_widget.set_text(f"{val}%")
        if self._updating_status:
            return
        threading.Thread(target=_do, daemon=True).start()

    def _on_brightness_change(self, val: int) -> None:
        def _do():
            subprocess.run(
                ["brightnessctl", "set", f"{max(1, val)}%"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        self._bri_lbl_widget.set_text(f"{val}%")
        if self._updating_status:
            return
        threading.Thread(target=_do, daemon=True).start()

    def _toggle_mute(self, active: bool) -> None:
        # active=True means unmuted → toggle to mute, vice versa
        def _do():
            subprocess.run(
                ["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            GLib.idle_add(refresh_waybar)
        threading.Thread(target=_do, daemon=True).start()
        GLib.timeout_add(200, self._refresh_live_status)

    def _toggle_mic(self, active: bool) -> None:
        def _do():
            subprocess.run(
                ["wpctl", "set-mute", "@DEFAULT_AUDIO_SOURCE@", "toggle"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            GLib.idle_add(refresh_waybar)
        threading.Thread(target=_do, daemon=True).start()
        GLib.timeout_add(200, self._refresh_live_status)

    def _toggle_dnd(self, active: bool) -> None:
        def _do():
            run_out(["dunstctl", "set-paused", "true" if active else "false"])
            subprocess.run(["pkill", "-RTMIN+8", "waybar"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            GLib.idle_add(self._refresh_live_status)
        threading.Thread(target=_do, daemon=True).start()

    # ── Power & Battery ────────────────────────────────────────────────────

    def _build_power(self, parent: Gtk.Box, bat: dict, profile: str) -> None:
        parent.pack_start(self._section_label("POWER & BATTERY"), False, False, 0)

        icon, bat_sub = self._battery_display(bat)

        bat_row = self._toggle_row(
            icon, "Battery", bat_sub, False,
            on_click=lambda: self._launch(str(SCRIPTS / "power-profile-menu.sh")),
            status_key="battery",
        )
        bat_row.set_tooltip_text("Click to open power profile menu")
        parent.pack_start(bat_row, False, False, 0)

        # Power profile row
        profile_icons = {"performance": "󰓅", "balanced": "󰾆", "power-saver": "󰌪"}
        profile_names = {"performance": "Performance", "balanced": "Balanced",
                         "power-saver": "Power Saver"}
        p_icon = profile_icons.get(profile, "󰾆")
        p_name = profile_names.get(profile, profile.capitalize())

        prof_row = self._toggle_row(
            p_icon, f"Profile: {p_name}", "Click to cycle", False,
            on_click=self._cycle_profile, status_key="profile",
        )
        parent.pack_start(prof_row, False, False, 0)

    def _cycle_profile(self) -> None:
        def _do():
            subprocess.run([str(SCRIPTS / "power-profile-menu.sh"), "cycle"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        threading.Thread(target=_do, daemon=True).start()

    # ── System Monitor tiles ───────────────────────────────────────────────

    def _build_system(self, parent: Gtk.Box, cpu: int,
                      ram: tuple[int, float, float],
                      cpu_t: Optional[float], gpu_t: Optional[float],
                      sec: dict) -> None:
        parent.pack_start(self._section_label("SYSTEM"), False, False, 0)

        grid = Gtk.FlowBox()
        grid.set_max_children_per_line(4)
        grid.set_min_children_per_line(4)
        grid.set_selection_mode(Gtk.SelectionMode.NONE)
        grid.set_homogeneous(True)
        grid.get_style_context().add_class("stat-grid")

        def _tile(icon: str, value: str, name: str, tooltip: str = "") -> Gtk.EventBox:
            eb = Gtk.EventBox()
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            box.get_style_context().add_class("stat-tile")
            ic = Gtk.Label(label=icon)
            ic.get_style_context().add_class("stat-icon")
            vl = Gtk.Label(label=value)
            vl.get_style_context().add_class("stat-value")
            nl = Gtk.Label(label=name)
            nl.get_style_context().add_class("stat-name")
            for w in [ic, vl, nl]:
                w.set_justify(Gtk.Justification.CENTER)
            box.pack_start(ic, False, False, 0)
            box.pack_start(vl, False, False, 0)
            box.pack_start(nl, False, False, 0)
            eb.add(box)
            if tooltip:
                eb.set_tooltip_text(tooltip)
            return eb

        ram_pct, ram_used, ram_total = ram

        cpu_tile = _tile("󰻠", f"{cpu}%", "CPU",
                          f"CPU: {cpu}%\nClick to open btop")
        cpu_tile.connect("button-press-event",
                         lambda w, e: self._open_btop())
        self._cpu_val = cpu_tile.get_child().get_children()[1]

        ram_str = f"{ram_pct}%"
        ram_tile = _tile("󰍛", ram_str, "RAM",
                          f"RAM: {ram_used:.1f} / {ram_total:.1f} GiB ({ram_pct}%)\nClick to open btop")
        ram_tile.connect("button-press-event", lambda w, e: self._open_btop())
        self._ram_val = ram_tile.get_child().get_children()[1]

        cpu_t_str = f"{cpu_t:.0f}°" if cpu_t else "N/A"
        cpu_t_tile = _tile("󰔄", cpu_t_str, "CPU °C", "AMD Tctl temperature")
        self._cput_val = cpu_t_tile.get_child().get_children()[1]

        gpu_t_str = f"{gpu_t:.0f}°" if gpu_t else "N/A"
        gpu_t_tile = _tile("󰍹", gpu_t_str, "GPU °C", "AMDGPU edge temperature")
        self._gput_val = gpu_t_tile.get_child().get_children()[1]

        for tile in [cpu_tile, ram_tile, cpu_t_tile, gpu_t_tile]:
            grid.add(tile)

        parent.pack_start(grid, False, False, 0)

        # Security row
        sec_text = sec.get("text", "󰒃 Sec")
        sec_class = sec.get("class", "unavailable")
        sec_tip = sec.get("tooltip", "")

        sec_row = Gtk.EventBox()
        sec_inner = self._toggle_row("󰒃", "HyprSec Container",
                                      sec_text.replace("󰒃 ", "").strip(),
                                      False, on_toggle=None)
        sec_row.add(sec_inner)
        sec_row.set_tooltip_text(sec_tip or sec_text)
        sec_row.connect("button-press-event",
                        lambda w, e: self._launch(str(SCRIPTS / "hyprsec-box.sh"), "menu")
                        if e.button == 1 else None)
        # Colour the sublabel based on class
        # (the label is the 3rd child: icon_lbl, text_box, [switch])
        # We style it after build
        parent.pack_start(sec_row, False, False, 0)

    def _open_btop(self) -> None:
        self._launch("kitty", "--class", "btop", "--title", "btop",
                     "--config", str(HOME / ".config/hypr/kitty/kitty.conf"),
                     "-e", "btop")

    # ── Action buttons ─────────────────────────────────────────────────────

    def _build_actions(self, parent: Gtk.Box) -> None:
        parent.pack_start(self._section_label("ACTIONS"), False, False, 0)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)

        actions = [
            ("󰌾", "Lock", self._lock),
            ("󰤄", "Sleep", self._sleep),
            ("󰑓", "Wi-Fi", lambda: self._launch(str(SCRIPTS / "wifi-menu.sh"))),
            ("󰂯", "BT", lambda: self._launch(str(SCRIPTS / "bluetooth-menu.sh"))),
            ("󰐥", "Power", lambda: self._launch(str(SCRIPTS / "power-menu.sh"))),
        ]

        for icon, label, cb in actions:
            btn_content = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL, spacing=3
            )
            icon_label = Gtk.Label(label=icon)
            icon_label.get_style_context().add_class("action-icon")
            text_label = Gtk.Label(label=label)
            text_label.get_style_context().add_class("action-label")
            btn_content.pack_start(icon_label, False, False, 0)
            btn_content.pack_start(text_label, False, False, 0)

            btn = Gtk.Button()
            btn.add(btn_content)
            btn.get_style_context().add_class("action-btn")
            btn.connect("clicked", lambda _, c=cb: (self._close(), c()))
            btn_box.pack_start(btn, True, True, 0)

        parent.pack_start(btn_box, False, False, 0)

    def _lock(self) -> None:
        lock_conf = str(HOME / ".config/hypr/hyprlock/hyprlock.conf")
        run_bg(["hyprlock", "-c", lock_conf])

    def _sleep(self) -> None:
        run_bg(["systemctl", "suspend"])

    # ── Stat refresh ───────────────────────────────────────────────────────

    def _collect_panel_data(self) -> dict:
        getters = {
            "network": get_network,
            "bluetooth": get_bluetooth,
            "volume": get_volume,
            "mic_muted": get_mic_muted,
            "brightness": get_brightness,
            "dnd": get_dnd,
            "battery": get_battery,
            "profile": get_power_profile,
            "cpu": get_cpu_usage,
            "ram": get_ram_usage,
            "cpu_temp": get_cpu_temp,
            "gpu_temp": get_gpu_temp,
            "security": get_hyprsec,
        }
        with ThreadPoolExecutor(max_workers=len(getters)) as executor:
            tasks = {name: executor.submit(getter) for name, getter in getters.items()}
            return {name: task.result() for name, task in tasks.items()}

    def _collect_status_data(self) -> dict:
        getters = {
            "network": get_network,
            "bluetooth": get_bluetooth,
            "volume": get_volume,
            "mic_muted": get_mic_muted,
            "brightness": get_brightness,
            "dnd": get_dnd,
            "battery": get_battery,
            "profile": get_power_profile,
        }
        with ThreadPoolExecutor(max_workers=len(getters)) as executor:
            tasks = {name: executor.submit(getter) for name, getter in getters.items()}
            return {name: task.result() for name, task in tasks.items()}

    def _refresh_panel(self) -> bool:
        self._refresh_live_status()
        return not self._closing

    def _refresh_live_status(self) -> bool:
        if self._closing or self._refreshing or not self._status_widgets:
            return False
        self._refreshing = True

        def _fetch() -> None:
            try:
                data = self._collect_status_data()
                GLib.idle_add(self._apply_live_status, data)
            except Exception as exc:
                self._refreshing = False
                print(f"Failed to refresh quick settings: {exc}", file=sys.stderr)

        threading.Thread(target=_fetch, daemon=True).start()
        return False

    def _apply_live_status(self, data: dict) -> bool:
        if self._closing:
            self._refreshing = False
            return False

        self._updating_status = True
        try:
            self._update_row(
                "wifi", "󰤨" if data["network"]["connected"] else "󰤭",
                "Wi-Fi",
                (f"{data['network']['ssid']}  {data['network']['signal']}%"
                 if data["network"]["connected"] and data["network"]["signal"]
                 else data["network"]["ssid"] if data["network"]["connected"]
                 else "On · not connected" if data["network"]["enabled"]
                 else "Off"),
                data["network"]["enabled"],
            )
            bt = data["bluetooth"]
            bt_icon = "󰂱" if bt["connected"] else ("󰂯" if bt["powered"] else "󰂲")
            bt_text = (bt["device"] or "Connected" if bt["connected"]
                       else "On · no device connected" if bt["powered"] else "Off")
            self._update_row("bluetooth", bt_icon, "Bluetooth", bt_text, bt["powered"])

            vol, muted = data["volume"]
            self._update_row(
                "speaker", "󰝟" if muted else "󰕾", "Speaker",
                "Muted" if muted else f"{vol}%", not muted,
            )
            self._vol_scale.set_value(vol)
            self._vol_lbl_widget.set_text(f"{vol}%")

            mic_muted = data["mic_muted"]
            self._update_row(
                "microphone", "󰍭" if mic_muted else "󰍬", "Microphone",
                "Muted" if mic_muted else "Active", not mic_muted,
            )
            self._update_row(
                "dnd", "󰂛" if data["dnd"] else "󰂚", "Do Not Disturb",
                "Notifications silenced" if data["dnd"] else "Notifications active",
                data["dnd"],
            )
            bat_icon, bat_text = self._battery_display(data["battery"])
            self._update_row("battery", bat_icon, "Battery", bat_text)

            profile = data["profile"]
            profile_icons = {"performance": "󰓅", "balanced": "󰾆", "power-saver": "󰌪"}
            profile_names = {"performance": "Performance", "balanced": "Balanced",
                             "power-saver": "Power Saver"}
            self._update_row(
                "profile", profile_icons.get(profile, "󰾆"),
                f"Profile: {profile_names.get(profile, profile.capitalize())}",
                "Click to cycle",
            )

            self._bri_scale.set_value(data["brightness"])
            self._bri_lbl_widget.set_text(f"{data['brightness']}%")
        finally:
            self._updating_status = False
            self._refreshing = False
        return False

    def _refresh_stats(self) -> bool:
        if self._closing:
            return False

        def _fetch() -> None:
            cpu = get_cpu_usage()
            ram_pct, ram_used, ram_total = get_ram_usage()
            cpu_t = get_cpu_temp()
            gpu_t = get_gpu_temp()
            GLib.idle_add(
                self._apply_stats, cpu, ram_pct, ram_used, ram_total, cpu_t, gpu_t
            )

        threading.Thread(target=_fetch, daemon=True).start()
        return not self._closing

    def _apply_stats(self, cpu: int, ram_pct: int, _ram_used: float,
                     _ram_total: float, cpu_t: Optional[float],
                     gpu_t: Optional[float]) -> bool:
        if self._closing:
            return False
        self._cpu_val.set_text(f"{cpu}%")
        self._ram_val.set_text(f"{ram_pct}%")
        self._cput_val.set_text(f"{cpu_t:.0f}°" if cpu_t is not None else "N/A")
        self._gput_val.set_text(f"{gpu_t:.0f}°" if gpu_t is not None else "N/A")
        return False

    def _update_row(self, key: str, icon: str, label: str,
                    sublabel: str, active: Optional[bool] = None) -> None:
        widgets = self._status_widgets[key]
        widgets["icon"].set_text(icon)
        widgets["label"].set_text(label)
        if widgets["sublabel"] is not None:
            widgets["sublabel"].set_text(sublabel)
        if widgets["switch"] is not None and active is not None:
            widgets["switch"].set_active(active)

    @staticmethod
    def _battery_display(bat: dict) -> tuple[str, str]:
        if not bat["present"]:
            return "󰚥", "No battery (AC)"
        status_map = {"Charging": "󰂆", "Discharging": "󰁼", "Full": "󰁹", "Unknown": "󰂎"}
        cap = bat["capacity"]
        stat = bat["status"]
        icon = status_map.get(stat, "󰁼")
        if stat == "Discharging":
            icons = ["󰂎","󰁺","󰁻","󰁼","󰁽","󰁾","󰁿","󰂀","󰂁","󰂂","󰁹"]
            icon = icons[min(len(icons) - 1, cap * len(icons) // 101)]
        sub_parts = [f"{cap}%  {stat}"]
        if bat["watts"]:
            sub_parts.append(f"{bat['watts']:.1f}W")
        if bat["health"]:
            sub_parts.append(f"Health {bat['health']:.0f}%")
        return icon, "  ·  ".join(sub_parts)

    # ── Launcher helper ────────────────────────────────────────────────────

    def _launch(self, *cmd: str) -> None:
        self._close()
        run_bg(list(cmd))


# ── Entry point ───────────────────────────────────────────────────────────────

def already_running() -> bool:
    """Return True if another instance holds the lock (and kill it if stale)."""
    if LOCK_FILE.exists():
        try:
            pid = int(LOCK_FILE.read_text().strip())
            os.kill(pid, 0)   # 0 = probe only
            # It's alive — send SIGTERM to toggle (close existing window)
            os.kill(pid, signal.SIGTERM)
            return True
        except (ValueError, ProcessLookupError, PermissionError):
            LOCK_FILE.unlink(missing_ok=True)
    return False


def main() -> None:
    if already_running():
        sys.exit(0)

    # Write PID lock
    LOCK_FILE.write_text(str(os.getpid()))

    signal.signal(signal.SIGTERM, lambda *_: (LOCK_FILE.unlink(missing_ok=True), sys.exit(0)))

    # Ensure WAYLAND_DISPLAY is available (needed inside sandboxed envs)
    if not os.environ.get("WAYLAND_DISPLAY") and not os.environ.get("DISPLAY"):
        # Try to inherit from running compositor
        wd = run_out(["hyprctl", "-j", "activeworkspace"], timeout=2)
        # If we're here, something is wrong. Fall through and let GTK fail gracefully.
        pass

    app = QuickSettings()

    # Handle SIGTERM cleanly
    def _sigterm(*_):
        app._close()

    signal.signal(signal.SIGTERM, _sigterm)

    Gtk.main()


if __name__ == "__main__":
    main()
