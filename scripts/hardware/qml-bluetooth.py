#!/usr/bin/env python3
"""JSON and safe device actions for the Quickshell Bluetooth page."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys

MAC = re.compile(r"^(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")


def call(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["bluetoothctl", *args], capture_output=True, text=True, check=False, timeout=15)


def main() -> int:
    if not shutil.which("bluetoothctl"):
        print("[]")
        return 0
    if len(sys.argv) == 2 and sys.argv[1] == "list":
        devices = call("devices")
        result = []
        for line in devices.stdout.splitlines():
            match = re.match(r"Device\s+([0-9A-Fa-f:]{17})\s+(.+)$", line.strip())
            if not match:
                continue
            mac, name = match.groups()
            info = call("info", mac).stdout
            result.append({
                "mac": mac,
                "name": name,
                "paired": "Paired: yes" in info,
                "connected": "Connected: yes" in info,
                "trusted": "Trusted: yes" in info,
            })
        print(json.dumps(result, ensure_ascii=False))
        return 0
    if len(sys.argv) == 3 and sys.argv[1] in {"pair", "connect", "disconnect", "remove"} and MAC.fullmatch(sys.argv[2]):
        result = call(sys.argv[1], sys.argv[2])
        if result.returncode:
            print(result.stderr.strip() or result.stdout.strip(), file=sys.stderr)
        return result.returncode
    print("Usage: qml-bluetooth.py list | pair|connect|disconnect|remove MAC", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
