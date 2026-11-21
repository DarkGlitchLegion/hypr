#!/usr/bin/env python3
"""Small JSON bridge for the native Quickshell clipboard history view."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


def run(args: list[str], *, data: bytes | None = None) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(args, input=data, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)


def list_entries() -> list[dict[str, str | int]]:
    if shutil.which("cliphist"):
        output = run(["cliphist", "list"]).stdout.decode("utf-8", "replace")
        entries = []
        for line in output.splitlines():
            identity, separator, preview = line.partition("\t")
            if separator and identity.isdigit():
                entries.append({"id": int(identity), "preview": preview})
        return entries

    cache = Path.home() / ".cache/hypr_clipboard"
    history = cache / "history.txt"
    entries = []
    if history.exists():
        for line in history.read_text(errors="replace").splitlines():
            identity, separator, preview = line.partition("|")
            if separator:
                entries.append({"id": identity, "preview": preview})
    return entries


def copy_entry(identity: str) -> int:
    if shutil.which("cliphist"):
        decoded = run(["cliphist", "decode"], data=(identity + "\n").encode())
        if decoded.returncode != 0:
            return decoded.returncode
        return run(["wl-copy"], data=decoded.stdout).returncode

    cache = Path.home() / ".cache/hypr_clipboard"
    item = cache / (identity + ".txt")
    if not item.is_file():
        return 1
    return run(["wl-copy"], data=item.read_bytes()).returncode


def main() -> int:
    if len(sys.argv) == 2 and sys.argv[1] == "list":
        print(json.dumps(list_entries(), ensure_ascii=False))
        return 0
    if len(sys.argv) == 3 and sys.argv[1] == "copy":
        return copy_entry(sys.argv[2])
    print("Usage: qml-clipboard.py list | copy ID", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
