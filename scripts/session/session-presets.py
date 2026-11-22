#!/usr/bin/env python3
"""Save, apply, and restore reversible desktop session presets."""

from __future__ import annotations

import json
import os
import runpy
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


CONFIG = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "hypr"
DISPLAY_MANAGER = CONFIG / "scripts" / "hardware" / "display-manager.py"
PRESETS_FILE = CONFIG / "state" / "session-presets.json"
IDLE_MANAGER = CONFIG / "scripts" / "idle-manager.py"
RUNTIME_DIR = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
RUNTIME_STATE = RUNTIME_DIR / "hypr-session-preset.json"
DISPLAY = runpy.run_path(str(DISPLAY_MANAGER))


def display_function(name: str):
    return DISPLAY[name]


def fail(message: str) -> None:
    raise display_function("DisplayError")(message)


def atomic_write(path: Path, data: dict[str, Any]) -> None:
    temp_name: str | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)
            file.write("\n")
        os.replace(temp_name, path)
    except OSError as exc:
        if temp_name is not None:
            try:
                os.unlink(temp_name)
            except OSError:
                pass
        fail(f"Could not save {path}: {exc}")


def load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default.copy()
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"Could not read {path}: {exc}")
    if not isinstance(data, dict):
        fail(f"{path} must contain a JSON object; it was not overwritten.")
    return data


def load_presets() -> dict[str, dict[str, Any]]:
    data = load_json(PRESETS_FILE, {"version": 1, "presets": {}})
    presets = data.get("presets")
    if not isinstance(presets, dict):
        fail("The session preset file is malformed; it was not overwritten.")
    valid: dict[str, dict[str, Any]] = {}
    for name, preset in presets.items():
        if (
            isinstance(name, str)
            and name
            and isinstance(preset, dict)
            and isinstance(preset.get("layout"), list)
            and preset["layout"]
        ):
            valid[name] = preset
    if len(valid) != len(presets):
        fail("The session preset file contains malformed entries; it was not overwritten.")
    return valid


def idle_inhibitor_pid() -> int | None:
    state = load_json(RUNTIME_STATE, {})
    pid = state.get("idle_inhibitor_pid")
    return pid if isinstance(pid, int) and pid > 1 and is_idle_inhibitor(pid) else None


def idle_manager_module() -> dict[str, Any]:
    return runpy.run_path(str(IDLE_MANAGER))


def is_idle_inhibitor(pid: int) -> bool:
    try:
        args = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
    except OSError:
        return False
    return (
        any(b"systemd-inhibit" in arg for arg in args)
        and b"--who=hypr-rice-session-preset" in args
    )


def capture_session() -> dict[str, Any]:
    if display_function("presentation_state")():
        fail("Exit Presentation Mode before saving or applying a session preset.")
    records = display_function("monitors")()
    layout = display_function("runtime_layout")(records)
    if not layout:
        fail("No active display layout is available to capture.")
    workspaces = [
        {
            "monitor": record["name"],
            "workspace": display_function("workspace_selector")(record.get("activeWorkspace", {})),
        }
        for record in display_function("active_records")(records)
        if display_function("workspace_selector")(record.get("activeWorkspace", {}))
    ]
    return {
        "layout": layout,
        "workspaces": workspaces,
        "dnd": display_function("dnd_status")(),
        "idle_inhibited": (
            idle_inhibitor_pid() is not None
            or idle_manager_module()["owned_inhibitor_pid"]() is not None
        ),
    }


def preset_summary(preset: dict[str, Any]) -> str:
    monitors = [
        f"{item.get('name')}{' off' if item.get('disabled') else ''}"
        for item in preset.get("layout", [])
        if isinstance(item, dict)
    ]
    workspaces = [
        f"{item.get('monitor')}:{item.get('workspace')}"
        for item in preset.get("workspaces", [])
        if isinstance(item, dict)
    ]
    dnd = preset.get("dnd")
    return (
        f"Displays: {', '.join(monitors) or 'unknown'}; "
        f"workspaces: {', '.join(workspaces) or 'unchanged'}; "
        f"DND: {'on' if dnd is True else 'off' if dnd is False else 'unchanged'}; "
        f"idle inhibit: {'on' if preset.get('idle_inhibited') else 'off'}"
    )


def prompt_preset_name() -> str | None:
    choices = ["Work", "Presentation", "Custom name…"]
    selected = display_function("rofi")(choices, "Save current session preset")
    if not selected:
        return None
    if selected != "Custom name…":
        return selected
    entered = display_function("rofi")(
        ["My preset"],
        "Type a preset name and press Enter",
    )
    if not entered:
        return None
    name = entered.strip()
    if not name or len(name) > 40 or any(char in name for char in "\n\r/"):
        fail("Preset names must be 1–40 characters and cannot contain slashes.")
    return name


def save_current_preset(name: str | None = None, *, replace: bool = False) -> None:
    name = name or prompt_preset_name()
    if not name:
        return
    if len(name) > 40 or any(char in name for char in "\n\r/"):
        fail("Preset names must be 1–40 characters and cannot contain slashes.")
    presets = load_presets()
    if name in presets:
        if not replace:
            return
    preset = capture_session()
    preset["saved_at"] = int(time.time())
    presets[name] = preset
    display_function("snapshot_before_config_change")("session-presets", PRESETS_FILE)
    atomic_write(PRESETS_FILE, {"version": 1, "presets": presets})
    display_function("notify")(
        "Session preset saved",
        f"{name}: {preset_summary(preset)}",
    )


def same_layout(first: list[dict[str, Any]], second: list[dict[str, Any]]) -> bool:
    return json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def apply_workspaces(workspaces: Any) -> None:
    if not isinstance(workspaces, list):
        fail("The session preset has an invalid workspace list.")
    with display_function("display_operation_lock")(timeout=5) as acquired:
        if not acquired:
            fail("Display Manager is busy; session workspaces were not changed.")
        for item in workspaces:
            if not isinstance(item, dict):
                fail("The session preset has an invalid workspace entry.")
            monitor = item.get("monitor")
            workspace = display_function("canonical_workspace")(item.get("workspace"))
            if not isinstance(monitor, str) or workspace is None:
                fail("The session preset contains an invalid monitor or workspace.")
            records = display_function("monitors")()
            active = next(
                (
                    record for record in records
                    if record.get("name") == monitor
                    and record.get("connected")
                    and not record.get("disabled")
                ),
                None,
            )
            if active is not None:
                display_function("move_workspace_to_monitor")(
                    workspace,
                    monitor,
                    allow_active_move=True,
                )


def set_idle_inhibition(enabled: bool, pid: int | None) -> int | None:
    idle_manager = idle_manager_module()
    if enabled:
        if pid is not None and is_idle_inhibitor(pid):
            idle_manager["stop_inhibitor"]()
            return pid
        idle_manager["stop_inhibitor"]()
        return display_function("start_idle_inhibitor")(
            who="hypr-rice-session-preset",
            reason="Session preset idle protection",
        )
    if pid is not None:
        display_function("stop_idle_inhibitor")(pid, who="hypr-rice-session-preset")
    idle_manager["stop_inhibitor"]()
    return None


def set_dnd_from_snapshot(snapshot: dict[str, Any]) -> None:
    dnd = snapshot.get("dnd")
    if dnd is not None:
        if not isinstance(dnd, bool):
            fail("The session preset has an invalid DND setting.")
        if display_function("dnd_status")() is None:
            fail("Dunst state is unavailable; DND was not changed.")
        display_function("set_dnd")(dnd)


def restore_snapshot(
    snapshot: dict[str, Any],
    current_pid: int | None,
    *,
    strict_outputs: bool = True,
) -> int | None:
    target_layout = snapshot.get("layout")
    if (
        not isinstance(target_layout, list)
        or not target_layout
        or any(not isinstance(item, dict) or not isinstance(item.get("name"), str) for item in target_layout)
    ):
        fail("The saved session has no valid display layout.")
    records = display_function("monitors")()
    expected_outputs = {item.get("name") for item in target_layout if isinstance(item, dict)}
    connected_outputs = display_function("connected_names")(records)
    if strict_outputs and expected_outputs != connected_outputs:
        fail("The connected displays differ from this preset. Connect the saved displays and retry.")
    if not strict_outputs and not connected_outputs.issubset(expected_outputs):
        fail("A new display is connected that was not part of the previous session.")
    before_layout = display_function("runtime_layout")()
    if not same_layout(before_layout, target_layout):
        if strict_outputs or connected_outputs == expected_outputs:
            if not display_function("transaction")(
                "Session preset restore",
                target_layout,
                allow_save=False,
            ):
                fail("The display layout was not confirmed; the session restore was cancelled.")
        else:
            display_function("restore_layout")(target_layout)
    apply_workspaces(snapshot.get("workspaces", []))
    set_dnd_from_snapshot(snapshot)
    return set_idle_inhibition(bool(snapshot.get("idle_inhibited", False)), current_pid)


def apply_preset(name: str) -> None:
    presets = load_presets()
    preset = presets.get(name)
    if preset is None:
        fail(f"Session preset '{name}' does not exist.")
    if display_function("presentation_state")():
        fail("Exit Presentation Mode before applying a session preset.")

    state = load_json(RUNTIME_STATE, {})
    before = capture_session()
    previous = state.get("previous") if state.get("active") else before
    current_pid = idle_inhibitor_pid()
    old_pid = current_pid
    applied_pid = current_pid
    try:
        next_pid = restore_snapshot(preset, current_pid)
        applied_pid = next_pid
        atomic_write(
            RUNTIME_STATE,
            {
                "active": True,
                "active_preset": name,
                "previous": previous,
                "idle_inhibitor_pid": next_pid,
            },
        )
    except Exception as exc:
        rollback_errors: list[str] = []
        restored_pid = applied_pid
        try:
            restored_pid = restore_snapshot(before, applied_pid, strict_outputs=False)
        except Exception as rollback_exc:
            rollback_errors.append(str(rollback_exc))
        try:
            if rollback_errors:
                atomic_write(
                    RUNTIME_STATE,
                    {
                        "active": True,
                        "active_preset": name,
                        "previous": previous,
                        "idle_inhibitor_pid": restored_pid,
                    },
                )
            elif state.get("active"):
                state["idle_inhibitor_pid"] = restored_pid
                atomic_write(RUNTIME_STATE, state)
            else:
                RUNTIME_STATE.unlink(missing_ok=True)
        except OSError as state_exc:
            rollback_errors.append(f"Could not update recovery state: {state_exc}")
        message = f"Preset was rolled back: {exc}"
        if rollback_errors:
            message += " Rollback issues: " + "; ".join(rollback_errors)
        fail(message)
    display_function("notify")("Session preset applied", f"{name}: {preset_summary(preset)}")


def restore_previous() -> None:
    state = load_json(RUNTIME_STATE, {})
    previous = state.get("previous")
    if not state.get("active") or not isinstance(previous, dict):
        fail("There is no session preset to restore.")
    if display_function("presentation_state")():
        fail("Exit Presentation Mode before restoring a session preset.")
    current_pid = idle_inhibitor_pid()
    current = capture_session()
    restored_pid = current_pid
    try:
        restored_pid = restore_snapshot(previous, current_pid, strict_outputs=False)
    except Exception as exc:
        rollback_errors: list[str] = []
        rollback_pid = restored_pid
        try:
            rollback_pid = restore_snapshot(current, restored_pid, strict_outputs=False)
        except Exception as rollback_exc:
            rollback_errors.append(str(rollback_exc))
        if rollback_errors:
            fail(f"Previous-session restore failed: {exc}. Rollback issues: {'; '.join(rollback_errors)}")
        fail(f"Previous-session restore failed and current state was recovered: {exc}")
    try:
        RUNTIME_STATE.unlink(missing_ok=True)
    except OSError as exc:
        fail(f"Previous session was restored, but its state file could not be cleared: {exc}")
    display_function("notify")(
        "Previous session restored",
        "Display layout, workspace selection, DND, and idle behavior were restored where available.",
    )


def delete_preset(name: str, *, confirm: bool = True) -> None:
    presets = load_presets()
    if name not in presets:
        fail(f"Session preset '{name}' does not exist.")
    if confirm:
        choice = display_function("rofi")([f"Delete {name}", "Cancel"], "Delete session preset")
        if not choice or choice == "Cancel":
            return
    del presets[name]
    display_function("snapshot_before_config_change")("session-presets", PRESETS_FILE)
    atomic_write(PRESETS_FILE, {"version": 1, "presets": presets})
    display_function("notify")("Session preset deleted", name)


def menu() -> None:
    presets = load_presets()
    state = load_json(RUNTIME_STATE, {})
    choices: list[str] = ["Save current session…"]
    actions: dict[str, tuple[str, str]] = {choices[0]: ("save", "")}
    for name, preset in sorted(presets.items()):
        label = f"Apply: {name}  ·  {preset_summary(preset)}"
        choices.append(label)
        actions[label] = ("apply", name)
        label = f"Delete: {name}"
        choices.append(label)
        actions[label] = ("delete", name)
    if state.get("active"):
        active_name = state.get("active_preset", "session preset")
        label = f"Restore previous session (active: {active_name})"
        choices.append(label)
        actions[label] = ("restore", "")
    selected = display_function("rofi")(choices, "󰐥  Session Presets")
    if not selected:
        return
    action, value = actions.get(selected, ("", ""))
    if action == "save":
        save_current_preset()
    elif action == "apply":
        apply_preset(value)
    elif action == "delete":
        delete_preset(value)
    elif action == "restore":
        restore_previous()


def main(argv: list[str]) -> int:
    try:
        if not argv:
            menu()
        elif argv == ["--json"]:
            presets = load_presets()
            print(json.dumps([
                {"name": name, "summary": preset_summary(preset)}
                for name, preset in sorted(presets.items())
            ], ensure_ascii=False))
        elif argv[0] == "--save" and len(argv) == 2:
            save_current_preset(argv[1])
        elif argv[0] == "--save" and len(argv) == 3 and argv[2] == "--replace":
            save_current_preset(argv[1], replace=True)
        elif argv[0] == "--apply" and len(argv) == 2:
            apply_preset(argv[1])
        elif argv == ["--restore"]:
            restore_previous()
        elif argv[0] == "--delete" and len(argv) == 3 and argv[2] == "--yes":
            delete_preset(argv[1], confirm=False)
        else:
            fail("Usage: session-presets.py [--save NAME|--apply NAME|--restore]")
    except display_function("DisplayError") as exc:
        display_function("notify")("Session Presets", str(exc), "critical")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
