from __future__ import annotations

import ast
import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ValidationResult:
    warnings: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    passed: list[str] = field(default_factory=list)


def validate(target: Path) -> ValidationResult:
    result = ValidationResult()
    scripts = target / "scripts"
    if scripts.is_dir():
        for path in scripts.rglob("*.sh"):
            if shutil.which("bash"):
                check = subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True)
                if check.returncode:
                    result.failures.append(f"Shell syntax: {path.relative_to(target)}")
                else:
                    result.passed.append(f"Shell syntax: {path.relative_to(target)}")
            if path.read_bytes().startswith(b"#!") and not os.access(path, os.X_OK):
                result.warnings.append(f"Script is not executable: {path.relative_to(target)}")
        for path in scripts.rglob("*.py"):
            try:
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                result.passed.append(f"Python syntax: {path.relative_to(target)}")
            except (OSError, SyntaxError) as exc:
                result.failures.append(f"Python syntax: {path.relative_to(target)}: {exc}")
    state = target / "state"
    if state.is_dir():
        for path in state.glob("*.json"):
            try:
                json.loads(path.read_text(encoding="utf-8"))
                result.passed.append(f"JSON: {path.relative_to(target)}")
            except (OSError, json.JSONDecodeError) as exc:
                result.failures.append(f"JSON: {path.relative_to(target)}: {exc}")
    expected = [
        target / "hyprland.conf",
        target / "hyprland.lua",
        target / "lua",
        target / "quickshell",
        target / "waybar",
        target / "rofi",
        target / "scripts",
        target / "kitty",
        target / "dunst",
    ]
    for path in expected:
        if path.exists():
            result.passed.append(f"Expected component: {path.relative_to(target)}")
        else:
            result.warnings.append(f"Missing expected component: {path.relative_to(target)}")
    quickshell = target / "quickshell"
    qml_files = sorted(quickshell.rglob("*.qml")) if quickshell.is_dir() else []
    if qml_files:
        qmllint = shutil.which("qmllint")
        if qmllint is None:
            qt_qmllint = Path("/usr/lib/qt6/bin/qmllint")
            qmllint = str(qt_qmllint) if qt_qmllint.is_file() else None
        if qmllint is None:
            result.warnings.append("QML syntax was not checked: qmllint is unavailable")
        else:
            env = os.environ.copy()
            import_paths = ["/usr/lib/qt6/qml"]
            if env.get("QML_IMPORT_PATH"):
                import_paths.insert(0, env["QML_IMPORT_PATH"])
            env["QML_IMPORT_PATH"] = os.pathsep.join(path for path in import_paths if Path(path).is_dir())
            try:
                check = subprocess.run(
                    [qmllint, "-E", "--max-warnings", "-1", *map(str, qml_files)],
                    capture_output=True,
                    text=True,
                    timeout=20,
                    env=env,
                )
            except subprocess.TimeoutExpired:
                result.failures.append("QML syntax verification timed out")
            else:
                if check.returncode:
                    result.failures.append("QML syntax verification failed")
                else:
                    result.passed.append(f"QML syntax: {len(qml_files)} file(s)")
    if shutil.which("Hyprland"):
        hyprland = shutil.which("Hyprland")
        check = subprocess.run(
            [hyprland, "--verify-config", "--config", str(target / "hyprland.lua")],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if check.returncode:
            result.failures.append("Hyprland configuration verification failed")
        else:
            result.passed.append("Hyprland configuration verification passed")
    else:
        result.warnings.append("Hyprland is not installed or not in PATH")
    for utility in ("qs", "waybar", "dunst", "rofi", "kitty", "hyprpaper", "hyprlock", "hypridle"):
        if shutil.which(utility) is None:
            result.warnings.append(f"Utility not found in PATH: {utility}")
    return result
