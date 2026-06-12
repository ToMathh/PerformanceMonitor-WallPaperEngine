"""
Configuration management for StrangeCat Monitor - UltraLowPerf edition.
Headless server only: no UI, no translations, no color palette.
"""
import os
import json
import sys

# ── Application identity ──────────────────────────────────────────────────────
APP_NAME = "StrangeCat Monitor"
APP_VER  = "6.0"

# Config file is stored in %APPDATA%\StrangeCatV6\config.json.
# This is the same path used by the full Beta app so settings are shared.
APPDATA  = os.path.join(os.getenv("APPDATA", os.path.expanduser("~")), "StrangeCatV6")
CFG_FILE = os.path.join(APPDATA, "config.json")
EXE_PATH = sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__)
STARTUP_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

# ── Collection cadence ────────────────────────────────────────────────────────
# Available modes for the "fast" metrics (CPU / RAM / GPU / NET).
REFRESH_MODES = {
    "realtime": 1.0,   # 1 s  – default for the full Beta app
    "low":      3.0,   # 3 s  – default for UltraLowPerf
}

# Per-metric collection intervals (seconds).
# Fans and process counting are intentionally disabled (999 s ≈ never).
RATE_CPU  = 2.0
RATE_RAM  = 2.0
RATE_NET  = 2.0
RATE_GPU  = 5.0
RATE_TEMP = 10.0
RATE_DISK = 60.0
RATE_PROC = 999.0   # disabled – process enumeration is expensive
RATE_FAN  = 999.0   # disabled – fans are not part of the minimal payload


def rate_for(key, cfg):
    """Return the collection interval (seconds) for the given metric key.

    Fast metrics (cpu / ram / net / gpu) scale with the configured refresh
    mode.  Temperature and disk use fixed slower intervals to keep CPU usage
    minimal.  Proc and fans are effectively disabled.
    """
    cfg  = cfg or {}
    mode = cfg.get("refresh_mode", "low")
    fast = REFRESH_MODES.get(mode, RATE_CPU)
    if key in ("cpu", "ram", "net", "gpu", "lhm"):
        return fast
    if key == "temp":
        return RATE_TEMP
    if key == "disk":
        return float(cfg.get("disk_interval", RATE_DISK))
    # proc / fans / anything else → effectively disabled
    return 999.0


# ── Persistent defaults ───────────────────────────────────────────────────────
# Only the keys that the headless server actually reads/writes.
DEFAULTS = {
    "http_enabled":  True,
    "http_port":     5100,
    "refresh_mode":  "low",   # Low (3 s) is the UltraLowPerf default
    "net_unit":      "kb",    # KB/s for upload / download
    "disk_interval": 60.0,
}


# ── Config I/O ────────────────────────────────────────────────────────────────

def load_cfg():
    """Load config from disk, merging with DEFAULTS for missing keys."""
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
    """Persist config dict to disk (silently swallows errors)."""
    try:
        os.makedirs(APPDATA, exist_ok=True)
        with open(CFG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass


# ── Windows startup (registry HKCU\Run) ───────────────────────────────────────

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
