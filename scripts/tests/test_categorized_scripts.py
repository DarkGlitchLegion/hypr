from __future__ import annotations

import ast
import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
CATEGORIES = ("core", "desktop", "hardware", "session", "clipboard", "wallpaper", "security")


class CategorizedScriptTests(unittest.TestCase):
    def test_every_script_is_in_a_category(self) -> None:
        root_scripts = [
            path for path in SCRIPTS.iterdir()
            if path.is_file() and path.suffix in (".py", ".sh")
        ]
        self.assertEqual(root_scripts, [], "Only the public rice CLI may remain as a top-level script")

    def test_category_directories_exist(self) -> None:
        for category in CATEGORIES:
            self.assertTrue((SCRIPTS / category).is_dir(), category)

    def test_shell_scripts_pass_bash_syntax_check(self) -> None:
        for path in SCRIPTS.rglob("*.sh"):
            with self.subTest(path=path.relative_to(ROOT)):
                result = subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_python_scripts_pass_ast_syntax_check(self) -> None:
        for path in SCRIPTS.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            with self.subTest(path=path.relative_to(ROOT)):
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    def test_categorized_paths_used_by_active_keybindings_exist(self) -> None:
        keybinds = (ROOT / "lua" / "keybinds.lua").read_text(encoding="utf-8")
        expected = (
            "/hardware/display-manager.py",
            "/hardware/wifi-menu.sh",
            "/hardware/bluetooth-menu.sh",
            "/security/hyprsec-box.sh",
            "/session/power-menu.sh",
            "/desktop/restart-waybar.sh",
            "/hardware/audio-menu.sh",
            "/session/notification-toggle.sh",
            "/session/notification-history.sh",
            "/desktop/keybindings-menu.sh",
            "/desktop/keybindings-window.sh",
            "/wallpaper/wallpaper-selector.sh",
            "/clipboard/clipboard-menu.sh",
            "/clipboard/clipboard-clear.sh",
            "/session/screenshot.sh",
            "/hardware/volume.sh",
            "/hardware/brightness.sh",
        )
        for suffix in expected:
            with self.subTest(suffix=suffix):
                self.assertIn(suffix, keybinds)
                self.assertTrue((SCRIPTS / suffix.lstrip("/")).exists(), suffix)

    def test_quick_settings_status_is_valid_json(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "desktop" / "quick-settings-status.py")],
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        import json
        data = json.loads(result.stdout)
        self.assertIn("text", data)
        self.assertIn("tooltip", data)
        self.assertIn("class", data)

    def test_idle_manager_status_and_validation(self) -> None:
        script = SCRIPTS / "session" / "idle-manager.py"
        status = subprocess.run(
            [sys.executable, str(script), "--status"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(status.returncode, 0, status.stderr)
        validation = subprocess.run(
            [sys.executable, str(script), "--validate"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(validation.returncode, 0, validation.stderr)

    def test_moved_scripts_have_no_old_sibling_paths(self) -> None:
        stale = (
            "${HOME}/.config/hypr/scripts/audio-manager.py",
            "${HOME}/.config/hypr/scripts/rice_maintenance.py",
            "${HOME}/.config/hypr/scripts/idle-manager.py",
            "${HOME}/.config/hypr/scripts/clipboard-menu.sh",
            "${HOME}/.config/hypr/scripts/clipboard-daemon.sh",
            "${HOME}/.config/hypr/scripts/bluetooth-agent.py",
            "${HOME}/.config/hypr/scripts/set-wallpaper.sh",
            "${HOME}/.config/hypr/scripts/restore-wallpaper.sh",
        )
        for path in SCRIPTS.rglob("*"):
            if not path.is_file() or path.suffix not in (".py", ".sh"):
                continue
            if "tests" in path.parts:
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for old in stale:
                with self.subTest(path=path.relative_to(ROOT), old=old):
                    self.assertNotIn(old, content)


if __name__ == "__main__":
    unittest.main()
