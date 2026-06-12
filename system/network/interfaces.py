#!/usr/bin/env python3
"""Read and inspect network interfaces."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from lib.cli import CLI, default as default_dec, template


class Interface(CLI):
    @default_dec
    @template("{ifname:<16} {status}")
    def list(self) -> list[dict]:
        """List network interfaces."""
        data = self._exec(["ip", "-j", "addr", "show"])
        out = []
        for entry in json.loads(data.stdout):
            flags = entry.get("flags", [])
            out.append({
                "ifname": entry["ifname"],
                "status": "UP" if "UP" in flags else "DOWN",
            })
        return out

    @template
    def read(
        self,
        iface: str = "",
        ifname: bool = False,
        status: bool = False,
        ip: bool = False,
        gateway: bool = False,
    ) -> str | dict:
        """Read interface information.

        Args:
            iface: Interface name (auto-detect default if omitted)
            ifname: Include interface name
            status: Include link status (UP/DOWN)
            ip: Include IPv4 address (requires exactly one inet4 addr)
            gateway: Include IPv4 gateway (requires exactly one inet4 addr)
        """
        if not iface:
            result = self._exec(["ip", "route", "show", "default"])
            lines = result.stdout.strip().splitlines()
            if not lines:
                raise RuntimeError("No default route found")
            iface = lines[0].split()[4]

        data = self._exec(["ip", "-j", "addr", "show", iface])
        entries = json.loads(data.stdout)
        if not entries:
            raise RuntimeError(f"Interface '{iface}' not found")

        entry = entries[0]

        if not (ifname or status or ip or gateway):
            return iface

        out: dict[str, object] = {}

        if ifname:
            out["ifname"] = entry["ifname"]

        if status:
            out["status"] = "UP" if "UP" in entry.get("flags", []) else "DOWN"

        if ip or gateway:
            inet4 = [a for a in entry.get("addr_info", []) if a.get("family") == "inet"]
            if len(inet4) != 1:
                raise RuntimeError(
                    f"Expected exactly 1 inet4 address on {iface}, got {len(inet4)}"
                )
            if ip:
                out["ip"] = f"{inet4[0]['local']}/{inet4[0]['prefixlen']}"
            if gateway:
                gw = self._exec(
                    ["ip", "route", "show", "default", "dev", iface]
                )
                gw_parts = gw.stdout.strip().split()
                out["gateway"] = gw_parts[2] if len(gw_parts) >= 3 else None

        return out


if __name__ == "__main__":
    Interface.run()
