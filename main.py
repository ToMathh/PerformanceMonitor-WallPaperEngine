"""
StrangeCat Monitor - UltraLowPerf (headless server)
====================================================
No window, no graphics.  Runs the data collector + HTTP server in the
background and is controlled from a system-tray icon with two settings:
  • Start at boot  (default: on)
  • Low mode 3 s   (default: on)

The JSON payload served on /performance is identical to the full Beta app
so any consumer (Wallpaper Engine widget, web dashboard, …) works with both.
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
import time

# Add the local base/ directory to sys.path so the headless build works both
# when run from source (python main.py) and when frozen by PyInstaller.
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (os.path.join(_HERE, "base"), os.path.join(_ROOT, "base"), _ROOT):
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

# Unique port used as a single-instance lock (full Beta uses 51997).
_LOCK_PORT    = 51998
# Registry entry name so the server has its own Run key, independent of Beta.
_STARTUP_NAME = f"{APP_NAME} Server"


def _make_tray_icon():
    """Generate a 64×64 RGBA cat icon with a green theme for the system tray."""
    sz = 64
    img = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([2, 2, sz - 3, sz - 3], radius=10,
                        fill=(12, 12, 12, 255), outline=(0, 180, 80, 255), width=2)
    for ex in (14, sz - 14):
        d.polygon([(ex - 9, 30), (ex, 8), (ex + 9, 30)], fill=(0, 200, 100, 255))
    d.ellipse([10, 28, sz - 10, sz - 6], fill=(22, 22, 22, 255),
              outline=(0, 180, 80, 180), width=1)
    for ex in (22, sz - 22):
        d.ellipse([ex - 5, 34, ex + 5, 44], fill=(0, 220, 120, 255))
    return img


def _single_instance() -> bool:
    """Return True if another instance is already running (socket lock)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", _LOCK_PORT))
        # Keep the socket open for the lifetime of the process.
        _single_instance._sock = s
        return False
    except OSError:
        return True


class HeadlessServer:
    """Manages the data collector and HTTP server for the headless build."""

    def __init__(self):
        self.cfg = load_cfg()

        # Ensure Low mode (3 s) is the default - realtime is not needed headless.
        if self.cfg.get("refresh_mode") not in ("realtime", "low"):
            self.cfg["refresh_mode"] = "low"

        # Network stats are always sent in KB/s from this build.
        self.cfg["net_unit"] = "kb"
        save_cfg(self.cfg)

        self.collector = DataCollector(self.cfg)
        self._alive    = True

        # Register a startup entry on first run so the server survives reboots.
        if not is_startup_entry(_STARTUP_NAME):
            if getattr(sys, "frozen", False):
                exe_path = sys.executable  # frozen .exe path
            else:
                script   = os.path.join(_HERE, "main.py")
                exe_path = f'"{sys.executable}" "{script}"'
            set_startup_entry(_STARTUP_NAME, exe_path, True)

        self._startup_enabled = is_startup_entry(_STARTUP_NAME)
        self._low_mode        = (self.cfg.get("refresh_mode", "low") == "low")

    def start(self):
        """Start the collector and HTTP server."""
        self.collector.start()
        port = self.cfg.get("http_port", 5100)
        start_http(port, self.collector)   # HTTP is the whole purpose of this build
        self.collector.update_cfg(self.cfg)

    def toggle_startup(self, icon=None):
        """Toggle the Windows startup registry entry and refresh the tray menu."""
        self._startup_enabled = not self._startup_enabled
        if getattr(sys, "frozen", False):
            exe_path = sys.executable
        else:
            script   = os.path.join(_HERE, "main.py")
            exe_path = f'"{sys.executable}" "{script}"'
        set_startup_entry(_STARTUP_NAME, exe_path, self._startup_enabled)
        if icon is not None:
            icon.update_menu()

    def toggle_low_mode(self, icon=None):
        """Switch between Low (3 s) and Realtime (1 s) refresh modes."""
        self._low_mode = not self._low_mode
        self.cfg["refresh_mode"] = "low" if self._low_mode else "realtime"
        save_cfg(self.cfg)
        self.collector.update_cfg(self.cfg)
        if icon is not None:
            icon.update_menu()

    def quit(self, icon=None):
        """Gracefully stop the collector, HTTP server, and tray icon, then exit."""
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
    # Prevent multiple headless instances from running simultaneously.
    if _single_instance():
        sys.exit(0)

    server = HeadlessServer()
    server.start()

    port  = server.cfg.get("http_port", 5100)
    title = f"{APP_NAME} – Server  127.0.0.1:{port}"

    if _HAS_TRAY:
        def make_menu():
            return Menu(
                MenuItem("Start at boot",
                         lambda i, it: server.toggle_startup(i),
                         checked=lambda item: server._startup_enabled),
                MenuItem("Low refresh (3 s)",
                         lambda i, it: server.toggle_low_mode(i),
                         checked=lambda item: server._low_mode),
                Menu.SEPARATOR,
                MenuItem("Quit", lambda i, it: server.quit(i)),
            )
        icon = Icon("StrangeCatServer", _make_tray_icon(), title, make_menu())
        icon.run()  # blocks the main thread; returns only when quit() is called
    else:
        # pystray not available – keep the process alive until killed.
        while server._alive:
            time.sleep(1.0)


if __name__ == "__main__":
    main()
