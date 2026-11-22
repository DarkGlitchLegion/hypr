from __future__ import annotations

import argparse
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from backup import BackupManager
from config_deployer import ConfigDeployer
from hardware_detect import detect_system
from package_manager import build_package_plan, install_packages
from validation import validate


RICE_NAME = "hypr-rice"


def confirm(message: str, default: bool = False) -> bool:
    if not sys.stdin.isatty():
        return default
    suffix = "[Y/n]" if default else "[y/N]"
    try:
        answer = input(f"{message} {suffix}: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    if not answer:
        return default
    return answer in ("y", "yes")


def log_install(home: Path, lines: list[str]) -> None:
    log_dir = home / ".local" / "state" / RICE_NAME
    log_dir.mkdir(parents=True, exist_ok=True)
    log = log_dir / "install.log"
    timestamp = datetime.now().isoformat(timespec="seconds")
    with log.open("a", encoding="utf-8") as stream:
        stream.write(f"[{timestamp}] " + "\n[" + timestamp + "] ".join(lines) + "\n")


def parser() -> argparse.ArgumentParser:
    args = argparse.ArgumentParser(
        description="Safely install or update the Hyprland rice.",
    )
    args.add_argument("--repository", default=None, help=argparse.SUPPRESS)
    args.add_argument("--dry-run", action="store_true", help="Show actions without changing files or packages")
    args.add_argument("--minimal", action="store_true", help="Use the minimal installation profile")
    args.add_argument("--standard", action="store_true", help="Use the standard installation profile")
    args.add_argument("--full", action="store_true", help="Use the full installation profile")
    args.add_argument("--skip-packages", action="store_true", help="Do not install or plan system packages")
    args.add_argument("--backup-only", action="store_true", help="Back up existing rice configuration and exit")
    args.add_argument("--restore", nargs="?", const="latest", metavar="BACKUP_DIR", help="Restore latest or named backup")
    args.add_argument("--symlinks", action="store_true", help="Use symlinks for deployable components")
    args.add_argument("--yes", action="store_true", help="Skip confirmation prompts")
    return args


def main(argv: list[str] | None = None) -> int:
    options = parser().parse_args(argv)
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        print("Error: do not run this installer as root.", file=sys.stderr)
        return 2
    home = Path.home()
    repository = Path(options.repository).resolve() if options.repository else Path(__file__).resolve().parents[3]
    if not (repository / "hyprland.lua").is_file():
        print(f"Error: repository root not found: {repository}", file=sys.stderr)
        return 2
    profiles = sum((options.minimal, options.standard, options.full))
    if profiles > 1:
        print("Error: choose only one profile: --minimal, --standard, or --full.", file=sys.stderr)
        return 2
    profile = "minimal" if options.minimal else "full" if options.full else "standard"
    backup = BackupManager(home, RICE_NAME)
    target = home / ".config" / "hypr"

    print("Hypr Rice Installer")
    print(f"Repository: {repository}")
    print(f"Target: {target}")
    print(f"Profile: {profile}")
    print("")

    if options.restore:
        if options.restore == "latest":
            backup_directory = None
        else:
            backup_directory = Path(options.restore).expanduser().resolve()
        if options.dry_run:
            if backup_directory is None:
                available = backup.list_backups()
                print("Dry run: would restore the latest backup." if available else "Dry run: no backups are available.")
            else:
                print(f"Dry run: would restore backup: {backup_directory}")
            return 0
        deployer = ConfigDeployer(repository, home, backup)
        paths = [(name, destination) for name, source, destination in deployer.components(profile)]
        restore_directory = backup_directory
        try:
            preview_items = backup.preview_restore(restore_directory)
        except Exception as exc:
            print(f"Error: restore rejected: {exc}", file=sys.stderr)
            log_install(home, [f"restore rejected: {exc}"])
            return 1
        print("Restore preview:")
        for item in preview_items:
            print(f"  - {item['name']}: {item['destination']}")
        if not options.yes and not confirm("Apply only the listed restore destinations?", False):
            print("Cancelled.")
            return 0
        if paths:
            safety_directory, _ = backup.backup_paths(paths, "pre-restore")
            print(f"Current configuration backed up before restore: {safety_directory}")
        ok, message = backup.restore(backup_directory)
        print(message)
        log_install(home, ["restore", message])
        return 0 if ok else 1

    required = ("python3", "Hyprland", "waybar", "dunst", "rofi", "kitty", "hyprpaper", "hyprlock", "hypridle")
    info = detect_system(home, required)
    print(f"Distribution: {info.distro_name} ({info.distro_id})")
    print(f"Architecture: {info.architecture}")
    print(f"Package manager: {info.package_manager}")
    print(f"Device type: {info.device_type}")
    print("GPU vendor(s): " + (", ".join(info.gpu_vendors) if info.gpu_vendors else "not detected"))
    print(f"Existing rice config: {'yes' if info.existing_config else 'no'}")
    print(f"Hyprland running: {'yes' if info.hyprland_running else 'no'}")
    if info.monitors:
        print("Detected monitors:")
        for monitor in info.monitors:
            print(f"  - {monitor.get('name', 'unknown')}: {monitor.get('width', '?')}x{monitor.get('height', '?')}@{monitor.get('refreshRate', '?')}Hz")
    else:
        print("Detected monitors: unavailable (generic preferred/auto monitor configuration will be used)")

    if options.backup_only:
        components = ConfigDeployer(repository, home, backup).components(profile)
        backup_items = [(name, destination) for name, source, destination in components if destination.exists() or destination.is_symlink()]
        if options.dry_run:
            print("Dry run: would back up:")
            for name, destination in backup_items:
                print(f"  - {name}: {destination}")
            return 0
        if not options.yes and not confirm("Create a timestamped backup of the existing rice?", True):
            print("Cancelled.")
            return 0
        directory, manifest = backup.backup_only(backup_items)
        print(f"Backup created: {directory}")
        log_install(home, [f"backup-only {directory}", f"items {len(manifest['items'])}"])
        return 0

    plan = None
    if not options.skip_packages:
        plan = build_package_plan(repository, profile, info.package_manager)
        print("")
        print("Package installation plan:")
        if info.package_manager == "unsupported":
            print("  - Unsupported package manager: no packages will be installed.")
        elif not plan.install:
            print("  - No missing packages detected.")
        else:
            for package in plan.install:
                print(f"  - install {package}")
        if plan.unsupported_tokens:
            print("  - Unsupported/unmapped package tokens: " + ", ".join(plan.unsupported_tokens))
        if plan.already_installed:
            print(f"  - Already installed: {len(plan.already_installed)} package(s)")

    deployer = ConfigDeployer(repository, home, backup, symlinks=options.symlinks)
    print("")
    print("Configuration deployment plan:")
    for name, source, destination in deployer.components(profile):
        print(f"  - {name}: {destination}")

    if options.dry_run:
        print("")
        print("Dry run complete. No files or packages were changed.")
        log_install(home, [f"dry-run profile={profile}", "no changes"])
        return 0

    if not options.yes:
        if plan and plan.install:
            if not confirm("Install the listed missing packages?", False):
                print("Package installation cancelled.")
                if not confirm("Continue with configuration deployment only?", False):
                    print("Installation cancelled.")
                    return 0
        elif not confirm("Continue with configuration deployment?", True):
            print("Cancelled.")
            return 0

    log_lines = [f"install profile={profile}"]
    if plan and plan.install:
        ok, message = install_packages(plan)
        print(message)
        log_lines.append(message)
        if not ok:
            print("Warning: package installation failed; configuration deployment will continue.", file=sys.stderr)
            log_lines.append("warning package installation failed")

    ok, deployed, backup_directory = deployer.deploy(profile)
    if not ok:
        print("Error: configuration deployment failed.", file=sys.stderr)
        return 1
    if backup_directory:
        print(f"Existing configuration backed up to: {backup_directory}")
        log_lines.append(f"backup {backup_directory}")
    print("Deployed components: " + ", ".join(deployed))

    state_file = home / ".local" / "state" / RICE_NAME / "installed-components.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(
        '{"components": ' + __import__("json").dumps(deployed) + ', "profile": ' + __import__("json").dumps(profile) + '}\n',
        encoding="utf-8",
    )
    validation = validate(target)
    print("")
    print("Validation summary:")
    print(f"  Passed: {len(validation.passed)}")
    print(f"  Warnings: {len(validation.warnings)}")
    print(f"  Failures: {len(validation.failures)}")
    for warning in validation.warnings[:20]:
        print(f"  Warning: {warning}")
    for failure in validation.failures[:20]:
        print(f"  Failure: {failure}")
    if validation.failures:
        print("Installation completed with validation failures. Review the report above.")
    else:
        print("Installation completed. Restart or reload your session only when you are ready.")
    log_lines.append(f"validation passed={len(validation.passed)} warnings={len(validation.warnings)} failures={len(validation.failures)}")
    log_install(home, log_lines)
    return 1 if validation.failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
