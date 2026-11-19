from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("idle_manager", ROOT / "scripts" / "idle-manager.py")
assert SPEC is not None and SPEC.loader is not None
idle = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = idle
SPEC.loader.exec_module(idle)


class PresetTests(unittest.TestCase):
    def test_balanced_preset_uses_requested_defaults_and_no_suspend(self) -> None:
        settings = idle.default_settings()
        self.assertEqual(settings["preset"], "Balanced")
        self.assertEqual(settings["actions"]["dim"]["seconds"], 120)
        self.assertEqual(settings["actions"]["blank"]["seconds"], 300)
        self.assertEqual(settings["actions"]["lock"]["seconds"], 600)
        self.assertEqual(settings["actions"]["display_off"]["seconds"], 900)
        self.assertFalse(settings["actions"]["suspend"]["enabled"])

    def test_power_saving_dpms_is_delayed_until_after_lock(self) -> None:
        settings = idle.preset_settings("Power Saving")
        self.assertEqual(idle.effective_dpms_timeout(settings), 305)
        self.assertEqual(idle.effective_suspend_timeout(settings), 900)
        preview = idle.preview(settings).splitlines()
        self.assertLess(
            preview.index("5m — Lock screen"),
            preview.index("5m 5s — Blank / power off displays (Hyprland DPMS)"),
        )

    def test_fixed_timeout_preset_locks_before_power_off_and_disables_suspend(self) -> None:
        settings = idle.preset_settings("5 Minutes")
        self.assertEqual(settings["actions"]["lock"]["seconds"], 300)
        self.assertEqual(idle.effective_dpms_timeout(settings), 360)
        self.assertFalse(settings["actions"]["suspend"]["enabled"])

    def test_never_has_no_automatic_action_listeners(self) -> None:
        settings = idle.preset_settings("Never")
        with patch.object(idle, "validate_dependencies"):
            config = idle.render_hypridle_config(settings)
        self.assertNotIn("listener {", config)
        self.assertIn("ignore_systemd_inhibit = false", config)

    def test_balanced_config_keeps_lock_before_effective_dpms(self) -> None:
        settings = idle.default_settings()
        with patch.object(idle, "validate_dependencies"):
            config = idle.render_hypridle_config(settings)
        self.assertIn("timeout = 605", config)
        self.assertLess(config.index("on-timeout = loginctl lock-session"), config.index("--dpms-off"))
        self.assertNotIn("systemctl suspend", config)

    def test_action_duration_rejects_non_integer_or_out_of_range_values(self) -> None:
        for value in (True, 14, 86401, "300"):
            settings = idle.default_settings()
            settings["actions"]["lock"]["seconds"] = value
            with self.subTest(value=value), self.assertRaises(idle.IdleError):
                idle.validate_settings(settings)

    def test_missing_action_fails_validation(self) -> None:
        settings = idle.default_settings()
        del settings["actions"]["blank"]
        with self.assertRaisesRegex(idle.IdleError, "Blank screen"):
            idle.validate_settings(settings)


class PersistenceTests(unittest.TestCase):
    def test_malformed_settings_are_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "idle-settings.json"
            path.write_text("{bad json", encoding="utf-8")
            with patch.object(idle, "SETTINGS_FILE", path):
                with self.assertRaises(idle.IdleError):
                    idle.load_settings()
            self.assertEqual(path.read_text(encoding="utf-8"), "{bad json")

    def test_committing_settings_persists_atomically_and_reloads_idle_manager(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "idle-settings.json"
            settings = idle.preset_settings("Never")
            with patch.object(idle, "SETTINGS_FILE", path), \
                 patch.object(idle, "snapshot_before_change"), \
                 patch.object(idle, "request_supervisor_reload"), \
                 patch.object(idle, "notify"), \
                 patch.object(idle, "log_event"):
                idle.commit_settings(settings)
            self.assertEqual(idle.validate_settings(idle.json.loads(path.read_text(encoding="utf-8"))), settings)
            self.assertEqual(list(Path(directory).glob(".idle-settings.json-*")), [])

    def test_reload_failure_rolls_persisted_settings_back(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "idle-settings.json"
            original = idle.preset_settings("Balanced")
            path.write_text(idle.json.dumps(original), encoding="utf-8")
            with patch.object(idle, "SETTINGS_FILE", path), \
                 patch.object(idle, "snapshot_before_change"), \
                 patch.object(idle, "request_supervisor_reload", side_effect=[
                     idle.IdleError("simulated failure"), None
                 ]), \
                 patch.object(idle, "notify"), \
                 patch.object(idle, "log_event"):
                with self.assertRaises(idle.IdleError):
                    idle.commit_settings(idle.preset_settings("Never"))
            self.assertEqual(idle.validate_settings(idle.json.loads(path.read_text(encoding="utf-8"))), original)


class DpmsSafetyTests(unittest.TestCase):
    def test_display_poweroff_is_blocked_until_lock_is_confirmed(self) -> None:
        settings = idle.default_settings()
        with patch.object(idle, "load_settings", return_value=settings), \
             patch.object(idle, "session_is_locked", return_value=False), \
             patch.object(idle.time, "monotonic", side_effect=[0, 20]), \
             patch.object(idle.time, "sleep"), \
             patch.object(idle.shutil, "which", return_value="/usr/bin/hyprctl"), \
             patch.object(idle.subprocess, "run") as run, \
             patch.object(idle, "log_event"), \
             patch.object(idle, "notify"):
            self.assertEqual(idle.dpms_off(), 1)
        run.assert_not_called()


class InhibitorTests(unittest.TestCase):
    def test_detects_absolute_systemd_inhibit_executable_path(self) -> None:
        with patch.object(idle, "load_inhibitor_state", return_value={"pid": 4242}), \
             patch.object(idle.Path, "glob", return_value=[Path("/proc/4242/cmdline")]), \
             patch.object(idle, "process_uid", return_value=1000), \
             patch.object(idle, "process_cmdline", return_value=[
                 b"/usr/bin/systemd-inhibit",
                 b"--who=hypr-rice-idle-manager",
             ]):
            self.assertEqual(idle.owned_inhibitor_pids(), [4242])

    def test_owned_inhibitor_search_includes_orphaned_manager_instances(self) -> None:
        with patch.object(idle, "load_inhibitor_state", return_value={"pid": 4242}), \
             patch.object(idle.Path, "glob", return_value=[
                 Path("/proc/4242/cmdline"), Path("/proc/4243/cmdline")
             ]), \
             patch.object(idle, "process_uid", return_value=1000), \
             patch.object(idle, "process_cmdline", side_effect={
                 4242: [b"/usr/bin/systemd-inhibit", b"--who=hypr-rice-idle-manager"],
                 4243: [b"/usr/bin/systemd-inhibit", b"--who=hypr-rice-idle-manager"],
             }.get):
            self.assertEqual(idle.owned_inhibitor_pids(), [4242, 4243])


if __name__ == "__main__":
    unittest.main()
