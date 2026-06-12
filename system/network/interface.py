#!/usr/bin/env python3
"""Show network interface details"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from lib.cli import CLI, default as default_dec, template


class Interface(CLI):
    _arg_labels = {"iface": "iface|default"}

    def _resolve_iface(self, name: str) -> str:
        if name == "default":
            result = self._exec(["ip", "route", "show", "default"])
            lines = result.stdout.strip().splitlines()
            if not lines:
                raise RuntimeError("No default route found")
            return lines[0].split()[4]
        return name

    @default_dec
    @template
    def show(
        self,
        iface: str,
        name: bool = False,
        status: bool = False,
        mtu: bool = False,
        ip: bool = False,
        gateway: bool = False,
    ) -> dict:
        """Show interface details

        Args:
            iface: Interface name or "default"
            name: Show interface name
            status: Show link status (UP/DOWN)
            mtu: Show MTU
            ip: Show IPv4 address
            gateway: Show IPv4 gateway
        """
        resolved = self._resolve_iface(iface)
        data = self._exec(["ip", "-j", "addr", "show", resolved])
        entries = json.loads(data.stdout)
        if not entries:
            raise RuntimeError(f"Interface '{resolved}' not found")
        entry = entries[0]

        if not (name or status or mtu or ip or gateway):
            name = status = mtu = ip = gateway = True

        out: dict[str, object] = {}
        if name:
            out["name"] = entry["ifname"]
        if status:
            out["status"] = "UP" if "UP" in entry.get("flags", []) else "DOWN"
        if mtu:
            out["mtu"] = entry.get("mtu")
        if ip or gateway:
            inet4 = [a for a in entry.get("addr_info", []) if a.get("family") == "inet"]
            if len(inet4) != 1:
                raise RuntimeError(
                    f"Expected exactly 1 IPv4 address on {resolved}, got {len(inet4)}"
                )
            if ip:
                out["ip"] = f"{inet4[0]['local']}/{inet4[0]['prefixlen']}"
            if gateway:
                gw = self._exec(["ip", "route", "show", "default", "dev", resolved])
                gw_parts = gw.stdout.strip().split()
                out["gateway"] = gw_parts[2] if len(gw_parts) >= 3 else None
        return out


if __name__ == "__main__":
    Interface.run()
