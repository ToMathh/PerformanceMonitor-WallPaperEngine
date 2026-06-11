"""
StrangeCat Monitor - Main Entry Point
Windows 11 Task Manager style system monitor.
"""
import ctypes
try:
    ctypes.windll.kernel32.FreeConsole()
except Exception:
    pass

import tkinter as tk
import socket
import threading
import sys
import os

# Path setup: add base/ (this dir) and project root so both flat imports
# (config, collector, ...) and the ui package resolve correctly.
_BASE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_BASE)
for _p in (_ROOT, _BASE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from config import load_cfg, APP_NAME, APP_VER
from collector import DataCollector
from http_server import start_http
from ui.app import App

try:
    from pystray import Icon, Menu, MenuItem
    from PIL import Image, ImageDraw
    _HAS_TRAY = True
except ImportError:
    _HAS_TRAY = False


def _make_tray_icon():
    """Create tray icon."""
    sz = 64
    img = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([2, 2, sz - 3, sz - 3], radius=10,
                        fill=(12, 12, 12, 255), outline=(0, 120, 212, 255), width=2)
    for ex in (14, sz - 14):
        d.polygon([(ex - 9, 30), (ex, 8), (ex + 9, 30)], fill=(0, 100, 200, 255))
    d.ellipse([10, 28, sz - 10, sz - 6], fill=(22, 22, 22, 255),
              outline=(0, 100, 200, 180), width=1)
    for ex in (22, sz - 22):
        d.ellipse([ex - 5, 34, ex + 5, 44], fill=(0, 120, 212, 255))
    d.polygon([(sz // 2, 46), (sz // 2 - 4, 50), (sz // 2 + 4, 50)], fill=(0, 80, 160, 255))
    return img


def _single_instance() -> bool:
    """Check if another instance is already running."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 51997))
        s.close()
        return False
    except OSError:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(("127.0.0.1", 51997))
            s.sendall(b"SHOW")
            s.close()
        except Exception:
            pass
        return True


def _listen_instance(app: App):
    """Listen for single-instance messages."""
    try:
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("127.0.0.1", 51997))
        srv.listen(1)
        srv.settimeout(1)
        while app._alive:
            try:
                conn, _ = srv.accept()
                data = conn.recv(64)
                conn.close()
                if data == b"SHOW":
                    app.root.after(0, app.show)
                elif data == b"QUIT":
                    app.root.after(0, app._do_quit)
                    srv.close()
                    return
            except socket.timeout:
                continue
            except Exception:
                break
    except Exception:
        pass


if __name__ == "__main__":
    if _single_instance():
        sys.exit(0)

    cfg = load_cfg()
    collector = DataCollector(cfg)
    collector.start()

    root = tk.Tk()
    app = App(root, cfg, collector)

    # Single instance listener
    threading.Thread(target=_listen_instance, args=(app,),
                     name="SCat-ipc", daemon=True).start()

    # HTTP server
    if cfg.get("http_enabled", True):
        start_http(cfg.get("http_port", 5100), collector)

    # System tray
    if _HAS_TRAY:
        tray = Icon(APP_NAME, _make_tray_icon(), APP_NAME, Menu(
            MenuItem("Afficher", lambda i, it: root.after(0, app.show)),
            MenuItem("Masquer", lambda i, it: root.after(0, app.hide)),
            Menu.SEPARATOR,
            MenuItem("Quitter", lambda i, it: (i.stop(), app._do_quit())),
        ))
        threading.Thread(target=tray.run, name="SCat-tray", daemon=True).start()

    if cfg.get("start_minimized"):
        root.after(1200, app.hide)

    root.mainloop()
