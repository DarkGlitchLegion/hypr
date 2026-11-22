from __future__ import annotations

import shutil
from pathlib import Path
from typing import Iterable

try:
    from .backup import BackupManager
except ImportError:
    from backup import BackupManager


class ConfigDeployer:
    def __init__(
        self,
        repository: Path,
        home: Path,
        backup_manager: BackupManager,
        symlinks: bool = False,
    ) -> None:
        self.repository = repository
        self.home = home
        self.target_root = home / ".config" / "hypr"
        self.backup = backup_manager
        self.symlinks = symlinks

    def components(self, profile: str) -> list[tuple[str, Path, Path]]:
        components: list[tuple[str, Path, Path]] = [
            ("hyprland.conf", self.repository / "hyprland.conf", self.target_root / "hyprland.conf"),
            ("hyprland.lua", self.repository / "hyprland.lua", self.target_root / "hyprland.lua"),
            ("lua", self.repository / "lua", self.target_root / "lua"),
            ("waybar", self.repository / "waybar", self.target_root / "waybar"),
            ("rofi", self.repository / "rofi", self.target_root / "rofi"),
            ("kitty", self.repository / "kitty", self.target_root / "kitty"),
            ("dunst", self.repository / "dunst", self.target_root / "dunst"),
            ("hyprlock", self.repository / "hyprlock", self.target_root / "hyprlock"),
            ("hyprpaper", self.repository / "hyprpaper", self.target_root / "hyprpaper"),
            ("hyprclock", self.repository / "hyprclock", self.target_root / "hyprclock"),
            ("scripts", self.repository / "scripts", self.target_root / "scripts"),
            ("wallpapers", self.repository / "wallpapers", self.target_root / "wallpapers"),
            ("state", self.repository / "state", self.target_root / "state"),
        ]
        if profile in ("standard", "full"):
            components.extend([
                ("hyprland", self.repository / "hyprland", self.target_root / "hyprland"),
                ("docs", self.repository / "docs", self.target_root / "docs"),
                ("requirements", self.repository / "requirements.txt", self.target_root / "requirements.txt"),
            ])
        if profile == "full":
            components.extend([
                ("packages", self.repository / "packages", self.target_root / "packages"),
            ])
        return [(name, source, destination) for name, source, destination in components if source.exists()]

    def _personalize(self, path: Path) -> None:
        if not path.is_file():
            return
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            return
        replacements = {
            str(self.repository): str(self.target_root),
        }
        for old, new in replacements.items():
            content = content.replace(old, new)
        if content.endswith("\n") or path.suffix in (".conf", ".lua", ".txt", ".json", ".sh", ".py"):
            path.write_text(content, encoding="utf-8")

    def _copy_leaf(self, source: Path, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() or destination.is_symlink():
            if destination.is_dir() and not destination.is_symlink():
                shutil.rmtree(destination)
            else:
                destination.unlink()
        shutil.copy2(source, destination)
        self._personalize(destination)

    def _copy_tree(self, source: Path, destination: Path) -> None:
        destination.mkdir(parents=True, exist_ok=True)
        for source_path in source.rglob("*"):
            relative = source_path.relative_to(source)
            target = destination / relative
            if source_path.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            elif source_path.is_symlink():
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists() or target.is_symlink():
                    if target.is_dir() and not target.is_symlink():
                        shutil.rmtree(target)
                    else:
                        target.unlink()
                target.symlink_to(source_path.readlink())
            elif source_path.is_file():
                if relative.parts and relative.parts[0] == "__pycache__":
                    continue
                if destination.name == "state" and target.exists():
                    continue
                self._copy_leaf(source_path, target)

    def deploy(self, profile: str, dry_run: bool = False) -> tuple[bool, list[str], Path | None]:
        components = self.components(profile)
        if dry_run:
            return True, [f"{name}: {source} -> {destination}" for name, source, destination in components], None
        backup_items: list[tuple[str, Path]] = []
        for name, source, destination in components:
            if destination.exists() or destination.is_symlink():
                backup_items.append((name, destination))
        backup_directory = None
        manifest = None
        if backup_items:
            backup_directory, manifest = self.backup.backup_paths(backup_items, "pre-install")
        self.target_root.mkdir(parents=True, exist_ok=True)
        deployed: list[str] = []
        for name, source, destination in components:
            if source.resolve() == destination.resolve():
                deployed.append(name)
                continue
            if self.symlinks:
                destination.parent.mkdir(parents=True, exist_ok=True)
                if destination.exists() or destination.is_symlink():
                    if destination.is_dir() and not destination.is_symlink():
                        shutil.rmtree(destination)
                    else:
                        destination.unlink()
                destination.symlink_to(source)
            elif source.is_dir():
                self._copy_tree(source, destination)
            else:
                self._copy_leaf(source, destination)
            deployed.append(name)
        compatibility = [
            ("animations.conf", "hyprland/legacy/animations.conf"),
            ("hypridle.conf", "hyprland/legacy/hypridle.conf"),
            ("keybinds.conf", "hyprland/legacy/keybinds.conf"),
            ("windowrules.conf", "hyprland/legacy/windowrules.conf"),
            ("hyprclock.conf", "hyprclock/hyprclock.conf"),
            ("hyprpaper.conf", "hyprpaper/hyprpaper.conf"),
        ]
        for link_name, relative_source in compatibility:
            link = self.target_root / link_name
            source = self.target_root / relative_source
            if not source.exists():
                continue
            if link.exists() or link.is_symlink():
                if link.is_symlink():
                    link.unlink()
                elif link.is_file():
                    link.unlink()
            link.symlink_to(source)
        return True, deployed, backup_directory
