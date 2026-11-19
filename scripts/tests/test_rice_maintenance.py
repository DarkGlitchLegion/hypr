from __future__ import annotations

import importlib.util
import tempfile
import unittest
import unittest.mock
from types import SimpleNamespace
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("rice_maintenance", ROOT / "scripts" / "rice_maintenance.py")
assert SPEC is not None and SPEC.loader is not None
maintenance = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = maintenance
SPEC.loader.exec_module(maintenance)


class JsoncTests(unittest.TestCase):
    def test_removes_comments_without_changing_string_values(self) -> None:
        parsed = maintenance.json.loads(
            maintenance.jsonc_to_json('{"url":"https://example.test/a/*b*/", // comment\n "count":2}')
        )
        self.assertEqual(parsed, {"url": "https://example.test/a/*b*/", "count": 2})

    def test_reports_unterminated_comment(self) -> None:
        with self.assertRaises(ValueError):
            maintenance.jsonc_to_json('{"value": 1 /* unfinished')


class GeometryTests(unittest.TestCase):
    def test_touching_monitor_edges_do_not_overlap(self) -> None:
        self.assertFalse(maintenance.rectangles_overlap((0, 0, 1920, 1080), (1920, 0, 3840, 1080)))

    def test_monitor_scale_and_rotation_are_accounted_for(self) -> None:
        monitor = {"x": 0, "y": 0, "width": 1080, "height": 1920, "scale": 1, "transform": 1}
        self.assertEqual(maintenance.monitor_rectangle(monitor), (0, 0, 1920, 1080))

    def test_overlap_reports_monitor_pair(self) -> None:
        monitors = [
            {"name": "eDP-1", "x": 0, "y": 0, "width": 1920, "height": 1080, "scale": 1},
            {"name": "HDMI-A-1", "x": 20, "y": 0, "width": 1920, "height": 1080, "scale": 1},
        ]
        self.assertEqual(maintenance.monitor_overlaps(monitors), ["eDP-1 / HDMI-A-1"])


class ConfigReferenceTests(unittest.TestCase):
    def test_autostart_script_arguments_are_not_treated_as_part_of_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / ".config" / "hypr"
            config.mkdir(parents=True)
            (config / "lua").mkdir()
            (config / "scripts").mkdir()
            (config / "waybar").mkdir(parents=True)
            (config / "scripts" / "display-manager.py").write_text("", encoding="utf-8")
            (config / "lua" / "autostart.lua").write_text(
                'local script = scripts .. "/display-manager.py --watch"\n',
                encoding="utf-8",
            )
            (config / "waybar" / "config.jsonc").write_text("{}", encoding="utf-8")
            with unittest.mock.patch.object(maintenance, "CONFIG", config):
                self.assertEqual(maintenance.missing_config_references(), [])

    def test_waybar_missing_script_reference_is_reported(self) -> None:
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / ".config" / "hypr"
            (config / "waybar").mkdir(parents=True)
            reference = config / "scripts" / "missing.sh"
            (config / "waybar" / "config.jsonc").write_text(
                maintenance.json.dumps({"custom/test": {"exec": str(reference)}}),
                encoding="utf-8",
            )
            with patch.object(maintenance, "CONFIG", config):
                self.assertTrue(any("Waybar references missing" in item
                                    for item in maintenance.missing_config_references()))

    def test_validation_file_scan_skips_backups_and_cache(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory)
            (config / ".backup").mkdir()
            (config / "__pycache__").mkdir()
            (config / "lua").mkdir()
            (config / ".backup" / "old.lua").write_text("", encoding="utf-8")
            (config / "__pycache__" / "cached.lua").write_text("", encoding="utf-8")
            (config / "lua" / "active.lua").write_text("", encoding="utf-8")
            with unittest.mock.patch.object(maintenance, "CONFIG", config):
                self.assertEqual([path.name for path in maintenance.config_files(".lua")], ["active.lua"])


class ReloadTests(unittest.TestCase):
    def test_reload_is_blocked_when_validation_fails(self) -> None:
        failed = maintenance.Check("core", "Hyprland config", "Failed", "bad config")
        with unittest.mock.patch.object(maintenance, "validate_configs", return_value=[failed]), \
             unittest.mock.patch.object(maintenance, "run") as run:
            self.assertEqual(maintenance.reload_command(), 2)
        run.assert_not_called()

    def test_reload_verifies_hyprland_reported_errors(self) -> None:
        healthy = maintenance.Check("core", "Hyprland config", "Healthy", "valid")
        result = maintenance.subprocess.CompletedProcess
        with unittest.mock.patch.object(maintenance, "validate_configs", return_value=[healthy]), \
             unittest.mock.patch.object(maintenance.shutil, "which", return_value="/usr/bin/hyprctl"), \
             unittest.mock.patch.object(maintenance, "run", side_effect=[
                 result(["hyprctl", "reload"], 0, "", ""),
                 result(["hyprctl", "configerrors"], 0, "[]", ""),
             ]) as run, \
             unittest.mock.patch.object(maintenance.time, "sleep"), \
             unittest.mock.patch.object(maintenance, "log_event"):
            self.assertEqual(maintenance.reload_command(), 0)
        self.assertEqual(run.call_count, 2)


class SnapshotTests(unittest.TestCase):
    def test_snapshot_file_filter_excludes_backups_secrets_and_cache(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "scripts").mkdir()
            (root / "scripts" / "ok.py").write_text("print('ok')", encoding="utf-8")
            (root / "scripts" / ".env").write_text("secret", encoding="utf-8")
            (root / ".backup").mkdir()
            (root / ".backup" / "old").write_text("old", encoding="utf-8")
            (root / "__pycache__").mkdir()
            (root / "__pycache__" / "temp.pyc").write_bytes(b"cache")
            paths = [path.relative_to(root).as_posix() for path in maintenance.snapshot_files(root)]
            self.assertEqual(paths, ["scripts/ok.py"])

    def test_snapshot_round_trip_and_compare(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot_dir = root / "snapshots"
            snapshot_dir.mkdir()
            config = root / "config"
            config.mkdir()
            (config / "hyprland.lua").write_text("config", encoding="utf-8")
            old_config = maintenance.CONFIG
            old_snapshot_dir = maintenance.SNAPSHOT_DIR
            old_settings = maintenance.SNAPSHOT_SETTINGS
            maintenance.CONFIG = config
            maintenance.SNAPSHOT_DIR = snapshot_dir
            maintenance.SNAPSHOT_SETTINGS = root / "settings.json"
            original_logger = maintenance.log_event
            maintenance.log_event = lambda *args, **kwargs: None
            try:
                archive = maintenance.create_snapshot("unit")
                metadata, files = maintenance.read_snapshot(archive)
                self.assertIn("hyprland.lua", files)
                self.assertEqual(maintenance.compare_to_current(archive, files), [])
                (config / "hyprland.lua").write_text("changed", encoding="utf-8")
                self.assertEqual(maintenance.compare_to_current(archive, files), ["REPLACE hyprland.lua"])
                self.assertEqual(metadata["label"], "unit")
            finally:
                maintenance.CONFIG = old_config
                maintenance.SNAPSHOT_DIR = old_snapshot_dir
                maintenance.SNAPSHOT_SETTINGS = old_settings
                maintenance.log_event = original_logger

    def test_restore_can_recover_an_invalid_current_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "config"
            snapshot_dir = root / "snapshots"
            config.mkdir()
            snapshot_dir.mkdir()
            config_file = config / "hyprland.lua"
            config_file.write_text("valid config", encoding="utf-8")
            old_config = maintenance.CONFIG
            old_snapshot_dir = maintenance.SNAPSHOT_DIR
            old_settings = maintenance.SNAPSHOT_SETTINGS
            original_logger = maintenance.log_event
            maintenance.CONFIG = config
            maintenance.SNAPSHOT_DIR = snapshot_dir
            maintenance.SNAPSHOT_SETTINGS = root / "settings.json"
            maintenance.log_event = lambda *args, **kwargs: None
            try:
                archive = maintenance.create_snapshot("recovery-test")
                config_file.write_text("invalid current config", encoding="utf-8")
                from unittest.mock import patch

                with patch.object(maintenance, "validate_current_config", return_value=[]) as validate:
                    changes = maintenance.restore_snapshot(archive, confirm=True)
                self.assertEqual(config_file.read_text(encoding="utf-8"), "valid config")
                self.assertEqual(changes, ["REPLACE hyprland.lua"])
                validate.assert_called_once()
                self.assertGreaterEqual(len(maintenance.snapshot_list()), 2)
            finally:
                maintenance.CONFIG = old_config
                maintenance.SNAPSHOT_DIR = old_snapshot_dir
                maintenance.SNAPSHOT_SETTINGS = old_settings
                maintenance.log_event = original_logger

    def test_empty_component_selection_has_no_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config"
            config.mkdir()
            archive = config / "dummy.tar.gz"
            contents = {"hyprland.lua": b"saved"}
            self.assertEqual(maintenance.compare_to_current(archive, contents, set()), [])


class EventLogTests(unittest.TestCase):
    def test_events_are_json_and_secret_fields_are_omitted(self) -> None:
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as directory:
            logger = maintenance.event_logger()
            with patch.object(logger, "LOG_DIR", Path(directory)), patch.object(
                logger, "LOG_FILE", Path(directory) / "events.jsonl"
            ), patch.object(logger, "LOCK_FILE", Path(directory) / ".events.lock"):
                logger.log_event(
                    "tests",
                    "sample",
                    details={"mode": "unit", "password": "do-not-log"},
                )
                events = logger.read_events()
            self.assertEqual(len(events), 1)
            self.assertNotIn("password", events[0].get("details", {}))
            self.assertEqual(events[0]["component"], "tests")

    def test_event_descriptions_redact_inline_secrets(self) -> None:
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as directory:
            logger = maintenance.event_logger()
            with patch.object(logger, "LOG_DIR", Path(directory)), patch.object(
                logger, "LOG_FILE", Path(directory) / "events.jsonl"
            ), patch.object(logger, "LOCK_FILE", Path(directory) / ".events.lock"):
                logger.log_event("tests", "password=hunter2 token: private-value")
                event = logger.read_events()[0]
            self.assertNotIn("hunter2", event["description"])
            self.assertNotIn("private-value", event["description"])

    def test_corrupt_log_records_are_reported(self) -> None:
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as directory:
            logger = maintenance.event_logger()
            log_file = Path(directory) / "events.jsonl"
            log_file.write_text("not json\n", encoding="utf-8")
            with patch.object(logger, "LOG_DIR", Path(directory)), patch.object(
                logger, "LOG_FILE", log_file
            ), patch.object(logger, "ROTATIONS", 0):
                with self.assertRaisesRegex(OSError, "Invalid activity log record"):
                    logger.read_events()

    def test_log_filters_and_export_keep_only_matching_events(self) -> None:
        events = [
            {"timestamp": "2026-01-01T10:00:00+00:00", "component": "audio",
             "severity": "info", "description": "sink changed"},
            {"timestamp": "2026-01-02T10:00:00+00:00", "component": "display",
             "severity": "warning", "description": "layout changed"},
        ]
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "filtered.jsonl"
            args = SimpleNamespace(
                limit=100, since="2026-01-02", module=None, severity=None,
                search=None, export=str(destination), clear=False, ui=False,
            )
            with unittest.mock.patch.object(maintenance, "filtered_events", return_value=events[1:]):
                self.assertEqual(maintenance.logs_command(args), 0)
            exported = [maintenance.json.loads(line) for line in destination.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(exported, events[1:])

    def test_log_clear_requires_confirmation(self) -> None:
        cleared = []
        logger = SimpleNamespace(clear_events=lambda: cleared.append(True))
        args = SimpleNamespace(clear=True, limit=100, since=None, module=None, severity=None,
                               search=None, export=None, ui=False)
        with unittest.mock.patch.object(maintenance, "confirm", return_value=False), \
             unittest.mock.patch.object(maintenance, "event_logger", return_value=logger):
            self.assertEqual(maintenance.logs_command(args), 1)
        self.assertEqual(cleared, [])


if __name__ == "__main__":
    unittest.main()
