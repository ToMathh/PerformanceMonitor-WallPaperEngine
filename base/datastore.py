"""
DataStore - Thread-safe cache for metrics data.
Uses ThreadPoolExecutor for parallel data collection.
"""
import time
import threading
import collections
import os
from concurrent.futures import ThreadPoolExecutor

from config import HIST_LEN, RATE_CPU, RATE_RAM, RATE_NET, RATE_GPU, RATE_TEMP, RATE_FAN, RATE_DISK
from collector import (
    collect_cpu, collect_ram, collect_gpu, collect_net,
    collect_cpu_temp, collect_fans, collect_disks
)

_APP_START = time.time()


class DataStore:
    """
    Thread-safe central cache.
    ThreadPoolExecutor collects in parallel.
    Exposes snapshot() for UI and http_payload() for HTTP.
    """
    def __init__(self, cfg: dict):
        self._cfg = cfg
        self._lock = threading.Lock()
        self._data: dict = {}
        self._disks: dict = {}
        self._hist: dict[str, collections.deque] = {}
        self._last: dict[str, float] = {}
        self._running = False
        self._pool = ThreadPoolExecutor(
            max_workers=min(os.cpu_count() or 4, 8),
            thread_name_prefix="SCat",
        )
        self._thread: threading.Thread | None = None
        # Initialize histories
        for key in ("cpu", "ram", "gpu", "gpu_temp", "vram", "net_dn", "net_up",
                    "cpu_temp", "cpu_fan", "case_fans"):
            self._hist[key] = collections.deque([0.0] * HIST_LEN, maxlen=HIST_LEN)

    # Start / stop
    def start(self):
        self._running = True
        # Initialize network (first measurement without delta)
        collect_net()
        time.sleep(0.05)
        self._thread = threading.Thread(
            target=self._loop, name="SCat-collect", daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._pool.shutdown(wait=False, cancel_futures=True)

    # Collection loop
    def _loop(self):
        while self._running:
            now = time.time()
            futs = {}

            def maybe(key, rate, fn):
                if now - self._last.get(key, 0) >= rate:
                    self._last[key] = now
                    futs[self._pool.submit(fn)] = key

            maybe("cpu", RATE_CPU, collect_cpu)
            maybe("ram", RATE_RAM, collect_ram)
            maybe("net", RATE_NET, collect_net)
            maybe("gpu", RATE_GPU, collect_gpu)
            maybe("temp", RATE_TEMP, collect_cpu_temp)
            maybe("fans", RATE_FAN, collect_fans)
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
        return collect_disks()

    def _update_hist(self, data: dict, key: str):
        pushes = []
        if key == "cpu":
            pushes = [("cpu", data.get("cpu", 0))]
        elif key == "ram":
            pushes = [("ram", data.get("memory", 0))]
        elif key == "gpu":
            pushes = [
                ("gpu", data.get("gpu_usage", 0)),
                ("gpu_temp", data.get("gpu_temp", 0)),
                ("vram", data.get("vram_usage", 0)),
            ]
        elif key == "net":
            pushes = [
                ("net_dn", data.get("download_speed", 0)),
                ("net_up", data.get("upload_speed", 0)),
            ]
        elif key == "temp":
            pushes = [("cpu_temp", data.get("cpu_temp", 0) or 0)]
        elif key == "fans":
            pushes = [
                ("cpu_fan", data.get("cpu_fan", 0) or 0),
                ("case_fans", data.get("case_fans", 0) or 0),
            ]
        with self._lock:
            for hkey, hval in pushes:
                if hkey in self._hist:
                    self._hist[hkey].append(float(hval))
            # Disks: history per drive
            for drive, ddata in self._disks.items():
                hk = f"disk_{drive}"
                if hk not in self._hist:
                    self._hist[hk] = collections.deque([0.0] * HIST_LEN, maxlen=HIST_LEN)
                self._hist[hk].append(float(ddata.get("pct", 0)))

    # Reading
    def snapshot(self) -> dict:
        """Return a snapshot of current data for UI."""
        with self._lock:
            d = dict(self._data)
            d["_disks"] = dict(self._disks)
            d["_hist"] = {k: list(v) for k, v in self._hist.items()}
            d["uptime_app"] = time.time() - _APP_START
        return d

    def http_payload(self) -> dict:
        """Return data in exact HTTP server format."""
        with self._lock:
            d = self._data
            di = self._disks
            ps: dict = {}
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
            ps["upload_speed"] = d.get("upload_speed", 0)
            ps["download_speed"] = d.get("download_speed", 0)
            ps["timestamp"] = time.time()
            for drive, dd in di.items():
                k = drive.lower().replace(":", "") + "_disk"
                ps[k] = f"{dd.get('used', 0):.1f} GB/{dd.get('total', 0):.1f} GB"
        return dict(timestamp=time.time(), psutil=ps, hwinfo=[])
