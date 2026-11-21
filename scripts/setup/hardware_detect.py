from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


@dataclass
class SystemInfo:
    distro_id: str
    distro_name: str
    package_manager: str
    architecture: str
    gpu_vendors: list[str] = field(default_factory=list)
    device_type: str = "desktop"
    hyprland_running: bool = False
    hyprland_installed: bool = False
    monitors: list[dict] = field(default_factory=list)
    existing_config: bool = False
    missing_utilities: list[str] = field(default_factory=list)


def run(command: list[str], timeout: float = 3.0) -> str:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
        return result.stdout.strip() if result.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def detect_distro() -> tuple[str, str]:
    values: dict[str, str] = {}
    try:
        for line in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key] = value.strip().strip('"')
    except OSError:
        return "unknown", "Unknown Linux"
    distro_id = (values.get("ID") or "unknown").lower()
    name = values.get("PRETTY_NAME") or values.get("NAME") or "Unknown Linux"
    return distro_id, name


def detect_package_manager(distro_id: str) -> str:
    for binary, manager in (("pacman", "pacman"), ("apt-get", "apt"), ("dnf", "dnf"), ("zypper", "zypper")):
        if shutil.which(binary):
            if manager == "pacman" or distro_id not in ("", "unknown"):
                return manager
    return "unsupported"


def detect_gpu_vendors() -> list[str]:
    vendors: set[str] = set()
    pci = run(["lspci", "-nn"])
    lowered = pci.lower()
    if "nvidia" in lowered:
        vendors.add("nvidia")
    if "advanced micro devices" in lowered or "amd" in lowered or "ati " in lowered:
        vendors.add("amd")
    if "intel" in lowered:
        vendors.add("intel")
    for vendor in Path("/sys/class/drm").glob("*/device/vendor"):
        try:
            value = vendor.read_text(encoding="ascii").strip().lower()
        except OSError:
            continue
        if value == "0x10de":
            vendors.add("nvidia")
        elif value == "0x1002":
            vendors.add("amd")
        elif value == "0x8086":
            vendors.add("intel")
    return sorted(vendors)


def detect_device_type() -> str:
    try:
        chassis = Path("/sys/class/dmi/id/chassis_type").read_text(encoding="ascii").strip()
        if chassis in {"8", "9", "10", "11", "14"}:
            return "laptop"
    except OSError:
        pass
    for indicator in (
        Path("/sys/class/power_supply"),
        Path("/proc/acpi/button"),
    ):
        try:
            if indicator.exists() and any(indicator.iterdir()):
                if indicator.name == "power_supply":
                    for entry in indicator.iterdir():
                        if entry.name.startswith("BAT"):
                            return "laptop"
        except OSError:
            pass
    return "desktop"


def detect_monitors() -> list[dict]:
    output = run(["hyprctl", "-j", "monitors"], timeout=5)
    if not output:
        return []
    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def detect_system(home: Path, required_utilities: Iterable[str]) -> SystemInfo:
    distro_id, distro_name = detect_distro()
    architecture = run(["uname", "-m"]) or os.uname().machine
    hyprland_binary = shutil.which("Hyprland") or shutil.which("hyprland")
    hyprland_running = bool(run(["hyprctl", "activeworkspace"], timeout=2))
    monitors = detect_monitors() if hyprland_running else []
    missing = [name for name in required_utilities if shutil.which(name) is None]
    config = home / ".config" / "hypr"
    return SystemInfo(
        distro_id=distro_id,
        distro_name=distro_name,
        package_manager=detect_package_manager(distro_id),
        architecture=architecture,
        gpu_vendors=detect_gpu_vendors(),
        device_type=detect_device_type(),
        hyprland_running=hyprland_running,
        hyprland_installed=bool(hyprland_binary),
        monitors=monitors,
        existing_config=config.exists(),
        missing_utilities=missing,
    )
