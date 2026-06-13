"""Automato utilities."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys


class CommandError(RuntimeError):
    def __init__(self, cmd: list[str], returncode: int, stderr: str):
        self.cmd = cmd
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(stderr or f"Command failed: {' '.join(cmd)}")


def require_root() -> None:
    """Re-execute with sudo if not running as root."""
    if os.geteuid() != 0:
        print("Elevating to root via sudo...")
        restart_as_superuser()


def restart_as_superuser() -> None:
    """Re-execute the current script with sudo."""
    os.execvp("sudo", ["sudo", sys.executable] + sys.argv)


def exec_cmd(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    kwargs.setdefault("capture_output", True)
    kwargs.setdefault("text", True)
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        stderr = result.stderr.strip()
        if os.geteuid() != 0:
            answer = input(
                f"Command failed. Retry with sudo? [y/N]: "
            ).strip().lower()
            if answer in ("y", "yes"):
                restart_as_superuser()
        raise CommandError(cmd, result.returncode, stderr)
    return result


def require_tool(tool: str) -> None:
    """Install a missing tool via apt."""
    if shutil.which(tool) is None:
        print(f"Installing missing tool: {tool}")
        exec_cmd(["apt", "install", "-y", tool])
