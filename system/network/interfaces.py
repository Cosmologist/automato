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
        return self._fetch_links()

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
        link = self._fetch_links(iface)[0]
        data = json.loads(result.stdout)[0]
        groups: dict[str, list[dict]] = {}
        for entry in data.get("addr_info", []):
            family = entry.get("family", "")
            if family == "inet":
                key = "inet4"
            elif family == "inet6":
                scope = entry.get("scope", "")
                if scope == "link":
                    key = "inet6.local"
                elif scope == "host":
                    key = "inet6.static"
                elif entry.get("noprefixroute"):
                    key = "inet6.dynamic"
                else:
                    key = "inet6.static"
            else:
                continue
            info: dict[str, object] = {
                "local": entry.get("local"),
                "prefixlen": entry.get("prefixlen"),
                "scope": entry.get("scope"),
            }
            for f in ("protocol", "dynamic", "noprefixroute"):
                v = entry.get(f)
                if v is not None:
                    info[f] = v
            groups.setdefault(key, []).append(info)
        link["addr_info"] = groups
        return link

    def _fetch_links(self, iface: str | None = None) -> list[dict]:
        cmd = ["ip", "-j", "link", "show"]
        if iface:
            cmd.append(iface)
        return json.loads(self._exec(cmd).stdout)


if __name__ == "__main__":
    Interface.run()
