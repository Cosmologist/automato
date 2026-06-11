#!/usr/bin/env python3
"""List and inspect network interfaces."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from lib.cli import CLI, default as default_dec


class Interface(CLI):
    @default_dec
    def all(self) -> list[dict]:
        """List all network interfaces."""
        result = self._exec(["ip", "-j", "addr", "show"])
        return json.loads(result.stdout)

    @default_dec
    def default(self, detail: bool = False) -> str | dict:
        """Show the default network interface.

        Args:
            detail: Show full interface details
        """
        result = self._exec(["ip", "route", "show", "default"])
        lines = result.stdout.strip().splitlines()
        if not lines:
            raise RuntimeError("No default route found")
        iface = lines[0].split()[4]

        if detail:
            return self.detail(iface)

        return iface

    @default_dec
    def detail(self, iface: str) -> dict:
        """Show interface details.

        Args:
            iface: Interface name
        """
        result = self._exec(["ip", "-j", "addr", "show", iface])
        return json.loads(result.stdout)[0]


if __name__ == "__main__":
    Interface.run()
