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
        if not isinstance(data, dict) or not isinstance(data.get("items"), list):
            raise BackupError("Backup manifest is invalid.")
        return data

    def restore(self, directory: Path | None = None) -> tuple[bool, str]:
        if directory is None:
            backups = self.list_backups()
            if not backups:
                return False, "No backups are available."
            directory = backups[0]
        if not directory.is_dir():
            return False, f"Backup directory not found: {directory}"
        manifest = self.read_manifest(directory)
        restored = 0
        for item in manifest["items"]:
            if not isinstance(item, dict):
                continue
            destination = Path(str(item.get("destination", "")))
            backup = Path(str(item.get("backup", "")))
            if str(destination) in ("", ".") or (not backup.exists() and not backup.is_symlink()):
                continue
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
