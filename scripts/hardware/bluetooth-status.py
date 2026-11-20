#!/usr/bin/env python3
"""Report Bluetooth power and connection state to Waybar."""

from __future__ import annotations

import json
import subprocess


ICONS = {
    "powered": "󰂯",
    "connected": "󰂱",
    "disabled": "󰂲",
    "unavailable": "󰂲",
}


def bluetoothctl(*args: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["bluetoothctl", *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"Could not query Bluetooth state: {exc}") from exc


def status() -> dict[str, str]:
    result = bluetoothctl("show")
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or "bluetoothctl show failed"
        raise RuntimeError(detail)

    fields = {}
    for line in result.stdout.splitlines():
        key, separator, value = line.strip().partition(":")
        if separator:
            fields[key] = value.strip()
    powered = fields.get("Powered")
    if powered not in {"yes", "no"}:
        raise RuntimeError("Bluetooth controller did not report its power state.")

    if powered == "no":
        return {
            "text": ICONS["disabled"],
            "tooltip": "Bluetooth: Off",
            "class": "disabled",
            "alt": "disabled",
        }

    connected_result = bluetoothctl("devices", "Connected")
    if connected_result.returncode:
        detail = connected_result.stderr.strip() or connected_result.stdout.strip()
        raise RuntimeError(detail or "Could not query connected Bluetooth devices.")
    devices = [
        line.partition(" ")[2].partition(" ")[2].strip()
        for line in connected_result.stdout.splitlines()
        if line.startswith("Device ") and line.partition(" ")[2].partition(" ")[2].strip()
    ]

    if devices:
        return {
            "text": f"{ICONS['connected']} {devices[0]}",
            "tooltip": "Bluetooth: On\nConnected:\n" + "\n".join(devices),
            "class": "connected",
            "alt": "connected",
        }
    return {
        "text": ICONS["powered"],
        "tooltip": "Bluetooth: On\nNo connected devices",
        "class": "powered",
        "alt": "powered",
    }


try:
    output = status()
except RuntimeError as exc:
    output = {
        "text": ICONS["unavailable"],
        "tooltip": f"Bluetooth status unavailable: {exc}",
        "class": "unavailable",
        "alt": "unavailable",
    }

print(json.dumps(output, ensure_ascii=False))
