#!/usr/bin/env python3
"""tsup StatusNotifierItem integrator — system tray panel."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core import Core


def _run_tray():
    import gi
    gi.require_version("Gtk", "3.0")
    gi.require_version("AyatanaAppIndicator3", "0.1")
    from gi.repository import AyatanaAppIndicator3, Gtk, GLib

    POLL_INTERVAL_SEC = 5

    def build_menu(items: list[dict]) -> Gtk.Menu:
        menu = Gtk.Menu()
        for item in items:
            menu_item = Gtk.MenuItem(label=item["label"])
            menu_item.connect("activate", _on_item_activate, item)
            menu_item.show()
            menu.append(menu_item)
        return menu

    def _on_item_activate(_widget, item: dict):
        print(item["label"], flush=True)

    core = Core()

    indicator = AyatanaAppIndicator3.Indicator.new(
        "tsup",
        "dialog-information",
        AyatanaAppIndicator3.IndicatorCategory.APPLICATION_STATUS,
    )
    indicator.set_status(AyatanaAppIndicator3.IndicatorStatus.ACTIVE)
    indicator.set_label("tsup", "tsup")

    items = core.get_items()
    indicator.set_menu(build_menu(items))

    def refresh():
        nonlocal items
        new_items = core.get_items()
        if new_items != items:
            items = new_items
            indicator.set_menu(build_menu(items))
        return True

    GLib.timeout_add_seconds(POLL_INTERVAL_SEC, refresh)
    Gtk.main()


def main():
    core = Core()

    if len(sys.argv) < 2:
        _run_tray()
        return

    command = sys.argv[1]

    if command == "autostart-enable":
        result = core.enable_autostart()
    elif command == "autostart-disable":
        result = core.disable_autostart()
    elif command == "autostart-status":
        result = core.autostart_status()
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        print("Usage: integrator_sni.py [autostart-enable|autostart-disable|autostart-status]", file=sys.stderr)
        sys.exit(1)

    for k, v in result.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
