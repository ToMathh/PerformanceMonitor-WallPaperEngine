"""
Fluid graphs with incremental updates (no full redraw).
Optimized for minimal CPU usage and anti-flicker.
"""
import tkinter as tk
import sys
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "base"))

from config import C


def _hex_to_rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def blend(fg, bg, alpha):
    """Return a solid hex color = fg over bg at the given alpha (0..1).

    Tkinter does not support RGBA colors, so we pre-blend to emulate the
    translucent area fill under the curve.
    """
    try:
        fr, fgc, fb = _hex_to_rgb(fg)
        br, bgc, bb = _hex_to_rgb(bg)
        r = round(fr * alpha + br * (1 - alpha))
        g = round(fgc * alpha + bgc * (1 - alpha))
        b = round(fb * alpha + bb * (1 - alpha))
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception:
        return fg


class MiniGraph(tk.Canvas):
    """Mini graph for sidebar with incremental updates."""
    
    def __init__(self, parent, key, color, **kwargs):
        bg = kwargs.pop("bg", C["sidebar_bg"])
        super().__init__(parent, bg=bg,
                        width=55, height=35, highlightthickness=0,
                        **kwargs)
        self.key = key
        self.color = color
        self._bg = bg
        self._fill = blend(color, bg, 0.22)
        self.history = []
        self._poly_id = None
        self._line_id = None
        self._dot_id = None
        self._last_pts = []
        self.bind("<Configure>", self._on_resize)

    def _on_resize(self, _e):
        # Debounce: wait 60ms after last resize event before redrawing
        if hasattr(self, "_resize_id"):
            self.after_cancel(self._resize_id)
        self._resize_id = self.after(60, self._do_resize)

    def _do_resize(self):
        self._last_pts = []
        if self.history:
            self.update(self.history)

    def update(self, history):
        """Update graph incrementally using coords() to avoid delete+recreate."""
        if not history or len(history) < 2:
            return

        self.history = list(history)

        try:
            cw = self.winfo_width()
            ch = self.winfo_height()
        except Exception:
            cw, ch = 55, 35

        if cw < 4 or ch < 4:
            return

        top = 100.0
        n = len(self.history)
        step = cw / max(n - 1, 1)
        pts = []
        for i, v in enumerate(self.history):
            x = i * step
            y = ch - 2 - (min(v, top) / top) * (ch - 4)
            pts.append((max(0, x), max(1, min(ch - 1, y))))

        # Skip if nothing changed
        if len(pts) == len(self._last_pts):
            changed = any(
                abs(p1[0] - p2[0]) > 0.5 or abs(p1[1] - p2[1]) > 0.5
                for p1, p2 in zip(pts, self._last_pts)
            )
            if not changed:
                return
        self._last_pts = pts

        # Update or create polygon (fill area)
        if len(pts) >= 2:
            poly = [(0, ch)] + pts + [(pts[-1][0], ch)]
            flat = [c for p in poly for c in p]
            if self._poly_id:
                self.coords(self._poly_id, flat)
            else:
                self._poly_id = self.create_polygon(flat, fill=self._fill, outline="")

        # Update or create line
        if len(pts) >= 2:
            flat = [c for p in pts for c in p]
            if self._line_id:
                self.coords(self._line_id, flat)
            else:
                self._line_id = self.create_line(flat, fill=self.color, width=1, smooth=True)

        # Update or create dot
        if pts:
            lx, ly = pts[-1]
            if self._dot_id:
                self.coords(self._dot_id, lx - 2, ly - 2, lx + 2, ly + 2)
            else:
                self._dot_id = self.create_oval(lx - 2, ly - 2, lx + 2, ly + 2,
                                                fill=self.color, outline="")


class MainGraph(tk.Canvas):
    """Main graph with incremental updates and grid."""
    
    def __init__(self, parent, key, color, **kwargs):
        bg = kwargs.pop("bg", C["graph_bg"])
        super().__init__(parent, bg=bg,
                        highlightthickness=0, **kwargs)
        self.key = key
        self.color = color
        self._bg = bg
        self._fill = blend(color, bg, 0.16)
        self.history = []
        self._meta = {}
        self._poly_id = None
        self._line_id = None
        self._dot_id = None
        self._dot_outline_id = None
        self._grid_ids = []
        self._scale_label_id = None
        self._last_pts = []
        self._last_top = None
        self.bind("<Configure>", self._on_resize)

    def _on_resize(self, _e):
        # Debounce: wait 60ms after last resize event before redrawing
        if hasattr(self, "_resize_id"):
            self.after_cancel(self._resize_id)
        self._resize_id = self.after(60, self._do_resize)

    def _do_resize(self):
        self._last_pts = []
        self._last_top = None
        if self.history:
            self.update(self.history, self._meta)

    def update(self, history, metric_meta):
        """Update graph incrementally."""
        if not history:
            return
        self._meta = metric_meta or {}

        try:
            cw = self.winfo_width()
            ch = self.winfo_height()
        except Exception:
            return

        if cw < 8 or ch < 8:
            return

        # Cap the number of plotted points to keep redraws cheap and fluid.
        # One point every ~3 px is visually indistinguishable from denser data
        # and keeps the smoothed line cheap to render.
        history = list(history)
        max_pts = max(2, min(len(history), int(cw) // 3, 180))
        if len(history) > max_pts:
            step_i = len(history) / max_pts
            history = [history[int(i * step_i)] for i in range(max_pts)]
        self.history = history
        
        # Determine scale
        if metric_meta.get("dynamic"):
            top = max(max(history), 1)
            for cap in (1, 5, 10, 50, 100, 500, 1000, 5000):
                if top <= cap:
                    top = cap
                    break
        else:
            top = metric_meta.get("max") or 100
        
        # Only redraw grid if scale changed
        if top != self._last_top:
            self._draw_grid(cw, ch, top)
            self._last_top = top
        
        # Calculate points
        n = len(history)
        step = cw / max(n - 1, 1)
        pad = 8
        draw_h = ch - pad * 2
        pts = []
        for i, v in enumerate(history):
            x = i * step
            y = pad + draw_h - (min(v, top) / top) * draw_h
            pts.append((max(0, x), max(pad, min(ch - pad, y))))
        
        # Only redraw if points changed significantly
        if len(pts) == len(self._last_pts):
            changed = False
            for i, (p1, p2) in enumerate(zip(pts, self._last_pts)):
                if abs(p1[0] - p2[0]) > 1 or abs(p1[1] - p2[1]) > 1:
                    changed = True
                    break
            if not changed:
                return
        
        self._last_pts = pts

        # Update or create polygon (fill area) using coords() - no delete needed
        if len(pts) >= 2:
            poly = [(0, ch)] + pts + [(pts[-1][0], ch)]
            flat = [c for p in poly for c in p]
            if len(flat) >= 6:
                if self._poly_id:
                    self.coords(self._poly_id, flat)
                else:
                    self._poly_id = self.create_polygon(flat, fill=self._fill, outline="")

        # Update or create line
        if len(pts) >= 2:
            flat = [c for p in pts for c in p]
            if self._line_id:
                self.coords(self._line_id, flat)
            else:
                self._line_id = self.create_line(
                    flat, fill=self.color, width=2, smooth=True,
                    joinstyle="round", capstyle="round"
                )

        # Update or create dots
        if pts:
            lx, ly = pts[-1]
            if self._dot_outline_id:
                self.coords(self._dot_outline_id, lx - 5, ly - 5, lx + 5, ly + 5)
            else:
                self._dot_outline_id = self.create_oval(
                    lx - 5, ly - 5, lx + 5, ly + 5, fill="", outline=self.color, width=1
                )
            if self._dot_id:
                self.coords(self._dot_id, lx - 3, ly - 3, lx + 3, ly + 3)
            else:
                self._dot_id = self.create_oval(lx - 3, ly - 3, lx + 3, ly + 3,
                                                fill=self.color, outline="")

        # Update scale label if dynamic
        if metric_meta.get("dynamic"):
            if self._scale_label_id:
                self.itemconfig(self._scale_label_id, text=f"{int(top)}")
                self.coords(self._scale_label_id, cw - 4, pad + 2)
            else:
                self._scale_label_id = self.create_text(
                    cw - 4, pad + 2, text=f"{int(top)}", anchor="ne",
                    fill=C["dim"], font=("Consolas", 7)
                )
    
    def _draw_grid(self, cw, ch, top):
        """Draw grid lines."""
        # Delete old grid
        for gid in self._grid_ids:
            self.delete(gid)
        self._grid_ids = []
        
        # Draw horizontal grid lines
        for pct in (25, 50, 75):
            y = ch - (pct / 100) * ch
            gid = self.create_line(0, y, cw, y, fill=C["grid"], dash=(2, 8))
            self._grid_ids.append(gid)


class CoreBarGraph(tk.Canvas):
    """Bar graph for CPU cores."""
    
    def __init__(self, parent, color, **kwargs):
        bg = kwargs.pop("bg", C["panel_bg"])
        super().__init__(parent, bg=bg,
                        highlightthickness=0, **kwargs)
        self.color = color
        self._bar_ids = []
        self._label_ids = []
    
    def update(self, percore):
        """Update core bars."""
        if not percore:
            return
        
        self.delete("all")
        self._bar_ids = []
        self._label_ids = []
        
        try:
            cw = self.winfo_width()
            ch = self.winfo_height()
        except Exception:
            return
        
        if cw < 10 or ch < 10:
            return
        
        n = len(percore)
        if n == 0:
            return
        
        bar_width = (cw - 20) / n - 4
        max_height = ch - 20
        
        for i, val in enumerate(percore):
            x = 10 + i * (bar_width + 4)
            h = (val / 100) * max_height
            y = ch - 10 - h
            
            # Bar
            bar_id = self.create_rectangle(
                x, y, x + bar_width, ch - 10,
                fill=self.color, outline=""
            )
            self._bar_ids.append(bar_id)
            
            # Label
            if bar_width > 15:
                label_id = self.create_text(
                    x + bar_width / 2, ch - 5,
                    text=f"{int(val)}",
                    fill=C["fg"], font=("Segoe UI", 7)
                )
                self._label_ids.append(label_id)
