#!/usr/bin/env python3
"""JSON and action bridge for the Quickshell Network page."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys


def fields(line: str) -> list[str]:
    result: list[str] = []
    current: list[str] = []
    escaped = False
    for char in line:
        if escaped:
            current.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == ":":
            result.append("".join(current))
            current = []
        else:
            current.append(char)
    result.append("".join(current))
    return result


def run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, check=False, timeout=15)


def main() -> int:
    if not shutil.which("nmcli"):
        print("[]")
        return 0
    if len(sys.argv) == 2 and sys.argv[1] == "list":
        result = run(["nmcli", "--terse", "--escape", "yes", "--fields", "IN-USE,SSID,SIGNAL,SECURITY", "device", "wifi", "list", "--rescan", "no"])
        networks = []
        for line in result.stdout.splitlines():
            values = fields(line)
            if len(values) >= 4 and values[1]:
                networks.append({"active": values[0] == "*", "ssid": values[1], "signal": int(values[2] or 0), "security": values[3] or "Open"})
        strongest: dict[str, dict[str, str | int | bool]] = {}
        for network in networks:
            previous = strongest.get(str(network["ssid"]))
            if previous is None or network["active"] or int(network["signal"]) > int(previous["signal"]):
                strongest[str(network["ssid"])] = network
        print(json.dumps(sorted(strongest.values(), key=lambda item: (-int(item["signal"]), str(item["ssid"]).casefold())), ensure_ascii=False))
        return 0
    if len(sys.argv) >= 3 and sys.argv[1] == "connect":
        ssid = sys.argv[2]
        password = sys.argv[3] if len(sys.argv) > 3 else ""
        args = ["nmcli", "--wait", "20", "device", "wifi", "connect", ssid]
        if password:
            args.extend(["password", password])
        result = run(args)
        if result.returncode:
            print(result.stderr.strip() or result.stdout.strip(), file=sys.stderr)
        return result.returncode
    print("Usage: qml-network.py list | connect SSID [PASSWORD]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
