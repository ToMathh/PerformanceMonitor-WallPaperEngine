"""
StrangeCat Monitor - UltraLowPerf data collector
=================================================
ThreadPoolExecutor-based metric collection for the headless HTTP server.
Only essential metrics are collected (CPU, RAM, GPU, CPU temp, network, disks).
No history / no graphs - all surplus is stripped to keep CPU usage minimal.
"""
import time
import threading
import os
from concurrent.futures import ThreadPoolExecutor
import psutil
import subprocess
import ctypes

_app_start_time = time.time()
_net_prev = dict(sent=0, recv=0, t=0.0)
_net_lock = threading.Lock()

_gpu_cache = dict(ts=0.0, data={
    "gpu_usage": 0.0, "gpu_temp": 0.0,
    "vram_used_gb": 0.0, "vram_total_gb": 0.0, "vram_usage": 0.0,
    "gpu_name": "GPU", "gpu_ok": False,
})
_gpu_lock = threading.Lock()

_disk_drives = []
_disk_lock = threading.Lock()

_cpu_name_cache = None


def get_cpu_name():
    """Return the marketing CPU name (e.g. 'AMD Ryzen 7 8700F'), cached.

    platform.processor() returns 'AMD64 Family...' on Windows, so we read the
    registry ProcessorNameString instead.
    """
    global _cpu_name_cache
    if _cpu_name_cache:
        return _cpu_name_cache
    name = None
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
        name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
        winreg.CloseKey(key)
        name = (name or "").strip()
    except Exception:
        name = None
    if not name:
        try:
            import platform
            name = platform.processor() or "CPU"
        except Exception:
            name = "CPU"
    _cpu_name_cache = name
    return _cpu_name_cache


def cached_disk_drives():
    """Return the last-detected disk drives without re-scanning (fast)."""
    with _disk_lock:
        return list(_disk_drives)


def detect_disk_drives():
    global _disk_drives
    with _disk_lock:
        try:
            drives = []
            for partition in psutil.disk_partitions(all=False):
                dev = partition.device
                if not dev or len(dev) < 2 or dev[1] != ":":
                    continue
                drive = dev[:2].upper()
                if drive not in drives:
                    drives.append(drive)
            _disk_drives = sorted(drives)
            return _disk_drives
        except Exception:
            return []


def collect_cpu():
    """Collect cheap CPU metrics (fast, runs frequently).

    Note: process/thread counting is intentionally NOT done here because
    iterating over every process is expensive (~seconds) and would stall the
    fast CPU sampling cadence. See collect_procs().
    """
    try:
        pct = psutil.cpu_percent(interval=0)
        percore = [round(p, 1) for p in psutil.cpu_percent(interval=0, percpu=True)]
        freq = psutil.cpu_freq()
        cur_ghz = round(freq.current / 1000, 2) if freq else 0.0
        max_ghz = round(freq.max / 1000, 2) if freq else 0.0
        logical = psutil.cpu_count(logical=True) or 0
        physical = psutil.cpu_count(logical=False) or 0
        uptime_sys = time.time() - psutil.boot_time()
        uptime_app = time.time() - _app_start_time
        return dict(
            cpu=round(pct, 1),
            cpu_percore=percore,
            cpu_freq_cur=cur_ghz,
            cpu_freq_max=max_ghz,
            cpu_logical=logical,
            cpu_physical=physical,
            cpu_name=get_cpu_name(),
            uptime_sys=uptime_sys,
            uptime_app=uptime_app,
        )
    except Exception:
        return dict(cpu=0.0, cpu_percore=[], cpu_freq_cur=0, cpu_freq_max=0,
                    cpu_logical=0, cpu_physical=0, uptime_sys=0, uptime_app=0)


def collect_ram():
    """Collect RAM metrics."""
    try:
        m = psutil.virtual_memory()
        return dict(
            memory=round(m.percent, 1),
            memory_used_gb=round(m.used / 1024**3, 1),
            memory_total_gb=round(m.total / 1024**3, 1),
            memory_avail_gb=round(m.available / 1024**3, 1),
        )
    except Exception:
        return dict(memory=0.0, memory_used_gb=0, memory_total_gb=0, memory_avail_gb=0)


def collect_gpu():
    """Collect GPU metrics with caching."""
    with _gpu_lock:
        now = time.time()
        if now - _gpu_cache["ts"] < 4.0 - 0.1:
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
    with _gpu_lock:
        _gpu_cache["data"] = data
        _gpu_cache["ts"] = time.time()
        return dict(data)


def collect_net(cfg=None):
    """Collect network metrics."""
    try:
        with _net_lock:
            now = psutil.net_io_counters()
            t_now = time.time()
            prev = _net_prev.copy()
            dt = max(t_now - prev["t"], 0.01)
            # Determine unit based on config (mb or kb)
            unit = (cfg or {}).get("net_unit", "mb")
            divisor = 1_048_576 if unit == "mb" else 1_024
            up = max(round((now.bytes_sent - prev["sent"]) / dt / divisor, 2), 0.0)
            dn = max(round((now.bytes_recv - prev["recv"]) / dt / divisor, 2), 0.0)
            _net_prev.update(sent=now.bytes_sent, recv=now.bytes_recv, t=t_now)
        return dict(upload_speed=up, download_speed=dn)
    except Exception:
        return dict(upload_speed=0.0, download_speed=0.0)


_disk_cache = {}        # drive -> last good metrics dict
_disk_poll_ts = {}      # drive -> last poll timestamp
_disk_slow = set()      # drives whose disk_usage() is slow (e.g. sleeping HDD)
_DISK_SLOW_SECS = 0.8   # a poll slower than this marks the drive "slow"
_DISK_SLOW_BACKOFF = 300.0   # slow drives are only re-polled every 5 min


def collect_disks():
    """Collect disk metrics with adaptive per-drive back-off.

    psutil.disk_usage() can block for several seconds on a sleeping/spinning-up
    HDD (and can hold the GIL during the wait, freezing the whole app). To keep
    the UI fluid we measure each drive's poll time: a drive that is slow is
    flagged and only re-polled occasionally, while its last-known values are
    served from cache in the meantime.
    """
    now = time.time()
    try:
        parts = psutil.disk_partitions(all=False)
    except Exception:
        return dict(_disk_cache)

    for part in parts:
        dev = part.device
        if not dev or len(dev) < 2 or dev[1] != ":":
            continue
        drive = dev[:2].upper()

        # Back off slow drives: serve cached data instead of waking them.
        if drive in _disk_slow and drive in _disk_cache:
            if (now - _disk_poll_ts.get(drive, 0)) < _DISK_SLOW_BACKOFF:
                continue

        t0 = time.perf_counter()
        try:
            du = psutil.disk_usage(drive)
            _disk_cache[drive] = dict(
                pct=round(du.percent, 1),
                used=round(du.used / 1024**3, 1),
                total=round(du.total / 1024**3, 1),
                free=round(du.free / 1024**3, 1),
            )
        except Exception:
            pass
        dt = time.perf_counter() - t0
        _disk_poll_ts[drive] = now
        if dt > _DISK_SLOW_SECS:
            _disk_slow.add(drive)
        elif dt < 0.3:
            _disk_slow.discard(drive)

    return dict(_disk_cache)


def collect_cpu_temp():
    """Collect CPU temperature from various sources."""
    val, method = None, "unavailable"
    
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            for k in ("coretemp", "k10temp", "zenpower", "cpu_thermal", "acpitz", "nct6798"):
                if k in temps:
                    vs = [e.current for e in temps[k] if 0 < e.current < 130]
                    if vs:
                        val, method = round(sum(vs)/len(vs), 1), f"psutil/{k}"
                        break
            if val is None:
                for name, sensors in temps.items():
                    vs = [e.current for e in sensors if 0 < e.current < 130]
                    if vs:
                        val, method = round(sum(vs)/len(vs), 1), f"psutil/{name}"
                        break
    except Exception:
        pass
    
    try:
        import wmi
        for ns in ("root/LibreHardwareMonitor", "root/OpenHardwareMonitor"):
            try:
                vs = [s.Value for s in wmi.WMI(namespace=ns).Sensor()
                      if s.SensorType == "Temperature"
                      and any(k in s.Name.lower() for k in
                              ("cpu", "core", "package", "tdie", "tccd"))
                      and s.Value and 0 < s.Value < 130]
                if vs:
                    val = round(sum(vs)/len(vs), 1)
                    method = ns.split("/")[1]
                    break
            except Exception:
                pass
    except Exception:
        pass
    
    try:
        MAX = 128
        class _CT(ctypes.Structure):
            _fields_ = [
                ("uiLoad", ctypes.c_uint * MAX),
                ("uiTjMax", ctypes.c_uint * MAX),
                ("uiCoreCnt", ctypes.c_uint),
                ("uiCPUCnt", ctypes.c_uint),
                ("fTemp", ctypes.c_float * MAX),
                ("fVID", ctypes.c_float),
                ("fCPUSpeed", ctypes.c_float),
                ("fFSBSpeed", ctypes.c_float),
                ("fMultiplier", ctypes.c_float),
                ("sCPUName", ctypes.c_char * 100),
                ("ucFahrenheit", ctypes.c_ubyte),
                ("ucDeltaToTjMax", ctypes.c_ubyte),
            ]
        hnd = ctypes.windll.kernel32.OpenFileMappingW(
            0x0004, False, "CoreTempMappingObject")
        if hnd:
            ptr = ctypes.windll.kernel32.MapViewOfFile(hnd, 0x0004, 0, 0, 0)
            if ptr:
                raw = ctypes.string_at(ptr, ctypes.sizeof(_CT))
                ctypes.windll.kernel32.UnmapViewOfFile(ptr)
                ctypes.windll.kernel32.CloseHandle(hnd)
                d = _CT.from_buffer(
                    ctypes.create_string_buffer(raw, ctypes.sizeof(_CT)))
                n = max(0, min(int(d.uiCoreCnt), MAX))
                vs = [d.fTemp[i] for i in range(n) if 0 < d.fTemp[i] < 130]
                if vs:
                    val, method = round(sum(vs)/len(vs), 1), "CoreTemp"
            else:
                ctypes.windll.kernel32.CloseHandle(hnd)
    except Exception:
        pass
    
    return dict(cpu_temp=val, cpu_temp_method=method)


class DataCollector:
    """Headless metric collector for the UltraLowPerf HTTP server.

    Intentional restrictions vs. the full Beta collector:
    - Single worker thread (max_workers=1) – no parallelism needed.
    - No history deques – no graphs, so nothing to store.
    - No process / fan collection (disabled via RATE_PROC / RATE_FAN = 999 s).
    - Main loop sleeps 1 s between dispatch rounds (lower than any metric rate).
    """

    def __init__(self, cfg):
        self._cfg     = cfg
        self._lock    = threading.Lock()
        self._data    = {}   # latest metric values
        self._disks   = {}   # latest disk metrics keyed by drive letter
        self._last    = {}   # last-dispatch timestamps per metric key
        self._running = False

        # One worker thread is enough: metrics are collected sequentially
        # anyway because only one can be in-flight at a time.
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="SCat")
        self._thread = None

        # Prime the network counter so the first delta is meaningful.
        collect_net()
        time.sleep(0.05)

        # Build the initial drive list so collect_disks() has something to work with.
        detect_disk_drives()
    
    def start(self):
        """Spawn the background collection thread."""
        self._running = True
        self._thread  = threading.Thread(
            target=self._loop, name="SCat-collect", daemon=True)
        self._thread.start()

    def stop(self):
        """Request collection to stop and clean up the thread pool."""
        self._running = False
        self._pool.shutdown(wait=False, cancel_futures=True)

    def update_cfg(self, cfg):
        """Update the collector's configuration at runtime."""
        with self._lock:
            self._cfg = cfg
    
    def _loop(self):
        """Background collection loop (runs in a daemon thread).

        Each metric is submitted to the single worker thread pool when its
        configured rate interval has elapsed.  Results are stored via a
        done-callback so the loop is never blocked by slow collectors (e.g.
        nvidia-smi, WMI temperature queries).
        """
        from config import rate_for

        inflight = set()  # keys whose futures are still pending

        def dispatch(key, rate, fn):
            """Submit fn() if the metric interval has elapsed and no prior call is pending."""
            if not self._running:
                return
            now = time.time()
            if key in inflight:
                return  # still waiting for the previous result
            if now - self._last.get(key, 0) < rate:
                return  # not due yet
            self._last[key] = now
            inflight.add(key)
            try:
                fut = self._pool.submit(fn)
            except RuntimeError:
                inflight.discard(key)  # pool was shut down
                return
            fut.add_done_callback(lambda f, k=key: self._on_result(k, f, inflight))

        while self._running:
            cfg = self._cfg
            # Essential metrics only - proc/fans have rate=999 s so they never fire
            dispatch("cpu",  rate_for("cpu",  cfg), collect_cpu)
            dispatch("ram",  rate_for("ram",  cfg), collect_ram)
            dispatch("net",  rate_for("net",  cfg), lambda: collect_net(cfg))
            dispatch("gpu",  rate_for("gpu",  cfg), collect_gpu)
            dispatch("temp", rate_for("temp", cfg), collect_cpu_temp)
            dispatch("disk", rate_for("disk", cfg), collect_disks)
            time.sleep(1.0)  # tick interval - must be <= smallest RATE_* value

    def _on_result(self, key, fut, inflight):
        """Called by the thread pool when a metric future completes."""
        try:
            result = fut.result()
            with self._lock:
                if key == "disk":
                    self._disks = result or {}
                elif isinstance(result, dict):
                    self._data.update(result)
            # No history updates: this build has no graphs
        except Exception:
            pass
        finally:
            inflight.discard(key)
    
    def snapshot(self):
        """Return a consistent copy of the latest collected data."""
        with self._lock:
            d              = dict(self._data)
            d["_disks"]    = dict(self._disks)
            d["_hist"]     = {}  # no history in headless build
            d["uptime_app"]= time.time() - _app_start_time
        return d
    
    def http_payload(self):
        """Build the JSON payload served on the /performance endpoint."""
        # Format mirrors the full Beta app so any consumer works with both.
        with self._lock:
            d = self._data
            di = self._disks
            ps = {}
            ps["cpu"] = d.get("cpu", 0)
            ps["cpu_percore"] = d.get("cpu_percore", [])
            ps["memory"] = d.get("memory", 0)
            used = d.get("memory_used_gb", 0)
            total = d.get("memory_total_gb", 0)
            ps["memory_gb"] = f"{used:.1f} GB/{total:.1f} GB"
            ps["gpu_usage"] = d.get("gpu_usage", 0)
            ps["vram_usage"] = d.get("vram_usage", 0)
            vu = d.get("vram_used_gb", 0)
            vt = d.get("vram_total_gb", 0)
            ps["vram_gb"] = f"{vu:.1f} GB/{vt:.1f} GB"
            ps["gpu_temp"] = d.get("gpu_temp", 0)
            ps["cpu_temp"] = d.get("cpu_temp", 0)
            ps["upload_speed"] = d.get("upload_speed", 0)
            ps["download_speed"] = d.get("download_speed", 0)
            ps["timestamp"] = d.get("timestamp", time.time())
            for drive, dd in di.items():
                k = drive.lower().replace(":", "") + "_disk"
                ps[k] = f"{dd.get('used', 0):.1f} GB/{dd.get('total', 0):.1f} GB"
        return dict(timestamp=time.time(), psutil=ps, hwinfo=[])
