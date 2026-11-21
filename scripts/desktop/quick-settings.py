#!/usr/bin/env python3
"""Toggle the Quickshell quick-controls panel from the bar."""
import os
import subprocess
from pathlib import Path

config = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "hypr"
raise SystemExit(subprocess.call([
    "qs", "ipc", "--path", str(config / "quickshell/shell.qml"),
    "call", "hyprshell", "toggleQuickControls",
]))
