from __future__ import annotations

import json
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Iterable


class BackupError(RuntimeError):
    pass


class BackupManager:
    def __init__(self, home: Path, rice_name: str = "hypr-rice") -> None:
        self.home = home
        self.backup_root = home / ".local" / "share" / rice_name / "backups"

    def create(self, label: str = "install") -> tuple[Path, dict]:
        self.backup_root.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        directory = self.backup_root / timestamp
        counter = 1
        while directory.exists():
            directory = self.backup_root / f"{timestamp}-{counter}"
            counter += 1
        directory.mkdir(parents=True)
        manifest = {
            "version": 1,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "label": label,
            "items": [],
        }
        return directory, manifest

    @staticmethod
    def _copy_existing(source: Path, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_symlink():
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.symlink_to(source.readlink())
        elif source.is_dir():
            shutil.copytree(source, destination, symlinks=True)
        elif source.is_file():
            shutil.copy2(source, destination)

    def backup_paths(
        self,
        paths: Iterable[tuple[str, Path]],
        label: str = "install",
    ) -> tuple[Path, dict]:
        directory, manifest = self.create(label)
        data_root = directory / "data"
        for name, source in paths:
            if not source.exists() and not source.is_symlink():
                continue
            safe_name = name.replace("/", "_").replace(" ", "_")
            data_destination = data_root / safe_name
            self._copy_existing(source, data_destination)
            manifest["items"].append({
                "name": name,
                "destination": str(source),
                "backup": str(data_destination),
            })
        (directory / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n",
            encoding="utf-8",
        )
        return directory, manifest

    def list_backups(self) -> list[Path]:
        if not self.backup_root.exists():
            return []
        return sorted(
            (path for path in self.backup_root.iterdir() if path.is_dir()),
            key=lambda path: path.name,
            reverse=True,
        )

    def read_manifest(self, directory: Path) -> dict:
        manifest_path = directory / "manifest.json"
        if not manifest_path.is_file():
            raise BackupError(f"No backup manifest found in {directory}")
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise BackupError(f"Could not read backup manifest: {exc}") from exc
        if (
            not isinstance(data, dict)
            or data.get("version") != 1
            or not isinstance(data.get("items"), list)
        ):
            raise BackupError("Backup manifest is invalid.")
        return data

    def _allowed_roots(self) -> list[Path]:
        return [
            (self.home / ".config" / "hypr").resolve(),
            (self.home / ".local" / "share" / "hypr-rice").resolve(),
            (self.home / ".local" / "state" / "hypr-rice").resolve(),
        ]

    def _is_within(self, path: Path, roots: list[Path]) -> bool:
        try:
            resolved = path.resolve()
        except (OSError, RuntimeError):
            return False
        return any(resolved == root or root in resolved.parents for root in roots)

    def _has_symlink_component(self, path: Path) -> bool:
        current = path
        for candidate in (path, *path.parents):
            if candidate.is_symlink():
                return True
        return False

    def validate_restore_items(self, directory: Path) -> list[dict]:
        try:
            backup_directory = directory.resolve(strict=True)
            backup_root = self.backup_root.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise BackupError(f"Invalid backup directory: {exc}") from exc
        if (
            backup_directory == backup_root
            or not (
                backup_directory == backup_root
                or backup_root in backup_directory.parents
            )
        ):
            raise BackupError("Restore is restricted to the rice backup directory.")
        manifest = self.read_manifest(backup_directory)
        validated: list[dict] = []
        allowed_roots = self._allowed_roots()
        for item in manifest["items"]:
            if not isinstance(item, dict):
                raise BackupError("Backup manifest contains an invalid item.")
            name = str(item.get("name", "")).strip()
            destination = Path(str(item.get("destination", ""))).expanduser()
            backup = Path(str(item.get("backup", ""))).expanduser()
            if not name or "/" in name or "\\" in name or name in (".", ".."):
                raise BackupError("Backup manifest contains an unsafe component name.")
            if not destination.is_absolute():
                raise BackupError("Backup manifest destination must be absolute.")
            if not self._is_within(destination, allowed_roots):
                raise BackupError(f"Refusing restore outside allowed rice directories: {destination}")
            if self._has_symlink_component(destination):
                raise BackupError(f"Refusing restore through a symlink: {destination}")
            safe_name = name.replace("/", "_").replace(" ", "_")
            expected_backup = (backup_directory / "data" / safe_name).resolve()
            try:
                backup_resolved = backup.resolve(strict=True)
            except (OSError, RuntimeError) as exc:
                raise BackupError(f"Backup item is missing or inaccessible: {backup}") from exc
            if backup_resolved != expected_backup:
                raise BackupError("Backup manifest item does not match its backed-up data path.")
            if not (backup_resolved.is_file() or backup_resolved.is_dir() or backup_resolved.is_symlink()):
                raise BackupError(f"Invalid backup item: {backup_resolved}")
            if self._has_symlink_component(backup_resolved):
                raise BackupError(f"Refusing restore from symlinked backup data: {backup_resolved}")
            validated.append({
                "name": name,
                "destination": destination,
                "backup": backup_resolved,
            })
        return validated

    def preview_restore(self, directory: Path | None = None) -> list[dict]:
        if directory is None:
            backups = self.list_backups()
            if not backups:
                raise BackupError("No backups are available.")
            directory = backups[0]
        return self.validate_restore_items(directory)

    def restore(self, directory: Path | None = None) -> tuple[bool, str]:
        if directory is None:
            backups = self.list_backups()
            if not backups:
                return False, "No backups are available."
            directory = backups[0]
        if not directory.is_dir():
            return False, f"Backup directory not found: {directory}"
        try:
            items = self.validate_restore_items(directory)
        except BackupError as exc:
            return False, str(exc)
        restored = 0
        for item in items:
            destination = item["destination"]
            backup = item["backup"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.is_symlink() or destination.is_file():
                destination.unlink(missing_ok=True)
            elif destination.is_dir():
                shutil.rmtree(destination)
            self._copy_existing(backup, destination)
            restored += 1
        return True, f"Restored {restored} component(s) from {directory}"

    def backup_only(self, paths: Iterable[tuple[str, Path]]) -> tuple[Path, dict]:
        return self.backup_paths(paths, "backup-only")
