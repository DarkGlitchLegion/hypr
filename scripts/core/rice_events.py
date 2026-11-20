"""Small rotating JSONL event log shared by rice maintenance tools."""

from __future__ import annotations

import json
import os
import fcntl
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LOG_DIR = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state")) / "hypr-rice"
LOG_FILE = LOG_DIR / "events.jsonl"
LOCK_FILE = LOG_DIR / ".events.lock"
MAX_BYTES = 2 * 1024 * 1024
ROTATIONS = 3


def _rotate_if_needed(incoming_bytes: int) -> None:
    if not LOG_FILE.exists() or LOG_FILE.stat().st_size + incoming_bytes <= MAX_BYTES:
        return
    oldest = LOG_FILE.with_suffix(f".jsonl.{ROTATIONS}")
    oldest.unlink(missing_ok=True)
    for index in range(ROTATIONS - 1, 0, -1):
        source = LOG_FILE.with_suffix(f".jsonl.{index}")
        if source.exists():
            source.replace(LOG_FILE.with_suffix(f".jsonl.{index + 1}"))
    LOG_FILE.replace(LOG_FILE.with_suffix(".jsonl.1"))


def log_event(
    component: str,
    description: str,
    *,
    category: str = "operation",
    severity: str = "info",
    result: str = "success",
    details: dict[str, Any] | None = None,
) -> None:
    """Append a bounded event without logging environment or secret values."""
    safe_description = re.sub(
        r"(?i)\b(password|passphrase|token|secret|credential|api[_-]?key|private[_-]?key)\b\s*[:=]\s*\S+",
        r"\1=[redacted]",
        description,
    )
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "category": category,
        "component": component,
        "severity": severity,
        "description": safe_description[:500],
        "result": result,
    }
    if details:
        event["details"] = {
            str(key)[:80]: str(value)[:300]
            for key, value in details.items()
            if not any(
                token in re.sub(r"[^a-z0-9]", "", str(key).lower())
                for token in ("password", "passphrase", "token", "secret", "credential", "apikey", "privatekey")
            )
        }
    line = (json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with LOCK_FILE.open("a") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        _rotate_if_needed(len(line))
        with LOG_FILE.open("ab") as file:
            file.write(line)
            file.flush()
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def read_events() -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for path in [
        *(LOG_DIR / f"events.jsonl.{index}" for index in range(ROTATIONS, 0, -1)),
        LOG_FILE,
    ]:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise OSError(f"Could not read activity log {path}: {exc}") from exc
        for line_number, line in enumerate(lines, start=1):
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise OSError(f"Invalid activity log record in {path} at line {line_number}: {exc}") from exc
            if isinstance(event, dict):
                events.append(event)
            else:
                raise OSError(f"Invalid activity log record in {path} at line {line_number}: expected an object.")
    return events


def clear_events() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with LOCK_FILE.open("a") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            for path in [LOG_FILE, *(LOG_DIR / f"events.jsonl.{index}" for index in range(1, ROTATIONS + 1))]:
                path.unlink(missing_ok=True)
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
