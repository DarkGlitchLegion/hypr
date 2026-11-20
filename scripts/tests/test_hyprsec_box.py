from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
MANAGER = ROOT / "scripts" / "hyprsec-box.sh"
INSTALLER = ROOT / "scripts" / "hyprsec-install.sh"


class HyprSecBoxTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.home = self.root / "home"
        self.home.mkdir()
        self.state = self.root / "podman-state"
        self.log = self.root / "podman-args"
        fake_podman = self.bin / "podman"
        fake_podman.write_text(
            """#!/usr/bin/env bash
set -eu
case "$1" in
  info) [[ "${FAKE_ROOTLESS:-true}" == true ]] && printf 'true\\n' || printf 'false\\n' ;;
  image) exit 0 ;;
  container)
    [[ -e "$FAKE_STATE" ]]
    ;;
  create)
    printf '%s\\n' "$@" > "$FAKE_LOG"
    touch "$FAKE_STATE"
    printf 'container-id\\n'
    ;;
  inspect)
    case "$2" in
      --format)
        case "$3" in
          *State.Status*) printf 'created\\n' ;;
          *State.Running*) printf 'false\\n' ;;
          *NetworkSettings.Networks*) printf '{}\\n' ;;
        esac
        ;;
    esac
    ;;
  *) exit 0 ;;
esac
""",
            encoding="utf-8",
        )
        fake_podman.chmod(0o755)
        self.config = self.root / "config.sh"
        self.config.write_text(
            'CONTAINER_NAME="test-kali"\n'
            'CONTAINER_IMAGE="example.invalid/kali:test"\n'
            'WORKSPACE_ROOT="${HOME}/HyprSec/workspace"\n'
            'NETWORK_PROFILE="none"\n'
            'NETWORK_NAME="test-bridge"\n'
            'CONTAINER_CAPABILITIES=()\n',
            encoding="utf-8",
        )
        self.env = os.environ.copy()
        self.env.update(
            {
                "HOME": str(self.home),
                "XDG_STATE_HOME": str(self.root / "state"),
                "HYPRSEC_CONFIG_FILE": str(self.config),
                "PATH": f"{self.bin}:{self.env['PATH']}",
                "FAKE_STATE": str(self.state),
                "FAKE_LOG": str(self.log),
            }
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_manager(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(MANAGER), *args],
            env=self.env,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_installer_preserves_existing_user_config(self) -> None:
        config_home = self.root / "xdg-config"
        hyprsec_config = config_home / "hyprsec"
        hyprsec_config.mkdir(parents=True)
        config_file = hyprsec_config / "config.sh"
        config_file.write_text('CONTAINER_NAME="user-choice"\n', encoding="utf-8")
        catalog_file = hyprsec_config / "tools.conf"
        catalog_file.write_text("Custom|git|user entry\n", encoding="utf-8")
        keybind_file = hyprsec_config / "keybind"
        keybind_file.write_text("SUPER + SHIFT + X\n", encoding="utf-8")
        self.env["XDG_CONFIG_HOME"] = str(config_home)
        result = subprocess.run(
            ["bash", str(INSTALLER)],
            env=self.env,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(config_file.read_text(encoding="utf-8"), 'CONTAINER_NAME="user-choice"\n')
        self.assertEqual(catalog_file.read_text(encoding="utf-8"), "Custom|git|user entry\n")
        self.assertEqual(keybind_file.read_text(encoding="utf-8"), "SUPER + SHIFT + X\n")

    def test_create_uses_none_network_and_workspace_mounts_only(self) -> None:
        result = self.run_manager("create")
        self.assertEqual(result.returncode, 0, result.stderr)
        args = self.log.read_text(encoding="utf-8").splitlines()
        self.assertIn("--network", args)
        self.assertEqual(args[args.index("--network") + 1], "none")
        self.assertIn("--cap-drop=ALL", args)
        self.assertIn("--security-opt=no-new-privileges", args)
        self.assertNotIn("--privileged", args)
        mounts = [args[i + 1] for i, item in enumerate(args[:-1]) if item == "--volume"]
        self.assertEqual(len(mounts), 6)
        self.assertTrue(all(mount.startswith(str(self.home / "HyprSec/workspace/")) for mount in mounts))
        self.assertTrue(all(":rw" in mount for mount in mounts))

    def test_refuses_non_rootless_engine(self) -> None:
        self.env["FAKE_ROOTLESS"] = "false"
        result = self.run_manager("status")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("non-rootless", result.stderr)

    def test_rejects_project_path_traversal(self) -> None:
        result = self.run_manager("workspace", "create-project", "../outside")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.home / "outside").exists())

    def test_refuses_symlinked_workspace_mount(self) -> None:
        workspace = self.home / "HyprSec" / "workspace"
        workspace.mkdir(parents=True)
        outside = self.root / "private"
        outside.mkdir()
        (workspace / "targets").symlink_to(outside, target_is_directory=True)
        result = self.run_manager("create")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must not be a symlink", result.stderr)
        self.assertFalse(self.log.exists())

    def test_refuses_symlinked_workspace_mount(self) -> None:
        workspace = self.home / "HyprSec" / "workspace"
        workspace.mkdir(parents=True)
        outside = self.root / "private"
        outside.mkdir()
        (workspace / "targets").symlink_to(outside, target_is_directory=True)
        result = self.run_manager("create")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must not be a symlink", result.stderr)
        self.assertFalse(self.log.exists())


if __name__ == "__main__":
    unittest.main()
