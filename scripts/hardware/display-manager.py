#!/usr/bin/env python3
"""Hyprland display manager and optional monitor hotplug watcher."""

from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import fcntl
import select
from contextlib import contextmanager
from pathlib import Path
from typing import Any


CONFIG = Path.home() / ".config" / "hypr"
ROFI_THEME = CONFIG / "rofi" / "command-center.rasi"
STATE_FILE = CONFIG / "state" / "display-profiles.json"
DISPLAY_PREFERENCES = CONFIG / "state" / "display-preferences.json"
RUNTIME_DIR = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
WATCH_LOCK = RUNTIME_DIR / "hypr-display-manager.lock"
APPLY_LOCK = RUNTIME_DIR / "hypr-display-manager-apply.lock"
PRESENTATION_STATE = RUNTIME_DIR / "hypr-display-presentation.json"
SESSION_PRESET_STATE = RUNTIME_DIR / "hypr-session-preset.json"
CONFIRM_SECONDS = 20
EVENT_DEBOUNCE_SECONDS = 0.35

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
NAMED_WORKSPACE = re.compile(r"^name:[A-Za-z0-9][A-Za-z0-9_. -]{0,31}$")
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


@contextmanager
def display_operation_lock(timeout: float = 0):
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    lock_file = APPLY_LOCK.open("a")
    deadline = time.monotonic() + timeout
    while True:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            if time.monotonic() >= deadline:
                lock_file.close()
                yield False
                return
            time.sleep(0.1)
    try:
        yield True
    finally:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        lock_file.close()


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


def log_event(description: str, *, severity: str = "info", result: str = "success") -> None:
    try:
        from scripts.core.rice_events import log_event as write_event
        write_event(
            "display",
            description,
            category="display",
            severity=severity,
            result=result,
        )
    except (ImportError, OSError) as exc:
        print(f"Display Manager: could not write activity log: {exc}", file=sys.stderr)


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


def hypr_dispatch(expression: str) -> subprocess.CompletedProcess[str]:
    return command(["hyprctl", "dispatch", expression])


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
    # These are DRM connector types, not machine-specific connector numbers.
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
        if name == "FALLBACK":
            continue
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
                "width": 0,
                "height": 0,
                "refreshRate": 0,
                "scale": 1,
                "transform": 0,
                "x": 0,
                "y": 0,
                "mirrorOf": "none",
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
        "mirror": None,
    }


def runtime_layout(records: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    records = records or monitors()
    by_id = {str(item.get("id")): item for item in records if item.get("id") is not None}
    layout = []
    for item in records:
        if not item.get("connected") or not item.get("name"):
            continue
        setting = current_setting(item)
        mirror_id = item.get("mirrorOf")
        if not item.get("disabled") and mirror_id not in (None, "none"):
            source = by_id.get(str(mirror_id))
            if source and source.get("name") != item["name"]:
                setting["mirror"] = source["name"]
        layout.append(setting)
    return layout


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
        return (
            "hl.monitor({ "
            f"output = {json.dumps(name)}, disabled = true, mirror = \"\" "
            "})"
        )
    position = "0x0" if setting.get("mirror") else f"{setting['x']}x{setting['y']}"
    scale = f"{float(setting.get('scale', 1)):g}"
    fields = [
        f"output = {json.dumps(name)}",
        "disabled = false",
        f"mode = {json.dumps(setting.get('mode', 'preferred'))}",
        f"position = {json.dumps(position)}",
        f"scale = {json.dumps(scale)}",
        f"transform = {int(setting.get('transform', 0))}",
    ]
    fields.append(f"mirror = {json.dumps(setting.get('mirror') or '')}")
    return "hl.monitor({ " + ", ".join(fields) + " })"


def native_mirroring_is_safe() -> bool:
    """Fail closed until a stable release containing the renderer fix is verified."""
    return False


def setting_rectangle(
    setting: dict[str, Any],
    by_name: dict[str, dict[str, Any]],
) -> tuple[int, int, int, int]:
    record = dict(by_name[setting["name"]])
    match = re.fullmatch(
        r"([0-9]+)x([0-9]+)(?:@[0-9]+(?:\.[0-9]+)?Hz)?",
        str(setting.get("mode", "preferred")),
    )
    if match:
        record["width"], record["height"] = int(match.group(1)), int(match.group(2))
    record["scale"] = setting.get("scale", record.get("scale", 1))
    record["transform"] = setting.get("transform", record.get("transform", 0))
    width, height = logical_size(record)
    x, y = setting.get("x", 0), setting.get("y", 0)
    return x, y, x + width, y + height


def rectangles_overlap(
    first: tuple[int, int, int, int],
    second: tuple[int, int, int, int],
) -> bool:
    return (
        first[0] < second[2]
        and second[0] < first[2]
        and first[1] < second[3]
        and second[1] < first[3]
    )


def monitor_setting_applied(setting: dict[str, Any], by_name: dict[str, dict[str, Any]]) -> bool:
    record = by_name.get(setting["name"])
    if not record or bool(record.get("disabled", False)) != bool(setting.get("disabled")):
        return False
    if setting.get("disabled"):
        return True
    if record.get("x") != setting.get("x", 0) or record.get("y") != setting.get("y", 0):
        return False
    mirror_id = record.get("mirrorOf")
    if not setting.get("mirror"):
        return mirror_id in (None, "none", "")
    source = by_name.get(setting["mirror"])
    return bool(source) and str(mirror_id) in (str(source.get("id")), setting["mirror"])


def apply_monitor_setting(setting: dict[str, Any], timeout: float = 5) -> None:
    records = monitors()
    by_name = {item["name"]: item for item in records}
    validate_setting(setting, by_name)
    command(["hyprctl", "eval", monitor_lua(setting)])

    deadline = time.monotonic() + timeout
    while True:
        records = monitors()
        by_name = {item["name"]: item for item in records}
        if monitor_setting_applied(setting, by_name):
            return
        if time.monotonic() >= deadline:
            raise DisplayError(f"Hyprland did not apply the monitor rule for {setting['name']}.")
        time.sleep(0.1)


def staging_position(output: str, records: list[dict[str, Any]]) -> int:
    right_edges = [
        item.get("x", 0) + logical_size(item)[0]
        for item in records
        if item.get("connected")
        and not item.get("disabled", False)
        and item.get("name") != output
        and item.get("mirrorOf") in (None, "none")
    ]
    return max([0, *right_edges])


def apply_layout(layout: list[dict[str, Any]]) -> None:
    if not layout:
        raise DisplayError("The requested display layout is empty.")
    names = [setting.get("name") for setting in layout]
    if len(names) != len(set(names)):
        raise DisplayError("The requested layout contains duplicate monitor rules.")
    if any(setting.get("mirror") for setting in layout) and not native_mirroring_is_safe():
        raise DisplayError(
            "Native mirroring remains disabled because no stable release with the "
            "mirror-disconnect renderer fix has been verified."
        )
    enabled = [item for item in layout if not item.get("disabled")]
    if not enabled:
        raise DisplayError("At least one display must remain enabled.")
    by_name = {item["name"]: item for item in monitors()}
    for setting in layout:
        validate_setting(setting, by_name)
    for first_index, first in enumerate(enabled):
        if first.get("mirror"):
            continue
        first_rect = setting_rectangle(first, by_name)
        for second in enabled[first_index + 1:]:
            if not second.get("mirror") and rectangles_overlap(first_rect, setting_rectangle(second, by_name)):
                raise DisplayError(
                    f"The requested positions for {first['name']} and {second['name']} overlap."
                )

    enabled_names = {item["name"] for item in enabled}
    pending = {item["name"]: item for item in enabled}
    while pending:
        records = monitors()
        by_name = {item["name"]: item for item in records}
        active = [
            item for item in records
            if item.get("connected") and not item.get("disabled", False)
        ]

        if any(item["name"] in enabled_names for item in active):
            for setting in layout:
                record = by_name.get(setting["name"])
                if setting.get("disabled") and record and not record.get("disabled", False):
                    apply_monitor_setting(setting)
            records = monitors()
            by_name = {item["name"]: item for item in records}
            active = [
                item for item in records
                if item.get("connected") and not item.get("disabled", False)
            ]

        ready = None
        for setting in pending.values():
            target_rect = setting_rectangle(setting, by_name)
            if not any(
                item["name"] != setting["name"]
                and item.get("mirrorOf") in (None, "none")
                and rectangles_overlap(
                    target_rect,
                    (
                        item.get("x", 0),
                        item.get("y", 0),
                        item.get("x", 0) + logical_size(item)[0],
                        item.get("y", 0) + logical_size(item)[1],
                    ),
                )
                for item in active
            ):
                ready = setting
                break

        if ready:
            apply_monitor_setting(ready)
            pending.pop(ready["name"])
            continue

        if not active:
            raise DisplayError("No active display is available to stage the requested layout.")

        stage = next(
            (
                item for item in pending.values()
                if by_name[item["name"]].get("disabled", False)
                or by_name[item["name"]].get("x") != staging_position(item["name"], records)
                or by_name[item["name"]].get("y") != 0
            ),
            None,
        )
        if stage is None:
            raise DisplayError("Could not find a non-overlapping temporary monitor position.")
        staged = dict(stage)
        staged.update(x=staging_position(stage["name"], records), y=0, mirror=None)
        apply_monitor_setting(staged)

    for setting in layout:
        if setting.get("disabled"):
            record = next(
                (item for item in monitors() if item.get("name") == setting["name"]),
                None,
            )
            if record and not record.get("disabled", False):
                apply_monitor_setting(setting)

    records = monitors()
    by_name = {item["name"]: item for item in records}
    if not all(monitor_setting_applied(setting, by_name) for setting in layout):
        raise DisplayError("Hyprland did not apply the requested monitor layout.")


def restore_layout(layout: list[dict[str, Any]]) -> None:
    if any(item.get("mirror") for item in layout) and not native_mirroring_is_safe():
        safe_fallback()
        return
    current = monitors()
    available = {item["name"]: item for item in current if item.get("connected")}
    restore = {
        item["name"]: dict(item)
        for item in layout
        if item.get("name") in available
    }
    active = [item for item in restore.values() if not item.get("disabled")]
    if not active:
        internal = next((item for item in available.values() if item.get("internal")), None)
        if not internal:
            internal = next(iter(available.values()), None)
        if not internal:
            raise DisplayError("No connected display is available for rollback.")
        restore[internal["name"]] = {
            "name": internal["name"],
            "disabled": False,
            "mode": "preferred",
            "x": 0,
            "y": 0,
            "scale": 1,
            "transform": 0,
            "mirror": None,
        }
    apply_layout(list(restore.values()))


def safe_fallback() -> None:
    records = [item for item in monitors() if item.get("connected")]
    target = next((item for item in records if item.get("internal")), None)
    if target is None:
        target = next((item for item in records if not item.get("disabled")), None)
    if target is None and records:
        target = records[0]
    if target is None:
        raise DisplayError("No connected display is available for recovery.")
    layout = [
        {
            "name": item["name"],
            "disabled": item["name"] != target["name"],
            "mode": "preferred",
            "x": 0,
            "y": 0,
            "scale": 1,
            "transform": 0,
            "mirror": None,
        }
        for item in records
    ]
    apply_layout(layout)


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


def snapshot_before_config_change(label: str, *targets: Path) -> Path | None:
    try:
        from scripts.core.rice_maintenance import snapshot_before_config_change as snapshot

        return snapshot(label, *targets)
    except (ImportError, OSError, RuntimeError) as exc:
        raise DisplayError(f"Could not create a safety snapshot before saving: {exc}") from exc


def save_profile(layout: list[dict[str, Any]]) -> None:
    snapshot_before_config_change("display-profile", STATE_FILE)
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    profile = {"savedAt": int(time.time()), "layout": layout}
    signature = {item["name"] for item in layout}
    layout_key = json.dumps(layout, sort_keys=True, separators=(",", ":"))
    profiles = [
        item
        for item in load_profiles()
        if (
            {monitor["name"] for monitor in item["layout"]} != signature
            or json.dumps(item["layout"], sort_keys=True, separators=(",", ":")) != layout_key
        )
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
    if record.get("mirrorOf") not in (None, "none"):
        return (
            f"{name}  ·  {record.get('width', '?')}×{record.get('height', '?')} "
            f"@ {float(record.get('refreshRate', 0)):.2f} Hz  ·  Mirrored"
        )
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


def transaction(
    label: str,
    layout: list[dict[str, Any]],
    allow_save: bool = True,
    presentation: dict[str, Any] | None = None,
) -> bool:
    with display_operation_lock(timeout=1) as acquired:
        if not acquired:
            notify("Display Manager busy", "Another display change is still in progress.")
            log_event(f"Could not start layout change: {label}", severity="warning", result="busy")
            return False
        previous = runtime_layout()
        if presentation is not None:
            presentation["previous_layout"] = previous
            try:
                write_presentation_state(presentation)
            except OSError as exc:
                notify("Presentation Mode unavailable", f"Could not preserve the current state: {exc}", "critical")
                return False
        try:
            apply_layout(layout)
        except DisplayError as exc:
            try:
                restore_layout(previous)
            except DisplayError as rollback_error:
                notify("Display change failed", f"{exc}; rollback also failed: {rollback_error}", "critical")
                log_event(f"Display layout failed and rollback failed: {label}", severity="critical", result="failure")
                return False
            notify("Display change failed", str(exc), "critical")
            log_event(f"Display layout failed and previous layout was restored: {label}",
                      severity="error", result="rolled-back")
            return False

        notify("Display configuration changed", f"{label}. Confirm within {CONFIRM_SECONDS} seconds or it will revert.")
        expected = connected_names()
        save_choice = "Keep this layout — save for startup and reconnection"
        session_choice = "Keep this layout for this session only"
        options = ([save_choice] if allow_save else []) + [
            session_choice,
            "Revert to the previous layout",
        ]
        process: subprocess.Popen[str] | None = None
        try:
            process = subprocess.Popen(
                ["rofi", "-dmenu", "-i", "-config", str(ROFI_THEME), "-p",
                 f"Confirm display layout ({CONFIRM_SECONDS}s)"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout, stderr = process.communicate("\n".join(options) + "\n", timeout=0.2)
        except subprocess.TimeoutExpired:
            stdout = stderr = None
        except OSError as exc:
            stdout = stderr = None
            notify("Display confirmation unavailable", str(exc), "critical")

        choice: str | None = None
        deadline = time.monotonic() + CONFIRM_SECONDS
        disconnected = False
        while process is not None and process.poll() is None and time.monotonic() < deadline:
            try:
                actual = connected_names()
            except DisplayError:
                actual = set()
            if actual != expected:
                disconnected = True
                process.kill()
                break
            try:
                stdout, stderr = process.communicate(timeout=0.3)
            except subprocess.TimeoutExpired:
                continue
        if process is not None and process.poll() is None:
            process.kill()
        if process is not None:
            try:
                if stdout is None:
                    stdout, stderr = process.communicate(timeout=1)
                if process.returncode == 0 and stdout:
                    choice = stdout.strip()
            except (OSError, subprocess.TimeoutExpired):
                pass

        if disconnected:
            try:
                safe_fallback()
                notify("Display changed during confirmation", "The connected display state changed; a safe layout was restored.", "critical")
            except DisplayError as exc:
                notify("Display recovery failed", str(exc), "critical")
            log_event(f"Display layout cancelled after hotplug during confirmation: {label}",
                      severity="warning", result="rolled-back")
            return False
        if choice not in (save_choice, session_choice):
            try:
                restore_layout(previous)
                notify("Display layout reverted", "The previous monitor layout has been restored.")
            except DisplayError as exc:
                notify("Display rollback failed", str(exc), "critical")
                log_event(f"Display layout rollback failed: {label}", severity="critical", result="failure")
            else:
                log_event(f"Display layout was not confirmed: {label}", severity="warning", result="rolled-back")
            return False

        if choice == save_choice:
            try:
                save_profile(runtime_layout())
            except OSError as exc:
                notify("Layout active, but not saved", str(exc), "critical")
                return True
            notify("Display layout saved", "It will be restored at startup and when its monitors reconnect.")
            log_event(f"Saved display layout: {label}")
        else:
            notify("Display layout applied", f"{label} is active for this session.")
            log_event(f"Applied display layout for this session: {label}")
        return True


def internal_output(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    return next((item for item in records if item.get("connected") and item.get("internal")), None)


def external_outputs(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in records if item.get("connected") and not item.get("internal")]


def canonical_workspace(value: Any) -> str | None:
    if isinstance(value, int) and not isinstance(value, bool):
        value = str(value)
    if not isinstance(value, str):
        return None
    value = value.strip()
    if value.isdigit() and 1 <= int(value) <= 10:
        return str(int(value))
    if value.startswith("name:") and NAMED_WORKSPACE.fullmatch(value):
        return value
    return None


def workspace_selector(record: dict[str, Any]) -> str | None:
    name = record.get("name")
    if isinstance(name, str) and name.startswith("name:"):
        return canonical_workspace(name)
    return canonical_workspace(name)


def load_external_workspace_preference() -> str | None:
    try:
        data = json.loads(DISPLAY_PREFERENCES.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError) as exc:
        notify("Display Manager", f"Could not read display preferences: {exc}", "critical")
        return None
    if not isinstance(data, dict):
        notify("Display Manager", "Display preferences are malformed and were ignored.", "critical")
        return None
    preference = canonical_workspace(data.get("external_workspace"))
    if data.get("external_workspace") is not None and preference is None:
        notify("Display Manager", "The saved external workspace is invalid and was ignored.", "critical")
    return preference


def save_external_workspace_preference(workspace: str) -> None:
    workspace = canonical_workspace(workspace)
    if workspace is None:
        raise DisplayError("Choose workspace 1-10 or a valid named workspace.")
    try:
        data = json.loads(DISPLAY_PREFERENCES.read_text(encoding="utf-8"))
    except FileNotFoundError:
        data = {}
    except (OSError, json.JSONDecodeError) as exc:
        raise DisplayError(f"Could not read display preferences: {exc}") from exc
    if not isinstance(data, dict):
        raise DisplayError("Display preferences are malformed; they were not overwritten.")
    data["external_workspace"] = workspace
    snapshot_before_config_change("display-workspace", DISPLAY_PREFERENCES)
    DISPLAY_PREFERENCES.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".display-preferences-", dir=DISPLAY_PREFERENCES.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)
            file.write("\n")
        os.replace(temp_name, DISPLAY_PREFERENCES)
    except OSError as exc:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise DisplayError(f"Could not save display preferences: {exc}") from exc


def choose_external_workspace(records: list[dict[str, Any]], current: str | None = None) -> str | None:
    workspaces = hyprctl_json("workspaces")
    if not isinstance(workspaces, list):
        raise DisplayError("Hyprland did not return workspace state.")
    named = sorted(
        {
            selector
            for record in workspaces
            if isinstance(record, dict)
            and (selector := workspace_selector(record)) is not None
            and selector.startswith("name:")
        }
    )
    options = [str(number) for number in range(1, 11)] + named
    labels = [f"Workspace: {item}" for item in options]
    custom = "Enter named workspace…"
    labels.append(custom)
    selected = rofi(labels, f"External workspace — current: {current or 'choose when extending'}")
    if not selected:
        return None
    if selected == custom:
        entered = rofi(["name:work"], "Named workspace (name:...)")
        workspace = canonical_workspace(entered)
        if workspace is None or not workspace.startswith("name:"):
            notify("Display Manager", "Enter a valid named workspace such as name:presentation.", "critical")
            return None
        return workspace
    return canonical_workspace(selected.partition(": ")[2])


def workspace_on_monitor(workspace: str, monitor: str) -> bool:
    records = monitors()
    target = next((item for item in records if item.get("name") == monitor), None)
    if not target or target.get("disabled"):
        return False
    active = target.get("activeWorkspace")
    return isinstance(active, dict) and workspace_selector(active) == workspace


def move_workspace_to_monitor(workspace: str, monitor: str, allow_active_move: bool = False) -> None:
    workspace = canonical_workspace(workspace)
    if workspace is None:
        raise DisplayError("The selected external workspace is invalid.")
    records = monitors()
    target = next(
        (
            item
            for item in records
            if item.get("name") == monitor and item.get("connected") and not item.get("disabled")
        ),
        None,
    )
    if not target:
        raise DisplayError(f"{monitor} is no longer an active connected display.")
    workspaces = hyprctl_json("workspaces")
    if not isinstance(workspaces, list):
        raise DisplayError("Hyprland did not return workspace state.")
    found = next(
        (
            record
            for record in workspaces
            if isinstance(record, dict) and workspace_selector(record) == workspace
        ),
        None,
    )
    if found and found.get("monitor") == monitor and workspace_on_monitor(workspace, monitor):
        return

    active_internal = next(
        (item for item in records if item.get("connected") and item.get("internal")),
        None,
    )
    active_name = None
    if active_internal:
        active = active_internal.get("activeWorkspace")
        active_name = workspace_selector(active) if isinstance(active, dict) else None
    if (
        found
        and active_internal
        and found.get("monitor") == active_internal["name"]
        and active_name == workspace
        and not allow_active_move
    ):
        choice = rofi(
            [
                f"Move workspace {workspace} to {monitor} (the laptop will switch workspaces)",
                "Cancel",
            ],
            "Workspace is active on laptop",
        )
        if not choice or choice == "Cancel":
            raise DisplayError("Workspace assignment cancelled to preserve the laptop's active workspace.")

    if found and found.get("monitor") != monitor:
        expression = (
            "hl.dsp.workspace.move({ "
            f"workspace = {json.dumps(workspace)}, "
            f"monitor = {json.dumps(monitor)} "
            "})"
        )
        hypr_dispatch(expression)
    focused = next((item for item in records if item.get("focused") and item.get("connected")), None)
    focus_back = focused["name"] if focused else None
    if not workspace_on_monitor(workspace, monitor):
        focus_target = "hl.dsp.focus({ monitor = " + json.dumps(monitor) + " })"
        focus_workspace = (
            "hl.dsp.focus({ workspace = " + json.dumps(workspace)
            + ", on_current_monitor = true })"
        )
        hypr_dispatch(focus_target)
        try:
            hypr_dispatch(focus_workspace)
        finally:
            if focus_back and focus_back != monitor:
                hypr_dispatch("hl.dsp.focus({ monitor = " + json.dumps(focus_back) + " })")

    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        if workspace_on_monitor(workspace, monitor):
            return
        time.sleep(0.1)
    raise DisplayError(f"Hyprland did not show workspace {workspace} on {monitor}.")


def assign_saved_external_workspace(records: list[dict[str, Any]]) -> None:
    preference = load_external_workspace_preference()
    if not preference:
        return
    active = active_records(records)
    if not any(item.get("internal") for item in active):
        return
    external = next((item for item in active if not item.get("internal")), None)
    if external is None:
        return
    with display_operation_lock(timeout=5) as acquired:
        if not acquired:
            return
        try:
            move_workspace_to_monitor(preference, external["name"], allow_active_move=True)
        except DisplayError as exc:
            notify("External workspace preference", str(exc), "critical")


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
        target = internal
        if not target:
            notify("Display Manager", "No connected built-in display was detected.", "critical")
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
        if preset == "mirror" and not native_mirroring_is_safe():
            notify(
                "Mirroring blocked for stability",
                "The installed Hyprland build has a matching mirror-disconnect crash report. "
                "No stable release with a verified fix is available; use Extend or External only.",
                "critical",
            )
            return None
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
    if preset == "presentation":
        start_presentation_mode()
        return
    side = "right"
    selected_workspace: str | None = None
    selected_output = output
    if preset == "extend":
        records = monitors()
        external = next(
            (item for item in external_outputs(records) if item["name"] == output),
            None,
        )
        if external is None:
            external = choose_output(external_outputs(records), "󰍹  Choose external display")
        if not external:
            return
        selected_output = external["name"]
        selected_workspace = choose_external_workspace(
            records,
            load_external_workspace_preference(),
        )
        if not selected_workspace:
            return
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
    result = preset_layout(preset, selected_output, side)
    if result:
        applied = transaction(result[0], result[1])
        if applied and preset == "extend" and selected_workspace and selected_output:
            with display_operation_lock(timeout=5) as acquired:
                if not acquired:
                    notify("Display Manager busy", "Could not safely assign the external workspace.")
                    return
                try:
                    move_workspace_to_monitor(selected_workspace, selected_output)
                    save_external_workspace_preference(selected_workspace)
                    notify(
                        "External workspace assigned",
                        f"Workspace {selected_workspace} is shown on {selected_output} and will be remembered.",
                    )
                except DisplayError as exc:
                    notify("External workspace assignment failed", str(exc), "critical")


def presentation_state() -> dict[str, Any] | None:
    try:
        state = json.loads(PRESENTATION_STATE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError) as exc:
        notify("Presentation Mode", f"Could not read its saved state: {exc}", "critical")
        return None
    if isinstance(state, dict) and state.get("active") is True:
        return state
    return None


def session_preset_active() -> bool:
    try:
        state = json.loads(SESSION_PRESET_STATE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return False
    except (OSError, json.JSONDecodeError) as exc:
        notify("Session Preset state", f"Could not read its state: {exc}", "critical")
        return True
    return isinstance(state, dict) and state.get("active") is True


def recover_interrupted_presentation() -> None:
    try:
        state = json.loads(PRESENTATION_STATE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return
    except (OSError, json.JSONDecodeError) as exc:
        notify("Presentation Mode recovery failed", f"Could not read its saved state: {exc}", "critical")
        return
    if not isinstance(state, dict) or state.get("active") is True:
        return
    with display_operation_lock(timeout=5) as acquired:
        if not acquired:
            return
        layout = state.get("previous_layout")
        if isinstance(layout, list) and layout:
            try:
                restore_layout(layout)
            except DisplayError as exc:
                notify("Presentation Mode recovery failed", str(exc), "critical")
        if state.get("manage_dnd") and isinstance(state.get("previous_dnd"), bool):
            try:
                set_dnd(state["previous_dnd"])
            except DisplayError as exc:
                notify("Presentation Mode recovery failed", f"DND state could not be restored: {exc}", "critical")
        stop_idle_inhibitor(state.get("idle_inhibitor_pid"))
        try:
            PRESENTATION_STATE.unlink(missing_ok=True)
        except OSError as exc:
            notify("Presentation Mode recovery failed", f"Could not clear its saved state: {exc}", "critical")


def write_presentation_state(state: dict[str, Any]) -> None:
    PRESENTATION_STATE.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".display-presentation-", dir=PRESENTATION_STATE.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(state, file, indent=2)
            file.write("\n")
        os.replace(temp_name, PRESENTATION_STATE)
    except OSError:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def dnd_status() -> bool | None:
    if not shutil.which("dunstctl"):
        return None
    try:
        result = command(["dunstctl", "is-paused"])
    except DisplayError:
        return None
    value = result.stdout.strip().lower()
    return value == "true" if value in ("true", "false") else None


def set_dnd(paused: bool) -> None:
    if not shutil.which("dunstctl"):
        return
    command(["dunstctl", "set-paused", "true" if paused else "false"])
    actual = dnd_status()
    if actual is not paused:
        raise DisplayError("Dunst did not apply the requested Do Not Disturb state.")
    if shutil.which("pkill"):
        subprocess.run(
            ["pkill", "-RTMIN+8", "waybar"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def start_idle_inhibitor(
    who: str = "hypr-rice-presentation",
    reason: str = "Presentation mode",
) -> int:
    if not shutil.which("systemd-inhibit"):
        raise DisplayError("systemd-inhibit is unavailable; idle blanking cannot be inhibited.")
    try:
        process = subprocess.Popen(
            [
                "systemd-inhibit",
                "--what=idle",
                f"--who={who}",
                f"--why={reason}",
                "--mode=block",
                "sleep",
                "infinity",
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
    except OSError as exc:
        raise DisplayError(f"Could not inhibit idle actions: {exc}") from exc
    time.sleep(0.15)
    if process.poll() is not None:
        error = process.stderr.read().strip() if process.stderr else ""
        raise DisplayError(error or "systemd-inhibit exited before the idle lock was acquired.")
    return process.pid


def stop_idle_inhibitor(pid: Any, who: str = "hypr-rice-presentation") -> None:
    if not isinstance(pid, int) or pid <= 1:
        return
    try:
        args = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
    except OSError:
        return
    if not any(b"systemd-inhibit" in arg for arg in args) or f"--who={who}".encode() not in args:
        return
    try:
        os.kill(pid, 15)
    except ProcessLookupError:
        return
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        if not Path(f"/proc/{pid}").exists():
            return
        time.sleep(0.05)


def start_presentation_mode() -> None:
    if session_preset_active():
        notify(
            "Session Preset active",
            "Restore the previous session before starting Presentation Mode.",
        )
        return
    if presentation_state():
        exit_presentation_mode()
        return

    records = monitors()
    external = choose_output(external_outputs(records), "󰍹  Choose presentation display")
    if not external:
        return
    options = [
        "Extend — external primary, laptop for presenter controls",
        "External display only",
    ]
    mode_by_choice = {
        options[0]: "presentation",
        options[1]: "external",
    }
    if native_mirroring_is_safe():
        options.append("Mirror presentation")
        mode_by_choice[options[-1]] = "mirror"
    selected = rofi(options, "󰍹  Presentation layout")
    if not selected:
        return
    behavior = rofi(
        [
            "Do Not Disturb + prevent idle blanking",
            "Do Not Disturb only",
            "Prevent idle blanking only",
            "Neither",
        ],
        "Presentation protections",
    )
    if not behavior:
        return
    manage_dnd = behavior in (
        "Do Not Disturb + prevent idle blanking",
        "Do Not Disturb only",
    )
    prevent_idle = behavior in (
        "Do Not Disturb + prevent idle blanking",
        "Prevent idle blanking only",
    )
    result = preset_layout(mode_by_choice[selected], external["name"])
    if not result:
        return

    previous_dnd = dnd_status() if manage_dnd else None
    state: dict[str, Any] = {
        "active": False,
        "previous_layout": [],
        "previous_dnd": previous_dnd,
        "manage_dnd": manage_dnd,
        "prevent_idle": prevent_idle,
        "idle_inhibitor_pid": None,
    }
    if not transaction(result[0], result[1], allow_save=False, presentation=state):
        try:
            PRESENTATION_STATE.unlink(missing_ok=True)
        except OSError as exc:
            notify("Presentation Mode cleanup failed", str(exc), "critical")
        return

    warnings: list[str] = []
    if manage_dnd:
        if previous_dnd is None:
            warnings.append("DND state could not be read.")
        if previous_dnd is None:
            pass
        elif shutil.which("dunstctl"):
            try:
                set_dnd(True)
            except DisplayError as exc:
                warnings.append(f"DND could not be enabled: {exc}")
        elif previous_dnd is not None:
            warnings.append("Dunst is unavailable; DND was not changed.")
    if prevent_idle:
        try:
            state["idle_inhibitor_pid"] = start_idle_inhibitor()
        except DisplayError as exc:
            warnings.append(f"Idle blanking could not be inhibited: {exc}")
    state["active"] = True
    try:
        write_presentation_state(state)
    except OSError as exc:
        if previous_dnd is not None:
            try:
                set_dnd(previous_dnd)
            except DisplayError as restore_error:
                warnings.append(f"DND restoration failed: {restore_error}")
        stop_idle_inhibitor(state["idle_inhibitor_pid"])
        try:
            restore_layout(state["previous_layout"])
        except DisplayError as restore_error:
            warnings.append(f"Display rollback failed: {restore_error}")
        try:
            PRESENTATION_STATE.unlink(missing_ok=True)
        except OSError as cleanup_error:
            warnings.append(f"Presentation state cleanup failed: {cleanup_error}")
        notify("Presentation Mode failed", f"Could not save presentation state: {exc}. " + " ".join(warnings), "critical")
        return

    message = (
        "External display is primary; the laptop remains available for presenter controls."
        if mode_by_choice[selected] == "presentation"
        else f"{result[0]} is active."
    )
    if warnings:
        message += " " + " ".join(warnings)
    notify("Presentation Mode activated", message, "critical" if warnings else "normal")
    log_event("Presentation Mode activated", severity="warning" if warnings else "info")


def exit_presentation_mode(lock_held: bool = False) -> None:
    state = presentation_state()
    if not state:
        notify("Presentation Mode", "Presentation Mode is not active.")
        return
    if not lock_held:
        with display_operation_lock(timeout=5) as acquired:
            if not acquired:
                notify("Display Manager busy", "Another display change is still in progress.")
                return
            _exit_presentation_state(state)
    else:
        _exit_presentation_state(state)


def _exit_presentation_state(state: dict[str, Any]) -> None:
    errors: list[str] = []
    previous = state.get("previous_layout")
    if isinstance(previous, list) and previous:
        try:
            restore_layout(previous)
        except DisplayError as exc:
            errors.append(f"Previous display layout could not be restored: {exc}")
            try:
                safe_fallback()
            except DisplayError as fallback_error:
                errors.append(f"Safe display fallback failed: {fallback_error}")
    if state.get("manage_dnd") and isinstance(state.get("previous_dnd"), bool):
        try:
            set_dnd(state["previous_dnd"])
        except DisplayError as exc:
            errors.append(f"Previous DND state could not be restored: {exc}")
    stop_idle_inhibitor(state.get("idle_inhibitor_pid"))
    try:
        PRESENTATION_STATE.unlink(missing_ok=True)
    except OSError as exc:
        errors.append(f"Presentation state could not be cleared: {exc}")
    message = "Previous display, DND, and idle-inhibition settings were restored where available."
    if errors:
        message += " " + " ".join(errors)
    notify("Presentation Mode deactivated", message, "critical" if errors else "normal")
    log_event("Presentation Mode deactivated", severity="error" if errors else "info",
              result="recovered" if errors else "success")


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
    presentation_running = presentation_state() is not None
    workspace_preference = load_external_workspace_preference()
    active_external = next(
        (item for item in active_records(records) if not item.get("internal")),
        None,
    )
    external_workspace_status = ""
    if active_external:
        active_workspace = active_external.get("activeWorkspace")
        active_selector = (
            workspace_selector(active_workspace)
            if isinstance(active_workspace, dict)
            else None
        )
        if active_selector:
            external_workspace_status = f"; currently showing {active_selector}"
    options = [display_card(item) for item in records]
    actions: dict[str, tuple[str, str | None]] = {}
    for item in records:
        actions[display_card(item)] = ("info", item["name"])
    options.extend([
        "Preset: Laptop only",
        "Preset: External display only",
        "Preset: Extend displays",
        "Preset: Mirror displays",
        f"External workspace: {workspace_preference or 'choose on Extend'}{external_workspace_status}",
        "Presentation Mode: Exit" if presentation_running else "Presentation Mode: Start",
        "Session Presets…",
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
    for preset in ("laptop", "external", "extend", "mirror"):
        actions[f"Preset: {dict(laptop='Laptop only', external='External display only', extend='Extend displays', mirror='Mirror displays')[preset]}"] = ("preset", preset)
    actions["Presentation Mode: Exit" if presentation_running else "Presentation Mode: Start"] = ("presentation", "")
    actions["Session Presets…"] = ("session-presets", "")
    actions[f"External workspace: {workspace_preference or 'choose on Extend'}{external_workspace_status}"] = ("external-workspace", "")
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
    elif action == "presentation":
        if presentation_running:
            exit_presentation_mode()
        else:
            start_presentation_mode()
    elif action == "session-presets":
        subprocess.Popen(
            [sys.executable, str(CONFIG / "scripts" / "session-presets.py")],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    elif action == "external-workspace":
        update_external_workspace_preference()
    elif action == "save":
        save_current_layout()
    elif action == "reapply":
        reapply_saved_layout()


def update_external_workspace_preference() -> None:
    records = monitors()
    selected = choose_external_workspace(records, load_external_workspace_preference())
    if not selected:
        return
    active = active_records(records)
    with display_operation_lock(timeout=5) as acquired:
        if not acquired:
            notify("Display Manager busy", "Could not safely update the external workspace preference.")
            return
        if any(item.get("internal") for item in active):
            external = next((item for item in active if not item.get("internal")), None)
            if external:
                try:
                    move_workspace_to_monitor(selected, external["name"])
                except DisplayError as exc:
                    notify("External workspace unchanged", str(exc), "critical")
                    return
        try:
            save_external_workspace_preference(selected)
        except DisplayError as exc:
            notify("Display Manager", str(exc), "critical")
            return
    notify("External workspace saved", f"Workspace {selected} will be used on the external display when extending.")


def saved_layout_ready(profile: dict[str, Any], records: list[dict[str, Any]]) -> bool:
    present = {item["name"] for item in records if item.get("connected")}
    layout = profile.get("layout", [])
    names = [item.get("name") for item in layout if isinstance(item, dict)]
    saved = set(names)
    if not saved or len(names) != len(saved) or saved != present or "FALLBACK" in saved:
        return False
    return not any(item.get("mirror") for item in layout) or native_mirroring_is_safe()


def restore_saved_layout(profile: dict[str, Any], label: str) -> bool:
    with display_operation_lock(timeout=5) as acquired:
        if not acquired:
            return False
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


def monitor_event(line: str) -> bool:
    event = line.partition(">>")[0]
    return event.startswith(("monitoradded", "monitorremoved"))


def wait_for_monitor_event(ipc: socket.socket, buffered: str) -> str:
    pending = buffered
    while True:
        ready, _, _ = select.select([ipc], [], [], 1)
        if not ready:
            continue
        data = ipc.recv(8192)
        if not data:
            raise ConnectionError("Hyprland IPC event socket closed.")
        pending += data.decode("utf-8", errors="replace")
        lines = pending.splitlines(keepends=True)
        pending = ""
        for line in lines:
            if not line.endswith(("\n", "\r")):
                pending = line
                continue
            if monitor_event(line):
                quiet_until = time.monotonic() + EVENT_DEBOUNCE_SECONDS
                hard_deadline = time.monotonic() + 1.5
                while time.monotonic() < quiet_until and time.monotonic() < hard_deadline:
                    ready, _, _ = select.select(
                        [ipc],
                        [],
                        [],
                        max(0.0, min(quiet_until - time.monotonic(), hard_deadline - time.monotonic())),
                    )
                    if not ready:
                        break
                    more = ipc.recv(8192)
                    if not more:
                        raise ConnectionError("Hyprland IPC event socket closed.")
                    more_lines = more.decode("utf-8", errors="replace").splitlines()
                    if any(monitor_event(item) for item in more_lines):
                        quiet_until = time.monotonic() + EVENT_DEBOUNCE_SECONDS
                return pending


def move_orphaned_workspaces(connected: set[str], target: str) -> None:
    workspaces = hyprctl_json("workspaces")
    if not isinstance(workspaces, list):
        raise DisplayError("Hyprland did not return workspace state.")
    for workspace in workspaces:
        if not isinstance(workspace, dict):
            continue
        name, monitor = workspace.get("name"), workspace.get("monitor")
        if not isinstance(name, (str, int)) or not isinstance(monitor, str):
            continue
        if monitor and monitor not in connected:
            workspace_name = str(name)
            expression = (
                "hl.dsp.workspace.move({ "
                f"workspace = {json.dumps(workspace_name)}, "
                f"monitor = {json.dumps(target)} "
                "})"
            )
            hypr_dispatch(expression)


def recover_disconnected_displays() -> None:
    with display_operation_lock(timeout=5) as acquired:
        if not acquired:
            return
        saved_presentation = presentation_state()
        if saved_presentation:
            _exit_presentation_state(saved_presentation)
        records = monitors()
        connected = connected_names(records)
        active = active_records(records)
        if not active:
            safe_fallback()
            records = monitors()
            connected = connected_names(records)
            active = active_records(records)
        if not active:
            raise DisplayError("No active display remains after fallback recovery.")
        target = next((item for item in active if item.get("internal")), active[0])
        move_orphaned_workspaces(connected, target["name"])


def watch_displays() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    lock_file = WATCH_LOCK.open("a")
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock_file.close()
        print("A display watcher is already running.", file=sys.stderr)
        return
    signature = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")
    if not signature:
        raise DisplayError("HYPRLAND_INSTANCE_SIGNATURE is not set; cannot connect to Hyprland IPC.")
    socket_path = RUNTIME_DIR / "hypr" / signature / ".socket2.sock"
    time.sleep(2)
    recover_interrupted_presentation()
    try:
        records = monitors()
        previous = connected_names(records)
    except DisplayError as exc:
        notify("Display watcher unavailable", str(exc), "critical")
        return
    profile = load_profile(records)
    if not presentation_state() and profile and saved_layout_ready(profile, records):
        restore_saved_layout(profile, "Your saved layout is active.")
    assign_saved_external_workspace(monitors())

    notified_unavailable = False
    while True:
        ipc = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            ipc.settimeout(None)
            ipc.connect(str(socket_path))
            if notified_unavailable:
                notify("Display watcher restored", "Hyprland monitor event monitoring is active again.")
                notified_unavailable = False
            buffered = ""
            while True:
                buffered = wait_for_monitor_event(ipc, buffered)
                try:
                    records = monitors()
                except DisplayError as exc:
                    notify("Display state unavailable", str(exc), "critical")
                    continue
                current = connected_names(records)
                appeared, disappeared = current - previous, previous - current
                previous = current
                if disappeared:
                    try:
                        recover_disconnected_displays()
                        for output in sorted(disappeared):
                            notify(
                                "External display disconnected",
                                f"{output} was removed. Workspaces were reassigned when necessary.",
                            )
                    except DisplayError as exc:
                        notify("Display recovery failed", str(exc), "critical")
                profile = load_profile(records)
                restored = bool(
                    appeared
                    and not presentation_state()
                    and profile
                    and saved_layout_ready(profile, records)
                    and restore_saved_layout(profile, "Your remembered monitor layout was restored.")
                )
                if appeared:
                    assign_saved_external_workspace(monitors())
                if appeared and not restored:
                    for output in sorted(appeared):
                        record = next((item for item in records if item["name"] == output), {})
                        if not record.get("internal"):
                            threading.Thread(target=action_notification, args=(output,), daemon=True).start()
        except (OSError, ConnectionError) as exc:
            if not notified_unavailable:
                notify("Display watcher reconnecting", f"Hyprland IPC event socket: {exc}", "critical")
                notified_unavailable = True
            time.sleep(2)
        finally:
            ipc.close()


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
