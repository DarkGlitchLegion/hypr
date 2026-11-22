#!/usr/bin/env python3
"""Configure and supervise the rice's single Hypridle process."""

from __future__ import annotations

import copy
import fcntl
import importlib.util
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


CONFIG = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "hypr"
SCRIPTS = CONFIG / "scripts"
SETTINGS_FILE = CONFIG / "state" / "idle-settings.json"
LOCK_CONFIG = CONFIG / "hyprlock" / "hyprlock.conf"
RUNTIME_DIR = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")) / "hypr-rice-idle"
RUNTIME_CONFIG = RUNTIME_DIR / "hypridle.conf"
MANAGER_STATE = RUNTIME_DIR / "manager.json"
INHIBITOR_STATE = RUNTIME_DIR / "inhibitor.json"
MANAGER_LOCK = RUNTIME_DIR / "manager.lock"
LOG_DIR = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state")) / "hypr-rice"
HYPRIDLE_LOG = LOG_DIR / "hypridle.log"
PRESET_NAMES = (
    "Never", "5 Minutes", "10 Minutes", "15 Minutes", "20 Minutes", "30 Minutes",
    "45 Minutes", "60 Minutes", "Balanced", "Power Saving", "Security Focused", "Relaxed", "Custom",
)
ACTION_NAMES = ("dim", "blank", "lock", "display_off", "suspend")
ACTION_LABELS = {
    "dim": "Dim screen",
    "blank": "Blank screen",
    "lock": "Lock screen",
    "display_off": "Turn off display",
    "suspend": "Suspend / sleep",
}
SIGNAL_RELOAD = getattr(signal, "SIGUSR1", signal.SIGHUP)
_shutdown_requested = False
_reload_requested = False


class IdleError(RuntimeError):
    """A user-facing idle configuration or daemon error."""


def action(enabled: bool, seconds: int | None) -> dict[str, Any]:
    return {"enabled": enabled, "seconds": seconds}


def action_profile(
    *, dim: int | None, blank: int | None, lock: int | None,
    display_off: int | None, suspend: int | None,
) -> dict[str, dict[str, Any]]:
    return {
        "dim": action(dim is not None, dim),
        "blank": action(blank is not None, blank),
        "lock": action(lock is not None, lock),
        "display_off": action(display_off is not None, display_off),
        "suspend": action(suspend is not None, suspend),
    }


PRESETS: dict[str, dict[str, Any]] = {
    "Never": action_profile(dim=None, blank=None, lock=None, display_off=None, suspend=None),
    "Balanced": action_profile(dim=120, blank=300, lock=600, display_off=900, suspend=None),
    "Power Saving": action_profile(dim=60, blank=180, lock=300, display_off=300, suspend=900),
    "Security Focused": action_profile(dim=120, blank=None, lock=300, display_off=600, suspend=None),
    "Relaxed": action_profile(dim=300, blank=600, lock=1200, display_off=1800, suspend=None),
}


def preset_settings(name: str) -> dict[str, Any]:
    if name in PRESETS:
        return {"version": 1, "enabled": True, "preset": name, "actions": copy.deepcopy(PRESETS[name])}
    match = re.fullmatch(r"(5|10|15|20|30|45|60) Minutes", name)
    if not match:
        raise IdleError(f"Unknown idle preset: {name}")
    lock_at = int(match.group(1)) * 60
    settings = action_profile(
        dim=max(60, lock_at - 180),
        blank=None,
        lock=lock_at,
        display_off=lock_at + 60,
        suspend=None,
    )
    return {"version": 1, "enabled": True, "preset": name, "actions": settings}


def default_settings() -> dict[str, Any]:
    return preset_settings("Balanced")


def validate_settings(settings: Any) -> dict[str, Any]:
    if not isinstance(settings, dict):
        raise IdleError("Idle settings must be a JSON object; the file was not overwritten.")
    if settings.get("version") not in (1, None):
        raise IdleError("This idle settings version is not supported.")
    enabled = settings.get("enabled", True)
    preset = settings.get("preset", "Balanced")
    actions = settings.get("actions")
    if not isinstance(enabled, bool):
        raise IdleError("The idle master toggle must be true or false.")
    if not isinstance(preset, str) or preset not in PRESET_NAMES:
        raise IdleError("The saved idle preset is not recognized.")
    if not isinstance(actions, dict):
        raise IdleError("The idle action settings are missing or malformed.")

    normalized: dict[str, Any] = {"version": 1, "enabled": enabled, "preset": preset, "actions": {}}
    for name in ACTION_NAMES:
        item = actions.get(name)
        if not isinstance(item, dict) or not isinstance(item.get("enabled"), bool):
            raise IdleError(f"Settings for {ACTION_LABELS[name]} are malformed.")
        seconds = item.get("seconds")
        if seconds is not None and (
            not isinstance(seconds, int) or isinstance(seconds, bool) or not 15 <= seconds <= 86400
        ):
            raise IdleError(f"{ACTION_LABELS[name]} must be 15 seconds to 24 hours.")
        if item["enabled"] and seconds is None:
            raise IdleError(f"{ACTION_LABELS[name]} is enabled but has no timeout.")
        normalized["actions"][name] = {"enabled": item["enabled"], "seconds": seconds}
    return normalized


def load_settings() -> dict[str, Any]:
    try:
        raw = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default_settings()
    except (OSError, json.JSONDecodeError) as exc:
        raise IdleError(f"Could not read {SETTINGS_FILE}: {exc}") from exc
    return validate_settings(raw)


def atomic_write(path: Path, content: bytes, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    except OSError:
        Path(temporary).unlink(missing_ok=True)
        raise


def snapshot_before_change() -> None:
    if not SETTINGS_FILE.exists():
        return
    try:
        path = SCRIPTS / "core" / "rice_maintenance.py"
        spec = importlib.util.spec_from_file_location("rice_idle_maintenance", path)
        if spec is None or spec.loader is None:
            raise IdleError("The rice snapshot manager could not be loaded.")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        try:
            spec.loader.exec_module(module)
        finally:
            sys.modules.pop(spec.name, None)
        module.snapshot_before_config_change("idle-settings", SETTINGS_FILE)
    except (ImportError, OSError, RuntimeError) as exc:
        raise IdleError(f"Could not create a safety snapshot before changing idle settings: {exc}") from exc


def event_logger():
    path = SCRIPTS / "core" / "rice_events.py"
    spec = importlib.util.spec_from_file_location("rice_idle_events", path)
    if spec is None or spec.loader is None:
        raise IdleError("The rice activity logger could not be loaded.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def log_event(description: str, *, severity: str = "info", result: str = "success") -> None:
    try:
        event_logger().log_event(
            "idle",
            description,
            category="idle-management",
            severity=severity,
            result=result,
        )
    except (IdleError, OSError) as exc:
        print(f"idle-manager: could not write activity log: {exc}", file=sys.stderr)


def notify(title: str, body: str) -> None:
    binary = shutil.which("dunstify")
    if not binary:
        return
    result = subprocess.run(
        [binary, "-a", "Hypr Rice Idle", "-u", "low", title, body],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        print(f"idle-manager: notification failed: {result.stderr.strip()}", file=sys.stderr)


def seconds_label(seconds: int | None) -> str:
    if seconds is None:
        return "off"
    if seconds % 3600 == 0:
        return f"{seconds // 3600}h"
    if seconds >= 60:
        minutes, remainder = divmod(seconds, 60)
        return f"{minutes}m" if remainder == 0 else f"{minutes}m {remainder}s"
    return f"{seconds}s"


def effective_dpms_timeout(settings: dict[str, Any]) -> int | None:
    actions = settings["actions"]
    candidates = [
        actions[name]["seconds"]
        for name in ("blank", "display_off")
        if actions[name]["enabled"]
    ]
    if not candidates:
        return None
    timeout = min(candidates)
    lock_action = actions["lock"]
    if lock_action["enabled"]:
        timeout = max(timeout, lock_action["seconds"] + 5)
    return timeout


def effective_suspend_timeout(settings: dict[str, Any]) -> int | None:
    item = settings["actions"]["suspend"]
    if not item["enabled"]:
        return None
    timeout = item["seconds"]
    dpms = effective_dpms_timeout(settings)
    if dpms is not None:
        timeout = max(timeout, dpms + 5)
    lock_action = settings["actions"]["lock"]
    if lock_action["enabled"]:
        timeout = max(timeout, lock_action["seconds"] + 5)
    return timeout


def required_commands(settings: dict[str, Any]) -> dict[str, list[str]]:
    actions = settings["actions"]
    required: dict[str, list[str]] = {"session handling": ["loginctl"]}
    if settings["enabled"]:
        if actions["dim"]["enabled"]:
            required["dim"] = ["brightnessctl"]
        if any(actions[name]["enabled"] for name in ("blank", "display_off")):
            required["display power management"] = ["hyprctl"]
        if actions["lock"]["enabled"] or actions["suspend"]["enabled"]:
            required["locking"] = ["pidof", "hyprlock"] if actions["lock"]["enabled"] else []
        if actions["suspend"]["enabled"]:
            required["suspend"] = ["systemctl"]
    return required


def validate_dependencies(settings: dict[str, Any]) -> None:
    if shutil.which("hypridle") is None:
        raise IdleError("hypridle is not installed; no idle settings were applied.")
    missing = [
        f"{group}: {binary}"
        for group, binaries in required_commands(settings).items()
        for binary in binaries
        if shutil.which(binary) is None
    ]
    if missing:
        raise IdleError("Unavailable command(s) required by this profile: " + "; ".join(missing))


def render_hypridle_config(settings: dict[str, Any]) -> str:
    settings = validate_settings(settings)
    validate_dependencies(settings)
    script = str(SCRIPTS / "session" / "idle-manager.py")
    config = [
        "# Generated by scripts/idle-manager.py. Edit idle-settings.json via the Control Center.",
        "general {",
        f'    lock_cmd = pidof hyprlock || hyprlock -c "{LOCK_CONFIG}"',
        "    before_sleep_cmd = loginctl lock-session",
        "    after_sleep_cmd = hyprctl dispatch dpms on",
        "    ignore_dbus_inhibit = false",
        "    ignore_systemd_inhibit = false",
        "}",
    ]
    if not settings["enabled"]:
        return "\n".join(config) + "\n"

    actions = settings["actions"]
    if actions["dim"]["enabled"]:
        config.extend([
            "",
            "listener {",
            f'    timeout = {actions["dim"]["seconds"]}',
            "    on-timeout = brightnessctl -s set 20%",
            "    on-resume = brightnessctl -r",
            "}",
        ])
    if actions["lock"]["enabled"]:
        config.extend([
            "",
            "listener {",
            f'    timeout = {actions["lock"]["seconds"]}',
            "    on-timeout = loginctl lock-session",
            "}",
        ])

    dpms_timeout = effective_dpms_timeout(settings)
    if dpms_timeout is not None:
        config.extend([
            "",
            "listener {",
            f"    timeout = {dpms_timeout}",
            f'    on-timeout = "{sys.executable}" "{script}" --dpms-off',
            "    on-resume = hyprctl dispatch dpms on",
            "}",
        ])
    suspend_timeout = effective_suspend_timeout(settings)
    if suspend_timeout is not None:
        config.extend([
            "",
            "listener {",
            f"    timeout = {suspend_timeout}",
            "    on-timeout = systemctl suspend",
            "}",
        ])
    return "\n".join(config) + "\n"


def preview(settings: dict[str, Any]) -> str:
    if not settings["enabled"]:
        return "Idle management is disabled."
    actions = settings["actions"]
    sequence: list[tuple[int, str]] = []
    if actions["dim"]["enabled"]:
        sequence.append((actions["dim"]["seconds"], "Dim screen"))
    if actions["lock"]["enabled"]:
        sequence.append((actions["lock"]["seconds"], "Lock screen"))
    dpms = effective_dpms_timeout(settings)
    if dpms is not None:
        sequence.append((dpms, "Blank / power off displays (Hyprland DPMS)"))
    suspend = effective_suspend_timeout(settings)
    if suspend is not None:
        sequence.append((suspend, "Suspend"))
    if not sequence:
        return "No automatic idle actions are enabled."
    return "\n".join(f"{seconds_label(seconds)} — {label}" for seconds, label in sorted(sequence))


def process_cmdline(pid: int) -> list[bytes]:
    try:
        stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
        if stat.rsplit(")", 1)[1].split()[0] in {"Z", "X"}:
            return []
        return Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
    except (OSError, IndexError):
        return []


def process_uid(pid: int) -> int | None:
    try:
        for line in Path(f"/proc/{pid}/status").read_text(encoding="utf-8").splitlines():
            if line.startswith("Uid:"):
                return int(line.split()[1])
    except (OSError, ValueError, IndexError):
        return None
    return None


def all_hypridle_processes() -> list[tuple[int, list[bytes]]]:
    processes: list[tuple[int, list[bytes]]] = []
    for cmdline_path in Path("/proc").glob("[0-9]*/cmdline"):
        try:
            pid = int(cmdline_path.parent.name)
        except ValueError:
            continue
        if process_uid(pid) != os.getuid():
            continue
        argv = process_cmdline(pid)
        if argv and Path(os.fsdecode(argv[0])).name == "hypridle":
            processes.append((pid, argv))
    return processes


def configured_path(argv: list[bytes]) -> str | None:
    for index, value in enumerate(argv):
        if value in (b"-c", b"--config") and index + 1 < len(argv):
            return os.fsdecode(argv[index + 1])
    return None


def terminate_process(pid: int, expected_configs: set[str]) -> None:
    argv = process_cmdline(pid)
    if not argv or Path(os.fsdecode(argv[0])).name != "hypridle":
        return
    if process_uid(pid) != os.getuid() or configured_path(argv) not in expected_configs:
        raise IdleError(f"Refusing to stop unrelated idle daemon PID {pid}.")
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if not process_cmdline(pid):
            return
        time.sleep(0.1)
    argv = process_cmdline(pid)
    if argv and Path(os.fsdecode(argv[0])).name == "hypridle" and configured_path(argv) in expected_configs:
        os.kill(pid, signal.SIGKILL)


def state_data() -> dict[str, Any]:
    try:
        value = json.loads(MANAGER_STATE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError) as exc:
        raise IdleError(f"Could not read idle-manager runtime state: {exc}") from exc
    return value if isinstance(value, dict) else {}


def write_manager_state(manager_pid: int, child_pid: int | None, generation: int, error: str = "") -> None:
    payload = {
        "manager_pid": manager_pid,
        "hypridle_pid": child_pid,
        "generation": generation,
        "updated_at": int(time.time()),
        "error": error[:500],
    }
    atomic_write(MANAGER_STATE, (json.dumps(payload, indent=2) + "\n").encode())


def load_inhibitor_state() -> dict[str, Any]:
    try:
        data = json.loads(INHIBITOR_STATE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError) as exc:
        raise IdleError(f"Could not read idle-inhibitor state: {exc}") from exc
    return data if isinstance(data, dict) else {}


def owned_inhibitor_pids() -> list[int]:
    state = load_inhibitor_state()
    recorded = state.get("pid")
    candidates = [recorded] if isinstance(recorded, int) and recorded > 1 else []
    candidates.extend(
        int(path.parent.name)
        for path in Path("/proc").glob("[0-9]*/cmdline")
        if path.parent.name.isdecimal()
    )
    owned: list[int] = []
    for pid in dict.fromkeys(candidates):
        if process_uid(pid) != os.getuid():
            continue
        args = process_cmdline(pid)
        if (
            args
            and Path(os.fsdecode(args[0])).name == "systemd-inhibit"
            and b"--who=hypr-rice-idle-manager" in args
        ):
            owned.append(pid)
    return owned


def owned_inhibitor_pid() -> int | None:
    pids = owned_inhibitor_pids()
    return pids[0] if pids else None


def start_inhibitor() -> int:
    current = owned_inhibitor_pid()
    if current:
        return current
    binary = shutil.which("systemd-inhibit")
    if binary is None:
        raise IdleError("systemd-inhibit is unavailable; temporary idle inhibition cannot start.")
    process = subprocess.Popen(
        [
            binary, "--what=idle", "--who=hypr-rice-idle-manager",
            "--why=User requested keep-awake mode", "--mode=block", "sleep", "infinity",
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    time.sleep(0.2)
    if process.poll() is not None:
        error = process.stderr.read().strip() if process.stderr else ""
        raise IdleError(error or "systemd-inhibit exited before the idle lock was acquired.")
    atomic_write(INHIBITOR_STATE, (json.dumps({"pid": process.pid}) + "\n").encode())
    return process.pid


def stop_inhibitor() -> None:
    pids = owned_inhibitor_pids()
    if not pids:
        INHIBITOR_STATE.unlink(missing_ok=True)
        return
    for pid in pids:
        args = process_cmdline(pid)
        if (
            process_uid(pid) != os.getuid()
            or not args
            or Path(os.fsdecode(args[0])).name != "systemd-inhibit"
            or b"--who=hypr-rice-idle-manager" not in args
        ):
            continue
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            continue
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline and any(process_cmdline(pid) for pid in pids):
        time.sleep(0.1)
    INHIBITOR_STATE.unlink(missing_ok=True)


def is_idle_inhibited() -> bool:
    if owned_inhibitor_pids():
        return True
    result = subprocess.run(
        ["systemd-inhibit", "--list", "--no-pager", "--no-legend"],
        capture_output=True,
        text=True,
        check=False,
    ) if shutil.which("systemd-inhibit") else None
    return bool(
        result
        and result.returncode == 0
        and any(
            tag in line
            for line in result.stdout.splitlines()
            for tag in ("hypr-rice-presentation", "hypr-rice-session-preset")
        )
    )


def supervisor_alive(state: dict[str, Any] | None = None) -> bool:
    state = state or state_data()
    pid = state.get("manager_pid")
    if not isinstance(pid, int) or pid <= 1:
        return False
    args = process_cmdline(pid)
    return (
        bool(args)
        and Path(os.fsdecode(args[0])).name.startswith("python")
        and any(b"idle-manager.py" in arg for arg in args)
        and b"--supervise" in args
        and process_uid(pid) == os.getuid()
    )


def wait_child_start(process: subprocess.Popen[Any], timeout: float = 1.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        code = process.poll()
        if code is not None:
            raise IdleError(f"Hypridle exited during startup (status {code}); inspect {HYPRIDLE_LOG}.")
        time.sleep(0.05)


def supervisor() -> int:
    global _shutdown_requested, _reload_requested
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    lock_stream = MANAGER_LOCK.open("a")
    try:
        fcntl.flock(lock_stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return 0

    def request_shutdown(_signum: int, _frame: Any) -> None:
        global _shutdown_requested
        _shutdown_requested = True

    def request_reload(_signum: int, _frame: Any) -> None:
        global _reload_requested
        _reload_requested = True

    signal.signal(signal.SIGTERM, request_shutdown)
    signal.signal(signal.SIGINT, request_shutdown)
    signal.signal(SIGNAL_RELOAD, request_reload)
    child: subprocess.Popen[Any] | None = None
    generation = 0
    backoff = 2.0
    error = ""
    expected_configs = {str(RUNTIME_CONFIG), str(CONFIG / "hypridle.conf")}

    def managed_child() -> subprocess.Popen[Any] | None:
        current_settings = load_settings()
        rendered = render_hypridle_config(current_settings)
        atomic_write(RUNTIME_CONFIG, rendered.encode())
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        log_file = HYPRIDLE_LOG.open("ab", buffering=0)
        try:
            process = subprocess.Popen(
                [shutil.which("hypridle") or "hypridle", "--config", str(RUNTIME_CONFIG)],
                stdin=subprocess.DEVNULL,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        finally:
            log_file.close()
        wait_child_start(process)
        return process

    try:
        validate_dependencies(load_settings())
        for pid, argv in all_hypridle_processes():
            path = configured_path(argv)
            if path not in expected_configs:
                raise IdleError(f"Another Hypridle instance (PID {pid}) uses {path or 'default configuration'}.")
            terminate_process(pid, expected_configs)
        child = managed_child()
        generation += 1
        write_manager_state(os.getpid(), child.pid, generation)
        log_event(f"Hypridle started with preset {load_settings()['preset']}")
        while not _shutdown_requested:
            if _reload_requested:
                _reload_requested = False
                previous_content = RUNTIME_CONFIG.read_bytes() if RUNTIME_CONFIG.exists() else None
                try:
                    if child is not None and child.poll() is None:
                        terminate_process(child.pid, {str(RUNTIME_CONFIG)})
                        child.wait(timeout=2)
                    child = managed_child()
                    generation += 1
                    error = ""
                    write_manager_state(os.getpid(), child.pid, generation)
                    log_event(f"Hypridle reloaded with preset {load_settings()['preset']}")
                except (OSError, IdleError, subprocess.TimeoutExpired) as exc:
                    error = str(exc)
                    if previous_content is not None:
                        atomic_write(RUNTIME_CONFIG, previous_content)
                        try:
                            child = managed_child()
                        except (OSError, IdleError, subprocess.TimeoutExpired) as fallback_exc:
                            error += f"; previous configuration could not restart: {fallback_exc}"
                            child = None
                    generation += 1
                    write_manager_state(os.getpid(), child.pid if child else None, generation, error)
                    log_event(f"Hypridle reload failed: {error}", severity="error", result="failure")
                    notify("Idle settings not applied", error)
            if child is None or child.poll() is not None:
                if child is not None:
                    code = child.returncode
                    error = f"Hypridle exited unexpectedly with status {code}."
                    log_event(error, severity="error", result="failure")
                time.sleep(backoff)
                try:
                    child = managed_child()
                    generation += 1
                    error = ""
                    backoff = 2.0
                    write_manager_state(os.getpid(), child.pid, generation)
                    log_event("Hypridle recovered and restarted")
                    notify("Idle management recovered", "Hypridle restarted successfully.")
                except (OSError, IdleError, subprocess.TimeoutExpired) as exc:
                    error = str(exc)
                    backoff = min(backoff * 2, 30)
                    write_manager_state(os.getpid(), None, generation, error)
                    log_event(f"Hypridle restart failed: {error}", severity="error", result="failure")
            if not _shutdown_requested:
                time.sleep(0.2)
        if child is not None and child.poll() is None:
            terminate_process(child.pid, {str(RUNTIME_CONFIG)})
        MANAGER_STATE.unlink(missing_ok=True)
        return 0
    except (OSError, IdleError) as exc:
        log_event(f"Idle manager could not start: {exc}", severity="error", result="failure")
        notify("Idle management unavailable", str(exc))
        write_manager_state(os.getpid(), None, generation, str(exc))
        return 1
    finally:
        fcntl.flock(lock_stream.fileno(), fcntl.LOCK_UN)
        lock_stream.close()


def request_supervisor_reload() -> None:
    state = state_data()
    if supervisor_alive(state):
        pid = state["manager_pid"]
        before = state.get("generation", 0)
        os.kill(pid, SIGNAL_RELOAD)
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            updated = state_data()
            if updated.get("generation", 0) > before and not updated.get("error"):
                return
            time.sleep(0.15)
        current = state_data()
        if current.get("error"):
            raise IdleError(f"Hypridle could not apply the new settings: {current['error']}")
        raise IdleError("Timed out waiting for Hypridle to apply the new settings.")

    python = sys.executable
    subprocess.Popen(
        [python, str(SCRIPTS / "session" / "idle-manager.py"), "--supervise"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        state = state_data()
        if supervisor_alive(state):
            if isinstance(state.get("hypridle_pid"), int) and not state.get("error"):
                return
            if state.get("error"):
                raise IdleError(f"Idle manager startup failed: {state['error']}")
        time.sleep(0.15)
    raise IdleError("Timed out waiting for the idle manager to start.")


def commit_settings(settings: dict[str, Any], notification: tuple[str, str] | None = None) -> None:
    normalized = validate_settings(settings)
    render_hypridle_config(normalized)
    old_exists = SETTINGS_FILE.exists()
    old_content = SETTINGS_FILE.read_bytes() if old_exists else None
    snapshot_before_change()
    try:
        atomic_write(SETTINGS_FILE, (json.dumps(normalized, indent=2) + "\n").encode())
        request_supervisor_reload()
    except (OSError, IdleError) as exc:
        if old_exists and old_content is not None:
            atomic_write(SETTINGS_FILE, old_content)
        else:
            SETTINGS_FILE.unlink(missing_ok=True)
        try:
            request_supervisor_reload()
        except (OSError, IdleError) as rollback_exc:
            raise IdleError(f"{exc}; settings were reverted but daemon rollback failed: {rollback_exc}") from exc
        raise IdleError(f"Settings were reverted because Hypridle could not apply them: {exc}") from exc
    log_event(f"Applied idle preset {normalized['preset']}")
    title, body = notification or ("Idle settings updated", f"Active preset: {normalized['preset']}.")
    notify(title, body)


def apply_preset(name: str) -> None:
    updated = preset_settings(name)
    current = load_settings()
    updated["enabled"] = current["enabled"]
    commit_settings(updated)


def set_master_enabled(enabled: bool) -> None:
    updated = load_settings()
    updated["enabled"] = enabled
    commit_settings(
        updated,
        (
            "Idle management " + ("enabled" if enabled else "disabled"),
            "Automatic idle actions are now " + ("active." if enabled else "paused."),
        ),
    )


def set_action(action_name: str, enabled: bool | None = None, seconds: int | None = None) -> None:
    if action_name not in ACTION_NAMES:
        raise IdleError(f"Unknown idle action: {action_name}")
    updated = load_settings()
    item = updated["actions"][action_name]
    if enabled is not None:
        item["enabled"] = enabled
        if enabled and item["seconds"] is None:
            item["seconds"] = 300
    if seconds is not None:
        if not isinstance(seconds, int) or isinstance(seconds, bool) or not 15 <= seconds <= 86400:
            raise IdleError("Timeout must be between 15 seconds and 24 hours.")
        item["seconds"] = seconds
    updated["preset"] = "Custom"
    commit_settings(updated)


def format_status(settings: dict[str, Any] | None = None) -> str:
    settings = settings or load_settings()
    state = state_data()
    manager = "running" if supervisor_alive(state) else "not running"
    child_pid = state.get("hypridle_pid")
    child_running = isinstance(child_pid, int) and bool(process_cmdline(child_pid))
    status = (
        f"Preset: {settings['preset']}\n"
        f"Idle management: {'enabled' if settings['enabled'] else 'disabled'}\n"
        f"Hypridle manager: {manager}\n"
        f"Hypridle process: {'running' if child_running else 'not running'}\n"
        f"Temporary idle inhibition: {'active' if is_idle_inhibited() else 'inactive'}\n"
        f"Next actions:\n{preview(settings)}"
    )
    if state.get("error"):
        status += f"\nLast daemon error: {state['error']}"
    return status


def choose(options: list[str], prompt: str) -> str | None:
    rofi = shutil.which("rofi")
    if rofi is None:
        raise IdleError("Rofi is not installed.")
    result = subprocess.run(
        [rofi, "-dmenu", "-i", "-config", str(CONFIG / "rofi" / "command-center.rasi"), "-p", prompt],
        input="\n".join(options) + "\n",
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    if result.returncode == 1:
        return None
    if result.returncode:
        raise IdleError(result.stderr.strip() or "Rofi returned an error.")
    return result.stdout.strip() or None


def custom_timeout(name: str, current: int | None) -> int | None:
    preset_values = [
        ("15 seconds", 15), ("30 seconds", 30), ("1 minute", 60), ("2 minutes", 120),
        ("3 minutes", 180), ("5 minutes", 300), ("10 minutes", 600),
        ("15 minutes", 900), ("20 minutes", 1200), ("30 minutes", 1800),
        ("45 minutes", 2700), ("60 minutes", 3600), ("Custom seconds…", None),
    ]
    labels = [f"{label}  ·  current" if seconds == current else label for label, seconds in preset_values]
    selected = choose(labels, f"{ACTION_LABELS[name]} timeout")
    if selected is None:
        return None
    index = labels.index(selected)
    value = preset_values[index][1]
    if value is not None:
        return value
    entered = choose([str(current or 300)], "Enter timeout in seconds (15–86400)")
    if entered is None:
        return None
    if not entered.isdecimal():
        raise IdleError("Timeout must be a whole number of seconds.")
    value = int(entered)
    if not 15 <= value <= 86400:
        raise IdleError("Timeout must be between 15 seconds and 24 hours.")
    return value


def edit_actions() -> None:
    while True:
        settings = load_settings()
        choices = []
        for name in ACTION_NAMES:
            item = settings["actions"][name]
            state = "On" if item["enabled"] else "Off"
            choices.append(
                f"{ACTION_LABELS[name]}: {state} · {seconds_label(item['seconds'])}"
            )
        choices.append("Back")
        selected = choose(choices, "Idle action settings")
        if not selected or selected == "Back":
            return
        action_name = next((name for name in ACTION_NAMES if selected.startswith(ACTION_LABELS[name] + ":")), None)
        if action_name is None:
            continue
        item = settings["actions"][action_name]
        operation = choose(
            [
                f"Toggle action ({'On' if item['enabled'] else 'Off'})",
                f"Set timeout ({seconds_label(item['seconds'])})",
                "Back",
            ],
            ACTION_LABELS[action_name],
        )
        if operation is None or operation == "Back":
            continue
        if operation.startswith("Toggle"):
            set_action(action_name, enabled=not item["enabled"])
        elif operation.startswith("Set"):
            value = custom_timeout(action_name, item["seconds"])
            if value is not None:
                set_action(action_name, seconds=value)


def toggle_inhibition() -> None:
    if owned_inhibitor_pid():
        stop_inhibitor()
        log_event("Temporary idle inhibition deactivated")
        notify("Keep awake disabled", "Normal idle behavior has resumed.")
        return
    pid = start_inhibitor()
    log_event(f"Temporary idle inhibition activated (PID {pid})")
    notify("Keep awake enabled", "Automatic idle actions are temporarily inhibited.")


def show_menu() -> None:
    while True:
        settings = load_settings()
        inhibitor = is_idle_inhibited()
        choices = [
            f"Current: {settings['preset']} · idle {'On' if settings['enabled'] else 'Off'}",
            "Choose timeout preset",
            f"Toggle idle management ({'On' if settings['enabled'] else 'Off'})",
            f"Keep screen awake ({'active' if inhibitor else 'inactive'})",
        ]
        choices.extend(["Edit individual actions", "Reset to preset defaults", "Preview timeout sequence", "Close"])
        selected = choose(choices, "Screen Timeout / Idle Management")
        if not selected or selected == "Close":
            return
        if selected == "Choose timeout preset":
            current = load_settings()["preset"]
            options = [f"{name}  ·  active" if name == current else name for name in PRESET_NAMES[:-1]]
            preset = choose(options, "Select timeout preset")
            if preset:
                apply_preset(preset.split("  ·  active")[0])
        elif selected.startswith("Toggle idle management"):
            set_master_enabled(not settings["enabled"])
        elif selected.startswith("Keep screen awake"):
            toggle_inhibition()
        elif selected == "Edit individual actions":
            edit_actions()
        elif selected == "Reset to preset defaults":
            preset = settings["preset"]
            if preset == "Custom":
                preset = choose([name for name in PRESET_NAMES if name != "Custom"], "Reset custom settings to preset")
            if preset:
                apply_preset(preset)
        elif selected == "Preview timeout sequence":
            choose([*format_status(settings).splitlines(), "Close"], "Idle configuration")


def session_is_locked() -> bool:
    loginctl = shutil.which("loginctl")
    if loginctl is None:
        return False
    session_id = os.environ.get("XDG_SESSION_ID")
    candidates = [session_id] if session_id else []
    if not candidates:
        result = subprocess.run(
            [loginctl, "list-sessions", "--no-legend", "--no-pager"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                fields = line.split()
                if len(fields) >= 2 and fields[1] == str(os.getuid()):
                    candidates.append(fields[0])
    for candidate in candidates:
        result = subprocess.run(
            [loginctl, "show-session", candidate, "--property=LockedHint", "--value"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip().lower() == "yes":
            return True
    return False


def dpms_off() -> int:
    settings = load_settings()
    lock_required = settings["enabled"] and settings["actions"]["lock"]["enabled"]
    if lock_required:
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline and not session_is_locked():
            time.sleep(0.5)
        if not session_is_locked():
            message = "Display power-off was cancelled because the lock screen could not be confirmed."
            log_event(message, severity="error", result="blocked")
            notify("Display remains on", message)
            return 1
    hyprctl = shutil.which("hyprctl")
    if hyprctl is None:
        raise IdleError("hyprctl is unavailable; displays were not powered off.")
    result = subprocess.run([hyprctl, "dispatch", "dpms", "off"], capture_output=True, text=True, check=False)
    if result.returncode:
        raise IdleError(result.stderr.strip() or result.stdout.strip() or "Hyprland could not power off displays.")
    return 0


def validate_command() -> int:
    settings = load_settings()
    validate_dependencies(settings)
    render_hypridle_config(settings)
    print(f"Settings: valid ({settings['preset']})")
    print("Hypridle config: generated and internally validated")
    print("Dependencies: available for enabled actions")
    print("Effective action sequence:")
    print(preview(settings))
    print("\nNote: Hyprland provides one DPMS off state; blanking and display power-off share it.")
    return 0


def main(argv: list[str]) -> int:
    try:
        if argv == ["--supervise"]:
            return supervisor()
        if argv == ["--status"]:
            print(format_status())
            return 0
        if argv == ["--validate"]:
            return validate_command()
        if argv in (["--menu"], ["--quick"]):
            show_menu()
            return 0
        if argv == ["--dpms-off"]:
            return dpms_off()
        if argv in (["--keep-awake"], ["--toggle-inhibit"]):
            toggle_inhibition()
            return 0
        if argv == ["--resume-idle"]:
            stop_inhibitor()
            log_event("Temporary idle inhibition deactivated")
            notify("Keep awake disabled", "Normal idle behavior has resumed.")
            return 0
        if len(argv) == 2 and argv[0] == "--preset":
            apply_preset(argv[1])
            return 0
        if len(argv) == 2 and argv[0] == "--master":
            if argv[1] == "toggle":
                set_master_enabled(not load_settings()["enabled"])
            elif argv[1] in ("on", "off"):
                set_master_enabled(argv[1] == "on")
            else:
                raise IdleError("Use --master on, off, or toggle.")
            return 0
        if len(argv) == 3 and argv[0] == "--action":
            name, operation = argv[1:]
            if operation == "on":
                set_action(name, enabled=True)
            elif operation == "off":
                set_action(name, enabled=False)
            elif operation.isdecimal():
                set_action(name, seconds=int(operation))
            else:
                raise IdleError("Action operation must be on, off, or a timeout in seconds.")
            return 0
        raise IdleError(
            "Usage: idle-manager.py [--menu|--quick (alias for --menu)|--status|--validate|--preset NAME|"
            "--master on|off|--action NAME on|off|SECONDS|--keep-awake|--resume-idle]"
        )
    except (IdleError, OSError, subprocess.TimeoutExpired) as exc:
        print(f"idle-manager: {exc}", file=sys.stderr)
        log_event(str(exc), severity="error", result="failure")
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
