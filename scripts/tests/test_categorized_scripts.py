from __future__ import annotations

import ast
import contextlib
import io
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
CATEGORIES = ("core", "desktop", "hardware", "session", "clipboard", "wallpaper")


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

    def test_office_thumbnail_renderer_is_configured(self) -> None:
        renderer = SCRIPTS / "desktop" / "office-thumbnailer.sh"
        plugin = Path.home() / ".local" / "share" / "thumbnailers" / "libreoffice.thumbnailer"
        self.assertTrue(renderer.is_file())
        self.assertIn("soffice", renderer.read_text(encoding="utf-8"))
        self.assertIn("pdftoppm", renderer.read_text(encoding="utf-8"))
        self.assertTrue(plugin.is_file())
        self.assertIn("spreadsheetml.sheet", plugin.read_text(encoding="utf-8"))

    def test_categorized_paths_used_by_active_keybindings_exist(self) -> None:
        keybinds = (ROOT / "lua" / "keybinds.lua").read_text(encoding="utf-8")
        expected = (
            "/hardware/display-manager.py",
            "/hardware/wifi-menu.sh",
            "/hardware/bluetooth-menu.sh",
            "/session/power-menu.sh",
            "/desktop/restart-bar.sh",
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

    def test_wifi_menu_selects_adapter_and_binds_connection_commands(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            nmcli_log = root / "nmcli.log"
            nmcli = fake_bin / "nmcli"
            nmcli.write_text(
                """#!/usr/bin/env bash
printf '%s\\n' "$*" >> "$NMCLI_LOG"
case "$*" in
    "-t -f DEVICE,TYPE device status")
        printf 'wlo1:wifi\\nwlp3s0f3u2:wifi\\np2p-dev-wlo1:wifi-p2p\\n'
        ;;
    "-g GENERAL.STATE device show wlo1") printf '30 (disconnected)\\n' ;;
    "-g GENERAL.PRODUCT device show wlo1") printf 'PCIe adapter\\n' ;;
    "-g GENERAL.STATE device show wlp3s0f3u2") printf '100 (connected)\\n' ;;
    "-g GENERAL.PRODUCT device show wlp3s0f3u2") printf 'USB adapter\\n' ;;
    "-t -f NAME,TYPE connection show") printf 'Home:802-11-wireless\\n' ;;
esac
""",
                encoding="utf-8",
            )
            rofi = fake_bin / "rofi"
            rofi.write_text("#!/usr/bin/env bash\nprintf '%s' \"$ROFI_OUTPUT\"\n", encoding="utf-8")
            for name in ("dunstify", "pkill"):
                executable = fake_bin / name
                executable.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            for executable in fake_bin.iterdir():
                executable.chmod(0o755)

            environment = os.environ.copy()
            environment.update({
                "PATH": f"{fake_bin}:{environment['PATH']}",
                "HOME": str(root / "home"),
                "XDG_STATE_HOME": str(root / "state"),
                "NMCLI_LOG": str(nmcli_log),
                "ROFI_OUTPUT": "󰤨  PCIe / built-in Wi-Fi  [wlo1] — PCIe adapter (30 disconnected)",
            })
            script = r"""
set -e
source "$WIFI_MENU"
select_wifi_device
[[ "$WIFI_DEVICE" == "wlo1" ]]
connect_saved "Home"
connect_open "OpenNet"
ROFI_OUTPUT="test-pass"
connect_secured_prompt "SecureNet"
ROFI_OUTPUT="󰤨  USB Wi-Fi  [wlp3s0f3u2] — USB adapter (100 connected)"
select_wifi_device
[[ "$WIFI_DEVICE" == "wlp3s0f3u2" ]]
"""
            environment["WIFI_MENU"] = str(SCRIPTS / "hardware" / "wifi-menu.sh")
            result = subprocess.run(
                ["bash", "-c", script],
                env=environment,
                capture_output=True,
                text=True,
                timeout=10,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                (root / "state" / "hypr-rice" / "wifi-device").read_text(encoding="utf-8"),
                "wlp3s0f3u2\n",
            )
            commands = nmcli_log.read_text(encoding="utf-8")
            self.assertIn("connection modify id Home connection.interface-name wlo1", commands)
            self.assertIn("connection up id Home ifname wlo1", commands)
            self.assertIn("device wifi connect OpenNet ifname wlo1", commands)
            self.assertIn(
                "device wifi connect SecureNet password test-pass ifname wlo1",
                commands,
            )

    def test_waybar_is_the_default_autostart(self) -> None:
        autostart = (ROOT / "lua" / "autostart.lua").read_text(encoding="utf-8")
        start_bar = (SCRIPTS / "desktop" / "start-bar.sh").read_text(encoding="utf-8")
        launcher = (SCRIPTS / "desktop" / "launcher.sh").read_text(encoding="utf-8")
        self.assertIn("/desktop/start-bar.sh", autostart)
        self.assertNotIn("waybar -c ", autostart)
        self.assertIn("waybar/config.jsonc", start_bar)
        self.assertIn("printf 'waybar\\n'", start_bar)
        self.assertIn('exec rofi -show drun', launcher)

    def test_waybar_quick_controls_and_keybindings_use_native_routes(self) -> None:
        quick_settings = (SCRIPTS / "desktop" / "quick-settings.py").read_text(encoding="utf-8")
        control_center = (SCRIPTS / "desktop" / "control-center.sh").read_text(encoding="utf-8")
        keybinds = (ROOT / "lua" / "keybinds.lua").read_text(encoding="utf-8")
        hyprland = (ROOT / "hyprland.lua").read_text(encoding="utf-8")

        self.assertIn("GtkLayerShell", quick_settings)
        self.assertIn("hardware\" / \"wifi-menu.sh", quick_settings)
        self.assertIn("hardware\" / \"bluetooth-menu.sh", quick_settings)
        self.assertIn("hardware\" / \"audio-menu.sh", quick_settings)
        self.assertIn("rofi", control_center)
        self.assertIn('hl.bind(mainMod .. " + W"', keybinds)
        self.assertIn('hl.bind(mainMod .. " + Q"', keybinds)
        self.assertIn('hl.dsp.window.close()', keybinds)
        self.assertIn('hl.bind(mainMod .. " + C"', keybinds)
        self.assertIn('controlCenter = configDir .. "/scripts/desktop/control-center.sh"', hyprland)

    def test_bar_launcher_defaults_to_waybar(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            output_file = root / "invocation.txt"
            for name in ("waybar",):
                executable = fake_bin / name
                executable.write_text(
                    "#!/bin/sh\nprintf '%s\\n' \"$*\" > \"$BAR_TEST_OUTPUT\"\n",
                    encoding="utf-8",
                )
                executable.chmod(0o755)
            pgrep = fake_bin / "pgrep"
            pgrep.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
            pgrep.chmod(0o755)
            state_root = root / "state"
            config_root = root / "config"
            environment = os.environ.copy()
            environment.update({
                "PATH": f"{fake_bin}:{environment['PATH']}",
                "HOME": str(root / "home"),
                "XDG_CONFIG_HOME": str(config_root),
                "XDG_STATE_HOME": str(state_root),
                "BAR_TEST_OUTPUT": str(output_file),
            })
            launcher = SCRIPTS / "desktop" / "start-bar.sh"

            result = subprocess.run([str(launcher)], env=environment, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("waybar/config.jsonc", output_file.read_text(encoding="utf-8"))
            self.assertEqual((state_root / "hypr-rice" / "bar-mode").read_text(encoding="utf-8"), "waybar\n")

    def test_application_launcher_uses_rofi_after_waybar_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            output_file = root / "invocation.txt"
            for name in ("rofi",):
                executable = fake_bin / name
                executable.write_text(
                    "#!/bin/sh\nprintf '%s\\n' \"$*\" > \"$LAUNCHER_TEST_OUTPUT\"\n",
                    encoding="utf-8",
                )
                executable.chmod(0o755)
            config_root = root / "config"
            state_root = root / "state"
            mode_file = state_root / "hypr-rice" / "bar-mode"
            mode_file.parent.mkdir(parents=True)
            mode_file.write_text("waybar\n", encoding="utf-8")
            environment = os.environ.copy()
            environment.update({
                "PATH": f"{fake_bin}:{environment['PATH']}",
                "HOME": str(root / "home"),
                "XDG_CONFIG_HOME": str(config_root),
                "XDG_STATE_HOME": str(state_root),
                "LAUNCHER_TEST_OUTPUT": str(output_file),
            })
            script = SCRIPTS / "desktop" / "launcher.sh"
            result = subprocess.run([str(script)], env=environment, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("-show drun", output_file.read_text(encoding="utf-8"))

    def test_bar_restart_routes_only_to_waybar(self) -> None:
        restart = (SCRIPTS / "desktop" / "restart-bar.sh").read_text(encoding="utf-8")
        restart_waybar = (SCRIPTS / "desktop" / "restart-waybar.sh").read_text(encoding="utf-8")
        rollback = (SCRIPTS / "desktop" / "rollback-to-waybar.sh").read_text(encoding="utf-8")
        self.assertIn("restart-waybar.sh", restart)
        self.assertIn('waybar/config.jsonc', restart_waybar)

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
        self.assertIn("notifications", data)
        self.assertGreaterEqual(data["notifications"], 0)
        self.assertIn("battery", data)
        self.assertIn("available", data["battery"])
        if data["battery"]["available"]:
            self.assertIn("status", data["battery"])
            self.assertTrue(
                data["battery"]["percentage"] is None
                or isinstance(data["battery"]["percentage"], int)
            )

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

    def test_idle_manager_snapshot_loader_works_without_repository_python_path(self) -> None:
        script = SCRIPTS / "session" / "idle-manager.py"
        spec = importlib.util.spec_from_file_location("idle_manager_test", script)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        idle_manager = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(idle_manager)

        with tempfile.TemporaryDirectory() as directory:
            settings = Path(directory) / "idle-settings.json"
            settings.write_text("{}", encoding="utf-8")
            snapshot = mock.Mock()
            loader = mock.Mock()
            loader.exec_module.side_effect = lambda module: setattr(
                module, "snapshot_before_config_change", snapshot
            )
            module_spec = mock.Mock(loader=loader)
            with (
                mock.patch.object(idle_manager, "SETTINGS_FILE", settings),
                mock.patch.object(idle_manager.importlib.util, "spec_from_file_location", return_value=module_spec) as load,
            ):
                idle_manager.snapshot_before_change()

            load.assert_called_once_with("rice_idle_maintenance", SCRIPTS / "core" / "rice_maintenance.py")
            snapshot.assert_called_once_with("idle-settings", settings)

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

    def test_bluetooth_agent_requires_interactive_approval(self) -> None:
        source = (SCRIPTS / "hardware" / "bluetooth-agent.py").read_text(encoding="utf-8")
        self.assertNotIn('return "0000"', source)
        self.assertNotIn("return dbus.UInt32(0)", source)
        self.assertNotIn("Auto-confirmed pairing", source)
        self.assertIn("ask_user(", source)
        self.assertIn("PairableTimeout\", dbus.UInt32(PAIRABLE_TIMEOUT_SECONDS)", source)
        self.assertIn('manager.RequestDefaultAgent(AGENT_PATH)', source)

    def test_bluetooth_approval_uses_the_rice_theme_and_rejects_cancel(self) -> None:
        script = SCRIPTS / "hardware" / "bluetooth-agent.py"
        spec = importlib.util.spec_from_file_location("bluetooth_agent_test", script)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        agent = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(agent)

        with (
            mock.patch.object(agent, "log"),
            mock.patch.object(agent, "notify"),
            mock.patch.object(
                agent.subprocess,
                "run",
                return_value=subprocess.CompletedProcess([], 0, stdout="Approve\n", stderr=""),
            ) as run,
        ):
            self.assertTrue(agent.ask_user("Pairing request", "Phone <request>"))

        args, kwargs = run.call_args
        self.assertEqual(args[0][args[0].index("-config") + 1], str(ROOT / "rofi" / "bluetooth-approval.rasi"))
        self.assertEqual(args[0][args[0].index("-mesg") + 1], "Pairing request\nPhone ‹request›")
        self.assertNotIn("<b>", script.read_text(encoding="utf-8"))
        self.assertEqual(kwargs["input"], "Approve\nReject")

        with (
            mock.patch.object(agent, "log"),
            mock.patch.object(agent, "notify"),
            mock.patch.object(
                agent.subprocess,
                "run",
                return_value=subprocess.CompletedProcess([], 1, stdout="", stderr=""),
            ),
        ):
            self.assertFalse(agent.ask_user("Pairing request", "Phone"))



if __name__ == "__main__":
    unittest.main()
