"""Diagnostics, validation, snapshots, activity logs, and regression tests."""

from __future__ import annotations

import argparse
import ast
import difflib
import hashlib
import importlib.util
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
import unittest
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


CONFIG = Path.home() / ".config" / "hypr"
SCRIPTS = CONFIG / "scripts"
SNAPSHOT_COMPAT_PATHS = {
    "animations.conf": "hyprland/legacy/animations.conf",
    "keybinds.conf": "hyprland/legacy/keybinds.conf",
    "windowrules.conf": "hyprland/legacy/windowrules.conf",
    "hypridle.conf": "hyprland/legacy/hypridle.conf",
    "hyprpaper.conf": "hyprpaper/hyprpaper.conf",
    "hyprclock.conf": "hyprclock/hyprclock.conf",
    "current_wallpaper": "state/current_wallpaper",
    "display-preferences.json": "state/display-preferences.json",
    "display-profiles.json": "state/display-profiles.json",
    "idle-settings.json": "state/idle-settings.json",
    "session-presets.json": "state/session-presets.json",
}
SNAPSHOT_DIR = Path.home() / ".local" / "share" / "hypr-rice" / "snapshots"
SNAPSHOT_SETTINGS = CONFIG / "snapshot-settings.json"
REPORT_DIR = Path.home() / ".local" / "state" / "hypr-rice" / "reports"
ROFI_THEME = CONFIG / "rofi" / "command-center.rasi"
MAX_SNAPSHOTS = 10
SNAPSHOT_EXCLUDES = {
    ".git",
    ".backup",
    "__pycache__",
    ".cache",
    ".venv",
    "node_modules",
    "wallpapers",
}
SECRET_NAMES = {".env", ".netrc", "credentials", "secrets", "id_rsa", "id_ed25519"}
SECRET_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}
REQUIRED_BINARIES = {
    "core": ["hyprctl", "Hyprland", "lua", "luac", "rofi"],
    "display": ["hyprctl", "Hyprland", "rofi"],
    "waybar": ["waybar"],
    "audio": ["pactl", "wpctl", "systemctl"],
    "bluetooth": ["bluetoothctl", "systemctl"],
}
OPTIONAL_BINARIES = {
    "desktop": ["hypridle", "hyprlock", "waybar", "dunst", "dunstify"],
    "audio": ["pavucontrol", "wpctl", "pactl"],
    "capture": ["grim", "slurp", "wl-copy", "wl-paste", "cliphist"],
    "network": ["nmcli", "bluetoothctl"],
    "applications": ["kitty", "firefox", "thunar", "code", "btop", "fastfetch"],
}
MODULES = ("core", "display", "waybar", "audio", "bluetooth", "idle", "session", "scripts")
VALIDATION_MODULES = ("core", "waybar", "idle", "scripts")


@dataclass
class Check:
    module: str
    name: str
    status: str
    details: str
    suggestion: str = ""


class MaintenanceError(RuntimeError):
    pass


def event_logger():
    path = SCRIPTS / "core" / "rice_events.py"
    spec = importlib.util.spec_from_file_location("rice_events", path)
    if spec is None or spec.loader is None:
        raise MaintenanceError("The rice event logger could not be loaded.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def log_event(component: str, description: str, **kwargs: Any) -> None:
    try:
        event_logger().log_event(component, description, **kwargs)
    except OSError as exc:
        print(f"rice: could not write activity log: {exc}", file=sys.stderr)


def run(args: list[str], timeout: float = 6) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(args, text=True, capture_output=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(args, 1, "", str(exc))


def jsonc_to_json(text: str) -> str:
    """Remove JSONC comments while preserving quoted strings and newlines."""
    out: list[str] = []
    index = 0
    in_string = False
    escaped = False
    while index < len(text):
        char = text[index]
        following = text[index + 1] if index + 1 < len(text) else ""
        if in_string:
            out.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if char == '"':
            in_string = True
            out.append(char)
            index += 1
        elif char == "/" and following == "/":
            while index < len(text) and text[index] not in "\r\n":
                out.append(" ")
                index += 1
        elif char == "/" and following == "*":
            out.extend("  ")
            index += 2
            while index < len(text) and text[index:index + 2] != "*/":
                out.append("\n" if text[index] == "\n" else " ")
                index += 1
            if index >= len(text):
                raise ValueError("Unterminated block comment.")
            out.extend("  ")
            index += 2
        else:
            out.append(char)
            index += 1
    if in_string:
        raise ValueError("Unterminated JSON string.")
    return "".join(out)


def parse_jsonc(path: Path) -> Any:
    return json.loads(jsonc_to_json(path.read_text(encoding="utf-8")))


def check_status(status: str, checks: list[Check]) -> None:
    if status not in {"Healthy", "Warning", "Failed", "Not Installed", "Not Applicable"}:
        raise ValueError(f"Unknown status: {status}")
    if not checks:
        raise ValueError("A diagnostic result requires at least one check.")


def build_diagnostics(*, full: bool = False, module: str | None = None) -> list[Check]:
    checks: list[Check] = []

    def add(module_name: str, name: str, status: str, details: str, suggestion: str = "") -> None:
        check_status(status, [Check(module_name, name, status, details, suggestion)])
        if module is None or module == module_name:
            checks.append(Check(module_name, name, status, details, suggestion))

    if module in (None, "core"):
        version = run(["Hyprland", "--version"])
        if version.returncode == 0:
            add("core", "Hyprland", "Healthy", version.stdout.strip().splitlines()[0])
        elif shutil.which("Hyprland"):
            add("core", "Hyprland", "Warning", version.stderr.strip() or "Not running or not queryable.")
        else:
            add("core", "Hyprland", "Failed", "Hyprland binary is missing.", "Install the Hyprland package.")
        verify = run(["Hyprland", "--verify-config", "--config", str(CONFIG / "hyprland.lua")], timeout=20)
        if verify.returncode == 0 and "config ok" in verify.stdout.lower():
            add("core", "Hyprland configuration", "Healthy", "Installed compositor accepted the current configuration.")
        else:
            detail = (verify.stdout + verify.stderr).strip().splitlines()[-4:]
            add("core", "Hyprland configuration", "Failed", "\n".join(detail) or "Configuration validation failed.",
                "Run `rice validate` and address the reported parser errors.")
        for binary in REQUIRED_BINARIES["core"]:
            if shutil.which(binary) is None:
                add("core", f"Required command: {binary}", "Failed", "Required rice command is missing.",
                    f"Install the Arch package providing {binary}.")
        for path in (CONFIG / "hyprland.lua", CONFIG / "hyprland.conf"):
            add("core", f"Config file: {path.name}", "Healthy" if path.is_file() else "Failed",
                "Present." if path.is_file() else "Required config file is missing.")
        runtime = run(["hyprctl", "version"])
        add("core", "Hyprland runtime", "Healthy" if runtime.returncode == 0 else "Warning",
            runtime.stdout.strip().splitlines()[0] if runtime.returncode == 0 and runtime.stdout.strip()
            else runtime.stderr.strip() or "Not connected to an active Hyprland session.",
            "" if runtime.returncode == 0 else "Run from the active Hyprland session for IPC diagnostics.")

    if module in (None, "waybar"):
        config_path = CONFIG / "waybar" / "config.jsonc"
        style_path = CONFIG / "waybar" / "style.css"
        try:
            parsed = parse_jsonc(config_path)
            if not isinstance(parsed, dict):
                raise ValueError("The config root must be a JSON object.")
            modules = parsed.get("modules-right", []) + parsed.get("modules-left", []) + parsed.get("modules-center", [])
            if not isinstance(modules, list) or not all(isinstance(item, str) for item in modules):
                raise ValueError("Waybar module lists must contain strings.")
            configured = set(parsed)
            missing = [item for item in modules if item.startswith("custom/") and item not in configured]
            if missing:
                raise ValueError("Missing custom module configuration: " + ", ".join(missing))
            add("waybar", "Waybar configuration", "Healthy", "JSONC parsed and custom modules are defined.")
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            add("waybar", "Waybar configuration", "Failed", str(exc), "Fix JSONC syntax or module references.")
        add("waybar", "Waybar stylesheet", "Healthy" if style_path.is_file() else "Failed",
            "Present." if style_path.is_file() else "Stylesheet missing.")
        pids = process_pids("waybar")
        add("waybar", "Waybar runtime", "Healthy" if pids else "Warning",
            f"Running process(es): {', '.join(pids)}" if pids else "Waybar is not running.",
            "" if pids else "Start Waybar from the Control Center or reload the desktop.")
        for binary in REQUIRED_BINARIES["waybar"]:
            add("waybar", f"Dependency: {binary}", "Healthy" if shutil.which(binary) else "Not Installed",
                "Available." if shutil.which(binary) else "Waybar package is not installed.")

    if module in (None, "audio"):
        for service in ("pipewire", "pipewire-pulse", "wireplumber"):
            state = run(["systemctl", "--user", "is-active", service])
            add("audio", f"Service: {service}", "Healthy" if state.returncode == 0 else "Warning",
                state.stdout.strip() or "Not active.",
                "" if state.returncode == 0 else f"Check `systemctl --user status {service}`.")
        if not shutil.which("pactl"):
            add("audio", "Audio devices", "Not Installed", "pactl is unavailable.")
        else:
            sinks = run(["pactl", "-f", "json", "list", "sinks"])
            default = run(["pactl", "get-default-sink"])
            try:
                parsed_sinks = json.loads(sinks.stdout)
                if sinks.returncode or not isinstance(parsed_sinks, list):
                    raise ValueError(sinks.stderr.strip() or "Invalid sink list.")
                active = next((item for item in parsed_sinks if item.get("name") == default.stdout.strip()), None)
                if not parsed_sinks:
                    add("audio", "Audio output", "Warning", "PipeWire has no available output sinks.")
                elif not active:
                    add("audio", "Audio output", "Failed", "The default output does not match an available sink.")
                else:
                    add("audio", "Audio output", "Healthy",
                        f"{active.get('description', active['name'])} is the default output.")
            except (ValueError, json.JSONDecodeError) as exc:
                add("audio", "Audio output", "Warning", str(exc), "Check PipeWire and WirePlumber status.")

    if module in (None, "display"):
        if not shutil.which("hyprctl"):
            add("display", "Hyprland IPC", "Not Installed", "hyprctl is unavailable.")
        else:
            monitors = run(["hyprctl", "-j", "monitors", "all"])
            if monitors.returncode:
                add("display", "Display state", "Warning", monitors.stderr.strip() or "Hyprland IPC unavailable.",
                    "Run this check inside the active Hyprland session.")
            else:
                try:
                    parsed = json.loads(monitors.stdout)
                    active = [item for item in parsed if not item.get("disabled", False)]
                    overlaps = monitor_overlaps(active)
                    if overlaps:
                        add("display", "Monitor geometry", "Failed", ", ".join(overlaps),
                            "Use Display Manager presets and reject overlapping layouts.")
                    else:
                        add("display", "Monitor geometry", "Healthy",
                            f"{len(active)} active monitor(s); no overlaps detected.")
                except (json.JSONDecodeError, TypeError, ValueError) as exc:
                    add("display", "Display state", "Failed", f"Invalid monitor response: {exc}")
        manager = SCRIPTS / "hardware" / "display-manager.py"
        add("display", "Display Manager", "Healthy" if manager.is_file() and os.access(manager, os.X_OK) else "Failed",
            "Script exists and is executable." if manager.is_file() and os.access(manager, os.X_OK)
            else "Display Manager script missing or not executable.")
        control_center = SCRIPTS / "desktop" / "control-center.sh"
        control_center_ok = control_center.is_file() and os.access(control_center, os.X_OK)
        add("display", "Quick Settings / Control Center",
            "Healthy" if control_center_ok else "Failed",
            "Control Center entry point is present." if control_center_ok
            else "Control Center script missing or not executable.",
            "" if control_center_ok else "Restore or mark scripts/control-center.sh executable.")
        launcher_theme = CONFIG / "rofi" / "launcher.rasi"
        launcher_ok = bool(shutil.which("rofi") and launcher_theme.is_file())
        add("display", "Rofi launcher",
            "Healthy" if launcher_ok else "Failed",
            "Rofi and launcher theme are available." if launcher_ok
            else "Rofi or its launcher theme is missing.",
            "" if launcher_ok else "Run `rice dependencies --full` for package guidance.")

    if module in (None, "session"):
        script = SCRIPTS / "session" / "session-presets.py"
        add("session", "Session Presets", "Healthy" if script.is_file() and os.access(script, os.X_OK) else "Failed",
            "CLI entry point is present." if script.is_file() and os.access(script, os.X_OK)
            else "Session preset entry point missing or not executable.")
        preset_file = CONFIG / "state" / "session-presets.json"
        if preset_file.exists():
            try:
                data = json.loads(preset_file.read_text(encoding="utf-8"))
                if not isinstance(data, dict) or not isinstance(data.get("presets", {}), dict):
                    raise ValueError("Expected an object containing a presets object.")
                add("session", "Saved presets", "Healthy", f"{len(data.get('presets', {}))} preset(s) loaded.")
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                add("session", "Saved presets", "Warning", str(exc), "Back up the JSON file before editing.")
        else:
            add("session", "Saved presets", "Not Applicable", "No presets saved yet.")

    if module in (None, "bluetooth"):
        if not shutil.which("bluetoothctl"):
            add("bluetooth", "Bluetooth", "Not Installed", "bluetoothctl is unavailable.")
        else:
            state = run(["systemctl", "is-active", "bluetooth"])
            controller = run(["bluetoothctl", "show"])
            if state.returncode:
                add("bluetooth", "Bluetooth service", "Warning", state.stdout.strip() or "Service is not active.",
                    "Start Bluetooth only if you intend to use Bluetooth.")
            else:
                add("bluetooth", "Bluetooth service", "Healthy", "BlueZ service is active.")
            if controller.returncode:
                add("bluetooth", "Bluetooth controller", "Warning", controller.stderr.strip() or "No controller.")
            else:
                powered = "Powered: yes" in controller.stdout
                add("bluetooth", "Bluetooth radio", "Healthy" if powered else "Not Applicable",
                    "Powered on." if powered else "Powered off by choice; not treated as an error.")

    if module in (None, "idle"):
        idle_script = SCRIPTS / "session" / "idle-manager.py"
        if not idle_script.is_file():
            add("idle", "Idle manager", "Failed", "scripts/idle-manager.py is missing.")
        else:
            validation = run([sys.executable, str(idle_script), "--validate"])
            add("idle", "Idle configuration",
                "Healthy" if validation.returncode == 0 else "Failed",
                validation.stdout.strip() if validation.returncode == 0
                else validation.stderr.strip() or validation.stdout.strip(),
                "" if validation.returncode == 0 else "Review the idle settings and required commands.")
            status = run([sys.executable, str(idle_script), "--status"])
            output = status.stdout.strip()
            manager_running = "Hypridle manager: running" in output
            child_running = "Hypridle process: running" in output
            add("idle", "Hypridle manager",
                "Healthy" if manager_running and child_running else "Warning",
                output or status.stderr.strip() or "Idle manager status is unavailable.",
                "" if manager_running and child_running else "Start idle-manager.py --supervise from Hyprland autostart.")
        hypridle_processes = process_pids("hypridle")
        status = "Healthy" if len(hypridle_processes) == 1 else "Failed" if len(hypridle_processes) > 1 else "Warning"
        add("idle", "Idle daemon count", status,
            f"{len(hypridle_processes)} Hypridle process(es): {', '.join(hypridle_processes) or 'none'}.",
            "" if len(hypridle_processes) == 1 else "The rice should run exactly one supervised Hypridle instance.")
        inhibitor = run(["systemd-inhibit", "--list", "--no-pager", "--no-legend"])
        if inhibitor.returncode == 0:
            active_rice_inhibitors = [
                line.strip() for line in inhibitor.stdout.splitlines()
                if any(tag in line for tag in ("hypr-rice-idle-manager", "hypr-rice-presentation", "hypr-rice-session-preset"))
            ]
            add("idle", "Idle inhibition",
                "Not Applicable" if not active_rice_inhibitors else "Healthy",
                "; ".join(active_rice_inhibitors) if active_rice_inhibitors
                else "No Rice temporary idle inhibition is active.")
        else:
            add("idle", "Idle inhibition", "Warning",
                inhibitor.stderr.strip() or "Could not query systemd idle inhibitors.")

    if module in (None, "scripts"):
        script_paths = sorted([*SCRIPTS.rglob("*.sh"), *SCRIPTS.rglob("*.py")])
        missing_exec = [
            path.name for path in script_paths
            if path.read_bytes().startswith(b"#!") and not os.access(path, os.X_OK)
        ]
        add("scripts", "Script permissions", "Warning" if missing_exec else "Healthy",
            "Not executable: " + ", ".join(missing_exec) if missing_exec else "Standalone scripts are executable.",
            "Set executable permission only for scripts with a shebang." if missing_exec else "")
        broken: list[str] = []
        for directory, dirs, names in os.walk(CONFIG, followlinks=False):
            current = Path(directory)
            for name in dirs:
                path = current / name
                if path.is_symlink() and not path.exists():
                    broken.append(str(path.relative_to(CONFIG)))
            dirs[:] = [name for name in dirs if name not in SNAPSHOT_EXCLUDES and not (current / name).is_symlink()]
            for name in names:
                path = current / name
                if path.is_symlink() and not path.exists():
                    broken.append(str(path.relative_to(CONFIG)))
        add("scripts", "Broken symlinks", "Warning" if broken else "Healthy",
            ", ".join(broken[:12]) if broken else "No broken symlinks found.")
        references = missing_config_references()
        add("scripts", "Config references", "Warning" if references else "Healthy",
            "; ".join(references[:12]) if references else "Known Lua module and startup references exist.")
        check_dependencies(add, module)

    if full and module in (None, "scripts"):
        for group, binaries in OPTIONAL_BINARIES.items():
            missing = [item for item in binaries if not shutil.which(item)]
            add("scripts", f"Optional dependencies: {group}",
                "Not Installed" if missing else "Healthy",
                "Not installed: " + ", ".join(missing) if missing else "All optional binaries are available.")

    if full and module is None:
        dunst = process_pids("dunst")
        add("core", "Notification daemon", "Healthy" if dunst else "Warning",
            "Dunst is running." if dunst else "Dunst is not running.",
            "" if dunst else "Start Dunst through the existing desktop startup.")
        if shutil.which("hyprlock"):
            add("core", "Lock screen dependency", "Healthy", "hyprlock is installed.")
        else:
            add("core", "Lock screen dependency", "Not Installed", "hyprlock is not installed.")
        configured_fonts = {"JetBrainsMono Nerd Font"}
        for font in configured_fonts:
            match = run(["fc-match", font])
            ok = match.returncode == 0 and match.stdout.strip() and "LastResort" not in match.stdout
            add("core", f"Font: {font}", "Healthy" if ok else "Warning",
                match.stdout.strip().splitlines()[0] if ok else "Fontconfig did not resolve this font.",
                "" if ok else "Install a compatible Nerd Font, or adjust the configured family.")
    return checks


def check_dependencies(add, module: str | None) -> None:
    for group, binaries in REQUIRED_BINARIES.items():
        missing = [binary for binary in binaries if shutil.which(binary) is None]
        status = "Failed" if missing and group == "core" else "Not Installed" if missing else "Healthy"
        add("scripts", f"Required dependencies: {group}", status,
            "Missing: " + ", ".join(missing) if missing else "All required commands are available.",
            "" if not missing else "Install packages through pacman after reviewing the dependency list.")


def process_pids(name: str) -> list[str]:
    pids: list[str] = []
    for path in Path("/proc").glob("[0-9]*/comm"):
        try:
            process_stat = (path.parent / "stat").read_text(encoding="utf-8")
            if process_stat.rsplit(")", 1)[1].split()[0] in {"Z", "X"}:
                continue
            if path.read_text(encoding="utf-8").strip() == name:
                pids.append(path.parent.name)
        except (OSError, IndexError):
            continue
    return pids


def monitor_overlaps(monitors: list[dict[str, Any]]) -> list[str]:
    normal = [item for item in monitors if item.get("mirrorOf") in (None, "none", "")]
    overlaps = []
    for index, first in enumerate(normal):
        first_rect = monitor_rectangle(first)
        for second in normal[index + 1:]:
            if rectangles_overlap(first_rect, monitor_rectangle(second)):
                overlaps.append(f"{first.get('name')} / {second.get('name')}")
    return overlaps


def monitor_rectangle(monitor: dict[str, Any]) -> tuple[float, float, float, float]:
    width = float(monitor.get("width", 0))
    height = float(monitor.get("height", 0))
    if int(monitor.get("transform", 0)) % 4 in (1, 3):
        width, height = height, width
    scale = float(monitor.get("scale", 1) or 1)
    x, y = float(monitor.get("x", 0)), float(monitor.get("y", 0))
    return x, y, x + width / scale, y + height / scale


def rectangles_overlap(first: tuple[float, float, float, float],
                       second: tuple[float, float, float, float]) -> bool:
    return first[0] < second[2] and second[0] < first[2] and first[1] < second[3] and second[1] < first[3]


def missing_config_references() -> list[str]:
    missing: list[str] = []
    main_lua = CONFIG / "hyprland.lua"
    if main_lua.is_file():
        text = main_lua.read_text(encoding="utf-8")
        for path in re.findall(r'dofile\(configDir \.\. "([^"]+)"\)', text):
            target = CONFIG / path.lstrip("/")
            if not target.is_file():
                missing.append(f"hyprland.lua references missing {target.relative_to(CONFIG)}")
    autostart = CONFIG / "lua" / "autostart.lua"
    if autostart.is_file():
        for reference in re.findall(r'scripts \.\. "([^"]+)"', autostart.read_text(encoding="utf-8")):
            relative = reference.strip().split()[0]
            target = CONFIG / "scripts" / relative.lstrip("/")
            if not target.exists():
                missing.append(f"autostart.lua references missing {target.relative_to(CONFIG)}")
    waybar_config = CONFIG / "waybar" / "config.jsonc"
    if waybar_config.is_file():
        try:
            data = parse_jsonc(waybar_config)
        except (OSError, ValueError, json.JSONDecodeError):
            data = None

        def find_paths(value: Any) -> Iterable[str]:
            if isinstance(value, dict):
                for item in value.values():
                    yield from find_paths(item)
            elif isinstance(value, list):
                for item in value:
                    yield from find_paths(item)
            elif isinstance(value, str):
                yield from re.findall(r"(?:\$\{HOME\}|\$HOME|~|/[^\s'\"]+)?/\.config/hypr/[^\s'\"]+", value)

        if data is not None:
            for reference in find_paths(data):
                expanded = reference.replace("${HOME}", str(Path.home())).replace("$HOME", str(Path.home()))
                target = Path(expanded).expanduser()
                if not target.exists():
                    missing.append(f"Waybar references missing {reference}")
    return missing


def validate_configs() -> list[Check]:
    checks: list[Check] = []
    hyprland = shutil.which("Hyprland")
    if hyprland:
        result = run([hyprland, "--verify-config", "--config", str(CONFIG / "hyprland.lua")], timeout=30)
        passed = result.returncode == 0 and "config ok" in result.stdout.lower()
        checks.append(Check("core", "Hyprland config", "Healthy" if passed else "Failed",
                            (result.stdout + result.stderr).strip() or "No validation output.",
                            "" if passed else "Review Hyprland parser output before reloading."))
    else:
        checks.append(Check("core", "Hyprland config", "Not Installed", "Hyprland binary is missing."))

    try:
        parse_jsonc(CONFIG / "waybar" / "config.jsonc")
        checks.append(Check("waybar", "Waybar JSONC", "Healthy", "Valid JSONC."))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        checks.append(Check("waybar", "Waybar JSONC", "Failed", str(exc)))

    lua_files = sorted(config_files(".lua"))
    luac = shutil.which("luac")
    if not luac:
        checks.append(Check("core", "Lua syntax", "Not Installed", "luac is not installed."))
    else:
        for path in lua_files:
            result = run([luac, "-p", str(path)])
            checks.append(Check("core", f"Lua: {path.relative_to(CONFIG)}",
                                "Healthy" if result.returncode == 0 else "Failed",
                                result.stderr.strip() or "Syntax is valid.",
                                "" if result.returncode == 0 else "Correct Lua syntax before reloading."))

    for path in sorted(SCRIPTS.rglob("*.sh")):
        result = run(["bash", "-n", str(path)])
        checks.append(Check("scripts", f"Shell: {path.name}",
                            "Healthy" if result.returncode == 0 else "Failed",
                            result.stderr.strip() or "Syntax is valid."))
    for path in sorted(SCRIPTS.rglob("*.py")):
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            checks.append(Check("scripts", f"Python: {path.name}", "Healthy", "Syntax is valid."))
        except (OSError, SyntaxError) as exc:
            checks.append(Check("scripts", f"Python: {path.name}", "Failed", str(exc)))
    idle_script = SCRIPTS / "session" / "idle-manager.py"
    if not idle_script.is_file():
        checks.append(Check("idle", "Idle settings", "Failed", "scripts/idle-manager.py is missing."))
    else:
        result = run([sys.executable, str(idle_script), "--validate"], timeout=10)
        checks.append(Check(
            "idle",
            "Idle settings",
            "Healthy" if result.returncode == 0 else "Failed",
            result.stdout.strip() if result.returncode == 0 else result.stderr.strip() or result.stdout.strip(),
            "" if result.returncode == 0 else "Review idle-settings.json and the Hypridle dependencies.",
        ))
    refs = missing_config_references()
    checks.append(Check("scripts", "Config references", "Healthy" if not refs else "Warning",
                        "; ".join(refs) if refs else "Known modular references resolve."))
    return checks


def config_files(suffix: str) -> list[Path]:
    files: list[Path] = []
    for directory, dirs, names in os.walk(CONFIG, followlinks=False):
        current = Path(directory)
        dirs[:] = [
            name for name in dirs
            if name not in SNAPSHOT_EXCLUDES and not (current / name).is_symlink()
        ]
        files.extend(
            current / name for name in names
            if name.endswith(suffix) and not (current / name).is_symlink()
        )
    return files


def render_checks(checks: list[Check], *, detailed: bool = True) -> str:
    statuses = {check.status for check in checks}
    overall = (
        "Failed" if "Failed" in statuses
        else "Warning" if "Warning" in statuses
        else "Healthy" if "Healthy" in statuses
        else "Not Installed" if "Not Installed" in statuses
        else "Not Applicable"
    )
    lines = [f"Rice health: {overall} — {len(checks)} check(s)"]
    for check in checks:
        lines.append(f"[{check.status.upper()}] {check.module}/{check.name}")
        if detailed:
            lines.append(f"  {check.details}")
            if check.suggestion:
                lines.append(f"  Suggestion: {check.suggestion}")
    return "\n".join(lines)


def doctor_exit_code(checks: list[Check]) -> int:
    if any(check.status == "Failed" for check in checks):
        return 2
    if any(check.status == "Warning" for check in checks):
        return 1
    return 0


def snapshot_files(root: Path | None = None) -> list[Path]:
    root = root or CONFIG
    files: list[Path] = []
    for directory, dirs, names in os.walk(root, followlinks=False):
        current = Path(directory)
        dirs[:] = [
            item for item in dirs
            if item not in SNAPSHOT_EXCLUDES and not (current / item).is_symlink()
        ]
        for name in names:
            path = current / name
            relative = path.relative_to(root)
            if path.is_symlink() or any(part in SNAPSHOT_EXCLUDES for part in relative.parts):
                continue
            lowered = name.lower()
            if lowered in SECRET_NAMES or Path(lowered).suffix in SECRET_SUFFIXES or lowered.endswith(".log"):
                continue
            if not path.is_file():
                continue
            files.append(path)
    return sorted(files, key=lambda path: path.relative_to(root).as_posix())


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def retention_limit() -> int:
    try:
        data = json.loads(SNAPSHOT_SETTINGS.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return MAX_SNAPSHOTS
    except (OSError, json.JSONDecodeError) as exc:
        raise MaintenanceError(f"Could not read snapshot settings: {exc}") from exc
    value = data.get("retention", MAX_SNAPSHOTS) if isinstance(data, dict) else None
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 50:
        raise MaintenanceError("Snapshot retention must be an integer from 1 to 50.")
    return value


def prune_snapshots(keep: int) -> None:
    archives = sorted(SNAPSHOT_DIR.glob("*.tar.gz"), reverse=True)
    for archive in archives[keep:]:
        archive.unlink()
        archive.with_suffix(".json").unlink(missing_ok=True)


def create_snapshot(label: str = "manual") -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", label):
        raise MaintenanceError("Snapshot label must use 1–32 letters, numbers, underscores, or hyphens.")
    files = snapshot_files()
    if not files:
        raise MaintenanceError("No rice configuration files were found to snapshot.")
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S-%f")
    archive = SNAPSHOT_DIR / f"{timestamp}-{label}.tar.gz"
    fd, temp_name = tempfile.mkstemp(prefix=".snapshot-", suffix=".tar.gz", dir=SNAPSHOT_DIR)
    os.close(fd)
    metadata = {
        "version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "label": label,
        "source": str(CONFIG),
        "files": {},
    }
    try:
        with tarfile.open(temp_name, "w:gz") as tar:
            for path in files:
                relative = path.relative_to(CONFIG).as_posix()
                tar.add(path, arcname=relative, recursive=False)
                metadata["files"][relative] = {
                    "sha256": file_hash(path),
                    "mode": path.stat().st_mode & 0o777,
                }
        os.replace(temp_name, archive)
        meta_path = archive.with_suffix(".json")
        atomic_write_bytes(meta_path, (json.dumps(metadata, indent=2) + "\n").encode(), 0o600)
        prune_snapshots(retention_limit())
    except (OSError, tarfile.TarError) as exc:
        Path(temp_name).unlink(missing_ok=True)
        archive.unlink(missing_ok=True)
        archive.with_suffix(".json").unlink(missing_ok=True)
        raise MaintenanceError(f"Snapshot creation failed: {exc}") from exc
    log_event("snapshots", f"Created snapshot {archive.name}", category="snapshot")
    return archive


def snapshot_before_config_change(label: str, *targets: Path) -> Path | None:
    if not any(path.exists() for path in targets):
        return None
    return create_snapshot(f"pre-{label}")


def snapshot_archive(identifier: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,32}|[0-9]{8}-[0-9]{6}-[0-9]{6}-[A-Za-z0-9_-]{1,32}", identifier):
        raise MaintenanceError("Invalid snapshot identifier.")
    matches = list(SNAPSHOT_DIR.glob(f"{identifier}*.tar.gz"))
    if len(matches) != 1:
        raise MaintenanceError(f"Expected one snapshot matching '{identifier}', found {len(matches)}.")
    return matches[0]


def read_snapshot(archive: Path) -> tuple[dict[str, Any], dict[str, bytes]]:
    try:
        metadata = json.loads(archive.with_suffix(".json").read_text(encoding="utf-8"))
        if not isinstance(metadata, dict):
            raise ValueError("Snapshot metadata must be an object.")
        files_meta = metadata.get("files")
        if not isinstance(files_meta, dict):
            raise ValueError("Missing file manifest.")
        contents: dict[str, bytes] = {}
        with tarfile.open(archive, "r:gz") as tar:
            for member in tar.getmembers():
                relative = PurePosixPath(member.name)
                if (
                    relative.is_absolute()
                    or ".." in relative.parts
                    or not relative.parts
                    or not member.isfile()
                    or member.name not in files_meta
                    or member.name in contents
                ):
                    raise ValueError(f"Unsafe snapshot member: {member.name}")
                extracted = tar.extractfile(member)
                if extracted is None:
                    raise ValueError(f"Could not read snapshot member {member.name}.")
                content = extracted.read()
                manifest = files_meta[member.name]
                if not isinstance(manifest, dict) or file_hash_bytes(content) != manifest.get("sha256"):
                    raise ValueError(f"Snapshot checksum mismatch: {member.name}")
                contents[member.name] = content
        if set(contents) != set(files_meta):
            raise ValueError("Snapshot file list does not match its manifest.")
        return metadata, contents
    except (OSError, ValueError, json.JSONDecodeError, tarfile.TarError) as exc:
        raise MaintenanceError(f"Could not read snapshot {archive.name}: {exc}") from exc


def compare_to_current(archive: Path, contents: dict[str, bytes], components: set[str] | None = None) -> list[str]:
    changes: list[str] = []
    for relative, saved in sorted(contents.items()):
        if components is not None:
            path_parts = Path(relative).parts
            component = path_parts[0] if len(path_parts) > 1 else "root"
            if component not in components:
                continue
        live = safe_config_path(relative)
        if not live.exists():
            changes.append(f"ADD     {relative}")
        elif not live.is_file() or live.read_bytes() != saved:
            changes.append(f"REPLACE {relative}")
    return changes


def validate_current_config() -> list[str]:
    checks = validate_configs()
    return [f"{item.name}: {item.details}" for item in checks if item.status == "Failed"]


def safe_config_path(relative: str) -> Path:
    parsed = PurePosixPath(relative)
    if parsed.is_absolute() or ".." in parsed.parts or not parsed.parts:
        raise MaintenanceError(f"Unsafe config path: {relative}")
    target = CONFIG.joinpath(*parsed.parts)
    if relative in SNAPSHOT_COMPAT_PATHS and target.is_symlink():
        target = CONFIG / SNAPSHOT_COMPAT_PATHS[relative]
    if CONFIG.resolve() not in target.resolve().parents and target.resolve() != CONFIG.resolve():
        raise MaintenanceError(f"Config path escapes rice directory: {relative}")
    return target


def file_hash_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def atomic_write_bytes(path: Path, content: bytes, mode: int) -> None:
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as file:
            file.write(content)
        os.chmod(temp_name, mode & 0o777)
        os.replace(temp_name, path)
    except OSError:
        Path(temp_name).unlink(missing_ok=True)
        raise


def restore_snapshot(archive: Path, components: set[str] | None = None, *, confirm: bool = False) -> list[str]:
    _metadata, files = read_snapshot(archive)
    selected = {
        relative: content for relative, content in files.items()
        if components is None
        or (Path(relative).parts[0] if len(Path(relative).parts) > 1 else "root") in components
    }
    targets = [safe_config_path(relative) for relative in selected]
    if len(targets) != len(set(targets)):
        raise MaintenanceError("Snapshot contains multiple paths for the same compatibility target.")
    changes = compare_to_current(archive, selected)
    if not changes:
        return []
    if not confirm:
        raise MaintenanceError("Restore requires explicit confirmation.")
    snapshot = create_snapshot("pre-restore")

    before: dict[str, tuple[bytes, int] | None] = {}
    try:
        for relative in selected:
            target = safe_config_path(relative)
            if target.is_symlink():
                raise MaintenanceError(f"Refusing to overwrite symlink: {relative}")
            if target.exists():
                before[relative] = (target.read_bytes(), target.stat().st_mode & 0o777)
            else:
                before[relative] = None
        for relative, content in selected.items():
            target = safe_config_path(relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            mode = _metadata.get("files", {}).get(relative, {}).get("mode", 0o644)
            atomic_write_bytes(target, content, mode)
        problems = validate_current_config()
        if problems:
            raise MaintenanceError("Restored configuration failed validation: " + "; ".join(problems))
    except Exception as exc:
        rollback_errors: list[str] = []
        for relative, previous in before.items():
            try:
                target = safe_config_path(relative)
                if previous is None:
                    target.unlink(missing_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    atomic_write_bytes(target, previous[0], previous[1])
            except OSError as rollback_exc:
                rollback_errors.append(f"{relative}: {rollback_exc}")
        message = f"Restore rolled back: {exc}; pre-restore snapshot: {snapshot.name}"
        if rollback_errors:
            message += "; rollback failures: " + "; ".join(rollback_errors)
        raise MaintenanceError(message) from exc
    log_event("snapshots", f"Restored {archive.name}", category="recovery",
              details={"components": ",".join(sorted(components or {"all"}))})
    return changes


def snapshot_list() -> list[Path]:
    return sorted(SNAPSHOT_DIR.glob("*.tar.gz"), reverse=True)


def snapshot_diff(archive: Path, components: set[str] | None = None) -> str:
    _metadata, files = read_snapshot(archive)
    changes = compare_to_current(archive, files, components)
    if not changes:
        return "No differences from the current configuration."
    lines = changes[:120]
    if len(changes) > 120:
        lines.append(f"… {len(changes) - 120} additional file(s) omitted")
    return "\n".join(lines)


def do_tests() -> tuple[int, str]:
    start = time.monotonic()
    suite = unittest.defaultTestLoader.discover(
        str(SCRIPTS / "tests"),
        pattern="test_*.py",
        top_level_dir=str(CONFIG),
    )
    stream = __import__("io").StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    duration = time.monotonic() - start
    summary = (
        f"Tests: {result.testsRun} run in {duration:.2f}s; "
        f"{len(result.failures)} failed, {len(result.errors)} errors, "
        f"{len(result.skipped)} skipped."
    )
    details = stream.getvalue().strip()
    log_event("tests", summary, category="test", severity="error" if not result.wasSuccessful() else "info",
              result="success" if result.wasSuccessful() else "failure")
    return (0 if result.wasSuccessful() else 1), summary + ("\n" + details if details else "")


def confirm(prompt: str) -> bool:
    answer = input(f"{prompt} [y/N] ").strip().lower()
    return answer in {"y", "yes"}


def rofi(options: list[str], prompt: str, *, multi: bool = False) -> str | list[str] | None:
    args = ["rofi", "-dmenu", "-i", "-config", str(ROFI_THEME), "-p", prompt]
    if multi:
        args += ["-multi-select", "-format", "s"]
    try:
        result = subprocess.run(args, input="\n".join(options) + "\n", capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise MaintenanceError(f"Rofi failed: {exc}") from exc
    if result.returncode == 1:
        return None
    if result.returncode:
        raise MaintenanceError(result.stderr.strip() or "Rofi returned an error.")
    if multi:
        return [line for line in result.stdout.splitlines() if line]
    return result.stdout.strip() or None


def write_report(text: str, destination: Path | None = None) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = destination or REPORT_DIR / f"doctor-{datetime.now().strftime('%Y%m%d-%H%M%S')}.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return path


def show_doctor_ui() -> int:
    while True:
        checks = build_diagnostics(full=True)
        report = render_checks(checks)
        options = [*report.splitlines(), "Refresh diagnostics", "Copy report", "Export report",
                   "View activity logs", "Close"]
        selected = rofi(options, "󰒓 Rice Diagnostics")
        if not selected or selected == "Close":
            return doctor_exit_code(checks)
        if selected == "Refresh diagnostics":
            continue
        if selected == "Copy report":
            if not shutil.which("wl-copy"):
                print("wl-copy is not installed; cannot copy the report.", file=sys.stderr)
                continue
            copied = subprocess.run(["wl-copy"], input=report, text=True, check=False)
            print("Report copied." if copied.returncode == 0 else "wl-copy failed.", file=sys.stderr)
        elif selected == "Export report":
            print(write_report(report))
        elif selected == "View activity logs":
            show_logs_ui()
        elif selected.startswith("["):
            details = next((item for item in checks if f"[{item.status.upper()}] {item.module}/{item.name}" == selected), None)
            if details:
                print(f"{details.details}\n{details.suggestion}")


def show_snapshot_ui() -> None:
    actions = ["Create Snapshot", "Snapshot History", "Restore Snapshot", "Compare Snapshot", "Delete Snapshot", "Snapshot Settings", "Close"]
    selected = rofi(actions, "󰒓 Configuration Snapshots")
    if not selected or selected == "Close":
        return
    if selected == "Create Snapshot":
        label = rofi(["manual", "pre-change", "milestone", "Custom label…"], "Snapshot label")
        if label == "Custom label…":
            label = rofi(["my-snapshot"], "Type a snapshot label")
        if not label:
            return
        print(create_snapshot(label))
        return
    if selected == "Snapshot Settings":
        settings = {"retention": retention_limit()}
        values = ["5", "10", "15", "20", "30", "50"]
        current = str(settings["retention"])
        if current not in values:
            values.append(current)
        value_text = rofi(values, f"Snapshot retention (current: {current})")
        if not value_text:
            return
        try:
            value = int(value_text)
        except ValueError as exc:
            raise MaintenanceError("Retention must be a number from 1 to 50.") from exc
        if not 1 <= value <= 50:
            raise MaintenanceError("Retention must be from 1 to 50.")
        snapshot_before_config_change("snapshot-settings", SNAPSHOT_SETTINGS)
        atomic_write_bytes(
            SNAPSHOT_SETTINGS,
            (json.dumps({"retention": value}, indent=2) + "\n").encode(),
            0o600,
        )
        prune_snapshots(value)
        return
    archives = snapshot_list()
    if not archives:
        print("No snapshots exist yet.")
        return
    selected_archive = rofi(
        [f"{item.name}  ·  {item.stat().st_size // 1024} KiB" for item in archives],
        "Select snapshot",
    )
    if not selected_archive:
        return
    archive = next(item for item in archives if item.name in selected_archive)
    if selected == "Snapshot History":
        print("\n".join(f"{item.name}  {item.stat().st_size // 1024} KiB" for item in archives))
    elif selected == "Compare Snapshot":
        other_selected = rofi(
            [f"{item.name}  ·  {item.stat().st_size // 1024} KiB" for item in archives if item != archive],
            "Compare with another snapshot",
        )
        if not other_selected:
            print(snapshot_diff(archive))
            return
        other = next(item for item in archives if item.name in other_selected)
        _first_meta, first = read_snapshot(archive)
        _second_meta, second = read_snapshot(other)
        changed = sorted(path for path in set(first) | set(second) if first.get(path) != second.get(path))
        print("\n".join(changed) or "Snapshots are identical.")
    elif selected == "Delete Snapshot":
        if confirm(f"Delete {archive.name}? This cannot be undone."):
            archive.unlink()
            archive.with_suffix(".json").unlink(missing_ok=True)
            log_event("snapshots", f"Deleted snapshot {archive.name}", category="snapshot")
            print("Snapshot deleted.")
    elif selected == "Restore Snapshot":
        components = sorted({Path(name).parts[0] if len(Path(name).parts) > 1 else "root"
                             for name in read_snapshot(archive)[1]})
        selected_components = rofi(["all", *components], "Restore component(s)", multi=True)
        if not selected_components:
            return
        selected_set = None if "all" in selected_components else set(selected_components)
        changes = compare_to_current(archive, read_snapshot(archive)[1], selected_set)
        print("\n".join(changes) or "No changes.")
        if changes and confirm("Apply this restore? A pre-restore snapshot will be created."):
            print("\n".join(restore_snapshot(archive, selected_set, confirm=True)))


def show_logs_ui() -> None:
    filters: dict[str, str] = {}
    while True:
        options = [
            "Show recent events",
            f"Filter module: {filters.get('module', 'all')}",
            f"Filter severity: {filters.get('severity', 'all')}",
            f"Search: {filters.get('search', 'none')}",
            f"Since date: {filters.get('since', 'all')}",
            "Export filtered logs",
            "Clear all logs",
            "Close",
        ]
        selected = rofi(options, "󰒓 Logs & Activity")
        if not selected or selected == "Close":
            return
        if selected.startswith("Filter module"):
            value = rofi(["all", "display", "audio", "bluetooth", "session", "snapshots", "tests", "diagnostics"],
                         "Filter by module")
            filters.pop("module", None) if value == "all" else filters.update(module=str(value))
        elif selected.startswith("Filter severity"):
            value = rofi(["all", "debug", "info", "warning", "error", "critical"], "Filter severity")
            filters.pop("severity", None) if value == "all" else filters.update(severity=str(value))
        elif selected.startswith("Search"):
            value = input("Search text (blank clears): ").strip()
            filters.pop("search", None) if not value else filters.update(search=value)
        elif selected.startswith("Since date"):
            value = input("Date (YYYY-MM-DD, blank clears): ").strip()
            if value and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                raise MaintenanceError("Date must use YYYY-MM-DD.")
            filters.pop("since", None) if not value else filters.update(since=value)
        elif selected == "Clear all logs":
            if confirm("Clear all rice activity logs?"):
                event_logger().clear_events()
        elif selected == "Show recent events":
            events = filtered_events(**filters)
            lines = [format_event(event) for event in events[-100:]]
            if lines:
                detail = rofi(lines, "Activity details")
                print(detail or "")
            else:
                print("No events match these filters.")
        elif selected == "Export filtered logs":
            events = filtered_events(**filters)
            path = REPORT_DIR / f"events-{datetime.now().strftime('%Y%m%d-%H%M%S')}.jsonl"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in events), encoding="utf-8")
            print(path)


def filtered_events(module: str | None = None, severity: str | None = None,
                    search: str | None = None, since: str | None = None) -> list[dict[str, Any]]:
    events = event_logger().read_events()
    return [
        item for item in events
        if (not module or item.get("component") == module)
        and (not severity or item.get("severity") == severity)
        and (not since or str(item.get("timestamp", ""))[:10] >= since)
        and (not search or search.lower() in json.dumps(item, ensure_ascii=False).lower())
    ]


def format_event(event: dict[str, Any]) -> str:
    return (
        f"{event.get('timestamp', '?')} [{event.get('severity', 'info')}] "
        f"{event.get('component', '?')}: {event.get('description', '')}"
    )


def doctor(args: argparse.Namespace) -> int:
    checks = build_diagnostics(full=args.full, module=args.module)
    output = render_checks(checks)
    print(output)
    log_event("diagnostics", f"Doctor scan completed ({len(checks)} checks)",
              category="diagnostic", severity="error" if doctor_exit_code(checks) == 2 else "info",
              result="success" if doctor_exit_code(checks) == 0 else "warning")
    if args.report:
        destination = Path(args.report).expanduser() if isinstance(args.report, str) else None
        path = write_report(output, destination)
        print(f"Report exported: {path}")
    if args.fix:
        safe_fix()
    return doctor_exit_code(checks)


def safe_fix() -> None:
    print("Safe repairs only refresh existing status modules; no files or services are changed.")
    if not confirm("Refresh Waybar status modules?"):
        return
    pids = process_pids("waybar")
    if not pids:
        raise MaintenanceError("Waybar is not running; no refresh was sent.")
    try:
        for pid in pids:
            os.kill(int(pid), signal.SIGRTMIN + 8)
    except (OSError, ValueError) as exc:
        raise MaintenanceError(f"Could not refresh Waybar status modules: {exc}") from exc
    log_event("repair", "Refreshed Waybar status modules", category="repair")
    print("Waybar refresh signal sent.")


def validate_command(args: argparse.Namespace) -> int:
    checks = validate_configs()
    filtered = [check for check in checks if not args.module or check.module == args.module]
    print(render_checks(filtered))
    return doctor_exit_code(filtered)


def reload_command() -> int:
    checks = [item for item in validate_configs() if item.module == "core"]
    print(render_checks(checks))
    if any(item.status in {"Failed", "Not Installed"} for item in checks):
        print("Hyprland was not reloaded because validation did not pass.", file=sys.stderr)
        return 2
    if not shutil.which("hyprctl"):
        raise MaintenanceError("hyprctl is unavailable; Hyprland was not reloaded.")
    result = run(["hyprctl", "reload"])
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or "hyprctl reload failed."
        log_event("maintenance", f"Hyprland reload failed: {detail}", category="reload",
                  severity="error", result="failure")
        raise MaintenanceError(detail)
    time.sleep(0.3)
    errors = run(["hyprctl", "configerrors"])
    if errors.returncode:
        raise MaintenanceError(errors.stderr.strip() or "Could not verify Hyprland after reload.")
    output = errors.stdout.strip()
    if output and output != "[]":
        try:
            parsed = json.loads(output)
        except json.JSONDecodeError:
            parsed = output
        if parsed:
            raise MaintenanceError(f"Hyprland reported configuration errors after reload: {output}")
    log_event("maintenance", "Hyprland configuration reloaded after validation", category="reload")
    print("Hyprland reloaded successfully. Waybar was left running.")
    return 0


def dependency_checks(full: bool) -> list[Check]:
    checks: list[Check] = []
    for group, binaries in REQUIRED_BINARIES.items():
        missing = [binary for binary in binaries if shutil.which(binary) is None]
        status = "Failed" if group == "core" and missing else "Not Installed" if missing else "Healthy"
        checks.append(Check("dependencies", f"Required: {group}", status,
                            "Missing: " + ", ".join(missing) if missing else "All commands are available."))
    if full:
        for group, binaries in OPTIONAL_BINARIES.items():
            missing = [binary for binary in binaries if shutil.which(binary) is None]
            checks.append(Check("dependencies", f"Optional: {group}",
                                "Not Installed" if missing else "Healthy",
                                "Not installed: " + ", ".join(missing) if missing
                                else "All optional commands are available."))
    return checks


def snapshot_command(args: argparse.Namespace) -> int:
    if args.snapshot_action == "create":
        print(create_snapshot(args.label))
    elif args.snapshot_action == "list":
        print("\n".join(str(path) for path in snapshot_list()) or "No snapshots found.")
    elif args.snapshot_action == "diff":
        print(snapshot_diff(snapshot_archive(args.identifier)))
    elif args.snapshot_action == "compare":
        first = snapshot_archive(args.identifier)
        second = snapshot_archive(args.other)
        first_meta, first_files = read_snapshot(first)
        second_meta, second_files = read_snapshot(second)
        paths = sorted(set(first_files) | set(second_files))
        differences = [
            f"{'ONLY FIRST' if path not in second_files else 'ONLY SECOND' if path not in first_files else 'DIFFERENT'} {path}"
            for path in paths
            if first_files.get(path) != second_files.get(path)
        ]
        print("\n".join(differences) or "Snapshots are identical.")
    elif args.snapshot_action == "restore":
        archive = snapshot_archive(args.identifier)
        components = set(args.component) if args.component else None
        changes = compare_to_current(archive, read_snapshot(archive)[1], components)
        print("\n".join(changes) or "No changes.")
        if not changes:
            return 0
        if not confirm("Restore these files? A pre-restore snapshot will be created."):
            return 1
        print("\n".join(restore_snapshot(archive, components, confirm=True)))
    elif args.snapshot_action == "delete":
        archive = snapshot_archive(args.identifier)
        if not confirm(f"Delete snapshot {archive.name}?"):
            return 1
        archive.unlink()
        archive.with_suffix(".json").unlink(missing_ok=True)
        log_event("snapshots", f"Deleted snapshot {archive.name}", category="snapshot")
        print("Snapshot deleted.")
    elif args.snapshot_action == "retention":
        try:
            value = int(args.value)
        except ValueError as exc:
            raise MaintenanceError("Retention must be an integer from 1 to 50.") from exc
        if not 1 <= value <= 50:
            raise MaintenanceError("Retention must be an integer from 1 to 50.")
        snapshot_before_config_change("snapshot-settings", SNAPSHOT_SETTINGS)
        atomic_write_bytes(
            SNAPSHOT_SETTINGS,
            (json.dumps({"retention": value}, indent=2) + "\n").encode(),
            0o600,
        )
        prune_snapshots(value)
        print(f"Snapshot retention set to {value}.")
    elif args.snapshot_action == "ui":
        show_snapshot_ui()
    return 0


def logs_command(args: argparse.Namespace) -> int:
    if args.limit < 1:
        raise MaintenanceError("Log limit must be at least 1.")
    if args.since:
        try:
            datetime.strptime(args.since, "%Y-%m-%d")
        except ValueError as exc:
            raise MaintenanceError("Since date must use YYYY-MM-DD.") from exc
    log_module = event_logger()
    if args.clear:
        if not confirm("Clear all rice activity logs?"):
            return 1
        log_module.clear_events()
        print("Activity logs cleared.")
        return 0
    events = filtered_events(args.module, args.severity, args.search, args.since)
    if args.export:
        destination = Path(args.export).expanduser()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in events), encoding="utf-8")
        print(destination)
        return 0
    if args.ui:
        show_logs_ui()
    else:
        print("\n".join(format_event(event) for event in events[-args.limit:]) or "No matching events.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rice", description="Rice configuration maintenance and diagnostics.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor_parser = subparsers.add_parser("doctor", help="Inspect rice and system health.")
    doctor_parser.add_argument("--full", action="store_true", help="Include optional dependencies, fonts, and services.")
    doctor_parser.add_argument("--module", choices=MODULES)
    doctor_parser.add_argument("--report", nargs="?", const=True, metavar="PATH")
    doctor_parser.add_argument("--fix", action="store_true", help="Offer only explicitly confirmed safe repairs.")
    doctor_parser.add_argument("--ui", action="store_true")

    validate_parser = subparsers.add_parser("validate", help="Validate current config syntax.")
    validate_parser.add_argument("--module", choices=VALIDATION_MODULES)
    subparsers.add_parser("reload", help="Validate and safely reload Hyprland.")

    snapshot_parser = subparsers.add_parser("snapshot", help="Create and manage configuration snapshots.")
    snapshot_sub = snapshot_parser.add_subparsers(dest="snapshot_action", required=True)
    create = snapshot_sub.add_parser("create")
    create.add_argument("--label", default="manual")
    snapshot_sub.add_parser("list")
    diff = snapshot_sub.add_parser("diff")
    diff.add_argument("identifier")
    compare = snapshot_sub.add_parser("compare")
    compare.add_argument("identifier")
    compare.add_argument("other")
    restore = snapshot_sub.add_parser("restore")
    restore.add_argument("identifier")
    restore.add_argument("--component", action="append")
    delete = snapshot_sub.add_parser("delete")
    delete.add_argument("identifier")
    retention = snapshot_sub.add_parser("retention")
    retention.add_argument("value")
    snapshot_sub.add_parser("ui")

    logs_parser = subparsers.add_parser("logs", help="Search, export, or clear activity events.")
    logs_parser.add_argument("--module")
    logs_parser.add_argument("--severity", choices=["debug", "info", "warning", "error", "critical"])
    logs_parser.add_argument("--search")
    logs_parser.add_argument("--since")
    logs_parser.add_argument("--limit", type=int, default=100)
    logs_parser.add_argument("--export")
    logs_parser.add_argument("--clear", action="store_true")
    logs_parser.add_argument("--ui", action="store_true")

    subparsers.add_parser("test", help="Run repeatable unit and safe integration tests.")
    deps_parser = subparsers.add_parser("dependencies", help="Report installed required and optional tools.")
    deps_parser.add_argument("--full", action="store_true")
    event_parser = subparsers.add_parser("event", help="Record a rice activity event.")
    event_parser.add_argument("component")
    event_parser.add_argument("severity", choices=["debug", "info", "warning", "error", "critical"])
    event_parser.add_argument("description")
    event_parser.add_argument("--category", default="operation")
    event_parser.add_argument("--result", default="success")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            if args.ui:
                return show_doctor_ui()
            return doctor(args)
        if args.command == "validate":
            return validate_command(args)
        if args.command == "reload":
            return reload_command()
        if args.command == "snapshot":
            return snapshot_command(args)
        if args.command == "logs":
            return logs_command(args)
        if args.command == "test":
            code, output = do_tests()
            print(output)
            return code
        if args.command == "dependencies":
            checks = dependency_checks(args.full)
            print(render_checks(checks))
            return doctor_exit_code(checks)
        if args.command == "event":
            log_event(args.component, args.description, category=args.category,
                      severity=args.severity, result=args.result)
            return 0
    except (MaintenanceError, OSError) as exc:
        print(f"rice: {exc}", file=sys.stderr)
        try:
            log_event("maintenance", str(exc), category="error", severity="error", result="failure")
        except OSError:
            pass
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
