"""
StrangeCat Monitor  v6.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sections :
  §1  Imports & bootstrap
  §2  Palette & constantes
  §3  Config (load/save)
  §4  Collecteurs de données (thread-safe, isolés)
  §5  DataStore (cache central thread-safe)
  §6  HTTP Server
  §7  Tray
  §8  UI — App (fenêtre, titlebar, tabbar, footer, scroll global)
  §9  UI — Sidebar (widgets créés une seule fois)
  §10 UI — Vues détail (CPU / RAM / GPU / NET / DISK)
  §11 UI — Paramètres (combobox sombre)
  §12 UI — Graphiques anti-scintillement
  §13 Entry point
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  §1  IMPORTS & BOOTSTRAP  ━━━━━━━━
import ctypes
try:
    ctypes.windll.kernel32.FreeConsole()
except Exception:
    pass

import tkinter as tk
from tkinter import ttk
import collections
import json
import os
import queue
import socket
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, HTTPServer

import psutil

try:
    import winreg
    _HAS_WINREG = True
except ImportError:
    _HAS_WINREG = False

try:
    from pystray import Icon, Menu, MenuItem
    from PIL import Image, ImageDraw
    _HAS_TRAY = True
except ImportError:
    _HAS_TRAY = False

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  §2  PALETTE & CONSTANTES  ━━━━━━━

APP_NAME   = "StrangeCat Monitor"
APP_VER    = "6.0"
APPDATA    = os.path.join(os.getenv("APPDATA", os.path.expanduser("~")), "StrangeCatV6")
CFG_FILE   = os.path.join(APPDATA, "config.json")
EXE_PATH   = sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__)
STARTUP_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

HIST_LEN   = 300   # historique graphiques
POLL_MS    = 500   # rafraîchissement UI (ms)

# Intervalles collecte (secondes)
RATE_CPU   = 0.5
RATE_RAM   = 0.5
RATE_NET   = 0.5
RATE_GPU   = 4.0
RATE_TEMP  = 5.0
RATE_FAN   = 8.0
RATE_DISK  = 10.0

# Palette Windows 11 Task Manager dark
C = {
    # Fond
    "bg":         "#0f0f0f",
    "sidebar_bg": "#131313",
    "panel_bg":   "#161616",
    "header_bg":  "#0c0c0c",
    "surface":    "#1c1c1c",
    "surface2":   "#202020",
    "graph_bg":   "#070707",
    # Bords
    "border":     "#252525",
    "border2":    "#333333",
    # Sélection sidebar
    "sel_bg":     "#1a2d3e",
    "sel_strip":  "#0078d4",
    "hov_bg":     "#181818",
    # Textes
    "fg":         "#c8c8c8",
    "fg_hi":      "#f0f0f0",
    "fg_dim":     "#888888",
    "fg_dark":    "#505050",
    # Accents
    "acc":        "#0078d4",
    "acc_dim":    "#004a8f",
    # États
    "ok":         "#0f7b0f",
    "warn":       "#c87000",
    "hot":        "#c42b1c",
    # Métriques
    "col_cpu":    "#0078d4",
    "col_ram":    "#107c10",
    "col_gpu":    "#7a5af8",
    "col_temp":   "#c42b1c",
    "col_net":    "#ca5010",
    "col_fan":    "#0097b2",
    "col_disk":   "#8b46b2",
    # Graphiques
    "grid":       "#181818",
    "foot_bg":    "#090909",
}

DEFAULTS = {
    "start_on_boot":   False,
    "start_minimized": False,
    "always_on_top":   True,
    "opacity":         0.97,
    "temp_unit":       "C",
    "language":        "fr",
    "show_cpu":        True,
    "show_ram":        True,
    "show_gpu":        True,
    "show_gpu_temp":   True,
    "show_vram":       True,
    "show_net":        True,
    "show_cpu_fan":    True,
    "show_case_fans":  True,
    "show_disks":      True,
    "http_enabled":    True,
    "http_port":       5100,
    "pos_x":           140,
    "pos_y":           80,
    "win_w":           980,
    "win_h":           640,
    "close_action":    "ask",
    "selected_metric": "cpu",
    "active_tab":      "perf",
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


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  §3  CONFIG  ━━━━━━━━━━━━━━━━━━━━━

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
    if not _HAS_WINREG:
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
    if not _HAS_WINREG:
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_KEY, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  §4  COLLECTEURS  ━━━━━━━━━━━━━━━━

_APP_START = time.time()

# ── CPU ───────────────────────────────────────────────────────────────────────
def _collect_cpu() -> dict:
    try:
        pct   = psutil.cpu_percent(interval=0)
        percore = [round(p, 1) for p in psutil.cpu_percent(interval=0, percpu=True)]
        freq  = psutil.cpu_freq()
        cur_ghz = round(freq.current / 1000, 2) if freq else 0.0
        max_ghz = round(freq.max    / 1000, 2) if freq else 0.0
        try:
            procs   = len(psutil.pids())
            threads = sum(p.info.get("num_threads") or 0
                          for p in psutil.process_iter(["num_threads"]))
        except Exception:
            procs = threads = 0
        logical  = psutil.cpu_count(logical=True)  or 0
        physical = psutil.cpu_count(logical=False) or 0
        uptime_sys = time.time() - psutil.boot_time()
        uptime_app = time.time() - _APP_START
        return dict(
            cpu=round(pct, 1),
            cpu_percore=percore,
            cpu_freq_cur=cur_ghz,
            cpu_freq_max=max_ghz,
            cpu_logical=logical,
            cpu_physical=physical,
            process_count=procs,
            thread_count=threads,
            uptime_sys=uptime_sys,
            uptime_app=uptime_app,
        )
    except Exception as e:
        return dict(cpu=0.0, cpu_percore=[], cpu_freq_cur=0, cpu_freq_max=0,
                    cpu_logical=0, cpu_physical=0, process_count=0,
                    thread_count=0, uptime_sys=0, uptime_app=0)

# ── RAM ───────────────────────────────────────────────────────────────────────
def _collect_ram() -> dict:
    try:
        m = psutil.virtual_memory()
        return dict(
            memory=round(m.percent, 1),
            memory_used_gb=round(m.used      / 1024**3, 1),
            memory_total_gb=round(m.total    / 1024**3, 1),
            memory_avail_gb=round(m.available/ 1024**3, 1),
        )
    except Exception:
        return dict(memory=0.0, memory_used_gb=0, memory_total_gb=0, memory_avail_gb=0)

# ── GPU (nvidia-smi, cache + lock) ────────────────────────────────────────────
_gpu_lock  = threading.Lock()
_gpu_cache = dict(ts=0.0, data={
    "gpu_usage": 0.0, "gpu_temp": 0.0,
    "vram_used_gb": 0.0, "vram_total_gb": 0.0, "vram_usage": 0.0,
    "gpu_name": "GPU", "gpu_ok": False,
})

def _collect_gpu() -> dict:
    with _gpu_lock:
        now = time.time()
        if now - _gpu_cache["ts"] < RATE_GPU - 0.1:
            return dict(_gpu_cache["data"])
        try:
            out = subprocess.check_output(
                ["nvidia-smi",
                 "--query-gpu=utilization.gpu,temperature.gpu,"
                 "memory.used,memory.total,name",
                 "--format=csv,noheader,nounits"],
                encoding="utf-8",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                timeout=3,
            )
            parts = [x.strip() for x in out.strip().split(",")]
            mu = float(parts[2]) / 1024
            mt = float(parts[3]) / 1024
            data = dict(
                gpu_usage=round(float(parts[0]), 1),
                gpu_temp=round(float(parts[1]), 1),
                vram_used_gb=round(mu, 1),
                vram_total_gb=round(mt, 1),
                vram_usage=round(mu / mt * 100, 1) if mt else 0.0,
                gpu_name=parts[4] if len(parts) > 4 else "GPU",
                gpu_ok=True,
            )
        except Exception:
            data = dict(gpu_usage=0.0, gpu_temp=0.0, vram_used_gb=0,
                        vram_total_gb=0, vram_usage=0.0,
                        gpu_name="GPU", gpu_ok=False)
        _gpu_cache["data"] = data
        _gpu_cache["ts"]   = now
        return dict(data)

# ── NET ───────────────────────────────────────────────────────────────────────
_net_prev = dict(sent=0, recv=0, t=0.0)
_net_lock  = threading.Lock()

def _collect_net() -> dict:
    try:
        with _net_lock:
            now   = psutil.net_io_counters()
            t_now = time.time()
            prev  = _net_prev.copy()
            dt    = max(t_now - prev["t"], 0.01)
            up    = max(round((now.bytes_sent - prev["sent"]) / dt / 1_048_576, 2), 0.0)
            dn    = max(round((now.bytes_recv - prev["recv"]) / dt / 1_048_576, 2), 0.0)
            _net_prev.update(sent=now.bytes_sent, recv=now.bytes_recv, t=t_now)
        return dict(upload_speed=up, download_speed=dn)
    except Exception:
        return dict(upload_speed=0.0, download_speed=0.0)

# ── CPU TEMP ─────────────────────────────────────────────────────────────────
_temp_state = dict(value=None, method="unavailable")
_temp_lock  = threading.Lock()

def _collect_temp() -> dict:
    """Essaie plusieurs sources, retourne la première valeur valide."""
    val, method = None, "unavailable"

    # 1 — psutil
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            for k in ("coretemp","k10temp","zenpower","cpu_thermal","acpitz","nct6798"):
                if k in temps:
                    vs = [e.current for e in temps[k] if 0 < e.current < 130]
                    if vs:
                        val, method = round(sum(vs)/len(vs),1), f"psutil/{k}"
                        break
            if val is None:
                for name, sensors in temps.items():
                    vs = [e.current for e in sensors if 0 < e.current < 130]
                    if vs:
                        val, method = round(sum(vs)/len(vs),1), f"psutil/{name}"
                        break
    except Exception:
        pass

    # 2 — LibreHardwareMonitor / OpenHardwareMonitor via WMI
    if val is None and _HAS_WINREG:
        try:
            import wmi  # type: ignore
            for ns in ("root/LibreHardwareMonitor", "root/OpenHardwareMonitor"):
                try:
                    vs = [s.Value for s in wmi.WMI(namespace=ns).Sensor()
                          if s.SensorType == "Temperature"
                          and any(k in s.Name.lower() for k in
                                  ("cpu","core","package","tdie","tccd"))
                          and s.Value and 0 < s.Value < 130]
                    if vs:
                        val   = round(sum(vs)/len(vs),1)
                        method = ns.split("/")[1]
                        break
                except Exception:
                    pass
        except Exception:
            pass

    # 3 — CoreTemp shared memory
    if val is None:
        try:
            MAX = 128
            class _CT(ctypes.Structure):
                _fields_ = [
                    ("uiLoad",    ctypes.c_uint  * MAX),
                    ("uiTjMax",   ctypes.c_uint  * MAX),
                    ("uiCoreCnt", ctypes.c_uint),
                    ("uiCPUCnt",  ctypes.c_uint),
                    ("fTemp",     ctypes.c_float * MAX),
                    ("fVID",      ctypes.c_float),
                    ("fCPUSpeed", ctypes.c_float),
                    ("fFSBSpeed", ctypes.c_float),
                    ("fMultiplier",ctypes.c_float),
                    ("sCPUName",  ctypes.c_char  * 100),
                    ("ucFahrenheit", ctypes.c_ubyte),
                    ("ucDeltaToTjMax",ctypes.c_ubyte),
                ]
            hnd = ctypes.windll.kernel32.OpenFileMappingW(
                0x0004, False, "CoreTempMappingObject")
            if hnd:
                ptr = ctypes.windll.kernel32.MapViewOfFile(hnd, 0x0004, 0, 0, 0)
                if ptr:
                    raw = ctypes.string_at(ptr, ctypes.sizeof(_CT))
                    ctypes.windll.kernel32.UnmapViewOfFile(ptr)
                    ctypes.windll.kernel32.CloseHandle(hnd)
                    d  = _CT.from_buffer(
                        ctypes.create_string_buffer(raw, ctypes.sizeof(_CT)))
                    n  = max(0, min(int(d.uiCoreCnt), MAX))
                    vs = [d.fTemp[i] for i in range(n) if 0 < d.fTemp[i] < 130]
                    if vs:
                        val, method = round(sum(vs)/len(vs),1), "CoreTemp"
                else:
                    ctypes.windll.kernel32.CloseHandle(hnd)
        except Exception:
            pass

    with _temp_lock:
        _temp_state["value"]  = val
        _temp_state["method"] = method
    return dict(cpu_temp=val, cpu_temp_method=method)

# ── FANS ──────────────────────────────────────────────────────────────────────
def _collect_fans() -> dict:
    cpu_fan, case_fans = None, []
    cpu_kw  = ("cpu","pump","water","aio","liquid")
    case_kw = ("case","chassis","sys","fan")
    try:
        f = psutil.sensors_fans()
        if f:
            for name, lst in f.items():
                for fan in lst:
                    if fan.current and fan.current > 50:
                        n = name.lower()
                        if any(k in n for k in cpu_kw):
                            if cpu_fan is None or fan.current > cpu_fan:
                                cpu_fan = round(fan.current)
                        else:
                            case_fans.append(round(fan.current))
    except Exception:
        pass
    if not cpu_fan and _HAS_WINREG:
        try:
            import wmi  # type: ignore
            for ns in ("root/LibreHardwareMonitor","root/OpenHardwareMonitor"):
                try:
                    for s in wmi.WMI(namespace=ns).Sensor():
                        if s.SensorType == "Fan" and s.Value and s.Value > 50:
                            n = s.Name.lower()
                            if any(k in n for k in cpu_kw):
                                if cpu_fan is None or s.Value > cpu_fan:
                                    cpu_fan = round(s.Value)
                            else:
                                case_fans.append(round(s.Value))
                except Exception:
                    pass
        except Exception:
            pass
    avg_case = round(sum(case_fans)/len(case_fans)) if case_fans else None
    return dict(cpu_fan=cpu_fan, case_fans=avg_case, case_fans_list=case_fans)

# ── DISQUES ───────────────────────────────────────────────────────────────────
def _collect_disks() -> dict:
    out = {}
    try:
        for part in psutil.disk_partitions(all=False):
            dev = part.device
            if not dev or len(dev) < 2 or dev[1] != ":":
                continue
            drive = dev[:2].upper()
            try:
                du = psutil.disk_usage(drive)
                out[drive] = dict(
                    pct=round(du.percent,1),
                    used=round(du.used  /1024**3,1),
                    total=round(du.total/1024**3,1),
                    free=round(du.free  /1024**3,1),
                )
            except Exception:
                pass
    except Exception:
        pass
    return out   # {"C:": {...}, "D:": {...}, ...}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  §5  DATASTORE  ━━━━━━━━━━━━━━━━━━

class DataStore:
    """
    Cache central thread-safe.
    Un ThreadPoolExecutor collecte en parallèle.
    On expose get() pour UI et HTTP.
    """
    def __init__(self, cfg: dict):
        self._cfg   = cfg
        self._lock  = threading.Lock()
        self._data: dict = {}
        self._disks: dict = {}
        self._hist: dict[str, collections.deque] = {}
        self._last: dict[str, float] = {}
        self._running = False
        self._pool  = ThreadPoolExecutor(
            max_workers=min(os.cpu_count() or 4, 8),
            thread_name_prefix="SCat",
        )
        self._thread: threading.Thread | None = None
        # initialiser historiques
        for key in ("cpu","ram","gpu","gpu_temp","vram","net_dn","net_up",
                    "cpu_temp","cpu_fan","case_fans"):
            self._hist[key] = collections.deque([0.0]*HIST_LEN, maxlen=HIST_LEN)

    # ── Démarrage / arrêt ────────────────────────────────────────────────────
    def start(self):
        self._running = True
        # Initialiser réseau (1ère mesure sans delta)
        _collect_net()
        time.sleep(0.05)
        self._thread = threading.Thread(
            target=self._loop, name="SCat-collect", daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._pool.shutdown(wait=False, cancel_futures=True)

    # ── Boucle collecte ──────────────────────────────────────────────────────
    def _loop(self):
        while self._running:
            now = time.time()
            futs = {}

            def maybe(key, rate, fn):
                if now - self._last.get(key, 0) >= rate:
                    self._last[key] = now
                    futs[self._pool.submit(fn)] = key

            maybe("cpu",  RATE_CPU,  _collect_cpu)
            maybe("ram",  RATE_RAM,  _collect_ram)
            maybe("net",  RATE_NET,  _collect_net)
            maybe("gpu",  RATE_GPU,  _collect_gpu)
            maybe("temp", RATE_TEMP, _collect_temp)
            maybe("fans", RATE_FAN,  _collect_fans)
            maybe("disk", RATE_DISK, self._disk_task)

            for fut, key in list(futs.items()):
                try:
                    result = fut.result(timeout=6)
                    with self._lock:
                        if key == "disk":
                            self._disks = result or {}
                        elif isinstance(result, dict):
                            self._data.update(result)
                    self._update_hist(result if key != "disk" else {}, key)
                except Exception:
                    pass

            time.sleep(0.4)

    def _disk_task(self):
        return _collect_disks()

    def _update_hist(self, data: dict, key: str):
        map_ = {
            "cpu":    ("cpu",       data.get("cpu",       0)),
            "ram":    ("ram",       data.get("memory",    0)),
            "gpu":    ("gpu",       data.get("gpu_usage", 0)),
            "gpu":    ("gpu",       data.get("gpu_usage", 0)),
            "gpu":    ("gpu_temp",  data.get("gpu_temp",  0)),
            "gpu":    ("vram",      data.get("vram_usage",0)),
            "net":    ("net_dn",    data.get("download_speed", 0)),
            "net":    ("net_up",    data.get("upload_speed",   0)),
            "temp":   ("cpu_temp",  data.get("cpu_temp",  0) or 0),
            "fans":   ("cpu_fan",   data.get("cpu_fan",   0) or 0),
            "fans":   ("case_fans", data.get("case_fans", 0) or 0),
        }
        # rebuild as list to avoid duplicate key issue
        pushes = []
        if key == "cpu":
            pushes = [("cpu", data.get("cpu", 0))]
        elif key == "ram":
            pushes = [("ram", data.get("memory", 0))]
        elif key == "gpu":
            pushes = [
                ("gpu",      data.get("gpu_usage", 0)),
                ("gpu_temp", data.get("gpu_temp",  0)),
                ("vram",     data.get("vram_usage",0)),
            ]
        elif key == "net":
            pushes = [
                ("net_dn", data.get("download_speed", 0)),
                ("net_up", data.get("upload_speed",   0)),
            ]
        elif key == "temp":
            pushes = [("cpu_temp", data.get("cpu_temp", 0) or 0)]
        elif key == "fans":
            pushes = [
                ("cpu_fan",   data.get("cpu_fan",   0) or 0),
                ("case_fans", data.get("case_fans", 0) or 0),
            ]
        with self._lock:
            for hkey, hval in pushes:
                if hkey in self._hist:
                    self._hist[hkey].append(float(hval))
            # Disques : historique par drive
            for drive, ddata in self._disks.items():
                hk = f"disk_{drive}"
                if hk not in self._hist:
                    self._hist[hk] = collections.deque([0.0]*HIST_LEN, maxlen=HIST_LEN)
                self._hist[hk].append(float(ddata.get("pct",0)))

    # ── Lecture ───────────────────────────────────────────────────────────────
    def snapshot(self) -> dict:
        with self._lock:
            d = dict(self._data)
            d["_disks"] = dict(self._disks)
            d["_hist"]  = {k: list(v) for k, v in self._hist.items()}
            d["uptime_app"] = time.time() - _APP_START
        return d

    def http_payload(self) -> dict:
        """Format JSON exact attendu par le serveur."""
        with self._lock:
            d = self._data
            di = self._disks
            ps: dict = {}
            ps["cpu"]           = d.get("cpu", 0)
            ps["cpu_percore"]   = d.get("cpu_percore", [])
            ps["memory"]        = d.get("memory", 0)
            used  = d.get("memory_used_gb", 0)
            total = d.get("memory_total_gb", 0)
            ps["memory_gb"]     = f"{used:.1f} GB/{total:.1f} GB"
            ps["gpu_usage"]     = d.get("gpu_usage", 0)
            ps["vram_usage"]    = d.get("vram_usage", 0)
            vu = d.get("vram_used_gb",  0)
            vt = d.get("vram_total_gb", 0)
            ps["vram_gb"]       = f"{vu:.1f} GB/{vt:.1f} GB"
            ps["gpu_temp"]      = d.get("gpu_temp", 0)
            ps["upload_speed"]  = d.get("upload_speed",   0)
            ps["download_speed"]= d.get("download_speed", 0)
            ps["timestamp"]     = d.get("timestamp", time.time())
            for drive, dd in di.items():
                k = drive.lower().replace(":","") + "_disk"
                ps[k] = f"{dd.get('used',0):.1f} GB/{dd.get('total',0):.1f} GB"
        return dict(timestamp=time.time(), psutil=ps, hwinfo=[])


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  §6  HTTP SERVER  ━━━━━━━━━━━━━━━━

_http_srv: HTTPServer | None = None

class _Handler(BaseHTTPRequestHandler):
    store: "DataStore"
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path == "/performance":
            try:
                body = json.dumps(self.store.http_payload()).encode()
                self.send_response(200)
                self.send_header("Content-Type",   "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(body)
            except Exception:
                self.send_response(500); self.end_headers()
        else:
            self.send_response(404); self.end_headers()

def start_http(port: int, store: "DataStore") -> bool:
    global _http_srv
    stop_http()
    try:
        class _H(_Handler): pass
        _H.store = store
        _http_srv = HTTPServer(("127.0.0.1", port), _H)
        threading.Thread(
            target=_http_srv.serve_forever,
            name="SCat-http", daemon=True).start()
        return True
    except Exception:
        return False

def stop_http():
    global _http_srv
    if _http_srv:
        try: _http_srv.shutdown()
        except Exception: pass
        _http_srv = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  §7  TRAY  ━━━━━━━━━━━━━━━━━━━━━━

def _make_tray_icon():
    sz = 64
    img = Image.new("RGBA", (sz, sz), (0,0,0,0))
    d   = ImageDraw.Draw(img)
    d.rounded_rectangle([2,2,sz-3,sz-3], radius=10,
                        fill=(12,12,12,255), outline=(0,120,212,255), width=2)
    for ex in (14, sz-14):
        d.polygon([(ex-9,30),(ex,8),(ex+9,30)], fill=(0,100,200,255))
    d.ellipse([10,28,sz-10,sz-6], fill=(22,22,22,255),
              outline=(0,100,200,180), width=1)
    for ex in (22, sz-22):
        d.ellipse([ex-5,34,ex+5,44], fill=(0,120,212,255))
    d.polygon([(sz//2,46),(sz//2-4,50),(sz//2+4,50)], fill=(0,80,160,255))
    return img


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  §8  UI — APP  ━━━━━━━━━━━━━━━━━━

def _fmt_dur(s: float) -> str:
    h = int(s//3600); m = int((s%3600)//60); sec = int(s%60)
    return f"{h}:{m:02d}:{sec:02d}"

def _state_color(v, warn, hot) -> str:
    if warn is None or v is None: return C["ok"]
    if v >= hot:  return C["hot"]
    if v >= warn: return C["warn"]
    return C["ok"]


class App:
    """Fenêtre principale. Crée les widgets une seule fois, les met à jour."""

    # ── Entrée ───────────────────────────────────────────────────────────────
    def __init__(self, root: tk.Tk, cfg: dict, store: DataStore):
        self.root  = root
        self.cfg   = cfg
        self.store = store
        self.lang  = cfg.get("language", "fr")
        self._alive = True
        self._active_tab = cfg.get("active_tab", "perf")
        self._selected   = cfg.get("selected_metric", "cpu")

        # Drag / resize
        self._drag  = False
        self._rsz   = False
        self._dx = self._dy = 0
        self._rx = self._ry = self._rw = self._rh = self._wx = self._wy = 0

        # Sous-composants
        self._sidebar:  "Sidebar | None"    = None
        self._detail:   "DetailView | None" = None
        self._settings_view: "SettingsView | None" = None
        self._content_frame: tk.Frame | None = None

        # Appliquer options globales Tkinter (combobox sombre)
        self._apply_tk_theme()

        self._build_window()
        self._build_titlebar()
        self._build_tabbar()
        self._build_footer()
        self._build_content()

        # Scroll global : déléguer au canvas actif
        self._active_scroll_target: tk.Canvas | None = None
        root.bind_all("<MouseWheel>", self._on_global_scroll, add="+")
        root.bind_all("<Button-4>",   self._on_global_scroll4, add="+")
        root.bind_all("<Button-5>",   self._on_global_scroll5, add="+")

        root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._poll()

    # ── Thème Tk (combobox sombre) ────────────────────────────────────────────
    def _apply_tk_theme(self):
        r = self.root
        r.option_add("*TCombobox*Listbox.background",      C["surface"])
        r.option_add("*TCombobox*Listbox.foreground",      C["fg"])
        r.option_add("*TCombobox*Listbox.selectBackground",C["acc"])
        r.option_add("*TCombobox*Listbox.selectForeground",C["fg_hi"])
        r.option_add("*TCombobox*Listbox.font",            "Segoe\\ UI 9")
        st = ttk.Style(r)
        st.theme_use("default")
        st.configure("Dark.TCombobox",
            fieldbackground=C["surface"],
            background=C["surface2"],
            foreground=C["fg"],
            arrowcolor=C["fg"],
            bordercolor=C["border"],
            lightcolor=C["border"],
            darkcolor=C["border"],
            relief="flat",
        )
        st.map("Dark.TCombobox",
            fieldbackground=[("readonly", C["surface"]),
                             ("disabled", C["surface2"])],
            foreground=[("readonly", C["fg"]),
                        ("disabled", C["fg_dim"])],
            background=[("active",   C["surface2"]),
                        ("readonly", C["surface2"])],
        )
        st.configure("Vertical.TScrollbar",
            background=C["surface2"], troughcolor=C["bg"],
            arrowcolor=C["fg_dim"], bordercolor=C["bg"],
            relief="flat",
        )

    # ── Fenêtre ───────────────────────────────────────────────────────────────
    def _build_window(self):
        r = self.root
        r.overrideredirect(True)
        r.configure(bg=C["bg"])
        r.attributes("-topmost", bool(self.cfg.get("always_on_top", True)))
        r.attributes("-alpha",   float(self.cfg.get("opacity", 0.97)))
        w = int(self.cfg.get("win_w", 980))
        h = int(self.cfg.get("win_h", 640))
        x = int(self.cfg.get("pos_x", 140))
        y = int(self.cfg.get("pos_y",  80))
        r.geometry(f"{w}x{h}+{x}+{y}")
        r.minsize(720, 480)
        r.bind("<Motion>",          self._on_motion)
        r.bind("<ButtonPress-1>",   self._on_press)
        r.bind("<B1-Motion>",       self._on_drag_ev)
        r.bind("<ButtonRelease-1>", self._on_release)

    # ── Titlebar ──────────────────────────────────────────────────────────────
    def _build_titlebar(self):
        tb = tk.Frame(self.root, bg=C["header_bg"], height=36)
        tb.pack(fill="x", side="top")
        tb.pack_propagate(False)
        self._titlebar = tb

        for w in (tb,):
            w.bind("<ButtonPress-1>",   self._on_press)
            w.bind("<B1-Motion>",       self._on_drag_ev)
            w.bind("<ButtonRelease-1>", self._on_release)

        left = tk.Frame(tb, bg=C["header_bg"])
        left.pack(side="left", padx=(14,0))
        tk.Label(left, text="🐱", font=("Segoe UI Emoji",11),
                 bg=C["header_bg"], fg=C["acc"]).pack(side="left", padx=(0,8))
        tk.Label(left, text=APP_NAME, font=("Segoe UI",9,"bold"),
                 bg=C["header_bg"], fg=C["fg_hi"]).pack(side="left")
        tk.Label(left, text=f"v{APP_VER}", font=("Segoe UI",7),
                 bg=C["header_bg"], fg=C["fg_dark"]).pack(side="left", padx=(6,0))

        right = tk.Frame(tb, bg=C["header_bg"])
        right.pack(side="right")

        def wbtn(txt, cmd, hbg=C["surface2"], hfg=C["fg_hi"]):
            b = tk.Label(right, text=txt, font=("Segoe UI",11),
                         bg=C["header_bg"], fg=C["fg_dim"],
                         cursor="hand2", padx=14, pady=5)
            b.pack(side="left")
            b.bind("<Button-1>", lambda e: cmd())
            b.bind("<Enter>", lambda e,b=b: b.config(fg=hfg, bg=hbg))
            b.bind("<Leave>", lambda e,b=b: b.config(fg=C["fg_dim"], bg=C["header_bg"]))

        wbtn("—", self.hide)
        wbtn("✕", self._on_close, hbg="#c42b1c", hfg="#fff")
        tk.Frame(self.root, bg=C["border"], height=1).pack(fill="x", side="top")

    # ── Tabbar ────────────────────────────────────────────────────────────────
    def _build_tabbar(self):
        if hasattr(self, "_tabbar"):
            self._tabbar.destroy()
        self._tabbar = tk.Frame(self.root, bg=C["header_bg"], height=34)
        self._tabbar.pack(fill="x", side="top")
        self._tabbar.pack_propagate(False)

        self._tabbar.bind("<ButtonPress-1>",   self._on_press)
        self._tabbar.bind("<B1-Motion>",       self._on_drag_ev)
        self._tabbar.bind("<ButtonRelease-1>", self._on_release)

        for key, lk in [("perf","tab_perf"),("settings","tab_set")]:
            active = (self._active_tab == key)
            bg = C["bg"] if active else C["header_bg"]
            fg = C["fg_hi"] if active else C["fg_dim"]
            font = ("Segoe UI",9,"bold") if active else ("Segoe UI",9)
            lbl = tk.Label(self._tabbar, text=f"  {T(lk,self.lang)}  ",
                           font=font, bg=bg, fg=fg, cursor="hand2",
                           padx=4, pady=6)
            lbl.pack(side="left")
            lbl.bind("<Button-1>", lambda e, k=key: self._switch_tab(k))
            if not active:
                lbl.bind("<Enter>", lambda e,l=lbl: l.config(fg=C["fg_hi"]))
                lbl.bind("<Leave>", lambda e,l=lbl: l.config(fg=C["fg_dim"]))

        # Ligne indicatrice
        if hasattr(self, "_tab_line"):
            self._tab_line.destroy()
        self._tab_line = tk.Frame(self.root, bg=C["acc"], height=2)
        self._tab_line.pack(fill="x", side="top")

    def _switch_tab(self, tab):
        if tab == self._active_tab:
            return
        self._active_tab = tab
        self.cfg["active_tab"] = tab
        self._build_tabbar()
        if self._content_frame:
            self._content_frame.destroy()
        self._sidebar  = None
        self._detail   = None
        self._settings_view = None
        self._active_scroll_target = None
        self._build_content()

    # ── Footer ────────────────────────────────────────────────────────────────
    def _build_footer(self):
        tk.Frame(self.root, bg=C["border"], height=1).pack(fill="x", side="bottom")
        foot = tk.Frame(self.root, bg=C["foot_bg"], height=22)
        foot.pack(fill="x", side="bottom")
        foot.pack_propagate(False)

        self._lbl_temp   = tk.Label(foot, text="", font=("Segoe UI",7),
                                    bg=C["foot_bg"], fg=C["fg_dark"], anchor="w")
        self._lbl_temp.pack(side="left", padx=12)

        self._lbl_session = tk.Label(foot, text="", font=("Segoe UI",7),
                                     bg=C["foot_bg"], fg=C["fg_dim"], anchor="center")
        self._lbl_session.pack(side="left", expand=True)

        self._lbl_http   = tk.Label(foot, text="", font=("Segoe UI",7),
                                    bg=C["foot_bg"], fg=C["fg_dark"], anchor="e")
        self._lbl_http.pack(side="right", padx=12)

        # Grip redimensionnement
        self._grip = tk.Label(self.root, text="◢", font=("Segoe UI",9),
                              bg=C["foot_bg"], fg=C["border2"], cursor="size_nw_se")
        self._grip.place(relx=1.0, rely=1.0, anchor="se", y=-2)
        self._grip.bind("<ButtonPress-1>",   self._on_press)
        self._grip.bind("<B1-Motion>",       self._on_drag_ev)
        self._grip.bind("<ButtonRelease-1>", self._on_release)

    # ── Content ───────────────────────────────────────────────────────────────
    def _build_content(self):
        self._content_frame = tk.Frame(self.root, bg=C["bg"])
        self._content_frame.pack(fill="both", expand=True, side="top")
        if self._active_tab == "perf":
            self._build_perf_layout()
        else:
            self._settings_view = SettingsView(self._content_frame, self)

    def _build_perf_layout(self):
        pane = tk.Frame(self._content_frame, bg=C["bg"])
        pane.pack(fill="both", expand=True)

        # Sidebar
        sb_frame = tk.Frame(pane, bg=C["sidebar_bg"], width=200)
        sb_frame.pack(side="left", fill="y")
        sb_frame.pack_propagate(False)
        tk.Frame(pane, bg=C["border"], width=1).pack(side="left", fill="y")

        self._sidebar = Sidebar(sb_frame, self)

        # Panel droit
        right = tk.Frame(pane, bg=C["panel_bg"])
        right.pack(side="left", fill="both", expand=True)
        self._detail = DetailView(right, self)
        self._detail.show(self._selected)

    # ── Scroll global ─────────────────────────────────────────────────────────
    def _on_global_scroll(self, event):
        t = self._active_scroll_target
        if t:
            try:
                t.yview_scroll(-1*(event.delta//120), "units")
            except Exception:
                pass

    def _on_global_scroll4(self, event):
        t = self._active_scroll_target
        if t:
            try: t.yview_scroll(-1, "units")
            except Exception: pass

    def _on_global_scroll5(self, event):
        t = self._active_scroll_target
        if t:
            try: t.yview_scroll(1, "units")
            except Exception: pass

    def set_scroll_target(self, canvas: tk.Canvas | None):
        self._active_scroll_target = canvas

    # ── Drag / Resize ─────────────────────────────────────────────────────────
    def _in_grip(self, rx, ry) -> bool:
        ww = self.root.winfo_width(); wh = self.root.winfo_height()
        return rx >= ww - 22 and ry >= wh - 22

    def _on_motion(self, e):
        try:
            rx = e.x_root - self.root.winfo_rootx()
            ry = e.y_root - self.root.winfo_rooty()
            self.root.config(cursor="size_nw_se" if self._in_grip(rx,ry) else "")
        except Exception: pass

    def _on_press(self, e):
        rx = e.x_root - self.root.winfo_rootx()
        ry = e.y_root - self.root.winfo_rooty()
        if self._in_grip(rx, ry):
            self._rsz = True; self._drag = False
            self._rx, self._ry = e.x_root, e.y_root
            self._rw = self.root.winfo_width()
            self._rh = self.root.winfo_height()
            self._wx = self.root.winfo_x()
            self._wy = self.root.winfo_y()
        else:
            self._rsz = False; self._drag = True
            self._dx = e.x_root - self.root.winfo_x()
            self._dy = e.y_root - self.root.winfo_y()

    def _on_drag_ev(self, e):
        if self._rsz:
            nw = max(720, self._rw + (e.x_root - self._rx))
            nh = max(480, self._rh + (e.y_root - self._ry))
            self.cfg["win_w"] = nw; self.cfg["win_h"] = nh
            self.root.geometry(f"{nw}x{nh}+{self._wx}+{self._wy}")
        elif self._drag:
            nx = e.x_root - self._dx; ny = e.y_root - self._dy
            self.root.geometry(f"+{nx}+{ny}")
            self.cfg["pos_x"] = nx; self.cfg["pos_y"] = ny

    def _on_release(self, e):
        self._rsz = False; self._drag = False
        try: self.root.config(cursor="")
        except Exception: pass

    # ── Poll UI ───────────────────────────────────────────────────────────────
    def _poll(self):
        try:
            snap = self.store.snapshot()
            self._update_footer(snap)
            if self._active_tab == "perf":
                if self._sidebar: self._sidebar.update(snap)
                if self._detail:  self._detail.update(snap)
        except Exception:
            pass
        self.root.after(POLL_MS, self._poll)

    def _update_footer(self, snap):
        try:
            method = snap.get("cpu_temp_method") or _temp_state.get("method","unavailable")
            self._lbl_temp.configure(text=f"{T('temp_src',self.lang)}: {method}")
            up = snap.get("uptime_app", 0)
            self._lbl_session.configure(text=f"Session : {_fmt_dur(up)}")
            port = self.cfg.get("http_port", 5100)
            if self.cfg.get("http_enabled", True):
                self._lbl_http.configure(text=f"● HTTP :{port}", fg=C["ok"])
            else:
                self._lbl_http.configure(text="○ HTTP off", fg=C["fg_dark"])
        except Exception: pass

    # ── Sélection métrique ────────────────────────────────────────────────────
    def select_metric(self, key: str):
        self._selected = key
        self.cfg["selected_metric"] = key
        if self._sidebar: self._sidebar.set_selected(key)
        if self._detail:  self._detail.show(key)

    # ── Fermeture ─────────────────────────────────────────────────────────────
    def _on_close(self):
        action = self.cfg.get("close_action", "ask")
        if action == "quit":
            self._do_quit()
        elif action == "hide":
            self.hide()
        else:
            self._close_dialog()

    def _close_dialog(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("Fermer"); dlg.geometry("300x140")
        dlg.configure(bg=C["surface"])
        dlg.attributes("-topmost", True); dlg.resizable(False, False)
        dlg.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width()-300)//2
        y = self.root.winfo_y() + (self.root.winfo_height()-140)//2
        dlg.geometry(f"+{x}+{y}")
        tk.Label(dlg, text=T("close_q",self.lang),
                 font=("Segoe UI",10,"bold"),
                 bg=C["surface"], fg=C["fg_hi"]).pack(pady=(16,10))
        bf = tk.Frame(dlg, bg=C["surface"]); bf.pack()
        rem = tk.BooleanVar(value=False)
        def do_hide():
            if rem.get(): self.cfg["close_action"] = "hide"
            save_cfg(self.cfg); dlg.destroy(); self.hide()
        def do_quit():
            if rem.get(): self.cfg["close_action"] = "quit"
            save_cfg(self.cfg); dlg.destroy(); self._do_quit()
        tk.Button(bf, text=T("minimize",self.lang), command=do_hide,
                  bg=C["surface2"], fg=C["fg"], font=("Segoe UI",9),
                  relief="flat", padx=12, pady=6).pack(side="left", padx=6)
        tk.Button(bf, text=T("quit",self.lang), command=do_quit,
                  bg=C["acc_dim"], fg="#fff", font=("Segoe UI",9),
                  relief="flat", padx=12, pady=6).pack(side="left", padx=6)
        tk.Checkbutton(dlg, text=T("remember",self.lang), variable=rem,
                       bg=C["surface"], fg=C["fg_dim"],
                       selectcolor=C["surface2"],
                       font=("Segoe UI",8),
                       activebackground=C["surface"],
                       activeforeground=C["fg"]).pack(pady=8)

    def hide(self):  self.root.withdraw()
    def show(self):  self.root.deiconify(); self.root.lift()

    def _do_quit(self):
        self._alive = False
        self.store.stop()
        stop_http()
        save_cfg(self.cfg)
        try: self.root.destroy()
        except Exception: pass
        try: os._exit(0)
        except Exception: sys.exit(0)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  §9  UI — SIDEBAR  ━━━━━━━━━━━━━━

class Sidebar:
    """
    Sidebar style Gestionnaire des tâches.
    Widgets créés UNE SEULE FOIS.
    On appelle .configure() pour les mises à jour.
    """

    ITEMS = [
        # (key,         label,        color_key,   unit,   warn, hot,  dynamic)
        ("cpu",         "CPU",        "col_cpu",   "%",    70,   90,   False),
        ("ram",         "Mémoire",    "col_ram",   "%",    75,   90,   False),
        ("gpu",         "GPU",        "col_gpu",   "%",    70,   90,   False),
        ("gpu_temp",    "GPU TEMP",   "col_temp",  "°",    70,   85,   False),
        ("vram",        "VRAM",       "col_gpu",   "%",    75,   90,   False),
        ("net_dn",      "NET ↓",      "col_net",   "MB/s", None, None, True),
        ("net_up",      "NET ↑",      "col_net",   "MB/s", None, None, True),
        ("cpu_fan",     "CPU FAN",    "col_fan",   "RPM",  None, None, True),
        ("case_fans",   "CASE FANS",  "col_fan",   "RPM",  None, None, True),
        # Disques ajoutés dynamiquement
    ]

    def __init__(self, parent: tk.Frame, app: App):
        self._app    = app
        self._parent = parent
        self._items: dict[str, dict] = {}
        self._graph_items: dict[str, dict] = {}  # {key: {poly_id, line_id, dot_id}}
        self._disk_keys: list[str] = []

        # Header
        hdr = tk.Frame(parent, bg=C["sidebar_bg"])
        hdr.pack(fill="x", padx=10, pady=(8,4))
        tk.Label(hdr, text=T("resources",app.lang),
                 font=("Segoe UI",7,"bold"),
                 bg=C["sidebar_bg"], fg=C["fg_dark"]).pack(side="left")

        # Canvas scrollable
        self._canvas = tk.Canvas(parent, bg=C["sidebar_bg"],
                                 highlightthickness=0)
        self._canvas.pack(fill="both", expand=True)

        self._inner = tk.Frame(self._canvas, bg=C["sidebar_bg"])
        self._win_id = self._canvas.create_window(
            (0,0), window=self._inner, anchor="nw")

        self._canvas.bind("<Configure>", self._on_canvas_resize)
        self._inner.bind("<Configure>",  self._on_inner_resize)

        # Hover → scroll target
        self._canvas.bind("<Enter>", lambda e: app.set_scroll_target(self._canvas))
        self._canvas.bind("<Leave>", lambda e: app.set_scroll_target(None))
        self._inner.bind("<Enter>",  lambda e: app.set_scroll_target(self._canvas))
        self._inner.bind("<Leave>",  lambda e: app.set_scroll_target(None))
        self._canvas.bind("<MouseWheel>",
            lambda e: self._canvas.yview_scroll(-1*(e.delta//120),"units"))

        self._build_items()

    def _on_canvas_resize(self, e):
        self._canvas.itemconfig(self._win_id, width=e.width)
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_inner_resize(self, e):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _build_items(self):
        for (key, label, col_key, unit, warn, hot, dynamic) in self.ITEMS:
            color = C[col_key]
            self._add_item(key, label, color, unit, warn, hot)

    def _add_item(self, key: str, label: str, color: str,
                  unit: str, warn, hot, insert_before=None):
        sel = (key == self._app._selected)
        bg  = C["sel_bg"] if sel else C["sidebar_bg"]

        row = tk.Frame(self._inner, bg=bg, height=52, cursor="hand2")
        row.pack(fill="x", pady=1)
        row.pack_propagate(False)

        # Bande couleur
        strip = tk.Frame(row, bg=color if sel else C["border"], width=3)
        strip.pack(side="left", fill="y")

        # Mini graphique
        mc = tk.Canvas(row, bg=bg, width=56, height=36, highlightthickness=0)
        mc.pack(side="left", padx=(6,0), pady=8)

        # Labels
        info = tk.Frame(row, bg=bg)
        info.pack(side="left", fill="both", expand=True, padx=(6,4))
        lbl_name = tk.Label(info, text=label, font=("Segoe UI",8,"bold"),
                            bg=bg, fg=C["fg"] if sel else C["fg_dim"], anchor="w")
        lbl_name.pack(anchor="w")
        lbl_val  = tk.Label(info, text="—", font=("Segoe UI",8),
                             bg=bg, fg=color if sel else C["fg_dark"], anchor="w")
        lbl_val.pack(anchor="w")

        # Clic
        for w in (row, mc, info, lbl_name, lbl_val):
            w.bind("<Button-1>", lambda e, k=key: self._app.select_metric(k))
            w.bind("<Enter>", lambda e: self._app.set_scroll_target(self._canvas))
            w.bind("<Leave>", lambda e: None)

        # Hover (non-sélectionné)
        if not sel:
            def _enter(e, r=row, s=strip):
                r.configure(bg=C["hov_bg"])
                for c in r.winfo_children():
                    try: c.configure(bg=C["hov_bg"])
                    except Exception: pass
                    for cc in c.winfo_children():
                        try: cc.configure(bg=C["hov_bg"])
                        except Exception: pass
            def _leave(e, r=row, bg_=bg, s=strip, sc=C["border"]):
                r.configure(bg=bg_)
                for c in r.winfo_children():
                    try: c.configure(bg=bg_)
                    except Exception: pass
                    for cc in c.winfo_children():
                        try: cc.configure(bg=bg_)
                        except Exception: pass
            row.bind("<Enter>", _enter)
            row.bind("<Leave>", _leave)

        # Créer les éléments graphiques (réutilisés, pas recréés)
        poly_id = mc.create_polygon([0,36, 0,36], fill=color+"33", outline="", smooth=True)
        line_id = mc.create_line([0,18, 56,18],  fill=color, width=1, smooth=True)
        dot_id  = mc.create_oval(52,16,56,20,    fill=color, outline="")

        self._graph_items[key] = dict(poly=poly_id, line=line_id, dot=dot_id, canvas=mc)
        self._items[key] = dict(
            row=row, strip=strip, mc=mc, info=info,
            lbl_name=lbl_name, lbl_val=lbl_val,
            color=color, warn=warn, hot=hot, unit=unit,
        )

    def add_disk_item(self, drive: str):
        key   = f"disk_{drive}"
        if key in self._items:
            return
        label = f"Disque {drive}"
        color = C["col_disk"]
        self._add_item(key, label, color, "%", 80, 95)
        self._disk_keys.append(key)
        # historique
        if key not in self._app.store._hist:
            self._app.store._hist[key] = collections.deque([0.0]*HIST_LEN, maxlen=HIST_LEN)

    def set_selected(self, key: str):
        # Remettre l'ancien en non-sélectionné
        old = self._app._selected  # avant mise à jour
        if old in self._items:
            it = self._items[old]
            bg = C["sidebar_bg"]
            it["row"].configure(bg=bg)
            it["strip"].configure(bg=C["border"])
            for c in it["row"].winfo_children():
                try: c.configure(bg=bg)
                except Exception: pass
                for cc in c.winfo_children():
                    try: cc.configure(bg=bg)
                    except Exception: pass
            it["lbl_name"].configure(fg=C["fg_dim"])
            it["lbl_val"].configure(fg=C["fg_dark"])
        # Activer le nouveau
        if key in self._items:
            it = self._items[key]
            bg = C["sel_bg"]
            it["row"].configure(bg=bg)
            it["strip"].configure(bg=it["color"])
            for c in it["row"].winfo_children():
                try: c.configure(bg=bg)
                except Exception: pass
                for cc in c.winfo_children():
                    try: cc.configure(bg=bg)
                    except Exception: pass
            it["lbl_name"].configure(fg=C["fg"])
            it["lbl_val"].configure(fg=it["color"])

    def update(self, snap: dict):
        """Mise à jour textes + mini-graphes. Pas de recréation de widgets."""
        disks = snap.get("_disks", {})
        hist  = snap.get("_hist",  {})

        # Ajouter dynamiquement les disques nouveaux
        for drive in sorted(disks.keys()):
            self.add_disk_item(drive)

        # Valeurs numériques
        vals = {
            "cpu":       snap.get("cpu"),
            "ram":       snap.get("memory"),
            "gpu":       snap.get("gpu_usage"),
            "gpu_temp":  snap.get("gpu_temp"),
            "vram":      snap.get("vram_usage"),
            "net_dn":    snap.get("download_speed"),
            "net_up":    snap.get("upload_speed"),
            "cpu_fan":   snap.get("cpu_fan"),
            "case_fans": snap.get("case_fans"),
        }
        for drive, dd in disks.items():
            vals[f"disk_{drive}"] = dd.get("pct")

        for key, it in self._items.items():
            v = vals.get(key)
            # Texte valeur
            if v is None:
                txt = "N/A"
            elif key in ("cpu_fan","case_fans"):
                txt = f"{int(v)} RPM"
            elif key in ("net_dn","net_up"):
                txt = f"{v:.2f} MB/s"
            elif key in ("gpu_temp","cpu_temp"):
                txt = f"{v:.1f}°"
            else:
                txt = f"{v:.0f} %"
            it["lbl_val"].configure(text=txt)

            # Mini graphe (mise à jour coords, pas delete+redraw)
            h_list = hist.get(key, [])
            if h_list:
                self._update_mini_graph(key, h_list, it["color"])

    def _update_mini_graph(self, key: str, history: list, color: str):
        gi = self._graph_items.get(key)
        if not gi:
            return
        mc = gi["canvas"]
        try:
            cw = mc.winfo_width()
            ch = mc.winfo_height()
        except Exception:
            cw, ch = 56, 36
        if cw < 4:
            cw, ch = 56, 36
        n = len(history)
        if n < 2:
            return
        # Déterminer plafond
        m = next((x for x in self.ITEMS if x[0]==key), None)
        dynamic = m[6] if m else False
        top = max(max(history), 1.0) if dynamic else 100.0

        step = cw / max(n-1, 1)
        pts  = []
        for i, v in enumerate(history):
            x = i * step
            y = ch - 2 - (min(v, top)/top) * (ch-4)
            pts.append((max(0,x), max(1, min(ch-1, y))))

        # Polygon
        poly_pts = [(0, ch)] + pts + [(pts[-1][0], ch)]
        flat_poly = [c for p in poly_pts for c in p]
        mc.coords(gi["poly"], flat_poly)

        # Ligne
        flat_line = [c for p in pts for c in p]
        mc.coords(gi["line"], flat_line)

        # Dot
        lx, ly = pts[-1]
        mc.coords(gi["dot"], lx-2, ly-2, lx+2, ly+2)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  §10  VUES DÉTAIL  ━━━━━━━━━━━━━━━

class SmoothGraph:
    """
    Graphique Canvas anti-scintillement.
    Crée les éléments une fois, met à jour via canvas.coords().
    """
    def __init__(self, parent: tk.Widget, color: str, dynamic=False):
        self.color   = color
        self.dynamic = dynamic
        self._cw = self._ch = 0

        outer = tk.Frame(parent, bg=C["graph_bg"],
                         highlightbackground=C["border"], highlightthickness=1)
        outer.pack(fill="both", expand=True, padx=0, pady=0)

        # Header
        gh = tk.Frame(outer, bg=C["graph_bg"])
        gh.pack(fill="x", padx=8, pady=(4,0))
        tk.Label(gh, text="60s", font=("Consolas",7),
                 bg=C["graph_bg"], fg=C["fg_dark"]).pack(side="left")
        self._scale_lbl = tk.Label(gh, text="100%", font=("Consolas",7),
                                    bg=C["graph_bg"], fg=C["fg_dark"])
        self._scale_lbl.pack(side="right")

        self.canvas = tk.Canvas(outer, bg=C["graph_bg"],
                                highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=4, pady=(0,4))

        # Grilles
        self._grid_lines = []
        for pct in (25,50,75):
            lid = self.canvas.create_line(0,0,1,0, fill=C["grid"], dash=(2,8))
            self._grid_lines.append((pct, lid))

        # Données
        dummy = [0]*6
        self._poly_id = self.canvas.create_polygon(
            [0,1,0,1,0,1], fill=color+"28", outline="", smooth=True)
        self._line_id = self.canvas.create_line(
            [0,1,1,1],      fill=color, width=2, smooth=True,
            joinstyle="round", capstyle="round")
        self._dot_id  = self.canvas.create_oval(0,0,1,1, fill=color, outline="")
        self._ring_id = self.canvas.create_oval(0,0,1,1, fill="", outline=color, width=1)

        self.canvas.bind("<Configure>", self._on_resize)

    def _on_resize(self, e):
        self._cw = e.width
        self._ch = e.height
        # Redessiner les grilles
        for pct, lid in self._grid_lines:
            y = self._ch - (pct/100)*self._ch
            self.canvas.coords(lid, 0, y, self._cw, y)

    def update(self, history: list, top: float | None = None):
        cw, ch = self._cw, self._ch
        if cw < 4 or ch < 4:
            return
        n = len(history)
        if n < 2:
            return

        # Plafond
        if self.dynamic:
            raw_max = max(max(history), 1.0)
            for cap in (1,5,10,50,100,500,1000,5000,10000):
                if raw_max <= cap:
                    top = float(cap); break
            else:
                top = raw_max
            self._scale_lbl.configure(text=f"{int(top)}")
        else:
            top = top or 100.0
            self._scale_lbl.configure(text="100 %")

        pad  = 8
        dh   = ch - pad*2
        step = cw / max(n-1, 1)
        pts  = []
        for i, v in enumerate(history):
            x = i * step
            y = pad + dh - (min(v,top)/top)*dh
            pts.append((max(0,x), max(pad, min(ch-pad, y))))

        # Polygon
        poly = [(0, ch)] + pts + [(pts[-1][0], ch)]
        self.canvas.coords(self._poly_id, [c for p in poly for c in p])

        # Ligne
        self.canvas.coords(self._line_id, [c for p in pts for c in p])

        # Dot
        lx, ly = pts[-1]
        self.canvas.coords(self._dot_id,  lx-3, ly-3, lx+3, ly+3)
        self.canvas.coords(self._ring_id, lx-5, ly-5, lx+5, ly+5)

        # Grilles
        for pct, lid in self._grid_lines:
            y = ch - (pct/100)*ch
            self.canvas.coords(lid, 0, y, cw, y)


class DetailView:
    """
    Affiche la vue de détail d'une métrique.
    Reconstruite uniquement quand on change de métrique.
    """
    def __init__(self, parent: tk.Frame, app: App):
        self._parent = parent
        self._app    = app
        self._current_key: str | None = None
        self._frame: tk.Frame | None  = None
        self._graph: SmoothGraph | None = None
        self._updater = None  # callable de mise à jour spécifique

    def show(self, key: str):
        """Détruire la vue précédente et construire la nouvelle."""
        if self._frame:
            self._frame.destroy()
        self._frame   = tk.Frame(self._parent, bg=C["panel_bg"])
        self._frame.pack(fill="both", expand=True)
        self._current_key = key
        self._graph       = None
        self._updater     = None

        builders = {
            "cpu":      self._build_cpu,
            "ram":      self._build_ram,
            "gpu":      self._build_gpu,
            "gpu_temp": self._build_gpu,
            "vram":     self._build_vram,
            "net_dn":   self._build_net,
            "net_up":   self._build_net,
            "cpu_fan":  self._build_fan,
            "case_fans":self._build_fan,
        }

        if key in builders:
            builders[key]()
        elif key.startswith("disk_"):
            self._build_disk(key)
        else:
            self._build_generic(key)

    def update(self, snap: dict):
        if self._updater:
            try:
                self._updater(snap)
            except Exception:
                pass

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _header(self, title: str, subtitle: str = "") -> tk.Label:
        hdr = tk.Frame(self._frame, bg=C["panel_bg"])
        hdr.pack(fill="x", padx=20, pady=(16,4))
        tk.Label(hdr, text=title, font=("Segoe UI",18,"bold"),
                 bg=C["panel_bg"], fg=C["fg_hi"]).pack(side="left")
        self._subtitle_lbl = tk.Label(hdr, text=subtitle,
                                      font=("Segoe UI",9),
                                      bg=C["panel_bg"], fg=C["fg_dim"])
        self._subtitle_lbl.pack(side="right", pady=(10,0))
        return self._subtitle_lbl

    def _big_value(self, color: str):
        """Retourne (val_label, unit_label)."""
        vf = tk.Frame(self._frame, bg=C["panel_bg"])
        vf.pack(fill="x", padx=20, pady=(0,4))
        lv = tk.Label(vf, text="—", font=("Segoe UI",32,"bold"),
                      bg=C["panel_bg"], fg=color)
        lv.pack(side="left")
        lu = tk.Label(vf, text="", font=("Segoe UI",14),
                      bg=C["panel_bg"], fg=C["fg_dim"])
        lu.pack(side="left", padx=(4,0), pady=(12,0))
        return lv, lu

    def _graph_widget(self, color: str, dynamic=False) -> SmoothGraph:
        wrapper = tk.Frame(self._frame, bg=C["panel_bg"])
        wrapper.pack(fill="both", expand=True, padx=20, pady=(0,6))
        g = SmoothGraph(wrapper, color, dynamic=dynamic)
        self._graph = g
        return g

    def _stats_row(self, keys: list) -> dict:
        """Crée une grille de stats, retourne {key: label_widget}."""
        sf = tk.Frame(self._frame, bg=C["panel_bg"])
        sf.pack(fill="x", padx=20, pady=(0,12))
        lbls = {}
        cols = min(len(keys), 4)
        for i, (k, title) in enumerate(keys):
            col = i % cols; row = i // cols
            cell = tk.Frame(sf, bg=C["surface"])
            cell.grid(row=row, column=col, padx=(0,8), pady=2, sticky="ew")
            sf.columnconfigure(col, weight=1)
            tk.Label(cell, text=title.upper(), font=("Segoe UI",7,"bold"),
                     bg=C["surface"], fg=C["fg_dark"], anchor="w"
                     ).pack(anchor="w", padx=8, pady=(6,0))
            lv = tk.Label(cell, text="—", font=("Segoe UI",11,"bold"),
                          bg=C["surface"], fg=C["fg_hi"], anchor="w")
            lv.pack(anchor="w", padx=8, pady=(2,6))
            lbls[k] = lv
        return lbls

    # ── Vue CPU ───────────────────────────────────────────────────────────────
    def _build_cpu(self):
        lang = self._app.lang
        color = C["col_cpu"]
        self._header(T("cpu_name",lang))
        self._lv, self._lu = self._big_value(color)
        self._lu.configure(text="%")

        # Graphique principal
        gw = self._graph_widget(color)

        # Grille par cœur
        core_outer = tk.Frame(self._frame, bg=C["panel_bg"])
        core_outer.pack(fill="x", padx=20, pady=(0,6))

        # Canvas scrollable pour les cœurs
        self._core_canvas = tk.Canvas(core_outer, bg=C["panel_bg"],
                                       highlightthickness=0, height=120)
        self._core_canvas.pack(fill="x")
        self._core_inner = tk.Frame(self._core_canvas, bg=C["panel_bg"])
        cw_id = self._core_canvas.create_window((0,0), window=self._core_inner, anchor="nw")
        self._core_canvas.bind("<Configure>",
            lambda e: self._core_canvas.itemconfig(cw_id, width=e.width))
        self._core_inner.bind("<Configure>",
            lambda e: self._core_canvas.configure(
                scrollregion=self._core_canvas.bbox("all")))
        self._core_canvas.bind("<Enter>",
            lambda e: self._app.set_scroll_target(self._core_canvas))
        self._core_canvas.bind("<Leave>",
            lambda e: self._app.set_scroll_target(None))
        self._core_canvas.bind("<MouseWheel>",
            lambda e: self._core_canvas.yview_scroll(-1*(e.delta//120),"units"))

        self._core_lbls: list[tk.Label] = []
        self._core_bars: list[tk.Canvas] = []
        self._cores_built = 0

        # Stats
        self._stat = self._stats_row([
            ("util",   T("utilization",lang)),
            ("speed",  T("speed",lang)),
            ("cores",  T("cores",lang)),
            ("procs",  T("processes",lang)),
            ("threads",T("threads",lang)),
            ("uptime_app", T("uptime_app",lang)),
            ("uptime_sys", T("uptime_sys",lang)),
        ])

        def _update(snap: dict):
            v  = snap.get("cpu") or 0
            pc = snap.get("cpu_percore", [])
            hist = snap.get("_hist",{}).get("cpu",[])

            self._lv.configure(text=f"{v:.0f}",
                fg=_state_color(v,70,90))
            gw.update(hist)

            # Créer les barres de cœurs si nécessaire (une seule fois)
            if pc and len(pc) != self._cores_built:
                for w in self._core_inner.winfo_children():
                    w.destroy()
                self._core_lbls.clear()
                self._core_bars.clear()
                ncol = 4
                for i, pct in enumerate(pc):
                    row = i // ncol; col = i % ncol
                    cell = tk.Frame(self._core_inner, bg=C["panel_bg"])
                    cell.grid(row=row, column=col, padx=4, pady=2, sticky="ew")
                    self._core_inner.columnconfigure(col, weight=1)
                    tk.Label(cell, text=f"Core {i+1}",
                             font=("Segoe UI",7), bg=C["panel_bg"],
                             fg=C["fg_dim"], anchor="w").pack(anchor="w")
                    bar_frame = tk.Frame(cell, bg=C["surface"], height=6)
                    bar_frame.pack(fill="x", pady=(0,2))
                    bar_frame.pack_propagate(False)
                    bar = tk.Canvas(bar_frame, bg=C["surface"],
                                    highlightthickness=0, height=6)
                    bar.pack(fill="x")
                    lbl = tk.Label(cell, text=f"{pct:.0f}%",
                                   font=("Consolas",7), bg=C["panel_bg"],
                                   fg=C["col_cpu"], anchor="e")
                    lbl.pack(anchor="e")
                    # Barre de progression via canvas rect
                    bar_id = bar.create_rectangle(0,0,1,6,
                                fill=C["col_cpu"], outline="")
                    bar.bind("<Configure>",
                        lambda e, b=bar, bid=bar_id, v=pct:
                            b.coords(bid, 0, 0, max(1, e.width*v/100), e.height))
                    self._core_lbls.append(lbl)
                    self._core_bars.append((bar, bar_id))
                self._cores_built = len(pc)
                self._core_canvas.configure(
                    scrollregion=self._core_canvas.bbox("all"))

            # Mettre à jour les barres (pas de recréation)
            for i, pct in enumerate(pc):
                if i < len(self._core_lbls):
                    self._core_lbls[i].configure(text=f"{pct:.0f}%")
                if i < len(self._core_bars):
                    bar, bid = self._core_bars[i]
                    try:
                        bw = bar.winfo_width()
                        bar.coords(bid, 0, 0, max(1, bw*pct/100), 6)
                    except Exception:
                        pass

            sl = self._stat
            sl["util"].configure(text=f"{v:.0f} %")
            sl["speed"].configure(text=f"{snap.get('cpu_freq_cur',0):.2f} GHz")
            log = snap.get("cpu_logical",0)
            phy = snap.get("cpu_physical",0)
            sl["cores"].configure(text=f"{phy} {T('cores',lang)} / {log} {T('logical',lang)}")
            sl["procs"].configure(text=str(snap.get("process_count","—")))
            sl["threads"].configure(text=str(snap.get("thread_count","—")))
            sl["uptime_app"].configure(text=_fmt_dur(snap.get("uptime_app",0)))
            sl["uptime_sys"].configure(text=_fmt_dur(snap.get("uptime_sys",0)))

        self._updater = _update

    # ── Vue RAM ───────────────────────────────────────────────────────────────
    def _build_ram(self):
        lang  = self._app.lang
        color = C["col_ram"]
        self._header(T("ram_name",lang))
        self._lv, self._lu = self._big_value(color)
        gw = self._graph_widget(color)
        self._stat = self._stats_row([
            ("used",    T("used",lang)),
            ("avail",   T("available",lang)),
            ("total",   T("total",lang)),
            ("uptime",  T("uptime_app",lang)),
        ])

        def _update(snap: dict):
            v = snap.get("memory") or 0
            self._lv.configure(text=f"{v:.0f}", fg=_state_color(v,75,90))
            self._lu.configure(text="%")
            used  = snap.get("memory_used_gb",  0)
            total = snap.get("memory_total_gb", 0)
            self._subtitle_lbl.configure(text=f"{used:.1f} GB / {total:.1f} GB")
            gw.update(snap.get("_hist",{}).get("ram",[]))
            sl = self._stat
            sl["used"].configure( text=f"{used:.1f} GB")
            sl["avail"].configure(text=f"{snap.get('memory_avail_gb',0):.1f} GB")
            sl["total"].configure(text=f"{total:.1f} GB")
            sl["uptime"].configure(text=_fmt_dur(snap.get("uptime_app",0)))

        self._updater = _update

    # ── Vue GPU ───────────────────────────────────────────────────────────────
    def _build_gpu(self):
        lang  = self._app.lang
        color = C["col_gpu"]
        self._header(T("gpu_name",lang))
        self._lv, self._lu = self._big_value(color)
        gw = self._graph_widget(color)
        self._stat = self._stats_row([
            ("util",  T("utilization",lang)),
            ("temp",  "GPU TEMP"),
            ("vram_u","VRAM utilisée"),
            ("vram_t","VRAM totale"),
        ])
        key = self._current_key

        def _update(snap: dict):
            if key in ("gpu","gpu_temp"):
                hk = "gpu" if key=="gpu" else "gpu_temp"
                v  = snap.get("gpu_usage") if key=="gpu" else snap.get("gpu_temp")
                col = color if key=="gpu" else C["col_temp"]
                self._lv.configure(text=f"{v:.0f}" if v else "N/A", fg=col)
                self._lu.configure(text="%" if key=="gpu" else "°C")
                self._subtitle_lbl.configure(
                    text=snap.get("gpu_name",""))
                hist_key = hk
                gw.update(snap.get("_hist",{}).get(hist_key,[]))
            sl = self._stat
            sl["util"].configure( text=f"{snap.get('gpu_usage',0):.0f} %")
            sl["temp"].configure( text=f"{snap.get('gpu_temp',0):.1f} °C")
            sl["vram_u"].configure(text=f"{snap.get('vram_used_gb',0):.1f} GB")
            sl["vram_t"].configure(text=f"{snap.get('vram_total_gb',0):.1f} GB")

        self._updater = _update

    # ── Vue VRAM ──────────────────────────────────────────────────────────────
    def _build_vram(self):
        lang  = self._app.lang
        color = C["col_gpu"]
        self._header("VRAM")
        self._lv, self._lu = self._big_value(color)
        gw = self._graph_widget(color)
        self._stat = self._stats_row([
            ("util",  T("utilization",lang)),
            ("used",  T("used",lang)),
            ("total", T("total",lang)),
        ])

        def _update(snap: dict):
            v = snap.get("vram_usage") or 0
            vu = snap.get("vram_used_gb", 0)
            vt = snap.get("vram_total_gb", 0)
            self._lv.configure(text=f"{v:.0f}", fg=_state_color(v,75,90))
            self._lu.configure(text="%")
            self._subtitle_lbl.configure(text=f"{vu:.1f} GB / {vt:.1f} GB")
            gw.update(snap.get("_hist",{}).get("vram",[]))
            sl = self._stat
            sl["util"].configure(text=f"{v:.0f} %")
            sl["used"].configure( text=f"{vu:.1f} GB")
            sl["total"].configure(text=f"{vt:.1f} GB")

        self._updater = _update

    # ── Vue NET ───────────────────────────────────────────────────────────────
    def _build_net(self):
        lang  = self._app.lang
        color = C["col_net"]
        key   = self._current_key
        title = T("net_dn",lang) if key=="net_dn" else T("net_up",lang)
        self._header(title)
        self._lv, self._lu = self._big_value(color)
        self._lu.configure(text="MB/s")
        gw = self._graph_widget(color, dynamic=True)
        self._stat = self._stats_row([
            ("dl", T("dl",lang)),
            ("ul", T("ul",lang)),
        ])

        def _update(snap: dict):
            dn = snap.get("download_speed", 0)
            up = snap.get("upload_speed",   0)
            v  = dn if key=="net_dn" else up
            self._lv.configure(text=f"{v:.2f}")
            hk = "net_dn" if key=="net_dn" else "net_up"
            gw.update(snap.get("_hist",{}).get(hk,[]))
            self._stat["dl"].configure(text=f"{dn:.2f} MB/s")
            self._stat["ul"].configure(text=f"{up:.2f} MB/s")

        self._updater = _update

    # ── Vue FAN ───────────────────────────────────────────────────────────────
    def _build_fan(self):
        key   = self._current_key
        color = C["col_fan"]
        label = "CPU FAN" if key=="cpu_fan" else "CASE FANS"
        self._header(label)
        self._lv, self._lu = self._big_value(color)
        self._lu.configure(text="RPM")
        gw = self._graph_widget(color, dynamic=True)
        self._stat = self._stats_row([("val","RPM")])

        def _update(snap: dict):
            v = snap.get("cpu_fan" if key=="cpu_fan" else "case_fans")
            txt = f"{int(v)}" if v else "N/A"
            self._lv.configure(text=txt)
            hk = key
            gw.update(snap.get("_hist",{}).get(hk,[]))
            self._stat["val"].configure(text=f"{int(v)} RPM" if v else "N/A")

        self._updater = _update

    # ── Vue DISK ──────────────────────────────────────────────────────────────
    def _build_disk(self, key: str):
        lang  = self._app.lang
        drive = key.replace("disk_","")
        color = C["col_disk"]
        self._header(f"Disque {drive}")
        self._lv, self._lu = self._big_value(color)
        self._lu.configure(text="%")
        gw = self._graph_widget(color)
        self._stat = self._stats_row([
            ("used",  T("used",lang)),
            ("free",  T("available",lang)),
            ("total", T("total",lang)),
        ])

        def _update(snap: dict):
            disks = snap.get("_disks",{})
            dd = disks.get(drive)
            if not dd:
                self._lv.configure(text="N/A")
                return
            v = dd.get("pct",0)
            self._lv.configure(text=f"{v:.0f}", fg=_state_color(v,80,95))
            self._subtitle_lbl.configure(
                text=f"{dd.get('used',0):.1f} GB / {dd.get('total',0):.1f} GB")
            gw.update(snap.get("_hist",{}).get(key,[]))
            sl = self._stat
            sl["used"].configure( text=f"{dd.get('used',0):.1f} GB")
            sl["free"].configure( text=f"{dd.get('free',0):.1f} GB")
            sl["total"].configure(text=f"{dd.get('total',0):.1f} GB")

        self._updater = _update

    # ── Vue générique ─────────────────────────────────────────────────────────
    def _build_generic(self, key: str):
        self._header(key.upper())
        self._lv, self._lu = self._big_value(C["acc"])
        gw = self._graph_widget(C["acc"])

        def _update(snap: dict):
            pass

        self._updater = _update


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  §11  PARAMÈTRES  ━━━━━━━━━━━━━━━━

class SettingsView:
    """Panneau paramètres avec combobox correctement sombres."""

    def __init__(self, parent: tk.Frame, app: App):
        self._app = app
        self._frame = tk.Frame(parent, bg=C["bg"])
        self._frame.pack(fill="both", expand=True)
        self._build()

    def _build(self):
        app  = self._app
        cfg  = app.cfg
        lang = app.lang

        # Canvas + scrollbar
        outer = tk.Frame(self._frame, bg=C["bg"])
        outer.pack(fill="both", expand=True)
        cv = tk.Canvas(outer, bg=C["bg"], highlightthickness=0)
        sb = ttk.Scrollbar(outer, orient="vertical",
                           command=cv.yview, style="Vertical.TScrollbar")
        cv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        cv.pack(side="left",  fill="both", expand=True)

        content = tk.Frame(cv, bg=C["bg"])
        win_id  = cv.create_window((0,0), window=content, anchor="nw")

        def _resize(e):
            cv.itemconfig(win_id, width=e.width)
            cv.configure(scrollregion=cv.bbox("all"))
        cv.bind("<Configure>", _resize)
        content.bind("<Configure>",
            lambda e: cv.configure(scrollregion=cv.bbox("all")))

        # Scroll sur ce canvas quand on le survole
        cv.bind("<Enter>", lambda e: app.set_scroll_target(cv))
        cv.bind("<Leave>", lambda e: app.set_scroll_target(None))
        cv.bind("<MouseWheel>",
            lambda e: cv.yview_scroll(-1*(e.delta//120),"units"))

        P = dict(padx=24)

        def section(txt):
            fr = tk.Frame(content, bg=C["bg"])
            fr.pack(fill="x", pady=(20,4), **P)
            tk.Label(fr, text=txt, font=("Segoe UI",8,"bold"),
                     bg=C["bg"], fg=C["fg_dark"]).pack(side="left")
            tk.Frame(content, bg=C["border"], height=1).pack(fill="x", **P)

        def row(label, fn):
            r = tk.Frame(content, bg=C["surface2"],
                         highlightbackground=C["border"], highlightthickness=1)
            r.pack(fill="x", pady=1, **P)
            tk.Label(r, text=label, font=("Segoe UI",9),
                     bg=C["surface2"], fg=C["fg"],
                     width=34, anchor="w").pack(side="left", padx=14, pady=9)
            fn(r)
            return r

        def mk_check(r, var):
            def toggle():
                var.set(not var.get()); apply()
            b = tk.Label(r, text="", font=("Segoe UI Emoji",12),
                         bg=C["surface2"], fg=C["acc"],
                         cursor="hand2", padx=8)
            b.pack(side="left")
            def upd(*a):
                b.config(text="☑" if var.get() else "☐",
                         fg=C["acc"] if var.get() else C["fg_dim"])
            upd(); var.trace_add("write", upd)
            b.bind("<Button-1>", lambda e: toggle())

        def mk_combo(r, var, values, w=12):
            cb = ttk.Combobox(r, textvariable=var, values=values,
                              width=w, state="readonly", style="Dark.TCombobox")
            cb.pack(side="left", padx=8, pady=4)
            cb.bind("<<ComboboxSelected>>", lambda e: apply())

        def mk_scale(r, var, lo, hi, res):
            tk.Scale(r, from_=lo, to=hi, resolution=res,
                     orient="horizontal", variable=var,
                     bg=C["surface2"], fg=C["fg"],
                     troughcolor=C["fg_dark"],
                     highlightthickness=0,
                     activebackground=C["acc"],
                     length=160, sliderlength=14,
                     command=lambda v: apply()
                     ).pack(side="left", padx=8)

        def mk_entry(r, var, w=7):
            e = tk.Entry(r, textvariable=var, width=w,
                         bg=C["surface"], fg=C["fg"],
                         insertbackground=C["fg"],
                         relief="flat", bd=6,
                         highlightbackground=C["border"],
                         highlightthickness=1)
            e.pack(side="left", padx=8, pady=4)
            e.bind("<Return>",   lambda e: apply())
            e.bind("<FocusOut>", lambda e: apply())

        # Variables Tk
        v_boot   = tk.BooleanVar(value=is_startup())
        v_mini   = tk.BooleanVar(value=bool(cfg.get("start_minimized")))
        v_top    = tk.BooleanVar(value=bool(cfg.get("always_on_top",True)))
        v_opac   = tk.DoubleVar( value=float(cfg.get("opacity",0.97)))
        v_unit   = tk.StringVar( value=str(cfg.get("temp_unit","C")))
        v_lang   = tk.StringVar( value=str(cfg.get("language","fr")))
        v_http   = tk.BooleanVar(value=bool(cfg.get("http_enabled",True)))
        v_port   = tk.IntVar(    value=int( cfg.get("http_port",5100)))
        v_cpu    = tk.BooleanVar(value=bool(cfg.get("show_cpu",True)))
        v_ram    = tk.BooleanVar(value=bool(cfg.get("show_ram",True)))
        v_gpu    = tk.BooleanVar(value=bool(cfg.get("show_gpu",True)))
        v_gpu_t  = tk.BooleanVar(value=bool(cfg.get("show_gpu_temp",True)))
        v_vram   = tk.BooleanVar(value=bool(cfg.get("show_vram",True)))
        v_net    = tk.BooleanVar(value=bool(cfg.get("show_net",True)))
        v_cfan   = tk.BooleanVar(value=bool(cfg.get("show_cpu_fan",True)))
        v_cfans  = tk.BooleanVar(value=bool(cfg.get("show_case_fans",True)))
        v_disks  = tk.BooleanVar(value=bool(cfg.get("show_disks",True)))

        def apply(*_):
            try: port = int(v_port.get())
            except Exception: port = cfg.get("http_port",5100)
            old_http = cfg.get("http_enabled")
            old_port = cfg.get("http_port")
            cfg.update(dict(
                start_on_boot=bool(v_boot.get()),
                start_minimized=bool(v_mini.get()),
                always_on_top=bool(v_top.get()),
                opacity=round(float(v_opac.get()),2),
                temp_unit=str(v_unit.get()),
                language=str(v_lang.get()),
                http_enabled=bool(v_http.get()),
                http_port=port,
                show_cpu=bool(v_cpu.get()),
                show_ram=bool(v_ram.get()),
                show_gpu=bool(v_gpu.get()),
                show_gpu_temp=bool(v_gpu_t.get()),
                show_vram=bool(v_vram.get()),
                show_net=bool(v_net.get()),
                show_cpu_fan=bool(v_cfan.get()),
                show_case_fans=bool(v_cfans.get()),
                show_disks=bool(v_disks.get()),
            ))
            set_startup(cfg["start_on_boot"])
            app.root.attributes("-topmost", cfg["always_on_top"])
            app.root.attributes("-alpha",   cfg["opacity"])
            app.lang = cfg["language"]
            if cfg["http_enabled"] != old_http or cfg["http_port"] != old_port:
                if cfg["http_enabled"]:
                    start_http(cfg["http_port"], app.store)
                else:
                    stop_http()
            save_cfg(cfg)

        section(T("sec_gen",lang))
        row(T("boot",lang),      lambda r: mk_check(r, v_boot))
        row(T("minimized",lang), lambda r: mk_check(r, v_mini))
        row(T("ontop",lang),     lambda r: mk_check(r, v_top))

        section(T("sec_disp",lang))
        row(T("opacity",lang),   lambda r: mk_scale(r, v_opac, 0.3, 1.0, 0.05))
        row(T("unit",lang),      lambda r: mk_combo(r, v_unit, ["C","F"], 4))
        row(T("lang",lang),      lambda r: mk_combo(r, v_lang, ["fr","en"], 5))

        def close_widget(r):
            def reset():
                cfg["close_action"] = "ask"; save_cfg(cfg)
            tk.Button(r, text=T("close_reset",lang),
                      font=("Segoe UI",8), bg=C["acc"], fg="#fff",
                      cursor="hand2", relief="flat",
                      padx=12, pady=4, command=reset).pack(side="left", padx=8)
        row(T("close_lbl",lang), close_widget)

        section(T("sec_net",lang))
        row(T("http_on",lang), lambda r: mk_check(r, v_http))
        def port_row(r):
            mk_entry(r, v_port, 6)
            tk.Label(r, text="→ 127.0.0.1:<port>/performance",
                     font=("Segoe UI",8), bg=C["surface2"],
                     fg=C["fg_dark"]).pack(side="left", padx=4)
        row(T("http_port",lang), port_row)

        section(T("sec_met",lang))
        row(T("show_cpu",lang),       lambda r: mk_check(r, v_cpu))
        row(T("show_ram",lang),       lambda r: mk_check(r, v_ram))
        row(T("show_gpu",lang),       lambda r: mk_check(r, v_gpu))
        row(T("show_gpu_temp",lang),  lambda r: mk_check(r, v_gpu_t))
        row(T("show_vram",lang),      lambda r: mk_check(r, v_vram))
        row(T("show_net",lang),       lambda r: mk_check(r, v_net))
        row(T("show_cpu_fan",lang),   lambda r: mk_check(r, v_cfan))
        row(T("show_case_fans",lang), lambda r: mk_check(r, v_cfans))
        row(T("show_disks",lang),     lambda r: mk_check(r, v_disks))

        # CPU Temp source info
        section("CPU TEMP SOURCE")
        with _temp_lock:
            val    = _temp_state.get("value")
            method = _temp_state.get("method","—")
        info = tk.Frame(content, bg=C["surface"],
                        highlightbackground=C["border2"], highlightthickness=1)
        info.pack(fill="x", pady=4, **P)
        icon = "✓" if val else "✗"
        fg   = C["ok"] if val else C["hot"]
        txt  = f"{icon}  {val:.1f}°  via {method}" if val else f"{icon}  {method}"
        tk.Label(info, text=txt, font=("Consolas",9,"bold"),
                 bg=C["surface"], fg=fg, anchor="w").pack(
                     anchor="w", padx=14, pady=(8,4))
        tk.Label(info,
                 text="Priorité : psutil → LibreHardwareMonitor → OpenHardwareMonitor → CoreTemp",
                 font=("Consolas",7), bg=C["surface"],
                 fg=C["fg_dark"], anchor="w").pack(anchor="w", padx=14, pady=(0,4))
        if not val:
            tk.Label(info,
                     text="→ Lancez LibreHardwareMonitor en Administrateur.",
                     font=("Consolas",7), bg=C["surface"],
                     fg=C["warn"], anchor="w").pack(anchor="w", padx=14, pady=(0,8))
        else:
            tk.Frame(info, height=4, bg=C["surface"]).pack()

        tk.Frame(content, bg=C["bg"], height=20).pack()

        content.update_idletasks()
        cv.configure(scrollregion=cv.bbox("all"))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  §13  ENTRY POINT  ━━━━━━━━━━━━━━━

def _single_instance() -> bool:
    """Retourne True si déjà en cours."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 51997)); s.close(); return False
    except OSError:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(("127.0.0.1", 51997))
            s.sendall(b"SHOW"); s.close()
        except Exception: pass
        return True

def _listen_instance(app: App):
    try:
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("127.0.0.1", 51997)); srv.listen(1); srv.settimeout(1)
        while app._alive:
            try:
                conn, _ = srv.accept()
                data = conn.recv(64); conn.close()
                if data == b"SHOW":
                    app.root.after(0, app.show)
                elif data == b"QUIT":
                    app.root.after(0, app._do_quit)
                    srv.close(); return
            except socket.timeout: continue
            except Exception: break
    except Exception: pass


if __name__ == "__main__":
    if _single_instance():
        sys.exit(0)

    cfg   = load_cfg()
    store = DataStore(cfg)
    store.start()

    root  = tk.Tk()
    app   = App(root, cfg, store)

    # Listener instance unique
    threading.Thread(target=_listen_instance, args=(app,),
                     name="SCat-ipc", daemon=True).start()

    # HTTP
    if cfg.get("http_enabled", True):
        start_http(cfg.get("http_port", 5100), store)

    # Tray
    if _HAS_TRAY:
        tray = Icon(APP_NAME, _make_tray_icon(), APP_NAME, Menu(
            MenuItem("Afficher", lambda i,it: root.after(0, app.show)),
            MenuItem("Masquer",  lambda i,it: root.after(0, app.hide)),
            Menu.SEPARATOR,
            MenuItem("Quitter",  lambda i,it: (i.stop(), app._do_quit())),
        ))
        threading.Thread(target=tray.run, name="SCat-tray", daemon=True).start()

    if cfg.get("start_minimized"):
        root.after(1200, app.hide)

    root.mainloop()