#!/usr/bin/env python3
"""Read and inspect network interfaces"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from lib.cli import CLI, default as default_dec, template


class Interface(CLI):
    def _resolve_iface(self, name: str) -> str:
        if name == "default":
            result = self._exec(["ip", "route", "show", "default"])
            lines = result.stdout.strip().splitlines()
            if not lines:
                raise RuntimeError("No default route found")
            return lines[0].split()[4]
        return name

    def _get_entry(self, iface: str) -> dict:
        data = self._exec(["ip", "-j", "addr", "show", iface])
        entries = json.loads(data.stdout)
        if not entries:
            raise RuntimeError(f"Interface '{iface}' not found")
        return entries[0]

    def _entry_fields(self, entry: dict, *, ifname=False, status=False, ip=False, gateway=False) -> dict:
        out: dict[str, object] = {}
        if ifname:
            out["ifname"] = entry["ifname"]
        if status:
            out["status"] = "UP" if "UP" in entry.get("flags", []) else "DOWN"
        if ip or gateway:
            inet4 = [a for a in entry.get("addr_info", []) if a.get("family") == "inet"]
            if len(inet4) != 1:
                raise RuntimeError(
                    f"Expected exactly 1 inet4 address on {entry['ifname']}, got {len(inet4)}"
                )
            if ip:
                out["ip"] = f"{inet4[0]['local']}/{inet4[0]['prefixlen']}"
            if gateway:
                gw = self._exec(["ip", "route", "show", "default", "dev", entry["ifname"]])
                gw_parts = gw.stdout.strip().split()
                out["gateway"] = gw_parts[2] if len(gw_parts) >= 3 else None
        return out

    @default_dec
    @template("{ifname:<16} {status}")
    def list(self) -> list[dict]:
        """List network interfaces"""
        data = self._exec(["ip", "-j", "addr", "show"])
        return [self._entry_fields(e, ifname=True, status=True) for e in json.loads(data.stdout)]

    @template
    def read(self, iface: str, ifname: bool = False, status: bool = False, ip: bool = False, gateway: bool = False) -> str | dict:
        """Read interface information

        Args:
            iface: Interface name or "default" for the default route interface
            ifname: Include interface name
            status: Include link status (UP/DOWN)
            ip: Include IPv4 address (requires exactly one inet4 addr)
            gateway: Include IPv4 gateway (requires exactly one inet4 addr)
        """
        name = self._resolve_iface(iface)
        entry = self._get_entry(name)
        if not (ifname or status or ip or gateway):
            return name
        return self._entry_fields(entry, ifname=ifname, status=status, ip=ip, gateway=gateway)


if __name__ == "__main__":
    Interface.run()
