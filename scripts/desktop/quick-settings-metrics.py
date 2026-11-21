#!/usr/bin/env python3
"""Emit compact CPU, memory, temperature, and network-counter data for Quickshell."""

from __future__ import annotations

import json
import sys


def main() -> int:
    try:
        import psutil
    except ImportError:
        print(json.dumps({"available": False, "error": "python-psutil is not installed"}))
        return 0

    memory = psutil.virtual_memory()
    temperatures: dict[str, float] = {}
    try:
        for sensor, readings in psutil.sensors_temperatures().items():
            if not readings:
                continue
            current = next((reading.current for reading in readings if reading.current > 0), None)
            if current is None:
                continue
            name = sensor.casefold()
            if "k10temp" in name or "coretemp" in name or "cpu" in name:
                temperatures["cpu"] = round(current, 1)
            elif "amdgpu" in name or "gpu" in name or "nvidia" in name:
                temperatures["gpu"] = round(current, 1)
    except (AttributeError, OSError):
        pass

    interface = sys.argv[1] if len(sys.argv) > 1 else ""
    counters = psutil.net_io_counters(pernic=True).get(interface) if interface else None
    print(json.dumps({
        "available": True,
        "cpuPercent": round(psutil.cpu_percent(interval=0.1), 1),
        "memoryPercent": round(memory.percent, 1),
        "memoryUsedBytes": memory.used,
        "memoryTotalBytes": memory.total,
        "temperatures": temperatures,
        "network": {
            "interface": interface or None,
            "rxBytes": counters.bytes_recv if counters else None,
            "txBytes": counters.bytes_sent if counters else None,
        },
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
