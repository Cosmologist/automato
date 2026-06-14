#!/usr/bin/env python3
"""tsup core — computer management panel kernel."""

from __future__ import annotations

from pathlib import Path


_AUTOSTART_DIR = Path.home() / ".config" / "autostart"
_AUTOSTART_FILE = _AUTOSTART_DIR / "tsup.desktop"

_DESKTOP_CONTENT = """\
[Desktop Entry]
Type=Application
Name=tsup
Comment=Computer management panel
Exec={exec_path}
Terminal=false
Hidden=false
X-GNOME-Autostart-enabled=true
"""


class Core:
    """Main application core providing menu items and system info."""

    def __init__(self):
        pass

    def get_items(self) -> list[dict]:
        """Return list of menu items.

        Returns:
            List of dicts with 'id' and 'label' keys.
        """
        return [
            {"id": "network-status", "label": "Network: connected"},
            {"id": "disk-usage", "label": "Disk: 42% used"},
            {"id": "uptime", "label": "Uptime: 3 days"},
        ]

    def enable_autostart(self, exec_path: str | None = None) -> dict:
        """Create .desktop file in XDG autostart directory.

        Args:
            exec_path: Command to run. If None, uses this script's parent dir integrator.
        """
        if exec_path is None:
            integrator = Path(__file__).resolve().parent / "integrator_sni.py"
            exec_path = f"python3 {integrator}"

        _AUTOSTART_DIR.mkdir(parents=True, exist_ok=True)
        _AUTOSTART_FILE.write_text(_DESKTOP_CONTENT.format(exec_path=exec_path))
        return {"enabled": True, "path": str(_AUTOSTART_FILE)}

    def disable_autostart(self) -> dict:
        """Remove .desktop file from XDG autostart directory."""
        if _AUTOSTART_FILE.exists():
            _AUTOSTART_FILE.unlink()
            return {"enabled": False, "removed": True}
        return {"enabled": False, "removed": False}

    def autostart_status(self) -> dict:
        """Check if autostart is enabled.

        Returns:
            Dict with 'enabled' (bool) and 'path' (str).
        """
        return {"enabled": _AUTOSTART_FILE.exists(), "path": str(_AUTOSTART_FILE)}
