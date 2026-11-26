#!/usr/bin/env python3
"""Show a quick health report for the Hyprland rice."""

from __future__ import annotations

import json
import shutil
import subprocess
import textwrap
from pathlib import Path


CONFIG = Path.home() / ".config" / "hypr"
DISPLAY_MANAGER = CONFIG / "scripts" / "display-manager.py"
DISPLAY_PREFERENCES = CONFIG / "state" / "display-preferences.json"
ROFI_THEME = CONFIG / "rofi" / "command-center.rasi"

REQUIRED_TOOLS = ("hyprctl", "rofi")
FEATURE_TOOLS = {
    "Display / session": ("qs", "waybar", "dunst", "dunstify", "hypridle", "hyprlock", "brightnessctl", "systemctl"),
    "Clipboard / capture": ("wl-paste", "wl-copy", "cliphist", "grim", "slurp", "swappy"),
    "Network / audio": ("nmcli", "bluetoothctl", "wpctl", "powerprofilesctl", "pavucontrol"),
    "Applications": ("kitty", "fastfetch", "btop", "thunar", "firefox", "code", "lazygit", "cmatrix"),
    "Desktop integration": ("gsettings", "hyprpaper", "playerctl", "dunstctl", "notify-send"),
}


def run(command: list[str], timeout: float = 5) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(command, 1, "", str(exc))


def watcher_pids() -> list[str]:
    found = []
    for path in Path("/proc").glob("[0-9]*/cmdline"):
        try:
            args = [arg.decode(errors="replace") for arg in path.read_bytes().split(b"\0") if arg]
        except OSError:
            continue
        if str(DISPLAY_MANAGER) in args and "--watch" in args:
            found.append(path.parent.name)
    return found


def connected_outputs() -> set[str]:
    connected = set()
    for path in Path("/sys/class/drm").glob("card*-*/status"):
        try:
            if path.read_text(encoding="utf-8").strip() == "connected":
                connected.add(path.parent.name.partition("-")[2])
        except OSError:
            continue
    return connected


def add_wrapped(lines: list[str], prefix: str, message: str, width: int = 88) -> None:
    lines.extend(textwrap.wrap(prefix + message, width=width, subsequent_indent="    ") or [prefix])


def monitor_rectangle(monitor: dict[str, object]) -> tuple[float, float, float, float]:
    width = float(monitor.get("width", 0))
    height = float(monitor.get("height", 0))
    scale = float(monitor.get("scale", 1) or 1)
    if int(monitor.get("transform", 0)) % 4 in (1, 3):
        width, height = height, width
    x, y = float(monitor.get("x", 0)), float(monitor.get("y", 0))
    return x, y, x + width / scale, y + height / scale


def build_report() -> tuple[list[str], int]:
    lines = []
    warnings = 0

    required_missing = [name for name in REQUIRED_TOOLS if shutil.which(name) is None]
    if required_missing:
        warnings += 1
        add_wrapped(lines, "[WARN] Required commands missing: ", ", ".join(required_missing))
    else:
        lines.append("[ OK ] Required commands: hyprctl, rofi")

    version = run(["hyprctl", "version"])
    if version.returncode == 0:
        add_wrapped(lines, "[ OK ] Hyprland: ", version.stdout.splitlines()[0] if version.stdout else "running")
    else:
        warnings += 1
        add_wrapped(lines, "[WARN] Hyprland version query failed: ", version.stderr.strip() or version.stdout.strip())

    config = run(["hyprctl", "configerrors"])
    config_errors = (config.stdout or config.stderr).strip()
    if config.returncode != 0:
        warnings += 1
        add_wrapped(lines, "[WARN] Config error query failed: ", config_errors or "hyprctl returned an error")
    elif config_errors:
        warnings += 1
        lines.append("[WARN] Hyprland reported configuration errors:")
        for error in config_errors.splitlines()[:8]:
            add_wrapped(lines, "    ", error)
        if len(config_errors.splitlines()) > 8:
            lines.append("    (additional errors omitted)")
    else:
        lines.append("[ OK ] Hyprland configuration: no errors reported")

    pids = watcher_pids()
    if len(pids) == 1:
        lines.append(f"[ OK ] Display watcher: one instance (PID {pids[0]})")
    elif not pids:
        warnings += 1
        lines.append("[WARN] Display watcher: not running; automatic hotplug recovery is unavailable")
    else:
        warnings += 1
        lines.append(f"[WARN] Display watcher: {len(pids)} instances found (PIDs {', '.join(pids)})")

    monitor_result = run(["hyprctl", "-j", "monitors", "all"])
    workspace_result = run(["hyprctl", "-j", "workspaces"])
    if monitor_result.returncode != 0 or workspace_result.returncode != 0:
        warnings += 1
        detail = monitor_result.stderr or workspace_result.stderr or "Hyprland IPC query failed"
        add_wrapped(lines, "[WARN] Monitor/workspace state unavailable: ", detail.strip())
    else:
        try:
            monitors = json.loads(monitor_result.stdout)
            workspaces = json.loads(workspace_result.stdout)
            if not isinstance(monitors, list) or not isinstance(workspaces, list):
                raise ValueError("unexpected JSON response")
        except (json.JSONDecodeError, ValueError) as exc:
            warnings += 1
            add_wrapped(lines, "[WARN] Could not parse monitor/workspace state: ", str(exc))
        else:
            connected = connected_outputs()
            connected |= {
                item["name"]
                for item in monitors
                if isinstance(item, dict) and item.get("connected")
            }
            active = [
                item for item in monitors
                if isinstance(item, dict)
                and not item.get("disabled", False)
                and (not connected or item.get("name") in connected)
            ]
            if active:
                details = []
                for monitor in active:
                    workspace = monitor.get("activeWorkspace", {}).get("name", "?")
                    details.append(
                        f"{monitor.get('name', '?')} {monitor.get('width', '?')}x"
                        f"{monitor.get('height', '?')} ws:{workspace}"
                    )
                add_wrapped(lines, f"[ OK ] Active display(s) ({len(active)}): ", "; ".join(details))
            else:
                warnings += 1
                lines.append("[WARN] No active connected displays were reported")

            normal_active = [
                item for item in active
                if item.get("mirrorOf") in (None, "none", "")
            ]
            overlaps = []
            for index, first in enumerate(normal_active):
                first_rect = monitor_rectangle(first)
                for second in normal_active[index + 1:]:
                    second_rect = monitor_rectangle(second)
                    if (
                        first_rect[0] < second_rect[2]
                        and second_rect[0] < first_rect[2]
                        and first_rect[1] < second_rect[3]
                        and second_rect[1] < first_rect[3]
                    ):
                        overlaps.append(f"{first.get('name')} / {second.get('name')}")
            if overlaps:
                warnings += 1
                add_wrapped(lines, "[WARN] Active monitor layout overlaps: ", ", ".join(overlaps))
            else:
                lines.append("[ OK ] Active monitor geometry: no overlaps detected")

            connected_names = connected or {
                item.get("name") for item in monitors
                if isinstance(item, dict) and not item.get("disabled", False)
            }
            stranded = [
                str(item.get("name"))
                for item in workspaces
                if isinstance(item, dict)
                and item.get("monitor")
                and item.get("monitor") not in connected_names
            ]
            if stranded:
                warnings += 1
                add_wrapped(lines, "[WARN] Workspace(s) assigned to unavailable displays: ", ", ".join(stranded))
            else:
                lines.append(f"[ OK ] Workspaces: {len(workspaces)} reported; none on unavailable displays")

    preference = "not set"
    try:
        data = json.loads(DISPLAY_PREFERENCES.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("external_workspace") is not None:
            preference = str(data["external_workspace"])
    except FileNotFoundError:
        pass
    except (OSError, json.JSONDecodeError):
        warnings += 1
        preference = "could not read (invalid JSON or permissions)"
    lines.append(f"[INFO] Saved external workspace preference: {preference}")

    for group, tools in FEATURE_TOOLS.items():
        missing = [name for name in tools if shutil.which(name) is None]
        if missing:
            add_wrapped(lines, f"[INFO] Optional {group} tools unavailable: ", ", ".join(missing))
        else:
            lines.append(f"[ OK ] Optional {group} tools: available")

    lines.append("")
    lines.append(f"Summary: {warnings} warning(s)")
    return lines, warnings


def show_report(lines: list[str]) -> str | None:
    options = [*lines, "Refresh diagnostics", "Close"]
    if not shutil.which("rofi"):
        print("\n".join(lines))
        return None
    result = run(
        [
            "rofi",
            "-dmenu",
            "-i",
            "-no-custom",
            "-config",
            str(ROFI_THEME),
            "-p",
            "Rice Health",
        ],
        timeout=120,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(result.stderr.strip() or "Rofi could not show the health report")
    return result.stdout.strip() if result.returncode == 0 else None


def main() -> int:
    while True:
        lines, _warnings = build_report()
        try:
            selected = show_report(lines)
        except RuntimeError as exc:
            print(f"Rice Health: {exc}")
            return 1
        if selected != "Refresh diagnostics":
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
