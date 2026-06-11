"""
StrangeCat Monitor - Ultra Low Perf (headless server)
=====================================================
No window, no graphics: just the data collector + HTTP server, controlled
from a system-tray icon whose only menu option is "Quitter".

This reuses the exact same collection engine and HTTP payload format as the
full app (../base), so the JSON served on /performance is identical.
"""
import ctypes
try:
    # Detach any console so nothing is displayed.
    ctypes.windll.kernel32.FreeConsole()
except Exception:
    pass

import os
import sys
import socket
import threading
import time

# Make the shared base/ engine importable.
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (os.path.join(_ROOT, "base"), _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from config import (load_cfg, save_cfg, APP_NAME, APP_VER,
                   set_startup_entry, is_startup_entry)  # noqa: E402
from collector import DataCollector                      # noqa: E402
from http_server import start_http, stop_http            # noqa: E402

try:
    from pystray import Icon, Menu, MenuItem
    from PIL import Image, ImageDraw
    _HAS_TRAY = True
except ImportError:
    _HAS_TRAY = False

_LOCK_PORT = 51998  # different from the full app (51997) so both can coexist
_STARTUP_NAME = f"{APP_NAME} Server"  # registry entry name for minimal app


def _make_tray_icon():
    """Draw a small server/cat icon for the tray."""
    sz = 64
    img = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([2, 2, sz - 3, sz - 3], radius=10,
                        fill=(12, 12, 12, 255), outline=(0, 160, 90, 255), width=2)
    for ex in (14, sz - 14):
        d.polygon([(ex - 9, 30), (ex, 8), (ex + 9, 30)], fill=(0, 150, 80, 255))
    d.ellipse([10, 28, sz - 10, sz - 6], fill=(22, 22, 22, 255),
              outline=(0, 150, 80, 180), width=1)
    for ex in (22, sz - 22):
        d.ellipse([ex - 5, 34, ex + 5, 44], fill=(0, 200, 110, 255))
    return img


def _single_instance() -> bool:
    """Return True if a headless instance is already running."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", _LOCK_PORT))
        # Keep the socket open for the lifetime of the process.
        _single_instance._sock = s
        return False
    except OSError:
        return True


class HeadlessServer:
    """Runs the collector + HTTP server with no GUI."""

    def __init__(self):
        self.cfg = load_cfg()
        # Set default refresh mode to "low" for minimal app if not set
        if "refresh_mode" not in self.cfg:
            self.cfg["refresh_mode"] = "low"
        self.collector = DataCollector(self.cfg)
        self._alive = True
        self._startup_enabled = is_startup_entry(_STARTUP_NAME)
        self._low_mode = (self.cfg.get("refresh_mode", "low") == "low")

    def start(self):
        self.collector.start()
        port = self.cfg.get("http_port", 5100)
        # Force HTTP on for the headless server (it is its whole purpose).
        start_http(port, self.collector)
        # Update collector with current refresh mode
        self.collector.update_cfg(self.cfg)

    def toggle_startup(self, icon=None):
        """Toggle startup at boot."""
        self._startup_enabled = not self._startup_enabled
        exe_path = sys.executable
        if getattr(sys, 'frozen', False):
            exe_path = sys.executable
        else:
            exe_path = os.path.join(_ROOT, "UltraLowPerf", "main.py")
            exe_path = f'"{sys.executable}" "{exe_path}"'
        set_startup_entry(_STARTUP_NAME, exe_path, self._startup_enabled)
        if icon is not None:
            icon.update_menu()

    def toggle_low_mode(self, icon=None):
        """Toggle low refresh mode (3s vs normal 2s)."""
        self._low_mode = not self._low_mode
        self.cfg["refresh_mode"] = "low" if self._low_mode else "normal"
        save_cfg(self.cfg)
        self.collector.update_cfg(self.cfg)
        if icon is not None:
            icon.update_menu()

    def quit(self, icon=None):
        self._alive = False
        try:
            self.collector.stop()
        except Exception:
            pass
        try:
            stop_http()
        except Exception:
            pass
        if icon is not None:
            try:
                icon.stop()
            except Exception:
                pass
        os._exit(0)


def main():
    if _single_instance():
        sys.exit(0)

    server = HeadlessServer()
    server.start()

    port = server.cfg.get("http_port", 5100)
    title = f"{APP_NAME} - Serveur (127.0.0.1:{port})"

    if _HAS_TRAY:
        def make_menu():
            return Menu(
                MenuItem("Start at boot", lambda i, it: server.toggle_startup(i),
                         checked=lambda item: server._startup_enabled),
                MenuItem("Low (3s)", lambda i, it: server.toggle_low_mode(i),
                         checked=lambda item: server._low_mode),
                Menu.SEPARATOR,
                MenuItem("Quitter", lambda i, it: server.quit(i)),
            )
        icon = Icon(
            "StrangeCatServer",
            _make_tray_icon(),
            title,
            make_menu(),
        )
        # icon.run() blocks on the main thread until quit.
        icon.run()
    else:
        # Fallback: no tray available -> just keep serving until killed.
        while server._alive:
            time.sleep(1.0)


if __name__ == "__main__":
    main()
