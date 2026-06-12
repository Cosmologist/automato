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

    def _entry_fields(self, entry: dict, *, ifname=True, status=True, ip=True, gateway=True) -> dict:
        out: dict[str, object] = {}
        if ifname:
            out["ifname"] = entry["ifname"]
        if status:
            out["status"] = "UP" if "UP" in entry.get("flags", []) else "DOWN"
        if ip:
            inet4 = [a for a in entry.get("addr_info", []) if a.get("family") == "inet"]
            if len(inet4) == 1:
                out["ip"] = f"{inet4[0]['local']}/{inet4[0]['prefixlen']}"
            elif len(inet4) > 1:
                out["ip"] = ",".join(f"{a['local']}/{a['prefixlen']}" for a in inet4)
        if gateway:
            try:
                gw = self._exec(["ip", "route", "show", "default", "dev", entry["ifname"]])
                gw_parts = gw.stdout.strip().split()
                if len(gw_parts) >= 3:
                    out["gateway"] = gw_parts[2]
            except RuntimeError:
                pass
        return out

    @default_dec
    @template("{ifname:<16} {status:<5} {ip:<18} {gateway}")
    def list(self) -> list[dict]:
        """List network interfaces"""
        data = self._exec(["ip", "-j", "addr", "show"])
        return [self._entry_fields(e) for e in json.loads(data.stdout)]

    @template
    def read(self, iface: str, ifname: bool = False, status: bool = False, ip: bool = False, gateway: bool = False) -> str | dict:
        """Read interface information

        Args:
            iface: Interface name or "default" for the default route interface
            ifname: Include interface name
            status: Include link status (UP/DOWN)
            ip: Include IPv4 address
            gateway: Include IPv4 gateway
        """
        name = self._resolve_iface(iface)
        entry = self._get_entry(name)
        if not (ifname or status or ip or gateway):
            return name
        return self._entry_fields(entry, ifname=ifname, status=status, ip=ip, gateway=gateway)


if __name__ == "__main__":
    Interface.run()
