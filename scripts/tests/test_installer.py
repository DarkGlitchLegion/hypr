from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SETUP = ROOT / "scripts" / "setup"
if str(SETUP) not in sys.path:
    sys.path.insert(0, str(SETUP))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


backup_module = load_module("installer_backup", SETUP / "backup.py")
package_module = load_module("installer_packages", SETUP / "package_manager.py")
deploy_module = load_module("installer_deploy", SETUP / "config_deployer.py")
validation_module = load_module("installer_validation", SETUP / "validation.py")


class PackageManagerTests(unittest.TestCase):
    def test_profile_lists_are_categorized(self) -> None:
        minimal = package_module.profile_tokens(ROOT, "minimal")
        standard = package_module.profile_tokens(ROOT, "standard")
        full = package_module.profile_tokens(ROOT, "full")
        self.assertIn("hyprland", minimal)
        self.assertGreater(len(standard), len(minimal))
        self.assertGreater(len(full), len(standard))

    def test_manifest_ignores_comments(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "packages.txt"
            path.write_text("# comment\nhyprland\n\nwaybar\n")
            self.assertEqual(package_module.read_manifest(path), ["hyprland", "waybar"])

    def test_pacman_mapping_is_not_empty(self) -> None:
        packages, unsupported = package_module.map_packages(["hyprland", "waybar", "unknown-token"], "pacman")
        self.assertIn("hyprland", packages)
        self.assertIn("waybar", packages)
        self.assertIn("unknown-token", unsupported)

    def test_quickshell_is_mapped_only_where_a_package_is_supported(self) -> None:
        packages, unsupported = package_module.map_packages(["quickshell"], "pacman")
        self.assertEqual(packages, ["quickshell"])
        self.assertEqual(unsupported, [])

        for manager in ("apt", "dnf"):
            packages, unsupported = package_module.map_packages(["quickshell"], manager)
            self.assertEqual(packages, [])
            self.assertEqual(unsupported, ["quickshell"])


class BackupTests(unittest.TestCase):
    def test_timestamped_backup_and_restore(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            source = home / ".config" / "hypr"
            source.mkdir(parents=True)
            (source / "setting.conf").write_text("original\n", encoding="utf-8")
            manager = backup_module.BackupManager(home)
            backup_directory, manifest = manager.backup_paths([("hypr", source)], "test")
            self.assertTrue((backup_directory / "manifest.json").is_file())
            (source / "setting.conf").write_text("changed\n", encoding="utf-8")
            ok, message = manager.restore(backup_directory)
            self.assertTrue(ok, message)
            self.assertEqual((source / "setting.conf").read_text(encoding="utf-8"), "original\n")

    def test_backups_never_overwrite_an_existing_timestamp_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            manager = backup_module.BackupManager(home)
            first, _ = manager.create("first")
            second, _ = manager.create("second")
            self.assertNotEqual(first, second)

    def test_restore_rejects_destination_outside_rice_roots(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            source = home / ".config" / "hypr"
            source.mkdir(parents=True)
            (source / "setting.conf").write_text("safe\n", encoding="utf-8")
            manager = backup_module.BackupManager(home)
            backup_directory, manifest = manager.backup_paths([("hypr", source)], "test")
            manifest_path = backup_directory / "manifest.json"
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            data["items"][0]["destination"] = str(home / "outside" / "target")
            manifest_path.write_text(json.dumps(data), encoding="utf-8")
            ok, message = manager.restore(backup_directory)
            self.assertFalse(ok)
            self.assertIn("outside allowed rice directories", message)

    def test_restore_rejects_symlinked_destination_parent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            source = home / ".config" / "hypr"
            source.mkdir(parents=True)
            (source / "setting.conf").write_text("safe\n", encoding="utf-8")
            manager = backup_module.BackupManager(home)
            backup_directory, _ = manager.backup_paths([("hypr", source)], "test")
            symlink_parent = home / ".config" / "symlinked"
            symlink_parent.symlink_to(home / "outside", target_is_directory=True)
            manifest_path = backup_directory / "manifest.json"
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            data["items"][0]["destination"] = str(symlink_parent / "target")
            manifest_path.write_text(json.dumps(data), encoding="utf-8")
            ok, message = manager.restore(backup_directory)
            self.assertFalse(ok)
            self.assertIn("outside allowed rice directories", message)


class ConfigDeployerTests(unittest.TestCase):
    def test_quickshell_configuration_is_deployed_without_replacing_waybar(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = root / "repo"
            home = root / "home"
            (repository / "quickshell").mkdir(parents=True)
            (repository / "quickshell" / "shell.qml").write_text("ShellRoot { property bool fresh: true }\n", encoding="utf-8")
            (repository / "waybar").mkdir()
            (repository / "waybar" / "config.jsonc").write_text("{}\n", encoding="utf-8")
            existing_quickshell = home / ".config" / "hypr" / "quickshell"
            existing_quickshell.mkdir(parents=True)
            (existing_quickshell / "shell.qml").write_text("ShellRoot { property bool old: true }\n", encoding="utf-8")
            (existing_quickshell / "user-local.qml").write_text("QtObject {}\n", encoding="utf-8")
            backup = backup_module.BackupManager(home)
            deployer = deploy_module.ConfigDeployer(repository, home, backup)

            components = {name: destination for name, _, destination in deployer.components("standard")}
            self.assertEqual(components["quickshell"], home / ".config" / "hypr" / "quickshell")
            self.assertEqual(components["waybar"], home / ".config" / "hypr" / "waybar")
            ok, _, backup_directory = deployer.deploy("standard")
            self.assertTrue(ok)
            self.assertEqual(
                (existing_quickshell / "shell.qml").read_text(encoding="utf-8"),
                "ShellRoot { property bool fresh: true }\n",
            )
            self.assertTrue((existing_quickshell / "user-local.qml").is_file())
            self.assertIsNotNone(backup_directory)
            self.assertEqual(
                (backup_directory / "data" / "quickshell" / "shell.qml").read_text(encoding="utf-8"),
                "ShellRoot { property bool old: true }\n",
            )

    def test_quickshell_is_in_the_minimal_package_profile(self) -> None:
        self.assertIn("quickshell", package_module.profile_tokens(ROOT, "minimal"))

    def test_copy_deployment_personalizes_absolute_paths_and_preserves_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            repository = Path(directory) / "repo"
            home.mkdir()
            (repository / "lua").mkdir(parents=True)
            (repository / "wallpapers").mkdir(parents=True)
            (repository / "state").mkdir(parents=True)
            (repository / "lua" / "test.lua").write_text(
                f'path = "{repository}/wallpapers/test.png"\n',
                encoding="utf-8",
            )
            (repository / "state" / "default.json").write_text('{"value": "default"}\n', encoding="utf-8")
            target = home / ".config" / "hypr"
            (target / "state").mkdir(parents=True)
            (target / "state" / "default.json").write_text('{"value": "user"}\n', encoding="utf-8")
            manager = backup_module.BackupManager(home)
            deployer = deploy_module.ConfigDeployer(repository, home, manager)
            ok, deployed, _ = deployer.deploy("minimal")
            self.assertTrue(ok)
            deployed_lua = (target / "lua" / "test.lua").read_text(encoding="utf-8")
            self.assertNotIn(str(repository), deployed_lua)
            self.assertIn(str(target), deployed_lua)
            self.assertEqual(
                (target / "state" / "default.json").read_text(encoding="utf-8"),
                '{"value": "user"}\n',
            )


class ValidationTests(unittest.TestCase):
    def test_validation_flags_missing_and_present_components(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            (target / "scripts").mkdir()
            (target / "scripts" / "ok.sh").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            (target / "scripts" / "ok.py").write_text("print('ok')\n", encoding="utf-8")
            result = validation_module.validate(target)
            self.assertTrue(any("Python syntax" in item for item in result.passed))
            self.assertTrue(any("Shell syntax" in item for item in result.passed))

    def test_validation_checks_quickshell_qml_syntax_when_qmllint_exists(self) -> None:
        if shutil.which("qmllint") is None and not Path("/usr/lib/qt6/bin/qmllint").is_file():
            self.skipTest("qmllint is not installed")
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            quickshell = target / "quickshell"
            quickshell.mkdir()
            (quickshell / "shell.qml").write_text("import QtQuick\nItem {}\n", encoding="utf-8")
            result = validation_module.validate(target)
            self.assertIn("QML syntax: 1 file(s)", result.passed)


if __name__ == "__main__":
    unittest.main()
