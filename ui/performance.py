"""
Performance views - detailed views for each metric type.
CPU, Memory, GPU, Disks, Network.
"""
import tkinter as tk
import sys
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "base"))

from config import C, T
from ui.graphs import MainGraph, CoreBarGraph
from ui.widgets import BigValueLabel, UnitLabel, SubtitleLabel, StatLabel, StatBox


class PerformanceView(tk.Frame):
    """Base class for performance views."""
    
    def __init__(self, parent, metric_meta, **kwargs):
        self.metric_meta = metric_meta
        super().__init__(parent, bg=C["panel_bg"], **kwargs)
        self.pack(fill="both", expand=True)
        
        # Order matters for the packer: fixed-height sections (header, value,
        # stats) are packed before the expanding graph so they always keep
        # their space and stay visible, while the graph flexes to fill the
        # rest. This keeps every section readable at any window size.
        self._build_header()
        self._build_value_display()
        self._build_stats()
        self._build_graph()
    
    def _build_header(self):
        """Build header with metric name."""
        self.header = tk.Frame(self, bg=C["panel_bg"])
        self.header.pack(fill="x", padx=20, pady=(16, 8))
        
        tk.Label(
            self.header, text=self.metric_meta["label"].upper(),
            font=("Segoe UI", 18, "bold"),
            bg=C["panel_bg"], fg=C["fg_hi"]
        ).pack(side="left")
        
        self.subtitle = SubtitleLabel(self.header)
        self.subtitle.pack(side="right", pady=(8, 0))
    
    def _build_value_display(self):
        """Build main value display."""
        self.value_frame = tk.Frame(self, bg=C["panel_bg"])
        self.value_frame.pack(fill="x", padx=20, pady=(0, 4))
        
        self.big_value = BigValueLabel(self.value_frame)
        self.big_value.pack(side="left")
        
        self.unit = UnitLabel(self.value_frame, text=self.metric_meta["unit"])
        self.unit.pack(side="left", padx=(4, 0), pady=(10, 0))
    
    def _build_graph(self):
        """Build main graph."""
        self.graph_container = tk.Frame(
            self, bg=C["graph_bg"],
            highlightbackground=C["border"], highlightthickness=1
        )
        self.graph_container.pack(fill="both", expand=True, padx=20, pady=(4, 8))
        
        self.graph_header = tk.Frame(self.graph_container, bg=C["graph_bg"])
        self.graph_header.pack(fill="x", padx=8, pady=(6, 2))
        
        tk.Label(
            self.graph_header, text="100 %",
            font=("Consolas", 7),
            bg=C["graph_bg"], fg=C["dim"]
        ).pack(side="right")
        
        tk.Label(
            self.graph_header, text="60 secondes",
            font=("Segoe UI", 7),
            bg=C["graph_bg"], fg=C["dim"]
        ).pack(side="left")
        
        self.main_graph = MainGraph(
            self.graph_container,
            self.metric_meta["key"],
            self.metric_meta["color"]
        )
        self.main_graph.pack(fill="both", expand=True, padx=4, pady=(0, 6))
    
    def _build_stats(self):
        """Build statistics section.

        Pinned to the bottom so the stat cards stay visible at any window size;
        the graph above flexes to fill the remaining space.
        """
        self.stats_frame = tk.Frame(self, bg=C["panel_bg"])
        self.stats_frame.pack(side="bottom", fill="x", padx=20, pady=(0, 12))
        self.stat_labels = {}
        self.stat_boxes = {}

    def _build_stat_grid(self, specs, cols=4):
        """Create a grid of StatBox cards. specs = [(key, title), ...]."""
        grid = tk.Frame(self.stats_frame, bg=C["panel_bg"])
        grid.pack(fill="x", pady=(8, 4))
        for c in range(cols):
            grid.columnconfigure(c, weight=1, uniform="stat")
        for i, (key, title) in enumerate(specs):
            r, cc = divmod(i, cols)
            box = StatBox(grid, title)
            box.grid(row=r, column=cc,
                     padx=(0 if cc == 0 else 6, 0), pady=3, sticky="ew")
            self.stat_boxes[key] = box
        return self.stat_boxes
    
    def update(self, data, history):
        """Update view with new data."""
        value = self._extract_value(data)
        
        # Update big value
        if value is None:
            self.big_value.configure(text="N/A", fg=C["dim"])
        else:
            self.big_value.configure(text=self._format_big_value(value))
            self._update_color(value)
        
        # Update subtitle
        self._update_subtitle(data)
        
        # Update graph: history may be the full hist dict or a list
        key = self.metric_meta["key"]
        hist = history.get(key, []) if isinstance(history, dict) else history
        self.main_graph.update(hist, self.metric_meta)
        
        # Update stats
        self._update_stats(data)
    
    def _extract_value(self, data):
        """Extract value from data."""
        key = self.metric_meta["key"]
        if key == "cpu":
            return data.get("cpu")
        elif key == "cpu_temp":
            return data.get("cpu_temp")
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
    
    def _format_big_value(self, value):
        """Format value for big display."""
        key = self.metric_meta["key"]
        if key in ("cpu_fan", "case_fans"):
            return f"{int(value)}"
        elif key in ("net_dn", "net_up"):
            return f"{value:.2f}"
        elif key in ("cpu_temp", "gpu_temp"):
            return f"{value:.1f}"
        elif isinstance(value, float) and value != int(value):
            return f"{value:.1f}"
        else:
            return f"{int(value)}"
    
    def _update_color(self, value):
        """Update color based on thresholds."""
        warn = self.metric_meta.get("warn")
        hot = self.metric_meta.get("hot")
        
        if warn and value is not None:
            if value >= hot:
                self.big_value.configure(fg=C["hot"])
            elif value >= warn:
                self.big_value.configure(fg=C["warn"])
            else:
                self.big_value.configure(fg=self.metric_meta["color"])
        else:
            self.big_value.configure(fg=self.metric_meta["color"])
    
    def _update_subtitle(self, data):
        """Update subtitle."""
        key = self.metric_meta["key"]
        if key in ("gpu", "gpu_temp", "vram"):
            self.subtitle.configure(text=data.get("gpu_name", ""))
        elif key == "cpu":
            self.subtitle.configure(text=data.get("cpu_name", ""))
        else:
            self.subtitle.configure(text="")
    
    def _update_stats(self, data):
        """Update statistics (override in subclasses)."""
        pass


class CPUView(PerformanceView):
    """CPU detailed view with per-core display."""
    
    def _build_stats(self):
        """Build CPU-specific stats."""
        super()._build_stats()

        # Per-core graph (pinned just above the stat cards)
        self.core_graph_frame = tk.Frame(
            self, bg=C["graph_bg"],
            highlightbackground=C["border"], highlightthickness=1
        )
        self.core_graph_frame.pack(side="bottom", fill="x", padx=20, pady=(0, 8))

        tk.Label(
            self.core_graph_frame, text="Cœurs logiques",
            font=("Segoe UI", 8, "bold"),
            bg=C["graph_bg"], fg=C["dim"]
        ).pack(anchor="w", padx=8, pady=(6, 2))

        self.core_graph = CoreBarGraph(
            self.core_graph_frame, self.metric_meta["color"], height=90
        )
        self.core_graph.pack(fill="both", expand=True, padx=4, pady=(0, 6))

        # Stat cards
        self._build_stat_grid([
            ("cores", "Cœurs"),
            ("freq", "Fréquence"),
            ("processes", "Processus"),
            ("threads_count", "Threads"),
            ("uptime_sys", "Uptime système"),
            ("uptime_app", "Session"),
        ], cols=4)

    def _update_stats(self, data):
        """Update CPU stats."""
        from metrics import fmt_duration
        logical = data.get("cpu_logical", 0)
        physical = data.get("cpu_physical", 0)
        freq = data.get("cpu_freq_cur", 0)
        b = self.stat_boxes
        b["cores"].set(f"{physical} / {logical}")
        b["freq"].set(f"{freq:.2f} GHz")
        b["processes"].set(str(data.get("process_count", "—")))
        b["threads_count"].set(str(data.get("thread_count", "—")))
        b["uptime_sys"].set(fmt_duration(data.get("uptime_sys", 0)))
        b["uptime_app"].set(fmt_duration(data.get("uptime_app", 0)))

        # Per-core graph
        self.core_graph.update(data.get("cpu_percore", []))


class MemoryView(PerformanceView):
    """Memory detailed view."""
    
    def _build_stats(self):
        """Build memory-specific stats."""
        super()._build_stats()
        self._build_stat_grid([
            ("used", "Utilisée"),
            ("available", "Disponible"),
            ("total", "Totale"),
            ("uptime", "Session"),
        ], cols=4)

    def _update_stats(self, data):
        """Update memory stats."""
        from metrics import fmt_duration
        b = self.stat_boxes
        b["used"].set(f"{data.get('memory_used_gb', 0):.1f} GB")
        b["available"].set(f"{data.get('memory_avail_gb', 0):.1f} GB")
        b["total"].set(f"{data.get('memory_total_gb', 0):.1f} GB")
        b["uptime"].set(fmt_duration(data.get("uptime_app", 0)))


class GPUView(PerformanceView):
    """GPU detailed view."""
    
    def _build_stats(self):
        """Build GPU-specific stats."""
        super()._build_stats()
        self._build_stat_grid([
            ("gpu_usage", "Utilisation"),
            ("gpu_temp", "Température"),
            ("vram_used", "VRAM utilisée"),
            ("vram_total", "VRAM totale"),
        ], cols=4)

    def _update_stats(self, data):
        """Update GPU stats."""
        b = self.stat_boxes
        b["gpu_usage"].set(f"{data.get('gpu_usage', 0):.0f} %")
        b["gpu_temp"].set(f"{data.get('gpu_temp', 0):.0f} °C")
        b["vram_used"].set(f"{data.get('vram_used_gb', 0):.1f} GB")
        b["vram_total"].set(f"{data.get('vram_total_gb', 0):.1f} GB")


class DiskView(PerformanceView):
    """Disk detailed view."""
    
    def _build_stats(self):
        """Build disk-specific stats."""
        super()._build_stats()
        self._build_stat_grid([
            ("used", "Utilisé"),
            ("available", "Libre"),
            ("total", "Total"),
        ], cols=3)

    def _update_stats(self, data):
        """Update disk stats."""
        drive = self.metric_meta["key"].replace("disk_", "")
        disks = data.get("_disks", {})
        dd = disks.get(drive)
        b = self.stat_boxes
        if dd:
            b["used"].set(f"{dd.get('used', 0):.1f} GB")
            b["available"].set(f"{dd.get('free', 0):.1f} GB")
            b["total"].set(f"{dd.get('total', 0):.1f} GB")


class NetworkView(PerformanceView):
    """Network detailed view."""
    
    def _build_stats(self):
        """Build network-specific stats."""
        super()._build_stats()
        self._build_stat_grid([
            ("download", "Téléchargement"),
            ("upload", "Envoi"),
        ], cols=2)

    def _update_stats(self, data):
        """Update network stats."""
        b = self.stat_boxes
        b["download"].set(f"{data.get('download_speed', 0):.2f} MB/s")
        b["upload"].set(f"{data.get('upload_speed', 0):.2f} MB/s")


def create_performance_view(parent, metric_meta):
    """Factory function to create appropriate performance view."""
    key = metric_meta["key"]
    
    if key == "cpu":
        return CPUView(parent, metric_meta)
    elif key == "ram":
        return MemoryView(parent, metric_meta)
    elif key in ("gpu", "gpu_temp", "vram"):
        return GPUView(parent, metric_meta)
    elif key.startswith("disk_"):
        return DiskView(parent, metric_meta)
    elif key in ("net_dn", "net_up"):
        return NetworkView(parent, metric_meta)
    else:
        return PerformanceView(parent, metric_meta)
