"""
Reusable UI widgets with dark theme styling.
"""
import tkinter as tk
from tkinter import ttk
import sys
import os

# Add project root and base/ to path for imports
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "base"))

from config import C, T


def setup_dark_theme(root):
    """Configure dark theme for the application with proper combobox styling."""
    # Global options for combobox dropdown
    root.option_add("*TCombobox*Listbox*background", C["surface"])
    root.option_add("*TCombobox*Listbox*foreground", C["fg"])
    root.option_add("*TCombobox*Listbox*selectBackground", C["acc"])
    root.option_add("*TCombobox*Listbox*selectForeground", "#ffffff")
    root.option_add("*TCombobox*Listbox*font", ("Segoe UI", 9))
    root.option_add("*TCombobox*Listbox*borderWidth", 0)
    root.option_add("*TCombobox*Listbox*relief", "flat")
    
    # Menu styling
    root.option_add("*Menu*background", C["surface"])
    root.option_add("*Menu*foreground", C["fg"])
    root.option_add("*Menu*activeBackground", C["acc"])
    root.option_add("*Menu*activeForeground", "#ffffff")
    root.option_add("*Menu*borderWidth", 0)
    root.option_add("*Menu*relief", "flat")
    
    style = ttk.Style()
    style.theme_use("default")
    
    # Combobox dark theme
    style.configure("Dark.TCombobox",
                   fieldbackground=C["surface"],
                   background=C["surface"],
                   foreground=C["fg"],
                   selectbackground=C["acc"],
                   selectforeground="#ffffff",
                   arrowcolor=C["fg"],
                   bordercolor=C["border"],
                   lightcolor=C["border"],
                   darkcolor=C["border"],
                   relief="flat",
                   borderwidth=1)
    
    style.map("Dark.TCombobox",
              selectbackground=[("focus", C["acc"]), ("!focus", C["acc"])],
              fieldbackground=[("focus", C["surface"]), ("!focus", C["surface"])],
              foreground=[("focus", C["fg"]), ("!focus", C["fg"])])
    
    # Scale dark theme
    style.configure("Dark.Horizontal.TScale",
                   background=C["surface2"],
                   troughcolor=C["dim"],
                   bordercolor=C["border"],
                   lightcolor=C["border"],
                   darkcolor=C["border"])


class DarkCheckbox(tk.Label):
    """Custom checkbox with dark theme."""
    
    def __init__(self, parent, variable, on_change=None, **kwargs):
        self.var = variable
        self.on_change = on_change
        super().__init__(parent, font=("Segoe UI", 10),
                        bg=kwargs.get("bg", C["surface2"]),
                        fg=C["acc"], cursor="hand2", padx=8, **kwargs)
        self.config(text="☑" if self.var.get() else "☐")
        self.bind("<Button-1>", self._toggle)
        self._update()
    
    def _toggle(self, event=None):
        self.var.set(not self.var.get())
        self._update()
        if self.on_change:
            self.on_change()
    
    def _update(self, *args):
        self.config(text="☑" if self.var.get() else "☐",
                   fg=C["acc"] if self.var.get() else C["mid"])


class DarkCombobox(ttk.Combobox):
    """Dark themed combobox."""
    
    def __init__(self, parent, variable, values, width=10, **kwargs):
        super().__init__(parent, textvariable=variable, values=values,
                        width=width, state="readonly", style="Dark.TCombobox",
                        **kwargs)


class DarkScale(tk.Scale):
    """Dark themed scale."""
    
    def __init__(self, parent, variable, from_, to, resolution, **kwargs):
        super().__init__(parent, from_=from_, to=to, resolution=resolution,
                        orient="horizontal", variable=variable,
                        bg=C["surface2"], fg=C["fg"], troughcolor=C["dim"],
                        highlightthickness=0, activebackground=C["acc"],
                        length=160, sliderlength=14, **kwargs)


class DarkEntry(tk.Entry):
    """Dark themed entry."""
    
    def __init__(self, parent, variable, width=7, **kwargs):
        super().__init__(parent, textvariable=variable, width=width,
                        bg=C["surface"], fg=C["fg"], insertbackground=C["fg"],
                        relief="flat", bd=6,
                        highlightbackground=C["border"], highlightthickness=1,
                        **kwargs)


class ThinScrollbar(tk.Canvas):
    """A slim, modern scrollbar: grey rounded thumb, no trough background.

    Matches the parent background so only the thumb is visible. The thumb
    auto-hides when all content fits, brightens on hover, and is draggable.
    """

    WIDTH = 8
    PAD = 2

    def __init__(self, parent, command, bg, **kwargs):
        super().__init__(parent, width=self.WIDTH, bg=bg,
                         highlightthickness=0, bd=0, **kwargs)
        self._command = command          # canvas.yview
        self._first = 0.0
        self._last = 1.0
        self._thumb = None
        self._drag_offset = 0
        self._hover = False
        self._color = C["dim"]
        self._color_hover = C["muted"]

        self.bind("<Configure>", lambda e: self._redraw())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)

    def set(self, first, last):
        """yscrollcommand callback."""
        self._first = float(first)
        self._last = float(last)
        self._redraw()

    def _visible(self):
        return not (self._first <= 0.0 and self._last >= 1.0)

    def _redraw(self):
        self.delete("all")
        self._thumb = None
        if not self._visible():
            return
        h = self.winfo_height()
        w = self.WIDTH
        if h < 4:
            return
        y0 = self.PAD + self._first * (h - 2 * self.PAD)
        y1 = self.PAD + self._last * (h - 2 * self.PAD)
        if y1 - y0 < 16:
            y1 = y0 + 16
        color = self._color_hover if self._hover else self._color
        self._thumb = self._round_rect(self.PAD, y0, w - self.PAD, y1,
                                       r=(w - 2 * self.PAD) / 2, fill=color)

    def _round_rect(self, x0, y0, x1, y1, r, **kw):
        r = min(r, (x1 - x0) / 2, (y1 - y0) / 2)
        pts = [
            x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r,
            x1, y1 - r, x1, y1, x1 - r, y1, x0 + r, y1,
            x0, y1, x0, y1 - r, x0, y0 + r, x0, y0,
        ]
        return self.create_polygon(pts, smooth=True, **kw)

    def _on_enter(self, _e):
        self._hover = True
        self._redraw()

    def _on_leave(self, _e):
        self._hover = False
        self._redraw()

    def _on_press(self, e):
        h = self.winfo_height()
        if h <= 0:
            return
        frac = max(0.0, min(1.0, e.y / h))
        # Center the thumb on click position.
        span = self._last - self._first
        target = max(0.0, min(1.0 - span, frac - span / 2))
        self._command("moveto", target)

    def _on_drag(self, e):
        h = self.winfo_height()
        if h <= 0:
            return
        frac = max(0.0, min(1.0, e.y / h))
        span = self._last - self._first
        target = max(0.0, min(1.0 - span, frac - span / 2))
        self._command("moveto", target)


class ScrollableFrame(tk.Frame):
    """A frame with a slim modern scrollbar that works with the global wheel."""

    def __init__(self, parent, bg=C["bg"], **kwargs):
        super().__init__(parent, bg=bg, **kwargs)

        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.scrollbar = ThinScrollbar(self, command=self.canvas.yview, bg=bg)

        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side="right", fill="y", padx=(0, 2))
        self.canvas.pack(side="left", fill="both", expand=True)

        self.content = tk.Frame(self.canvas, bg=bg)
        self.window = self.canvas.create_window((0, 0), window=self.content,
                                                anchor="nw")

        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.content.bind("<Configure>", self._on_content_configure)

        # Local wheel binding (global handler in App also covers this).
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-4>", self._on_mousewheel)
        self.canvas.bind("<Button-5>", self._on_mousewheel)

    def _on_canvas_configure(self, event):
        """Handle canvas resize."""
        self.canvas.itemconfig(self.window, width=event.width)

    def _on_content_configure(self, event):
        """Handle content resize."""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_mousewheel(self, event):
        """Handle mouse wheel scroll."""
        if event.num == 4 or event.delta > 0:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5 or event.delta < 0:
            self.canvas.yview_scroll(1, "units")

    def pack(self, **kwargs):
        """Override pack to trigger update."""
        super().pack(**kwargs)
        self.content.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))


class SectionHeader(tk.Frame):
    """Section header with title and separator."""
    
    def __init__(self, parent, text, bg=C["bg"], **kwargs):
        super().__init__(parent, bg=bg, **kwargs)
        
        self.pack(fill="x", pady=(18, 4), padx=24)
        
        tk.Label(self, text=text, font=("Segoe UI", 8, "bold"),
                bg=bg, fg=C["dim"]).pack(side="left")
        
        tk.Frame(parent, bg=C["border"], height=1).pack(fill="x", padx=24)


class SettingRow(tk.Frame):
    """A row for a setting with label and widget."""
    
    def __init__(self, parent, label, widget_fn, bg=C["surface2"], **kwargs):
        super().__init__(parent, bg=bg,
                       highlightbackground=C["border"], highlightthickness=1,
                       **kwargs)
        
        self.pack(fill="x", pady=1, padx=24)
        
        tk.Label(self, text=label, font=("Segoe UI", 9), bg=bg, fg=C["fg"],
                width=32, anchor="w").pack(side="left", padx=14, pady=9)
        
        widget_fn(self)


class InfoRow(tk.Frame):
    """Info row with background and border."""
    
    def __init__(self, parent, bg=C["surface"], **kwargs):
        super().__init__(parent, bg=bg,
                       highlightbackground=C["border2"], highlightthickness=1,
                       **kwargs)
        self.pack(fill="x", pady=4, padx=24)


class MetricLabel(tk.Label):
    """Label for metric values with color coding."""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, font=("Segoe UI", 9),
                        bg=kwargs.get("bg", C["panel_bg"]),
                        fg=kwargs.get("fg", C["fg"]),
                        **kwargs)


class BigValueLabel(tk.Label):
    """Large label for main metric value."""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, font=("Segoe UI", 32, "bold"),
                        bg=kwargs.get("bg", C["panel_bg"]),
                        fg=kwargs.get("fg", C["fg"]),
                        **kwargs)


class UnitLabel(tk.Label):
    """Label for unit."""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, font=("Segoe UI", 14),
                        bg=kwargs.get("bg", C["panel_bg"]),
                        fg=kwargs.get("fg", C["mid"]),
                        **kwargs)


class SubtitleLabel(tk.Label):
    """Label for subtitle (e.g., GPU name)."""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, font=("Segoe UI", 9),
                        bg=kwargs.get("bg", C["panel_bg"]),
                        fg=kwargs.get("fg", C["mid"]),
                        **kwargs)


class StatLabel(tk.Label):
    """Label for statistics."""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, font=("Segoe UI", 9),
                        bg=kwargs.get("bg", C["panel_bg"]),
                        fg=kwargs.get("fg", C["fg"]),
                        **kwargs)


class StatBox(tk.Frame):
    """A bordered card showing a titled statistic for a clean Task-Manager look."""

    def __init__(self, parent, title, **kwargs):
        super().__init__(parent, bg=C["surface"],
                         highlightbackground=C["border"], highlightthickness=1,
                         **kwargs)
        tk.Label(self, text=title.upper(), font=("Segoe UI", 7, "bold"),
                 bg=C["surface"], fg=C["dim"], anchor="w").pack(
                     anchor="w", padx=10, pady=(7, 0))
        self._value = tk.Label(self, text="—", font=("Segoe UI", 12, "bold"),
                               bg=C["surface"], fg=C["fg_hi"], anchor="w")
        self._value.pack(anchor="w", padx=10, pady=(1, 7))

    def set(self, text, fg=None):
        """Update the value text (and optionally its color)."""
        self._value.configure(text=text)
        if fg:
            self._value.configure(fg=fg)
