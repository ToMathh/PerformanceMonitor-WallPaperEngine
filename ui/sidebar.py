"""
Sidebar component - Task Manager style.
Displays metrics with name, percentage, and mini graph.
"""
import tkinter as tk
import sys
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "base"))

from config import C
from ui.graphs import MiniGraph
from metrics import fmt_val


class SidebarItem(tk.Frame):
    """Single sidebar item with metric info and mini graph."""
    
    def __init__(self, parent, metric, on_select, is_selected=False, **kwargs):
        self.metric = metric
        self.on_select = on_select
        self.is_selected = is_selected
        
        bg = C["sidebar_sel"] if is_selected else C["sidebar_bg"]
        super().__init__(parent, bg=bg, cursor="hand2", height=52, **kwargs)
        self.pack(fill="x", pady=1, padx=0)
        self.pack_propagate(False)
        
        # Color indicator
        self.indicator = tk.Frame(
            self, bg=metric["color"] if is_selected else C["sidebar_bg"],
            width=3
        )
        self.indicator.pack(side="left", fill="y")
        
        # Mini graph (hidden for summary/general metric)
        if metric.get("is_summary"):
            self.mini_graph = tk.Label(
                self, text="≡", font=("Segoe UI", 14),
                bg=bg, fg=metric["color"], width=4
            )
        else:
            self.mini_graph = MiniGraph(
                self, metric["key"], metric["color"],
                bg=bg
            )
        self.mini_graph.pack(side="left", padx=(6, 0), pady=8)

        # Info frame
        self.info_frame = tk.Frame(self, bg=bg)
        self.info_frame.pack(side="left", fill="both", expand=True, padx=8)
        
        # Label
        self.label = tk.Label(
            self.info_frame, text=metric["label"],
            font=("Segoe UI", 8, "bold"),
            bg=bg, fg=C["fg"] if is_selected else C["muted"],
            anchor="w"
        )
        self.label.pack(anchor="w")
        
        # Value
        self.value_label = tk.Label(
            self.info_frame, text="—",
            font=("Segoe UI", 8),
            bg=bg, fg=metric["color"] if is_selected else C["dim"],
            anchor="w"
        )
        self.value_label.pack(anchor="w")

        # Pre-built widget list used by _bind_events and update_selection
        self._all_widgets = [self, self.mini_graph, self.info_frame,
                             self.label, self.value_label]

        # Bind events
        self._bind_events()
    
    def _bind_events(self):
        """Bind mouse events once at construction time.
        Handlers read self.is_selected dynamically, so no rebinding is needed.
        """
        def on_click(e):
            self.on_select(self.metric["key"])

        def on_enter(e):
            if not self.is_selected:
                for w in self._all_widgets:
                    w.configure(bg=C["sidebar_hov"])

        def on_leave(e):
            bg = C["sidebar_sel"] if self.is_selected else C["sidebar_bg"]
            for w in self._all_widgets:
                w.configure(bg=bg)

        for widget in self._all_widgets:
            widget.bind("<Button-1>", on_click)
            widget.bind("<Enter>",    on_enter)
            widget.bind("<Leave>",    on_leave)
    
    def update_selection(self, is_selected):
        """Update selection state (no rebinding – handlers are already dynamic)."""
        self.is_selected = is_selected
        bg = C["sidebar_sel"] if is_selected else C["sidebar_bg"]
        for w in self._all_widgets:
            w.configure(bg=bg)
        self.indicator.configure(bg=self.metric["color"] if is_selected else bg)
        self.label.configure(bg=bg, fg=C["fg"] if is_selected else C["muted"])
        self.value_label.configure(bg=bg, fg=self.metric["color"] if is_selected else C["dim"])
    
    def update_value(self, value):
        """Update value display."""
        if value is None:
            self.value_label.configure(text="—")
        else:
            self.value_label.configure(text=value)
    
    def update_graph(self, history):
        """Update mini graph (no-op for summary metrics)."""
        if self.metric.get("is_summary"):
            return
        self.mini_graph.update(history)


class Sidebar(tk.Frame):
    """Sidebar component with scrollable list of metrics."""
    
    def __init__(self, parent, metrics, on_select, selected_key, app=None, **kwargs):
        self.metrics = metrics
        self.on_select = on_select
        self.selected_key = selected_key
        self.items = {}
        self.app = app
        
        super().__init__(parent, bg=C["sidebar_bg"], **kwargs)
        self.pack(side="left", fill="y", padx=(0, 1))
        
        # Header
        header = tk.Frame(self, bg=C["sidebar_bg"])
        header.pack(fill="x", pady=(8, 4), padx=8)
        
        tk.Label(
            header, text="RESSOURCES",
            font=("Segoe UI", 7, "bold"),
            bg=C["sidebar_bg"], fg=C["dim"]
        ).pack(side="left")
        
        # Scrollable container
        from ui.widgets import ScrollableFrame
        self.scroll_frame = ScrollableFrame(self, bg=C["sidebar_bg"])
        self.scroll_frame.pack(fill="both", expand=True)
        
        # Register scroll target
        if self.app:
            self.app.register_scroll_target(self.scroll_frame.canvas)
        
        # Build items
        self._build_items()
    
    def _build_items(self):
        """Build sidebar items."""
        for metric in self.metrics:
            item = SidebarItem(
                self.scroll_frame.content,
                metric,
                self.on_select,
                is_selected=(metric["key"] == self.selected_key)
            )
            item.pack(fill="x")
            self.items[metric["key"]] = item
        
        self.scroll_frame.content.update_idletasks()
        self.scroll_frame.canvas.configure(
            scrollregion=self.scroll_frame.canvas.bbox("all")
        )
    
    def update_selection(self, key):
        """Update selection for all items."""
        self.selected_key = key
        for metric_key, item in self.items.items():
            item.update_selection(metric_key == key)
    
    def update_values(self, data):
        """Update all values."""
        for metric_key, item in self.items.items():
            if metric_key == "general":
                continue
            value = self._extract_value(metric_key, data)
            item.update_value(value)
    
    def update_graphs(self, histories):
        """Update all graphs."""
        for metric_key, item in self.items.items():
            history = histories.get(metric_key)
            if history:
                item.update_graph(history)
    
    def _extract_value(self, key, data):
        """Extract value from data."""
        if key == "cpu":
            v = data.get("cpu")
            return f"{v:.1f}%" if v is not None else "—"
        elif key == "cpu_temp":
            v = data.get("cpu_temp")
            return f"{v:.1f}°" if v is not None else "—"
        elif key == "ram":
            v = data.get("memory")
            return f"{v:.1f}%" if v is not None else "—"
        elif key == "gpu":
            v = data.get("gpu_usage")
            return f"{v:.1f}%" if v is not None else "—"
        elif key == "gpu_temp":
            v = data.get("gpu_temp")
            return f"{v:.1f}°" if v is not None else "—"
        elif key == "vram":
            v = data.get("vram_usage")
            return f"{v:.1f}%" if v is not None else "—"
        elif key == "net_dn":
            v = data.get("download_speed")
            return f"{v:.2f} MB/s" if v is not None else "—"
        elif key == "net_up":
            v = data.get("upload_speed")
            return f"{v:.2f} MB/s" if v is not None else "—"
        elif key == "cpu_fan":
            v = data.get("cpu_fan")
            return f"{int(v)} RPM" if v is not None else "—"
        elif key == "case_fans":
            v = data.get("case_fans")
            return f"{int(v)} RPM" if v is not None else "—"
        elif key.startswith("disk_"):
            drive = key.replace("disk_", "")
            disks = data.get("_disks", {})
            if drive in disks:
                v = disks[drive].get("pct")
                return f"{v:.1f}%" if v is not None else "—"
        return "—"
    
    def rebuild(self, metrics, selected_key):
        """Rebuild sidebar with new metrics."""
        # Clear existing
        for item in self.items.values():
            item.destroy()
        self.items.clear()
        
        self.metrics = metrics
        self.selected_key = selected_key
        
        self._build_items()
