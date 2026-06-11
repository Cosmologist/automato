"""Automato infrastructure utilities."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def require_root() -> None:
    """Re-execute with sudo if not running as root."""
    if os.geteuid() != 0:
        print("Elevating to root via sudo...")
        os.execvp("sudo", ["sudo", sys.executable] + sys.argv)


def require_tools(*tools: str) -> None:
    """Install missing tools via apt."""
    missing = []
    for tool in tools:
        if not any(
            (Path(p) / tool).is_file() for p in os.getenv("PATH", "").split(os.pathsep)
        ):
            missing.append(tool)
    if missing:
        for tool in missing:
            print(f"Installing missing tool: {tool}")
            subprocess.run(["apt", "install", "-y", tool], check=True)
