"""
Metric definitions and helper functions.
"""
from config import C, T


def build_metrics(cfg, disk_drives=None):
    """Build the list of metrics based on configuration."""
    lang = cfg.get("language", "fr")
    metrics = []
    
    if cfg.get("show_cpu", True):
        metrics.append({
            "key": "cpu",
            "label": T("cpu_name", lang),
            "color": C["col_cpu"],
            "unit": "%",
            "max": 100,
            "warn": 70,
            "hot": 90,
        })
    
    if cfg.get("show_ram", True):
        metrics.append({
            "key": "ram",
            "label": T("ram_name", lang),
            "color": C["col_ram"],
            "unit": "%",
            "max": 100,
            "warn": 75,
            "hot": 90,
        })
    
    if cfg.get("show_gpu", True):
        metrics.append({
            "key": "gpu",
            "label": T("gpu_name", lang),
            "color": C["col_gpu"],
            "unit": "%",
            "max": 100,
            "warn": 70,
            "hot": 90,
        })
    
    if cfg.get("show_gpu_temp", True):
        u = "°F" if cfg.get("temp_unit") == "F" else "°C"
        metrics.append({
            "key": "gpu_temp",
            "label": "GPU TEMP",
            "color": C["col_temp"],
            "unit": u,
            "max": 100,
            "warn": 70,
            "hot": 85,
            "is_temp": True,
        })
    
    if cfg.get("show_vram", True):
        metrics.append({
            "key": "vram",
            "label": "VRAM",
            "color": C["col_gpu"],
            "unit": "%",
            "max": 100,
            "warn": 75,
            "hot": 90,
        })
    
    if cfg.get("show_net", True):
        metrics.append({
            "key": "net_dn",
            "label": T("net_dn", lang),
            "color": C["col_net"],
            "unit": "MB/s",
            "max": None,
            "warn": None,
            "hot": None,
            "dynamic": True,
        })
        metrics.append({
            "key": "net_up",
            "label": T("net_up", lang),
            "color": C["col_net"],
            "unit": "MB/s",
            "max": None,
            "warn": None,
            "hot": None,
            "dynamic": True,
        })
    
    if cfg.get("show_cpu_fan", True):
        metrics.append({
            "key": "cpu_fan",
            "label": "CPU Fan",
            "color": C["col_fan"],
            "unit": "RPM",
            "max": None,
            "warn": None,
            "hot": None,
            "dynamic": True,
        })
    
    if cfg.get("show_case_fans", True):
        metrics.append({
            "key": "case_fans",
            "label": "Case Fans",
            "color": C["col_fan"],
            "unit": "RPM",
            "max": None,
            "warn": None,
            "hot": None,
            "dynamic": True,
        })
    
    if cfg.get("show_disks", True) and disk_drives:
        for drive in disk_drives:
            metrics.append({
                "key": f"disk_{drive}",
                "label": f"Disque {drive}",
                "color": C["col_disk"],
                "unit": "%",
                "max": 100,
                "warn": 80,
                "hot": 90,
            })
    
    return metrics


def extract_val(key, data):
    """Extract value from data dict based on metric key."""
    if key == "cpu":
        return data.get("cpu")
    elif key == "ram":
        return data.get("memory")
    elif key == "gpu":
        return data.get("gpu_usage")
    elif key == "gpu_temp":
        return data.get("gpu_temp")
    elif key == "vram":
        return data.get("vram_usage")
    elif key == "net_dn":
        return data.get("download_speed")
    elif key == "net_up":
        return data.get("upload_speed")
    elif key == "cpu_fan":
        return data.get("cpu_fan")
    elif key == "case_fans":
        return data.get("case_fans")
    elif key.startswith("disk_"):
        drive = key.replace("disk_", "")
        disks = data.get("_disks", {})
        if drive in disks:
            return disks[drive].get("pct")
    return None


def fmt_val(key, val):
    """Format value for display."""
    if val is None:
        return "—"
    
    if key in ("cpu_fan", "case_fans"):
        return f"{int(val)} RPM"
    elif key in ("net_dn", "net_up"):
        return f"{val:.2f} MB/s"
    elif key in ("gpu_temp",):
        return f"{val:.1f}°"
    elif isinstance(val, float) and val != int(val):
        return f"{val:.1f}%"
    else:
        return f"{int(val)}%"


def status_color(val, warn, hot):
    """Get color based on value thresholds."""
    if warn is None or val is None:
        return C["ok"]
    if val >= hot:
        return C["hot"]
    if val >= warn:
        return C["warn"]
    return C["ok"]


def fmt_duration(seconds):
    """Format duration in seconds to HH:MM:SS."""
    if seconds is None:
        return "—"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"
