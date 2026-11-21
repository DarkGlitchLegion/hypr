#!/usr/bin/env python3
"""Compatibility command that opens the Quickshell native controls page."""
import os
import subprocess
from pathlib import Path

config = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "hypr"
raise SystemExit(subprocess.call([
    "qs", "ipc", "--path", str(config / "quickshell/shell.qml"),
    "call", "hyprshell", "openHub", "controls",
]))
