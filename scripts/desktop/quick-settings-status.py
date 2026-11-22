#!/usr/bin/env python3
"""
Quick Settings Cluster Status for Waybar
Outputs a compact JSON status line showing: network · audio · battery · security
"""
from __future__ import annotations

import glob
import json
import os
import subprocess
from pathlib import Path

HOME = Path.home()
SCRIPTS = HOME / ".config" / "hypr" / "scripts"


def run(cmd: list[str], timeout: float = 2.0) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception:
        return ""


def _read(path: str) -> str:
    try:
        return Path(path).read_text().strip()
    except Exception:
        return ""


# ── Network ─────────────────────────────────────────────────────────────────
def net_icon() -> str:
    wifi_enabled = run(["nmcli", "radio", "wifi"]) == "enabled"
    if wifi_enabled:
        out = run(["nmcli", "-t", "-f", "ACTIVE,SIGNAL", "dev", "wifi"])
        for line in out.splitlines():
            parts = line.split(":")
            if len(parts) >= 2 and parts[0] == "yes":
                try:
                    sig = int(parts[1])
                except ValueError:
                    sig = 50
                if sig >= 75:
                    return "󰤨"
                elif sig >= 50:
                    return "󰤥"
                elif sig >= 25:
                    return "󰤢"
                else:
                    return "󰤟"

    # Ethernet?
    eth = run(["nmcli", "-t", "-f", "TYPE,STATE", "dev"])
    for line in eth.splitlines():
        if "ethernet" in line.lower() and "connected" in line.lower():
            return "󰈀"

    # Keep radio state separate from whether it currently has an active connection.
    return "󰤨" if wifi_enabled else "󰤭"


# ── Audio ────────────────────────────────────────────────────────────────────
def audio_icon() -> str:
    out = run(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"])
    if not out:
        return "󰕿"
    if "[MUTED]" in out:
        return "󰝟"
    try:
        vol = float(out.split()[1]) * 100
    except (IndexError, ValueError):
        vol = 50
    if vol < 1:
        return "󰝟"
    elif vol < 33:
        return "󰕿"
    elif vol < 66:
        return "󰖀"
    return "󰕾"


def microphone_icon() -> str:
    out = run(["wpctl", "get-volume", "@DEFAULT_AUDIO_SOURCE@"])
    return "󰍭" if "[MUTED]" in out else "󰍬"


# ── Battery ──────────────────────────────────────────────────────────────────
def battery_icon() -> str:
    bats = glob.glob("/sys/class/power_supply/BAT*")
    if not bats:
        return "󰚥"  # AC plugged, no battery
    b = bats[0]
    cap_s = _read(f"{b}/capacity")
    status = _read(f"{b}/status")
    try:
        cap = int(cap_s)
    except ValueError:
        cap = 0
    if status == "Charging":
        charging = ["󰢟","󰢜","󰂆","󰂇","󰂈","󰢝","󰂉","󰢞","󰂊","󰂋","󰂅"]
        return charging[min(len(charging)-1, cap * len(charging) // 101)]
    elif status in ("Full", "Not charging") and cap >= 95:
        return "󰁹"
    else:
        icons = ["󰂎","󰁺","󰁻","󰁼","󰁽","󰁾","󰁿","󰂀","󰂁","󰂂","󰁹"]
        return icons[min(len(icons)-1, cap * len(icons) // 101)]


def battery_pct() -> str:
    bats = glob.glob("/sys/class/power_supply/BAT*")
    if not bats:
        return ""
    return _read(f"{bats[0]}/capacity") + "%"


def battery_status() -> dict[str, object]:
    bats = glob.glob("/sys/class/power_supply/BAT*")
    if not bats:
        return {"available": False, "percentage": None, "status": ""}
    battery = bats[0]
    try:
        percentage = int(_read(f"{battery}/capacity"))
    except ValueError:
        percentage = None
    return {
        "available": True,
        "percentage": percentage,
        "status": _read(f"{battery}/status"),
    }


# ── Security ─────────────────────────────────────────────────────────────────
def sec_class() -> str:
    out = run([str(SCRIPTS / "security" / "hyprsec-box.sh"), "waybar-status"], timeout=5)
    try:
        return json.loads(out).get("class", "unavailable")
    except Exception:
        return "unavailable"


# ── DND ──────────────────────────────────────────────────────────────────────
def dnd_icon() -> str:
    out = run(["dunstctl", "is-paused"])
    return "󰂛" if out == "true" else ""  # only show when active


def displayed_notification_count() -> int:
    out = run(["dunstctl", "count", "displayed"])
    try:
        return max(0, int(out))
    except ValueError:
        return 0


# ── Compose ──────────────────────────────────────────────────────────────────
n_icon = net_icon()
a_icon = audio_icon()
m_icon = microphone_icon()
b_icon = battery_icon()
b_pct = battery_pct()
battery = battery_status()
d_icon = dnd_icon()
n_count = displayed_notification_count()
s_cls = sec_class()

# Security indicator dot
sec_dot = ""  # green dot
if s_cls == "running":
    sec_dot = " 󰒃"
elif s_cls == "unavailable":
    sec_dot = ""  # don't show if podman not available

parts = [n_icon, a_icon, m_icon, f"{b_icon} {b_pct}".strip()]
if d_icon:
    parts.append(d_icon)
if sec_dot:
    parts.append(sec_dot)

text = "  ".join(parts)

# Build tooltip
bat_tooltip = ""
bats = glob.glob("/sys/class/power_supply/BAT*")
if bats:
    b = bats[0]
    cap = _read(f"{b}/capacity")
    stat = _read(f"{b}/status")
    bat_tooltip = f"Battery: {cap}% ({stat})"

tooltip_parts = [
    "Quick Settings",
    bat_tooltip,
    f"Notifications: {n_count} displayed",
    f"Security: {s_cls}",
]
tooltip = "\n".join(p for p in tooltip_parts if p)

print(json.dumps({
    "text": text,
    "tooltip": tooltip,
    "class": f"cluster sec-{s_cls}",
    "alt": s_cls,
    "notifications": n_count,
    "battery": battery,
}))
