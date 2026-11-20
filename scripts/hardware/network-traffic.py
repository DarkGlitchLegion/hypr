#!/usr/bin/env python3
"""Track default-route network traffic and persist cumulative byte totals."""

from __future__ import annotations

import fcntl
import json
import os
import signal
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any


HOME = Path.home()
STATE_DIR = Path(os.environ.get("XDG_STATE_HOME", HOME / ".local" / "state")) / "hypr-rice"
STATE_FILE = STATE_DIR / "network-traffic.json"
RUNTIME_DIR = Path(os.environ.get("XDG_RUNTIME_DIR", tempfile.gettempdir())) / "hypr-rice"
LOCK_FILE = RUNTIME_DIR / "network-traffic.lock"
INTERFACES_DIR = Path("/sys/class/net")
IPV4_ROUTES = Path("/proc/net/route")
IPV6_ROUTES = Path("/proc/net/ipv6_route")
POLL_INTERVAL = 1.0
_stop = threading.Event()


class TrafficError(RuntimeError):
    """Invalid or unavailable persisted network traffic state."""


def _read_totals(path: Path) -> tuple[int, int]:
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return 0, 0
    except (OSError, json.JSONDecodeError) as exc:
        raise TrafficError(f"Cannot read network statistics from {path}: {exc}") from exc

    if not isinstance(state, dict) or state.get("version") != 1:
        raise TrafficError(f"Unsupported network statistics format in {path}.")
    downloaded = state.get("downloaded_bytes")
    uploaded = state.get("uploaded_bytes")
    if (type(downloaded) is not int or downloaded < 0
            or type(uploaded) is not int or uploaded < 0):
        raise TrafficError(f"Invalid cumulative byte totals in {path}.")
    return downloaded, uploaded


def _atomic_write(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(state, stream, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def read_interface_counters(interfaces_dir: Path = INTERFACES_DIR) -> dict[str, tuple[int, int]]:
    counters = {}
    try:
        interfaces = list(interfaces_dir.iterdir())
    except OSError:
        return counters

    for interface in interfaces:
        if interface.name == "lo":
            continue
        try:
            received = int((interface / "statistics" / "rx_bytes").read_text().strip())
            transmitted = int((interface / "statistics" / "tx_bytes").read_text().strip())
        except (OSError, ValueError):
            continue
        if received >= 0 and transmitted >= 0:
            counters[interface.name] = (received, transmitted)
    return counters


def default_route_interface(
    interfaces: set[str],
    ipv4_routes: str | None = None,
    ipv6_routes: str | None = None,
) -> str | None:
    if ipv4_routes is None:
        try:
            ipv4_routes = IPV4_ROUTES.read_text(encoding="ascii")
        except OSError:
            ipv4_routes = ""
    if ipv6_routes is None:
        try:
            ipv6_routes = IPV6_ROUTES.read_text(encoding="ascii")
        except OSError:
            ipv6_routes = ""

    routes: list[tuple[int, str]] = []
    for line in ipv4_routes.splitlines()[1:]:
        fields = line.split()
        if len(fields) < 7 or fields[1] != "00000000":
            continue
        try:
            flags = int(fields[3], 16)
            metric = int(fields[6])
        except ValueError:
            continue
        if flags & 1 and fields[0] in interfaces:
            routes.append((metric, fields[0]))

    for line in ipv6_routes.splitlines():
        fields = line.split()
        if len(fields) < 10 or fields[0] != "0" * 32 or fields[1] != "00":
            continue
        try:
            metric = int(fields[5], 16)
            flags = int(fields[8], 16)
        except ValueError:
            continue
        if flags & 1 and fields[9] in interfaces:
            routes.append((metric, fields[9]))

    return min(routes)[1] if routes else None


class TrafficMonitor:
    def __init__(self, state_file: Path = STATE_FILE) -> None:
        self.state_file = state_file
        self.downloaded_bytes, self.uploaded_bytes = _read_totals(state_file)
        self._previous_counters: dict[str, tuple[int, int]] | None = None
        self._previous_interface: str | None = None
        self._previous_time: float | None = None

    def sample(
        self,
        counters: dict[str, tuple[int, int]] | None = None,
        active_interface: str | None = None,
        now: float | None = None,
    ) -> dict[str, Any]:
        if counters is None:
            counters = read_interface_counters()
        if active_interface not in counters:
            active_interface = None
        if now is None:
            now = time.monotonic()

        download_delta = 0
        upload_delta = 0
        elapsed = 0.0
        if (self._previous_counters is not None and self._previous_time is not None
                and active_interface is not None
                and active_interface == self._previous_interface
                and active_interface in self._previous_counters):
            elapsed = max(0.0, now - self._previous_time)
            old_rx, old_tx = self._previous_counters[active_interface]
            new_rx, new_tx = counters[active_interface]
            if elapsed > 0 and new_rx >= old_rx:
                download_delta = new_rx - old_rx
            if elapsed > 0 and new_tx >= old_tx:
                upload_delta = new_tx - old_tx

        self.downloaded_bytes += download_delta
        self.uploaded_bytes += upload_delta
        self._previous_counters = counters.copy()
        self._previous_interface = active_interface
        self._previous_time = now

        state = {
            "version": 1,
            "updated_at": time.time(),
            "interface": active_interface or "",
            "connected": active_interface is not None,
            "download_bps": download_delta / elapsed if elapsed > 0 else 0.0,
            "upload_bps": upload_delta / elapsed if elapsed > 0 else 0.0,
            "downloaded_bytes": self.downloaded_bytes,
            "uploaded_bytes": self.uploaded_bytes,
        }
        _atomic_write(self.state_file, state)
        return state


def run_monitor() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    with LOCK_FILE.open("w", encoding="utf-8") as lock_stream:
        try:
            fcntl.flock(lock_stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return

        monitor = TrafficMonitor()

        def stop(*_args: object) -> None:
            _stop.set()

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        while not _stop.is_set():
            counters = read_interface_counters()
            active = default_route_interface(set(counters))
            monitor.sample(counters, active)
            _stop.wait(POLL_INTERVAL)


def main(argv: list[str]) -> int:
    if argv != ["--watch"]:
        print("Usage: network-traffic.py --watch", file=sys.stderr)
        return 2
    try:
        run_monitor()
    except (OSError, TrafficError) as exc:
        print(f"Network traffic monitor failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
