"""
Configuration management for StrangeCat Monitor.
"""
import os
import json
import sys

APP_NAME = "StrangeCat Monitor"
APP_VER = "6.0"
APPDATA = os.path.join(os.getenv("APPDATA", os.path.expanduser("~")), "StrangeCatV6")
CFG_FILE = os.path.join(APPDATA, "config.json")
EXE_PATH = sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__)
STARTUP_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

HIST_LEN = 300
POLL_MS = 1000

# Refresh modes -> base interval (seconds) for the "fast" metrics
# (CPU, RAM, GPU, VRAM, Download, Upload).
REFRESH_MODES = {
    "realtime": 1.0,   # 1 s
    "normal": 2.0,     # 2 s
    "low": 3.0,        # 3 s (used by the Minimal/server build)
}

# Refresh rates (seconds) - legacy constants kept for reference
RATE_CPU = 0.5
RATE_RAM = 0.5
RATE_NET = 0.5
RATE_PROC = 3.0
RATE_GPU = 4.0
RATE_TEMP = 5.0
RATE_FAN = 8.0
RATE_DISK = 10.0


def rate_for(key, cfg):
    """Return the collection interval (seconds) for a metric key given cfg.

    Fast metrics follow the configured refresh mode; heavier/less important
    metrics use fixed, slower intervals. Disks use `disk_interval` (default
    60 s) so they barely cost anything.
    """
    cfg = cfg or {}
    mode = cfg.get("refresh_mode", "normal")
    fast = REFRESH_MODES.get(mode, 2.0)
    if key in ("cpu", "ram", "net", "gpu"):
        return fast
    if key == "proc":
        return max(fast, 3.0)
    if key == "temp":
        return 5.0
    if key == "fans":
        return 8.0
    if key == "disk":
        return float(cfg.get("disk_interval", 60.0))
    return fast

# Palette Windows 11 Task Manager dark
C = {
    # Fond
    "bg": "#0f0f0f",
    "sidebar_bg": "#131313",
    "panel_bg": "#161616",
    "header_bg": "#0c0c0c",
    "surface": "#1c1c1c",
    "surface2": "#202020",
    "graph_bg": "#070707",
    # Bords
    "border": "#252525",
    "border2": "#333333",
    # Sélection sidebar
    "sel_bg": "#1a2d3e",
    "sel_strip": "#0078d4",
    "hov_bg": "#181818",
    # Textes
    "fg": "#c8c8c8",
    "fg_hi": "#f0f0f0",
    "fg_dim": "#888888",
    "fg_dark": "#505050",
    # Accents
    "acc": "#0078d4",
    "acc_dim": "#004a8f",
    # États
    "ok": "#0f7b0f",
    "warn": "#c87000",
    "hot": "#c42b1c",
    # Métriques
    "col_cpu": "#0078d4",
    "col_ram": "#107c10",
    "col_gpu": "#7a5af8",
    "col_temp": "#c42b1c",
    "col_net": "#ca5010",
    "col_fan": "#0097b2",
    "col_disk": "#8b46b2",
    # Graphiques
    "grid": "#181818",
    "foot_bg": "#090909",
    # Aliases for compatibility
    "cpu": "#0078d4",
    "ram": "#107c10",
    "gpu": "#7a5af8",
    "temp": "#c42b1c",
    "net": "#ca5010",
    "fan": "#0097b2",
    "disk": "#8b46b2",
    "dim": "#505050",
    "mid": "#686868",
    "muted": "#888888",
    "sidebar_sel": "#1a2d3e",
    "sidebar_hov": "#181818",
}

DEFAULTS = {
    "start_on_boot": False,
    "start_minimized": False,
    "always_on_top": True,
    "opacity": 0.97,
    "temp_unit": "C",
    "language": "fr",
    "show_cpu": True,
    "show_ram": True,
    "show_gpu": True,
    "show_gpu_temp": True,
    "show_vram": True,
    "show_net": True,
    "show_cpu_fan": True,
    "show_case_fans": True,
    "show_disks": True,
    "http_enabled": True,
    "http_port": 5100,
    "refresh_mode": "normal",
    "disk_interval": 60.0,
    "pos_x": 140,
    "pos_y": 80,
    "win_w": 980,
    "win_h": 640,
    "close_action": "ask",
    "selected_metric": "cpu",
    "active_tab": "perf",
}

TR = {
    "fr": {
        "tab_perf": "Performance", "tab_set": "Paramètres",
        "resources": "RESSOURCES",
        "cpu_name": "Processeur", "ram_name": "Mémoire",
        "gpu_name": "GPU", "net_dn": "Téléchargement", "net_up": "Envoi",
        "uptime_app": "Session", "uptime_sys": "Uptime système",
        "processes": "Processus", "threads": "Threads",
        "utilization": "Utilisation", "speed": "Fréquence",
        "freq_base": "Fréq. de base", "freq_max": "Fréq. max",
        "total": "Total", "available": "Disponible", "used": "Utilisé",
        "dl": "Débit ↓", "ul": "Débit ↑",
        "sec_gen": "GÉNÉRAL", "sec_disp": "AFFICHAGE",
        "sec_met": "MÉTRIQUES", "sec_net": "RÉSEAU",
        "sec_perf": "PERFORMANCE",
        "refresh": "Fréquence de rafraîchissement",
        "rate_realtime": "Temps réel (1 s)", "rate_normal": "Normal (2 s)",
        "boot": "Démarrage avec Windows", "minimized": "Démarrer minimisé",
        "ontop": "Toujours au premier plan", "opacity": "Opacité",
        "unit": "Unité température", "lang": "Langue",
        "http_on": "Serveur HTTP", "http_port": "Port HTTP",
        "show_cpu": "Afficher CPU", "show_ram": "Afficher Mémoire",
        "show_gpu": "Afficher GPU", "show_gpu_temp": "Afficher GPU TEMP",
        "show_vram": "Afficher VRAM", "show_net": "Afficher Réseau",
        "show_cpu_fan": "Afficher CPU FAN",
        "show_case_fans": "Afficher CASE FANS",
        "show_disks": "Afficher Disques",
        "close_lbl": "Action fermeture", "close_reset": "Redemander",
        "temp_src": "Source temp.",
        "minimize": "Minimiser", "quit": "Quitter", "remember": "Se souvenir",
        "close_q": "Que faire ?", "cores": "cœurs", "logical": "logiques",
        "seconds": "s",
    },
    "en": {
        "tab_perf": "Performance", "tab_set": "Settings",
        "resources": "RESOURCES",
        "cpu_name": "CPU", "ram_name": "Memory",
        "gpu_name": "GPU", "net_dn": "Download", "net_up": "Upload",
        "uptime_app": "Session", "uptime_sys": "System uptime",
        "processes": "Processes", "threads": "Threads",
        "utilization": "Utilization", "speed": "Speed",
        "freq_base": "Base freq.", "freq_max": "Max freq.",
        "total": "Total", "available": "Available", "used": "In use",
        "dl": "Speed ↓", "ul": "Speed ↑",
        "sec_gen": "GENERAL", "sec_disp": "DISPLAY",
        "sec_met": "METRICS", "sec_net": "NETWORK",
        "sec_perf": "PERFORMANCE",
        "refresh": "Refresh rate",
        "rate_realtime": "Real-time (1 s)", "rate_normal": "Normal (2 s)",
        "boot": "Start with Windows", "minimized": "Start minimized",
        "ontop": "Always on top", "opacity": "Opacity",
        "unit": "Temperature unit", "lang": "Language",
        "http_on": "HTTP server", "http_port": "HTTP port",
        "show_cpu": "Show CPU", "show_ram": "Show Memory",
        "show_gpu": "Show GPU", "show_gpu_temp": "Show GPU TEMP",
        "show_vram": "Show VRAM", "show_net": "Show Network",
        "show_cpu_fan": "Show CPU FAN",
        "show_case_fans": "Show CASE FANS",
        "show_disks": "Show Disks",
        "close_lbl": "Close action", "close_reset": "Ask again",
        "temp_src": "Temp source",
        "minimize": "Minimize", "quit": "Quit", "remember": "Remember",
        "close_q": "What to do?", "cores": "cores", "logical": "logical",
        "seconds": "s",
    },
}

def T(key, lang="fr"):
    return TR.get(lang, TR["fr"]).get(key, key)


def _fmt_dur(seconds):
    """Format duration in seconds to HH:MM:SS."""
    if seconds is None:
        return "—"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _state_color(val, warn=70, hot=90):
    """Get color based on value thresholds."""
    if val is None:
        return C["fg_dim"]
    if val >= hot:
        return C["hot"]
    if val >= warn:
        return C["warn"]
    return C["ok"]


def load_cfg():
    try:
        os.makedirs(APPDATA, exist_ok=True)
        if os.path.exists(CFG_FILE):
            with open(CFG_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
            out = DEFAULTS.copy()
            out.update(d)
            return out
    except Exception:
        pass
    return DEFAULTS.copy()


def save_cfg(cfg):
    try:
        os.makedirs(APPDATA, exist_ok=True)
        with open(CFG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass


def set_startup(enable):
    try:
        import winreg
    except ImportError:
        return
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_KEY, 0, winreg.KEY_SET_VALUE)
        if enable:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{EXE_PATH}"')
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception:
        pass


def is_startup():
    try:
        import winreg
    except ImportError:
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_KEY, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def set_startup_entry(name, command, enable):
    """Create/remove an arbitrary HKCU\\Run startup entry.

    Used by the Minimal/server build so it has its own registry entry,
    independent from the full app's.
    """
    try:
        import winreg
    except ImportError:
        return
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_KEY, 0,
                             winreg.KEY_SET_VALUE)
        if enable:
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, command)
        else:
            try:
                winreg.DeleteValue(key, name)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception:
        pass


def is_startup_entry(name):
    """Return True if an HKCU\\Run entry with the given name exists."""
    try:
        import winreg
    except ImportError:
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_KEY, 0,
                             winreg.KEY_READ)
        winreg.QueryValueEx(key, name)
        winreg.CloseKey(key)
        return True
    except Exception:
        return False
