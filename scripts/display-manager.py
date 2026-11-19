#!/usr/bin/env python3
"""Hyprland display manager and optional monitor hotplug watcher."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any


CONFIG = Path.home() / ".config" / "hypr"
ROFI_THEME = CONFIG / "rofi" / "command-center.rasi"
STATE_FILE = CONFIG / "display-profiles.json"
RUNTIME_DIR = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
WATCH_STATE = RUNTIME_DIR / "hypr-display-manager.json"
CONFIRM_SECONDS = 20
POLL_SECONDS = 3

TRANSFORMS = {
    0: "Landscape",
    1: "Portrait (90°)",
    2: "Landscape flipped",
    3: "Portrait (270°)",
    4: "Flipped",
    5: "Flipped portrait (90°)",
    6: "Flipped landscape",
    7: "Flipped portrait (270°)",
}
OUTPUT_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")
MODE = re.compile(r"^(?:preferred|[0-9]{2,5}x[0-9]{2,5}(?:@[0-9]+(?:\.[0-9]+)?Hz)?)$")


class DisplayError(RuntimeError):
    pass


def command(args: list[str], timeout: float = 5) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(args, text=True, capture_output=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise DisplayError(f"Could not run {args[0]}: {exc}") from exc
    output = result.stdout.strip()
    if result.returncode or re.match(r"^(?:error\b|unknown request\b)", output, re.IGNORECASE):
        detail = result.stderr.strip() or result.stdout.strip() or "command failed"
        raise DisplayError(detail)
    return result


def notify(title: str, message: str, urgency: str = "normal") -> None:
    if not shutil.which("dunstify"):
        print(f"{title}: {message}", file=sys.stderr)
        return
    subprocess.run(
        ["dunstify", "--app-name=Display Manager", "-u", urgency, title, message],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

def rofi(options: list[str], prompt: str, timeout: int | None = None) -> str | None:
    if not options:
        return None
    if not shutil.which("rofi"):
        raise DisplayError("Rofi is required to use Display Manager.")
    args = [
        "rofi",
        "-dmenu",
        "-i",
        "-config",
        str(ROFI_THEME),
        "-p",
        prompt,
    ]
    try:
        process = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except OSError as exc:
        raise DisplayError(f"Could not open Rofi: {exc}") from exc
    try:
        stdout, stderr = process.communicate("\n".join(options) + "\n", timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
        return None
    if process.returncode not in (0, 1):
        raise DisplayError(stderr.strip() or "Rofi failed.")
    return stdout.strip() if process.returncode == 0 and stdout.strip() else None


def hyprctl_json(*args: str) -> Any:
    result = command(["hyprctl", "-j", *args])
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise DisplayError(f"Hyprland returned invalid JSON for {' '.join(args)}.") from exc


def drm_connectors() -> dict[str, bool]:
    connectors: dict[str, bool] = {}
    for status_file in Path("/sys/class/drm").glob("card*-*/status"):
        connector = status_file.parent.name.partition("-")[2]
        if not connector:
            continue
        try:
            connectors[connector] = status_file.read_text(encoding="utf-8").strip() == "connected"
        except OSError:
            continue
    return connectors


def is_internal(name: str) -> bool:
    return name.lower().startswith(("edp", "lvds", "dsi"))


def monitors() -> list[dict[str, Any]]:
    try:
        records = hyprctl_json("monitors", "all")
    except DisplayError:
        records = hyprctl_json("monitors")
    if not isinstance(records, list):
        raise DisplayError("Hyprland did not return a monitor list.")
    connectors = drm_connectors()
    result: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict) or not record.get("name"):
            continue
        name = str(record["name"])
        record["connected"] = connectors.get(name, True)
        record["internal"] = is_internal(name)
        result[name] = record
    for name, connected in connectors.items():
        if name not in result:
            result[name] = {
                "name": name,
                "description": "Display connector",
                "connected": connected,
                "internal": is_internal(name),
                "disabled": True,
                "availableModes": [],
            }
    return sorted(result.values(), key=lambda item: (not item["internal"], item["name"].lower()))


def connected_names(records: list[dict[str, Any]] | None = None) -> set[str]:
    return {item["name"] for item in (records or monitors()) if item.get("connected")}


def active_records(records: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    return [
        item
        for item in (records or monitors())
        if item.get("connected") and not item.get("disabled", False)
    ]


def mode_for(record: dict[str, Any]) -> str:
    width = record.get("width", 0)
    height = record.get("height", 0)
    refresh = record.get("refreshRate", 0)
    if width and height and refresh:
        return f"{width}x{height}@{refresh:.2f}Hz"
    return "preferred"


def current_setting(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": record["name"],
        "disabled": bool(record.get("disabled", False)),
        "mode": mode_for(record),
        "x": int(record.get("x", 0)),
        "y": int(record.get("y", 0)),
        "scale": float(record.get("scale", 1)),
        "transform": int(record.get("transform", 0)),
        "mirror": record.get("mirrorOf") if record.get("mirrorOf") not in (None, "none") else None,
    }


def runtime_layout(records: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    return [
        current_setting(item)
        for item in (records or monitors())
        if item.get("connected") and item.get("name")
    ]


def validate_setting(setting: dict[str, Any], by_name: dict[str, dict[str, Any]]) -> None:
    name = setting.get("name")
    if not isinstance(name, str) or not OUTPUT_NAME.fullmatch(name):
        raise DisplayError("The monitor name is not valid.")
    if name not in by_name or not by_name[name].get("connected"):
        raise DisplayError(f"{name} is no longer connected.")
    if setting.get("disabled"):
        return
    for coordinate in ("x", "y"):
        value = setting.get(coordinate, 0)
        if not isinstance(value, int) or not -100_000 <= value <= 100_000:
            raise DisplayError(f"Position for {name} is not valid.")
    mode = str(setting.get("mode", "preferred"))
    if not MODE.fullmatch(mode):
        raise DisplayError(f"Invalid display mode for {name}.")
    available = by_name[name].get("availableModes") or []
    current = mode_for(by_name[name])
    if mode != "preferred" and available and mode not in available and mode != current:
        raise DisplayError(f"{mode} is not available on {name}.")
    scale = setting.get("scale", 1)
    if not isinstance(scale, (int, float)) or not 0.5 <= float(scale) <= 3:
        raise DisplayError(f"Scale for {name} must be between 0.5 and 3.")
    transform = setting.get("transform", 0)
    if not isinstance(transform, int) or transform not in TRANSFORMS:
        raise DisplayError(f"Orientation for {name} is not supported.")
    mirror = setting.get("mirror")
    if mirror is not None and (not isinstance(mirror, str) or not OUTPUT_NAME.fullmatch(mirror)):
        raise DisplayError(f"Mirror source for {name} is not valid.")
    if mirror is not None and (mirror == name or mirror not in by_name or not by_name[mirror].get("connected")):
        raise DisplayError(f"Mirror source for {name} is not connected.")


def monitor_lua(setting: dict[str, Any]) -> str:
    name = setting["name"]
    if setting.get("disabled"):
        return f"hl.monitor({{ output = {json.dumps(name)}, disabled = true }})"
    position = "0x0" if setting.get("mirror") else f"{setting['x']}x{setting['y']}"
    scale = f"{float(setting.get('scale', 1)):g}"
    fields = [
        f"output = {json.dumps(name)}",
        f"mode = {json.dumps(setting.get('mode', 'preferred'))}",
        f"position = {json.dumps(position)}",
        f"scale = {json.dumps(scale)}",
        f"transform = {int(setting.get('transform', 0))}",
    ]
    if setting.get("mirror"):
        fields.append(f"mirror = {json.dumps(setting['mirror'])}")
    return "hl.monitor({ " + ", ".join(fields) + " })"


def apply_layout(layout: list[dict[str, Any]]) -> None:
    records = monitors()
    by_name = {item["name"]: item for item in records}
    for setting in layout:
        validate_setting(setting, by_name)
    enabled = [item for item in layout if not item.get("disabled")]
    if not enabled:
        raise DisplayError("At least one display must remain enabled.")
    ordered = enabled + [item for item in layout if item.get("disabled")]
    for setting in ordered:
        command(["hyprctl", "eval", monitor_lua(setting)])


def restore_layout(layout: list[dict[str, Any]]) -> None:
    available = connected_names()
    restore = [item for item in layout if item.get("name") in available]
    if not any(not item.get("disabled") for item in restore):
        internal = next((item for item in monitors() if item.get("connected") and item.get("internal")), None)
        if internal:
            restore.insert(0, {
                "name": internal["name"],
                "disabled": False,
                "mode": "preferred",
                "x": 0,
                "y": 0,
                "scale": 1,
                "transform": 0,
            })
    if restore:
        apply_layout(restore)


def load_profiles() -> list[dict[str, Any]]:
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except (OSError, json.JSONDecodeError) as exc:
        notify("Display Manager", f"Could not read saved display profile: {exc}", "critical")
        return []
    if not isinstance(data, dict):
        notify("Display Manager", "Saved display profile is malformed and was ignored.", "critical")
        return []
    profiles = data.get("profiles")
    if profiles is None and isinstance(data.get("layout"), list):
        profiles = [data]
    if not isinstance(profiles, list):
        notify("Display Manager", "Saved display profile is malformed and was ignored.", "critical")
        return []
    valid_profiles = []
    for profile in profiles:
        layout = profile.get("layout") if isinstance(profile, dict) else None
        if (
            isinstance(layout, list)
            and bool(layout)
            and all(isinstance(item, dict) and isinstance(item.get("name"), str) for item in layout)
        ):
            valid_profiles.append(profile)
    if len(valid_profiles) != len(profiles):
        notify("Display Manager", "Malformed saved layouts were ignored.", "critical")
    return valid_profiles


def load_profile(records: list[dict[str, Any]] | None = None) -> dict[str, Any] | None:
    profiles = load_profiles()
    if records is not None:
        profiles = [profile for profile in profiles if saved_layout_ready(profile, records)]
    return max(profiles, key=lambda profile: profile.get("savedAt", 0), default=None)


def save_profile(layout: list[dict[str, Any]]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    profile = {"savedAt": int(time.time()), "layout": layout}
    signature = {item["name"] for item in layout}
    profiles = [
        item
        for item in load_profiles()
        if {monitor["name"] for monitor in item["layout"]} != signature
    ]
    profiles.append(profile)
    payload = {"version": 2, "profiles": profiles}
    fd, temp_name = tempfile.mkstemp(prefix=".display-profiles-", dir=STATE_FILE.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2)
            file.write("\n")
        os.replace(temp_name, STATE_FILE)
    except OSError:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def logical_size(record: dict[str, Any]) -> tuple[int, int]:
    width = int(record.get("width", 0))
    height = int(record.get("height", 0))
    if not width or not height:
        for mode in record.get("availableModes") or []:
            match = re.match(r"([0-9]+)x([0-9]+)", mode)
            if match:
                width, height = int(match.group(1)), int(match.group(2))
                break
    if not width or not height:
        width, height = 1920, 1080
    if int(record.get("transform", 0)) % 4 in (1, 3):
        width, height = height, width
    scale = float(record.get("scale", 1))
    return max(1, round(width / scale)), max(1, round(height / scale))


def status_line(record: dict[str, Any]) -> str:
    name = record["name"]
    if not record.get("connected"):
        return f"{name}  ·  Disconnected"
    if record.get("disabled", False):
        return f"{name}  ·  Connected, disabled"
    is_primary = (
        record.get("x") == 0
        and record.get("y") == 0
        and record.get("mirrorOf") in (None, "none")
    )
    return (
        f"{name}  ·  {record.get('width', '?')}×{record.get('height', '?')} "
        f"@ {float(record.get('refreshRate', 0)):.2f} Hz  ·  Scale {record.get('scale', 1)}"
        f"{'  ·  Primary' if is_primary else ''}"
    )


def display_card(record: dict[str, Any]) -> str:
    kind = "Built-in" if record.get("internal") else "External"
    return f"{kind}: {record.get('description', record['name'])} [{record['name']}] — {status_line(record)}"


def choose_output(records: list[dict[str, Any]], prompt: str) -> dict[str, Any] | None:
    choices = [item for item in records if item.get("connected")]
    if not choices:
        notify("Display Manager", "No connected displays were detected.", "critical")
        return None
    options = [display_card(item) for item in choices]
    selected = rofi(options, prompt)
    return next((item for item, text in zip(choices, options) if text == selected), None)


def transaction(label: str, layout: list[dict[str, Any]]) -> bool:
    previous = runtime_layout()
    try:
        apply_layout(layout)
    except DisplayError as exc:
        try:
            restore_layout(previous)
        except DisplayError as rollback_error:
            notify("Display change failed", f"{exc}; rollback also failed: {rollback_error}", "critical")
            return False
        notify("Display change failed", str(exc), "critical")
        return False

    notify("Display configuration changed", f"{label}. Confirm within {CONFIRM_SECONDS} seconds or it will revert.")
    choice = rofi(
        [
            f"Keep this layout — save for startup and reconnection",
            "Keep this layout for this session only",
            "Revert to the previous layout",
        ],
        f"Confirm display layout ({CONFIRM_SECONDS}s)",
        timeout=CONFIRM_SECONDS,
    )
    if choice not in (
        "Keep this layout — save for startup and reconnection",
        "Keep this layout for this session only",
    ):
        try:
            restore_layout(previous)
            notify("Display layout reverted", "The previous monitor layout has been restored.")
        except DisplayError as exc:
            notify("Display rollback failed", str(exc), "critical")
        return False

    if choice.startswith("Keep this layout —"):
        try:
            save_profile(runtime_layout())
        except OSError as exc:
            notify("Layout active, but not saved", str(exc), "critical")
            return True
        notify("Display layout saved", "It will be restored at startup and when its monitors reconnect.")
    else:
        notify("Display layout applied", f"{label} is active for this session.")
    return True


def internal_output(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    return next((item for item in records if item.get("connected") and item.get("internal")), None)


def external_outputs(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in records if item.get("connected") and not item.get("internal")]


def common_mirror_mode(first: dict[str, Any], second: dict[str, Any]) -> str | None:
    first_modes = set(first.get("availableModes") or [])
    second_modes = set(second.get("availableModes") or [])
    first_current = mode_for(first)
    second_current = mode_for(second)
    if first_current != "preferred":
        first_modes.add(first_current)
    if second_current != "preferred":
        second_modes.add(second_current)
    common = first_modes & second_modes
    if not common:
        return None

    def rank(mode: str) -> tuple[int, float]:
        match = re.fullmatch(r"([0-9]+)x([0-9]+)@([0-9.]+)Hz", mode)
        if not match:
            return (0, 0)
        width, height, refresh = match.groups()
        return (int(width) * int(height), float(refresh))

    return max(common, key=rank)


def preset_layout(preset: str, external_name: str | None = None, side: str = "right") -> tuple[str, list[dict[str, Any]]] | None:
    records = monitors()
    internal = internal_output(records)
    externals = external_outputs(records)
    active = active_records(records)
    layout = runtime_layout(records)
    by_name = {item["name"]: item for item in records}

    if preset == "laptop":
        target = internal or (active[0] if active else None)
        if not target:
            notify("Display Manager", "No connected display is available.", "critical")
            return None
        settings = {item["name"]: item for item in layout}
        if target["name"] not in settings:
            settings[target["name"]] = {
                "name": target["name"], "disabled": False, "mode": "preferred",
                "x": 0, "y": 0, "scale": 1, "transform": 0,
            }
        settings[target["name"]].update(disabled=False, x=0, y=0, mirror=None)
        for item in records:
            if item.get("connected") and item["name"] != target["name"]:
                settings.setdefault(item["name"], {"name": item["name"]})["disabled"] = True
        return "Laptop only", list(settings.values())

    if preset in ("external", "extend", "mirror", "presentation"):
        external = by_name.get(external_name or "")
        if not external or not external.get("connected") or external.get("internal"):
            external = choose_output(externals, "󰍹  Choose external display")
        if not external:
            return None
        if preset == "external":
            settings = {item["name"]: item for item in layout}
            settings[external["name"]] = {
                "name": external["name"], "disabled": False, "mode": "preferred",
                "x": 0, "y": 0, "scale": 1, "transform": 0,
            }
            for item in records:
                if item.get("connected") and item["name"] != external["name"]:
                    settings.setdefault(item["name"], {"name": item["name"]})["disabled"] = True
            return f"{external['name']} only", list(settings.values())

        source = internal or next((item for item in active if item["name"] != external["name"]), None)
        if not source:
            notify("Display Manager", "Could not identify a built-in or active display to pair with.", "critical")
            return None
        settings = {item["name"]: item for item in layout}
        source_setting = settings.get(source["name"]) or {
            "name": source["name"], "disabled": False, "mode": "preferred",
            "x": 0, "y": 0, "scale": 1, "transform": 0,
        }
        source_setting.update(disabled=False, mirror=None)
        settings[source["name"]] = source_setting
        ext_setting = settings.get(external["name"]) or {
            "name": external["name"], "disabled": False, "mode": "preferred",
            "x": 0, "y": 0, "scale": 1, "transform": 0,
        }
        ext_setting.update(disabled=False, mode="preferred", mirror=None)
        if preset == "mirror":
            mode = common_mirror_mode(source, external)
            if not mode:
                notify(
                    "Mirroring unavailable",
                    f"{source['name']} and {external['name']} have no common reported resolution and refresh rate.",
                    "critical",
                )
                return None
            source_setting.update(mode=mode, x=0, y=0)
            ext_setting.update(mode=mode, x=0, y=0, mirror=source["name"])
        else:
            sw, sh = logical_size(source)
            ew, eh = logical_size(external)
            if preset == "presentation":
                source_setting.update(x=ew, y=0)
                ext_setting.update(x=0, y=0)
            elif side == "left":
                source_setting.update(x=ew, y=0)
                ext_setting.update(x=0, y=0)
            elif side == "above":
                source_setting.update(x=0, y=eh)
                ext_setting.update(x=0, y=0)
            elif side == "below":
                source_setting.update(x=0, y=0)
                ext_setting.update(x=0, y=sh)
            else:
                source_setting.update(x=0, y=0)
                ext_setting.update(x=sw, y=0)
        settings[source["name"]] = source_setting
        settings[external["name"]] = ext_setting
        if preset in ("external", "presentation"):
            for item in records:
                if item.get("connected") and item["name"] not in (source["name"], external["name"]):
                    settings.setdefault(item["name"], {"name": item["name"]})["disabled"] = True
        title = {
            "extend": f"Extend {external['name']} {side}",
            "mirror": f"Mirror to {external['name']}",
            "presentation": f"Presentation on {external['name']}",
        }[preset]
        return title, list(settings.values())
    return None


def apply_preset(preset: str, output: str | None = None) -> None:
    side = "right"
    if preset == "extend":
        position = rofi(
            ["Right of laptop", "Left of laptop", "Above laptop", "Below laptop"],
            "󰍹  Position external display",
        )
        if not position:
            return
        side = {
            "Right of laptop": "right",
            "Left of laptop": "left",
            "Above laptop": "above",
            "Below laptop": "below",
        }[position]
    result = preset_layout(preset, output, side)
    if result:
        transaction(result[0], result[1])


def select_mode(record: dict[str, Any], setting: dict[str, Any]) -> None:
    modes = list(dict.fromkeys(record.get("availableModes") or []))
    current = mode_for(record)
    if current not in modes and current != "preferred":
        modes.insert(0, current)
    if not modes:
        modes = ["preferred"]
    selected = rofi(modes, f"Resolution / refresh — {record['name']}")
    if selected:
        setting.update(mode=selected, disabled=False, mirror=None)
        transaction(f"{record['name']} set to {selected}", replace_setting(setting))


def replace_setting(updated: dict[str, Any]) -> list[dict[str, Any]]:
    layout = runtime_layout()
    found = False
    for item in layout:
        if item["name"] == updated["name"]:
            item.update(updated)
            found = True
    if not found:
        layout.append(updated)
    return layout


def configure_output(record: dict[str, Any]) -> None:
    name = record["name"]
    setting = current_setting(record)
    actions = [
        "Choose resolution and refresh rate",
        "Set scaling",
        "Set orientation",
        "Position relative to another display",
        "Make this the primary display",
        "Enable this display" if record.get("disabled") else "Disable this display",
        "Back",
    ]
    action = rofi(actions, f"Display settings — {name}")
    if not action or action == "Back":
        return
    if action == "Choose resolution and refresh rate":
        select_mode(record, setting)
    elif action == "Set scaling":
        scale = rofi(["0.75", "1.0", "1.25", "1.5", "1.75", "2.0"], f"Scale — {name}")
        if scale:
            setting.update(scale=float(scale), disabled=False, mirror=None)
            transaction(f"Scale for {name} set to {scale}", replace_setting(setting))
    elif action == "Set orientation":
        options = [f"{value}: {label}" for value, label in TRANSFORMS.items()]
        selected = rofi(options, f"Orientation — {name}")
        if selected:
            transform = int(selected.split(":", 1)[0])
            setting.update(transform=transform, disabled=False, mirror=None)
            transaction(f"Orientation for {name} changed", replace_setting(setting))
    elif action == "Position relative to another display":
        others = [item for item in active_records() if item["name"] != name]
        reference = choose_output(others, f"Place {name} relative to")
        if reference:
            relation = rofi(["Right of", "Left of", "Above", "Below"], "󰍹  Choose position")
            if relation:
                rw, rh = logical_size(reference)
                tw, th = logical_size(record)
                x, y = int(reference.get("x", 0)), int(reference.get("y", 0))
                if relation == "Right of":
                    x += rw
                elif relation == "Left of":
                    x -= tw
                elif relation == "Above":
                    y -= th
                else:
                    y += rh
                setting.update(x=x, y=y, disabled=False, mirror=None)
                transaction(f"Positioned {name} {relation.lower()} {reference['name']}", replace_setting(setting))
    elif action == "Make this the primary display":
        layout = runtime_layout()
        selected_record = next((item for item in layout if item["name"] == name), setting)
        selected_record.update(x=0, y=0, disabled=False, mirror=None)
        others = [item for item in layout if item["name"] != name and not item.get("disabled")]
        x = logical_size(record)[0]
        for item in others:
            item.update(x=x, y=0, mirror=None)
            source = next((candidate for candidate in monitors() if candidate["name"] == item["name"]), {})
            x += logical_size(source)[0] if source else 1920
        transaction(f"{name} is now primary", layout)
    elif action == "Enable this display":
        layout = runtime_layout()
        others = [item for item in layout if item["name"] != name and not item.get("disabled")]
        x = sum(logical_size(next((candidate for candidate in monitors() if candidate["name"] == item["name"]), {}))[0] for item in others)
        setting.update(disabled=False, mode="preferred", x=x, y=0, mirror=None)
        transaction(f"{name} enabled", replace_setting(setting))
    elif action == "Disable this display":
        layout = runtime_layout()
        enabled_count = sum(not item.get("disabled") for item in layout)
        if enabled_count <= 1:
            notify("Display Manager", "The last active display cannot be disabled.", "critical")
            return
        setting["disabled"] = True
        transaction(f"{name} disabled", replace_setting(setting))


def save_current_layout() -> None:
    layout = runtime_layout()
    if not layout:
        notify("Display Manager", "No connected monitor layout is available to save.", "critical")
        return
    try:
        save_profile(layout)
    except OSError as exc:
        notify("Display Manager", f"Could not save layout: {exc}", "critical")
        return
    notify("Display layout saved", "This layout will be restored at startup when its displays are connected.")


def reapply_saved_layout() -> None:
    records = monitors()
    profiles = [profile for profile in load_profiles() if saved_layout_ready(profile, records)]
    if not profiles:
        notify("Display Manager", "Connect a previously saved display setup before restoring it.", "critical")
        return
    options = [
        f"{', '.join(item['name'] for item in profile['layout'])} — "
        f"saved {time.strftime('%Y-%m-%d %H:%M', time.localtime(profile.get('savedAt', 0)))}"
        for profile in profiles
    ]
    selected = rofi(options, "󰍹  Choose saved display layout")
    if not selected:
        return
    profile = next((profile for profile, label in zip(profiles, options) if label == selected), None)
    if not profile:
        return
    transaction("Saved display layout", profile["layout"])


def display_manager() -> None:
    records = monitors()
    options = [display_card(item) for item in records]
    actions: dict[str, tuple[str, str | None]] = {}
    for item in records:
        actions[display_card(item)] = ("info", item["name"])
    options.extend([
        "Preset: Laptop only",
        "Preset: External display only",
        "Preset: Extend displays",
        "Preset: Mirror displays",
        "Preset: Presentation mode",
    ])
    for item in records:
        if item.get("connected"):
            text = f"Configure: {item['name']}"
            options.append(text)
            actions[text] = ("configure", item["name"])
    options.extend([
        "Reapply saved layout (with rollback)",
        "Save current layout for startup/reconnect",
        "Refresh monitor list",
        "Close",
    ])
    for preset in ("laptop", "external", "extend", "mirror", "presentation"):
        actions[f"Preset: {dict(laptop='Laptop only', external='External display only', extend='Extend displays', mirror='Mirror displays', presentation='Presentation mode')[preset]}"] = ("preset", preset)
    actions["Save current layout for startup/reconnect"] = ("save", "")
    actions["Reapply saved layout (with rollback)"] = ("reapply", "")

    selected = rofi(options, "󰍹  Display Manager")
    if not selected or selected == "Close":
        return
    if selected == "Refresh monitor list":
        display_manager()
        return
    action, value = actions.get(selected, ("", None))
    if action == "info" and value:
        record = next((item for item in records if item["name"] == value), None)
        if record:
            modes = ", ".join(record.get("availableModes") or []) or "Not reported while disconnected"
            notify(value, f"{status_line(record)}\nAvailable modes: {modes}")
    elif action == "configure" and value:
        record = next((item for item in records if item["name"] == value), None)
        if record:
            configure_output(record)
    elif action == "preset" and value:
        apply_preset(value)
    elif action == "save":
        save_current_layout()
    elif action == "reapply":
        reapply_saved_layout()


def saved_layout_ready(profile: dict[str, Any], records: list[dict[str, Any]]) -> bool:
    present = {item["name"] for item in records if item.get("connected")}
    layout = profile.get("layout", [])
    saved = {item.get("name") for item in layout if isinstance(item, dict)}
    return bool(saved) and saved == present


def restore_saved_layout(profile: dict[str, Any], label: str) -> bool:
    previous = runtime_layout()
    try:
        apply_layout(profile["layout"])
    except DisplayError as exc:
        try:
            restore_layout(previous)
        except DisplayError as rollback_error:
            notify("Saved display layout failed", f"{exc}; safe fallback also failed: {rollback_error}", "critical")
            return False
        notify("Saved display layout unavailable", f"{exc}. The current safe layout was retained.", "critical")
        return False
    notify("Display layout restored", label)
    return True


def action_notification(output: str) -> None:
    if not shutil.which("dunstify"):
        return
    try:
        result = subprocess.run(
            [
                "dunstify",
                "--app-name=Display Manager",
                "--expire-time=15000",
                "--action=extend,Extend",
                "--action=mirror,Mirror",
                "--action=external,External only",
                "--action=manager,Open manager",
                "--wait",
                "External display connected",
                f"{output} is ready. Choose a layout or press Super + Shift + M.",
            ],
            text=True,
            capture_output=True,
            timeout=17,
        )
    except (OSError, subprocess.TimeoutExpired):
        return
    action = result.stdout.strip()
    if action in ("extend", "mirror", "external"):
        subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "--preset", action, output],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    elif action == "manager":
        subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve())],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )


def write_watch_state(names: set[str]) -> None:
    WATCH_STATE.parent.mkdir(parents=True, exist_ok=True)
    WATCH_STATE.write_text(json.dumps(sorted(names)), encoding="utf-8")


def read_watch_state() -> set[str] | None:
    try:
        names = json.loads(WATCH_STATE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return set(names) if isinstance(names, list) and all(isinstance(item, str) for item in names) else None


def watch_displays() -> None:
    time.sleep(3)
    try:
        records = monitors()
    except DisplayError as exc:
        notify("Display watcher unavailable", str(exc), "critical")
        return
    current = {item["name"] for item in records if item.get("connected")}
    try:
        write_watch_state(current)
    except OSError as exc:
        notify("Display watcher unavailable", f"Could not save monitor state: {exc}", "critical")
        return
    profile = load_profile(records)
    if profile and saved_layout_ready(profile, records):
        restore_saved_layout(profile, "Your saved layout is active.")
    while True:
        time.sleep(POLL_SECONDS)
        try:
            records = monitors()
        except DisplayError:
            continue
        current = {item["name"] for item in records if item.get("connected")}
        previous = read_watch_state() or current
        appeared = current - previous
        disappeared = previous - current
        try:
            write_watch_state(current)
        except OSError as exc:
            notify("Display watcher error", f"Could not save monitor state: {exc}", "critical")
            continue
        for output in appeared:
            record = next((item for item in records if item["name"] == output), {})
            if not record.get("internal"):
                threading.Thread(target=action_notification, args=(output,), daemon=True).start()
        for output in disappeared:
            record = next((item for item in records if item["name"] == output), {})
            if not record.get("internal"):
                notify("External display disconnected", f"{output} was removed. Hyprland moved its workspaces to the remaining displays.")
        profile = load_profile(records)
        if profile and appeared and saved_layout_ready(profile, records):
            restore_saved_layout(profile, "Your remembered monitor layout was restored.")


def main() -> int:
    try:
        if len(sys.argv) > 1 and sys.argv[1] == "--watch":
            watch_displays()
        elif len(sys.argv) > 1 and sys.argv[1] == "--preset" and len(sys.argv) >= 3:
            apply_preset(sys.argv[2], sys.argv[3] if len(sys.argv) >= 4 else None)
        else:
            display_manager()
    except DisplayError as exc:
        notify("Display Manager error", str(exc), "critical")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
