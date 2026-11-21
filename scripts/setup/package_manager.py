from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


PACKAGE_MAP: dict[str, dict[str, list[str]]] = {
    "hyprland": {"pacman": ["hyprland"], "apt": ["hyprland"], "dnf": ["hyprland"]},
    "waybar": {"pacman": ["waybar"], "apt": ["waybar"], "dnf": ["waybar"]},
    "dunst": {"pacman": ["dunst"], "apt": ["dunst"], "dnf": ["dunst"]},
    "rofi": {"pacman": ["rofi-wayland"], "apt": ["rofi"], "dnf": ["rofi-wayland"]},
    "kitty": {"pacman": ["kitty"], "apt": ["kitty"], "dnf": ["kitty"]},
    "hyprpaper": {"pacman": ["hyprpaper"], "apt": ["hyprpaper"], "dnf": ["hyprpaper"]},
    "hyprlock": {"pacman": ["hyprlock"], "apt": ["hyprlock"], "dnf": ["hyprlock"]},
    "hypridle": {"pacman": ["hypridle"], "apt": ["hypridle"], "dnf": ["hypridle"]},
    "polkit-agent": {"pacman": ["hyprpolkitagent"], "apt": ["polkitd"], "dnf": ["hyprpolkitagent"]},
    "network-manager": {"pacman": ["networkmanager"], "apt": ["network-manager"], "dnf": ["NetworkManager"]},
    "quickshell": {"pacman": ["quickshell"], "apt": [], "dnf": []},
    "pipewire": {"pacman": ["pipewire"], "apt": ["pipewire"], "dnf": ["pipewire"]},
    "wireplumber": {"pacman": ["wireplumber"], "apt": ["wireplumber"], "dnf": ["wireplumber"]},
    "pipewire-pulse": {"pacman": ["pipewire-pulse"], "apt": ["pipewire-pulse"], "dnf": ["pipewire-pulseaudio"]},
    "pavucontrol": {"pacman": ["pavucontrol"], "apt": ["pavucontrol"], "dnf": ["pavucontrol"]},
    "wl-clipboard": {"pacman": ["wl-clipboard"], "apt": ["wl-clipboard"], "dnf": ["wl-clipboard"]},
    "grim": {"pacman": ["grim"], "apt": ["grim"], "dnf": ["grim"]},
    "slurp": {"pacman": ["slurp"], "apt": ["slurp"], "dnf": ["slurp"]},
    "brightnessctl": {"pacman": ["brightnessctl"], "apt": ["brightnessctl"], "dnf": ["brightnessctl"]},
    "cliphist": {"pacman": ["cliphist"], "apt": [], "dnf": []},
    "bluez": {"pacman": ["bluez", "bluez-utils"], "apt": ["bluez"], "dnf": ["bluez"]},
    "thunar": {"pacman": ["thunar"], "apt": ["thunar"], "dnf": ["thunar"]},
    "btop": {"pacman": ["btop"], "apt": ["btop"], "dnf": ["btop"]},
    "fastfetch": {"pacman": ["fastfetch"], "apt": ["fastfetch"], "dnf": ["fastfetch"]},
    "firefox": {"pacman": ["firefox"], "apt": ["firefox-esr"], "dnf": ["firefox"]},
    "code": {"pacman": ["code"], "apt": [], "dnf": ["code"]},
    "lazygit": {"pacman": ["lazygit"], "apt": [], "dnf": ["lazygit"]},
    "psutil": {"pacman": ["python-psutil"], "apt": ["python3-psutil"], "dnf": ["python3-psutil"]},
    "pygobject": {"pacman": ["python-gobject"], "apt": ["python3-gi"], "dnf": ["python3-gobject"]},
    "gtk-layer-shell": {"pacman": ["gtk-layer-shell"], "apt": ["libgtk-layer-shell0"], "dnf": ["gtk-layer-shell"]},
}


@dataclass
class PackagePlan:
    package_manager: str
    profile: str
    install: list[str]
    already_installed: list[str]
    unsupported_tokens: list[str]


def read_manifest(path: Path) -> list[str]:
    tokens: list[str] = []
    section = "all"
    if not path.exists():
        return tokens
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].lower()
            continue
        if section in ("all", "common"):
            tokens.append(line)
    return tokens


def map_packages(tokens: Iterable[str], manager: str) -> tuple[list[str], list[str]]:
    packages: list[str] = []
    unsupported: list[str] = []
    for token in tokens:
        mapping = PACKAGE_MAP.get(token, {})
        names = mapping.get(manager, [])
        if not names:
            unsupported.append(token)
        else:
            packages.extend(names)
    return list(dict.fromkeys(packages)), list(dict.fromkeys(unsupported))


def package_is_installed(package: str, manager: str) -> bool:
    if manager == "pacman":
        return subprocess.run(["pacman", "-Qi", package], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
    if manager == "apt":
        result = subprocess.run(["dpkg-query", "-W", "-f=${Status}", package], capture_output=True, text=True)
        return result.returncode == 0 and "ok installed" in result.stdout
    if manager == "dnf":
        return subprocess.run(["rpm", "-q", package], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
    return False


def profile_tokens(repository: Path, profile: str) -> list[str]:
    manifests = {
        "minimal": ["core.txt"],
        "standard": ["core.txt", "desktop.txt", "hardware.txt"],
        "full": ["core.txt", "desktop.txt", "hardware.txt", "optional.txt"],
    }
    tokens: list[str] = []
    for name in manifests[profile]:
        tokens.extend(read_manifest(repository / "packages" / name))
    return list(dict.fromkeys(tokens))


def build_package_plan(repository: Path, profile: str, manager: str) -> PackagePlan:
    tokens = profile_tokens(repository, profile)
    packages, unsupported = map_packages(tokens, manager)
    install = [package for package in packages if not package_is_installed(package, manager)]
    installed = [package for package in packages if package_is_installed(package, manager)]
    return PackagePlan(manager, profile, install, installed, unsupported)


def install_packages(plan: PackagePlan, dry_run: bool = False) -> tuple[bool, str]:
    if not plan.install:
        return True, "No packages need installation."
    if dry_run:
        return True, "Dry run: package installation skipped."
    if plan.package_manager == "pacman":
        command = ["sudo", "pacman", "-S", "--needed", "--noconfirm", *plan.install]
    elif plan.package_manager == "apt":
        command = ["sudo", "apt-get", "install", "-y", *plan.install]
    elif plan.package_manager == "dnf":
        command = ["sudo", "dnf", "install", "-y", *plan.install]
    else:
        return False, "Unsupported package manager."
    if shutil.which(command[0]) is None:
        return False, "sudo is unavailable."
    if plan.package_manager == "apt":
        update = subprocess.run(["sudo", "apt-get", "update"], check=False)
        if update.returncode:
            return False, "Could not refresh the apt package index."
    result = subprocess.run(command, check=False)
    return (result.returncode == 0), ("Package installation completed." if result.returncode == 0 else "Package installation failed.")
