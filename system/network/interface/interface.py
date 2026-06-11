#!/usr/bin/env python3
"""List and inspect network interfaces."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from lib.cli import CLI, default


class Interface(CLI):
    @default
    def all(self) -> list[dict]:
        """List all network interfaces."""
        return self._fetch_links()

    @default
    def show(self, iface: str) -> dict:
        """Show interface details.

        Args:
            iface: Interface name
        """
        data = self._fetch_links(iface)[0]
        try:
            result = self._exec(["ip", "-j", "addr", "show", iface])
        except RuntimeError:
            return data
        addr_info = []
        for entry in json.loads(result.stdout):
            addr_info.extend(entry.get("addr_info", []))
        data["addr_info"] = addr_info
        return data

    def _fetch_links(self, iface: str | None = None) -> list[dict]:
        cmd = ["ip", "-j", "link", "show"]
        if iface:
            cmd.append(iface)
        return json.loads(self._exec(cmd).stdout)


if __name__ == "__main__":
    Interface.run()
