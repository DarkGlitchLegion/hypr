#!/usr/bin/env python3
"""PipeWire device backend and optional sink hotplug manager."""

from __future__ import annotations

import fcntl
import html
import json
import logging
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


CONFIG = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "hypr"
PREFERENCES = CONFIG / "audio-preferences.json"
ROFI_THEME = CONFIG / "rofi" / "audio.rasi"
VOLUME_SCRIPT = CONFIG / "scripts" / "volume.sh"
RUNTIME_DIR = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
WATCH_LOCK = RUNTIME_DIR / "hypr-audio-manager.lock"
LOG_FILE = Path.home() / ".cache" / "hypr-audio-manager.log"
POLL_INTERVAL = 2


class AudioError(RuntimeError):
    """An audio device query or operation failed."""


def log_event(description: str, *, severity: str = "info", result: str = "success") -> None:
    try:
        from scripts.core.rice_events import log_event as write_event
        write_event(
            "audio",
            description,
            category="audio",
            severity=severity,
            result=result,
        )
    except (ImportError, OSError) as exc:
        print(f"Audio Manager: could not write activity log: {exc}", file=sys.stderr)


def notify(title: str, message: str, urgency: str = "low") -> None:
    try:
        subprocess.run(
            ["dunstify", "-a", "Audio", "-u", urgency, "-i", "audio-volume-high", title, message],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass


def run(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(args, text=True, capture_output=True, check=False)
    except FileNotFoundError as exc:
        raise AudioError(f"Required command not found: {args[0]}") from exc
    if check and result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or f"exit status {result.returncode}"
        raise AudioError(f"{' '.join(args)} failed: {detail}")
    return result


def load_preferences() -> dict[str, Any]:
    try:
        raw = json.loads(PREFERENCES.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"auto_switch_hdmi": False}
    except (OSError, json.JSONDecodeError) as exc:
        raise AudioError(f"Could not read {PREFERENCES}: {exc}") from exc
    if not isinstance(raw, dict):
        raise AudioError(f"Audio preferences in {PREFERENCES} must be a JSON object.")
    raw.setdefault("auto_switch_hdmi", False)
    return raw


def save_preferences(preferences: dict[str, Any]) -> None:
    if PREFERENCES.exists():
        try:
            from scripts.core.rice_maintenance import snapshot_before_config_change

            snapshot_before_config_change("audio-preferences", PREFERENCES)
        except (ImportError, OSError, RuntimeError) as exc:
            raise AudioError(f"Could not create a safety snapshot before saving preferences: {exc}") from exc
    PREFERENCES.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".audio-preferences-", dir=PREFERENCES.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(preferences, file, indent=2)
            file.write("\n")
        os.replace(temp_name, PREFERENCES)
    except OSError as exc:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise AudioError(f"Could not save audio preferences: {exc}") from exc


def get_devices(kind: str) -> list[dict[str, Any]]:
    if kind not in {"sinks", "sources"}:
        raise ValueError(f"Unsupported audio device type: {kind}")
    result = run(["pactl", "-f", "json", "list", kind])
    try:
        devices = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise AudioError(f"PipeWire returned invalid {kind} JSON: {exc}") from exc
    if not isinstance(devices, list):
        raise AudioError(f"PipeWire returned an invalid {kind} list.")
    normalized: list[dict[str, Any]] = []
    for device in devices:
        if not isinstance(device, dict) or not isinstance(device.get("name"), str):
            continue
        if kind == "sources" and device["name"].endswith(".monitor"):
            continue
        properties = device.get("properties")
        if not isinstance(properties, dict):
            properties = {}
        device["properties"] = properties
        device["description"] = str(device.get("description") or device["name"])
        normalized.append(device)
    return normalized


def get_default(kind: str) -> str:
    command = "get-default-sink" if kind == "sink" else "get-default-source"
    return run(["pactl", command]).stdout.strip()


def device_kind(device: dict[str, Any]) -> str:
    properties = device["properties"]
    searchable = " ".join(
        [device["name"], device["description"]]
        + [str(value) for value in properties.values() if isinstance(value, (str, int, float))]
    ).lower()
    if any(token in searchable for token in ("hdmi", "displayport", "display port")):
        return "HDMI / DisplayPort"
    if properties.get("device.bus") == "bluetooth" or "bluetooth" in searchable:
        return "Bluetooth"
    form_factor = str(properties.get("device.form_factor", "")).lower()
    if form_factor in {"headphone", "headphones", "headset"} or any(
        token in searchable for token in ("headphones", "headset", "earbuds")
    ):
        return "Headphones"
    profile = str(properties.get("device.profile.description", "")).lower()
    if "microphone" in profile or "mic" in profile:
        return "Microphone"
    if "speaker" in profile or form_factor in {"internal", "speaker"}:
        return "Built-in speakers"
    if properties.get("device.api") == "alsa" and properties.get("device.bus") == "pci":
        return "Local audio device"
    return "Audio output"


def is_hdmi(device: dict[str, Any]) -> bool:
    return device_kind(device) == "HDMI / DisplayPort"


def is_internal(device: dict[str, Any]) -> bool:
    return device_kind(device) == "Built-in speakers"


def device_identity(device: dict[str, Any]) -> str:
    properties = device["properties"]
    profile = str(properties.get("device.profile.name", ""))
    for key in ("device.serial", "device.address", "device.bus_path", "device.sysfs.path"):
        value = properties.get(key)
        if isinstance(value, str) and value:
            return f"{key}:{value}|profile:{profile}"
    return f"node:{device['name']}|profile:{profile}"


def resolve_device(reference: Any, identity: Any, devices: list[dict[str, Any]]) -> dict[str, Any] | None:
    if isinstance(reference, str):
        found = next((device for device in devices if device["name"] == reference), None)
        if found is not None:
            return found
    if isinstance(identity, str):
        return next((device for device in devices if device_identity(device) == identity), None)
    return None


def percent(device: dict[str, Any]) -> str:
    volume = device.get("volume")
    if not isinstance(volume, dict) or not volume:
        return "?"
    values = [
        int(str(channel.get("value_percent", "0%")).rstrip("%"))
        for channel in volume.values()
        if isinstance(channel, dict)
    ]
    return str(round(sum(values) / len(values))) if values else "?"


def set_sink(device: dict[str, Any], *, move_streams: bool = True) -> None:
    name = device["name"]
    previous_name = get_default("sink")
    run(["pactl", "set-default-sink", name])
    if move_streams and previous_name != name:
        previous = next(
            (sink for sink in get_devices("sinks") if sink["name"] == previous_name),
            None,
        )
        previous_index = str(previous.get("index")) if previous is not None else None
        stream_result = run(["pactl", "list", "short", "sink-inputs"])
        failures: list[str] = []
        for line in stream_result.stdout.splitlines():
            fields = line.split("\t")
            if len(fields) < 2 or not fields[0].isdigit() or fields[1] != previous_index:
                continue
            moved = run(["pactl", "move-sink-input", fields[0], name], check=False)
            if moved.returncode:
                detail = moved.stderr.strip() or f"exit status {moved.returncode}"
                failures.append(f"stream {fields[0]}: {detail}")
        if failures:
            raise AudioError(
                f"Default output changed to {device['description']}, but some active streams "
                f"could not be moved: {'; '.join(failures)}"
            )
    if get_default("sink") != name:
        raise AudioError(f"PipeWire did not confirm {device['description']} as the default output.")


def set_source(device: dict[str, Any]) -> None:
    run(["pactl", "set-default-source", device["name"]])
    if get_default("source") != device["name"]:
        raise AudioError(f"PipeWire did not confirm {device['description']} as the default input.")


def rofi_select(prompt: str, rows: list[str]) -> int | None:
    if not rows:
        notify("No audio devices", "No matching audio devices are currently available.", "normal")
        return None
    result = run(
        [
            "rofi",
            "-dmenu",
            "-i",
            "-markup-rows",
            "-format",
            "i",
            "-config",
            str(ROFI_THEME),
            "-p",
            prompt,
        ],
        check=False,
    )
    if result.returncode == 1 and not result.stdout.strip():
        return None
    if result.returncode:
        detail = result.stderr.strip() or f"exit status {result.returncode}"
        raise AudioError(f"Rofi audio selector failed: {detail}")
    try:
        selected = int(result.stdout.strip())
    except ValueError as exc:
        raise AudioError("Rofi returned an invalid audio menu selection.") from exc
    if not 0 <= selected < len(rows):
        raise AudioError("Rofi returned an out-of-range audio menu selection.")
    return selected


def device_row(device: dict[str, Any], active: bool) -> str:
    icon = {
        "HDMI / DisplayPort": "󰍹",
        "Bluetooth": "󰂯",
        "Headphones": "󰋋",
        "Microphone": "󰍬",
        "Built-in speakers": "󰕾",
    }.get(device_kind(device), "󰕾")
    marker = "●" if active else "○"
    color = "#AAAAAA" if active else "#888888"
    status = "Active" if active else "Select"
    return (
        f"<span color='{color}'><b>{marker} {icon} {html.escape(device_kind(device))} — "
        f"{html.escape(device['description'])}</b></span> "
        f"<span color='#D5D5D5'>│ {percent(device)}% · {status}</span>"
    )


def action_row(label: str, detail: str) -> str:
    return (
        f"<span color='#AAAAAA'><b>{html.escape(label)}</b></span> "
        f"<span color='#888888'>│ {html.escape(detail)}</span>"
    )


def change_volume() -> None:
    levels = list(range(0, 101, 5))
    current = run(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"]).stdout.strip()
    current_value = "?"
    fields = current.split()
    if len(fields) > 1:
        try:
            current_value = str(round(float(fields[1]) * 100))
        except ValueError:
            pass
    rows = [
        action_row(f"{level}%{'  · current' if str(level) == current_value else ''}", "Set output volume")
        for level in levels
    ]
    selected = rofi_select("󰕾  Output Volume", rows)
    if selected is None:
        return
    level = levels[selected]
    run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{level / 100:.2f}"])
    notify("Volume changed", f"Output volume set to {level}%.")


def toggle_auto_switch() -> None:
    preferences = load_preferences()
    enabled = not bool(preferences.get("auto_switch_hdmi", False))
    preferences["auto_switch_hdmi"] = enabled
    if enabled:
        preferences["auto_switch_requested"] = True
        message = "HDMI audio will be selected when a compatible output appears."
    else:
        preferences["auto_switch_requested"] = False
        message = "Automatic HDMI audio switching is off."
        auto_sink = preferences.get("auto_selected_sink")
        if isinstance(auto_sink, str) or isinstance(preferences.get("auto_selected_sink_id"), str):
            available = get_devices("sinks")
            active_auto_sink = resolve_device(
                auto_sink,
                preferences.get("auto_selected_sink_id"),
                available,
            )
            fallback = resolve_device(
                preferences.get("auto_fallback_sink"),
                preferences.get("auto_fallback_sink_id"),
                available,
            )
            if active_auto_sink is not None and get_default("sink") == active_auto_sink["name"]:
                if fallback is not None:
                    set_sink(fallback)
        preferences.pop("auto_selected_sink", None)
        preferences.pop("auto_selected_sink_id", None)
        preferences.pop("auto_fallback_sink", None)
        preferences.pop("auto_fallback_sink_id", None)
    save_preferences(preferences)
    notify("Audio automation", message)
    log_event(
        "Automatic HDMI audio switching " + ("enabled" if enabled else "disabled"),
        result="success",
    )


def open_menu(mode: str = "all") -> None:
    preferences = load_preferences()
    options: list[tuple[str, Any]] = []
    sinks = get_devices("sinks") if mode in {"all", "outputs"} else []
    sources = get_devices("sources") if mode in {"all", "inputs"} else []

    if mode in {"all", "outputs"}:
        default = get_default("sink")
        for sink in sinks:
            options.append((device_row(sink, sink["name"] == default), ("sink", sink)))
    if mode in {"all", "inputs"}:
        default = get_default("source")
        for source in sources:
            options.append((device_row(source, source["name"] == default), ("source", source)))
    if mode == "all":
        options.extend(
            [
                (action_row("󰝟  Toggle output mute", "Mute or unmute the active output"), ("action", "mute")),
                (action_row("󰍭  Toggle microphone mute", "Mute or unmute the active microphone"), ("action", "mic")),
                (action_row("󰕾  Set output volume…", "Choose a level from 0% to 100%"), ("action", "volume")),
                (
                    action_row(
                        "󰍹  Automatic HDMI audio",
                        "On" if preferences.get("auto_switch_hdmi", False) else "Off",
                    ),
                    ("action", "auto"),
                ),
                (action_row("󰒓  Advanced audio mixer", "Open Pavucontrol volume sliders and app routing"), ("action", "mixer")),
            ]
        )
    if not options:
        notify("No audio devices", "No matching audio devices are currently available.", "normal")
        return

    selected = rofi_select(
        "󰕾  Audio Control" if mode == "all" else ("󰕾  Audio Output" if mode == "outputs" else "󰍬  Audio Input"),
        [row for row, _ in options],
    )
    if selected is None:
        return
    selected_type, value = options[selected][1]
    if selected_type == "sink":
        set_sink(value)
        preferences["preferred_sink"] = value["name"]
        preferences["preferred_sink_id"] = device_identity(value)
        preferences.pop("auto_selected_sink", None)
        preferences.pop("auto_selected_sink_id", None)
        preferences.pop("auto_fallback_sink", None)
        preferences.pop("auto_fallback_sink_id", None)
        save_preferences(preferences)
        notify("Audio output switched", f"Default output: {value['description']}")
        log_event(f"Audio output changed to {value['description']}")
    elif selected_type == "source":
        set_source(value)
        preferences["preferred_source"] = value["name"]
        save_preferences(preferences)
        notify("Audio input switched", f"Default input: {value['description']}")
    elif value == "mute":
        run([str(VOLUME_SCRIPT), "mute"])
    elif value == "mic":
        run([str(VOLUME_SCRIPT), "mic"])
    elif value == "volume":
        change_volume()
    elif value == "auto":
        toggle_auto_switch()
    elif value == "mixer":
        try:
            subprocess.Popen(["pavucontrol"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError as exc:
            raise AudioError("Pavucontrol is not installed.") from exc


def fallback_sink(sinks: list[dict[str, Any]], preferences: dict[str, Any]) -> dict[str, Any] | None:
    fallback = resolve_device(
        preferences.get("auto_fallback_sink"),
        preferences.get("auto_fallback_sink_id"),
        sinks,
    )
    if fallback is not None:
        return fallback
    preferred = resolve_device(
        preferences.get("preferred_sink"),
        preferences.get("preferred_sink_id"),
        sinks,
    )
    if preferred is not None:
        return preferred
    return next((sink for sink in sinks if is_internal(sink)), sinks[0] if sinks else None)


def watch() -> None:
    WATCH_LOCK.parent.mkdir(parents=True, exist_ok=True)
    lock_fd = os.open(WATCH_LOCK, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(lock_fd)
        return

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    load_preferences()
    previous_names: set[str] = set()
    initialized = False
    last_error = ""
    try:
        while True:
            try:
                preferences = load_preferences()
                original_preferences = dict(preferences)
                sinks = get_devices("sinks")
                available = {sink["name"]: sink for sink in sinks}
                current = get_default("sink")
                added = set(available) - previous_names
                auto_sink = preferences.get("auto_selected_sink")
                auto_sink_device = resolve_device(
                    auto_sink,
                    preferences.get("auto_selected_sink_id"),
                    sinks,
                )

                if isinstance(auto_sink, str) and auto_sink_device is None:
                    if current == auto_sink:
                        fallback = fallback_sink(sinks, preferences)
                        if fallback is not None:
                            set_sink(fallback)
                            current = fallback["name"]
                            notify("Audio output restored", f"Using {fallback['description']} after HDMI disconnected.")
                            log_event(f"Audio fallback selected after HDMI disconnect: {fallback['description']}")
                    preferences.pop("auto_selected_sink", None)
                    preferences.pop("auto_selected_sink_id", None)
                    preferences.pop("auto_fallback_sink", None)
                    preferences.pop("auto_fallback_sink_id", None)
                    auto_sink = None
                elif auto_sink_device is not None and current != auto_sink_device["name"]:
                    preferences.pop("auto_selected_sink", None)
                    preferences.pop("auto_selected_sink_id", None)
                    preferences.pop("auto_fallback_sink", None)
                    preferences.pop("auto_fallback_sink_id", None)
                    auto_sink = None
                elif auto_sink_device is not None:
                    auto_sink = auto_sink_device["name"]

                if current not in available:
                    fallback = fallback_sink(sinks, preferences)
                    if fallback is not None:
                        set_sink(fallback)
                        current = fallback["name"]
                        notify("Audio output restored", f"Unavailable output replaced with {fallback['description']}.")

                hdmi = next((sink for sink in sinks if is_hdmi(sink)), None)
                preferred = resolve_device(
                    preferences.get("preferred_sink"),
                    preferences.get("preferred_sink_id"),
                    sinks,
                )
                auto_requested = bool(preferences.pop("auto_switch_requested", False))
                should_auto_switch = (
                    bool(preferences.get("auto_switch_hdmi", False))
                    and hdmi is not None
                    and auto_sink is None
                    and (not initialized or hdmi["name"] in added or auto_requested)
                )
                if should_auto_switch and hdmi is not None:
                    current = get_default("sink")
                    if current != hdmi["name"]:
                        previous = available.get(current)
                        if previous is not None:
                            preferences["auto_fallback_sink"] = previous["name"]
                            preferences["auto_fallback_sink_id"] = device_identity(previous)
                        set_sink(hdmi)
                        notify("HDMI audio connected", f"Audio is now routed to {hdmi['description']}.")
                        log_event(f"Automatic HDMI audio selected: {hdmi['description']}")
                    preferences["auto_selected_sink"] = hdmi["name"]
                    preferences["auto_selected_sink_id"] = device_identity(hdmi)
                elif (
                    not initialized
                    and not bool(preferences.get("auto_switch_hdmi", False))
                    and preferred is not None
                    and current != preferred["name"]
                ):
                    set_sink(preferred)
                    notify("Preferred audio restored", f"Using {preferred['description']}.")
                elif (
                    initialized
                    and not bool(preferences.get("auto_switch_hdmi", False))
                    and preferred is not None
                    and preferred["name"] in added
                    and current != preferred["name"]
                ):
                    set_sink(preferred)
                    notify("Preferred audio reconnected", f"Using {preferred['description']}.")

                if preferences != original_preferences:
                    save_preferences(preferences)
                previous_names = set(available)
                initialized = True
                last_error = ""
            except (AudioError, OSError) as exc:
                message = str(exc)
                if message != last_error:
                    logging.exception("Audio hotplug watcher could not refresh device state")
                    notify("Audio device refresh failed", message, "normal")
                    log_event(f"Audio hotplug refresh failed: {message}", severity="error", result="failure")
                    last_error = message
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        logging.info("Audio hotplug watcher stopped")
    finally:
        os.close(lock_fd)


def main(argv: list[str]) -> int:
    try:
        if argv == ["--watch"]:
            watch()
            return 0
        if argv == ["--json"]:
            sinks = get_devices("sinks")
            sources = get_devices("sources")
            print(json.dumps([
                {"type": kind, "name": device["name"], "description": device["description"],
                 "active": device["name"] == get_default("sink" if kind == "output" else "source"),
                 "volume": percent(device)}
                for kind, devices in (("output", sinks), ("input", sources))
                for device in devices
            ]))
            return 0
        if argv == ["--toggle-auto"]:
            toggle_auto_switch()
            return 0
        if len(argv) == 3 and argv[0] == "--set" and argv[1] in {"output", "input"}:
            kind, name = argv[1:]
            devices = get_devices("sinks" if kind == "output" else "sources")
            device = next((item for item in devices if item["name"] == name), None)
            if device is None:
                raise AudioError(f"The requested audio {kind} is no longer available.")
            if kind == "output":
                set_sink(device)
                preferences = load_preferences()
                preferences["preferred_sink"] = device["name"]
                preferences["preferred_sink_id"] = device_identity(device)
                save_preferences(preferences)
                notify("Audio output switched", f"Default output: {device['description']}")
            else:
                set_source(device)
                preferences = load_preferences()
                preferences["preferred_source"] = device["name"]
                save_preferences(preferences)
                notify("Audio input switched", f"Default input: {device['description']}")
            return 0
        if argv and argv[0] in {"toggle-mute", "toggle-mic"}:
            run([str(VOLUME_SCRIPT), "mute" if argv[0] == "toggle-mute" else "mic"])
            return 0
        if len(argv) > 1 or (argv and argv[0] not in {"all", "outputs", "inputs"}):
            raise AudioError("Usage: audio-manager.py [all|outputs|inputs|--watch|--json|--set output|input DEVICE]")
        if argv and argv[0] in {"all", "outputs", "inputs"}:
            subprocess.run([
                "qs", "ipc", "--path", str(CONFIG / "quickshell" / "shell.qml"),
                "call", "hyprshell", "openHub", "audio",
            ], check=False)
            return 0
        subprocess.run([
            "qs", "ipc", "--path", str(CONFIG / "quickshell" / "shell.qml"),
            "call", "hyprshell", "openHub", "audio",
        ], check=False)
        return 0
    except AudioError as exc:
        print(f"Audio Manager: {exc}", file=sys.stderr)
        notify("Audio operation failed", str(exc), "normal")
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
